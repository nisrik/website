#!/usr/bin/env python3
"""Builds the whole site from the markdown files in content/.

    python3 build/build.py          (run from the project root; standard library only)

  content/inquiry.md                the Inquiry page title + intro
  content/<section>/_section.md     one folder per section on the Inquiry page
  content/<section>/*.md            one file per entry (paper, course, essay, ...)

Writes: index.html, essays/<slug>.html, teaching/<slug>.html. See README.md.
GitHub Actions runs this on every push (.github/workflows/pages.yml), so adding a file is all you do.
"""
import html, os, re, sys, shutil, struct
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
C = "content"
esc = html.escape

# ------------------------------------------------------------------ tiny front-matter + markdown
def parse_file(path):
    t = open(path, encoding="utf8").read().replace("\r\n", "\n")
    fm, body = {}, t
    if t.startswith("---\n"):
        end = t.find("\n---", 4)
        if end != -1:
            for line in t[4:end].split("\n"):
                if not line.strip() or line.lstrip().startswith("#") or ":" not in line: continue
                k, v = line.split(":", 1); fm[k.strip()] = value(v.strip())
            body = t[end + 4:].lstrip("\n")
    return fm, body.strip("\n")

def value(v):
    if v.startswith("[") and v.endswith("]"): return [x.strip().strip("\"'") for x in v[1:-1].split(",") if x.strip()]
    if len(v) > 1 and v[0] == v[-1] and v[0] in "\"'": return v[1:-1]
    if v.lower() in ("true", "yes"): return True
    if v.lower() in ("false", "no"): return False
    return v

def num(v, d=999):
    try: return float(v)
    except Exception: return d

def link(u):
    ext = re.match(r"https?://", u or "")
    return 'href="%s"%s' % (esc(u, quote=True), ' target="_blank" rel="noopener"' if ext else "")

def inline(s, breaks=False):
    s = esc(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", lambda m: "<a %s>%s</a>" % (link(html.unescape(m.group(2))), m.group(1)), s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*([^*]+?)\*(?!\w)", r"<em>\1</em>", s)
    s = s.replace("&lt;br&gt;", "<br>")
    s = re.sub(r"(  |\\)\n", "<br>", s)
    if breaks: s = s.replace("\n", "<br>")
    else: s = s.replace("\n", " ")
    return s.strip()

def slugify(t): return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")

def blocks(body):
    """split markdown into simple blocks: (kind, data)"""
    out, lines, i = [], body.split("\n"), 0
    while i < len(lines):
        ln = lines[i]
        if not ln.strip(): i += 1; continue
        m = re.match(r"(#{2,3})\s+(.*)", ln)
        if m: out.append(("h" + str(len(m.group(1))), m.group(2).strip())); i += 1; continue
        if ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"): rows.append(lines[i]); i += 1
            cols = None
            if i < len(lines) and lines[i].startswith("{cols:"): cols = lines[i][6:].strip(" }"); i += 1
            cells = [[c.strip() for c in re.split(r"(?<!\\)\|", r.strip()[1:-1])] for r in rows if not re.match(r"^\|[\s:|-]+\|$", r)]
            cells = [[c.replace("\\|", "|") for c in r] for r in cells]
            out.append(("table", (cells, cols))); continue
        if re.match(r"\s*[-*]\s+", ln) or re.match(r"\s*\d+\.\s+", ln):
            ordered = bool(re.match(r"\s*\d+\.", ln)); items = []
            while i < len(lines) and re.match(r"\s*([-*]|\d+\.)\s+", lines[i]):
                items.append(re.sub(r"^\s*([-*]|\d+\.)\s+", "", lines[i])); i += 1
            out.append(("ol" if ordered else "ul", items)); continue
        if i + 1 < len(lines) and lines[i + 1].startswith(": "):
            defs = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(": "):
                term = lines[i].strip(); i += 1; dd = []
                while i < len(lines) and lines[i].startswith(": "): dd.append(lines[i][2:].strip()); i += 1
                defs.append((term, dd))
                while i < len(lines) and not lines[i].strip(): i += 1
                if not (i + 1 < len(lines) and lines[i + 1].startswith(": ")): break
            out.append(("dl", defs)); continue
        if ln.startswith(">"):
            q = []
            while i < len(lines) and lines[i].startswith(">"): q.append(lines[i].lstrip("> ")); i += 1
            out.append(("quote", " ".join(q))); continue
        if re.match(r"!\[[^\]]*\]\([^)]+\)\s*$", ln):
            m = re.match(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"([^\"]*)\")?\)", ln); out.append(("img", (m.group(1), m.group(2), m.group(3) or ""))); i += 1; continue
        para = []
        while i < len(lines) and lines[i].strip() and not re.match(r"(#{2,3}\s|\||>|!\[)", lines[i]) and not (re.match(r"\s*([-*]|\d+\.)\s+", lines[i])):
            if i + 1 < len(lines) and lines[i + 1].startswith(": ") and para: break
            para.append(lines[i]); i += 1
        out.append(("p", "\n".join(para)))
    return out

# ------------------------------------------------------------------ path handling for pages in subfolders
def up(s, depth):
    if not depth: return s
    return re.sub(r'(src|href)="(?!https?:|mailto:|#|\.\./)([^"]+)"', lambda m: '%s="%s%s"' % (m.group(1), "../" * depth, m.group(2)), s)

def rel(p, depth): return p if re.match(r"(https?:|mailto:|#|\.\./)", p or "") else "../" * depth + p

HEADER = open("build/partials/header.html", encoding="utf8").read().strip()
FOOTER = open("build/partials/footer.html", encoding="utf8").read().strip()

def page(title, desc, depth, main, scripts, current="inquiry.html", body_class=""):
    d = "../" * depth
    hdr = re.sub(r'(<a href="%s")' % re.escape(current), r'\1 aria-current="page"', HEADER)
    sc = "\n".join('<script src="%sjs/%s.js"></script>' % (d, s) for s in scripts)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} — None More Blue</title>
<meta name="description" content="{esc(desc, quote=True)}">
<link rel="icon" href="{d}images/logo/nmb-black.png">
<script>(function(){{var t;try{{t=localStorage.getItem('theme')}}catch(e){{}}if(t!=='light'&&t!=='dark'){{var m=/nmbtheme=(light|dark)/.exec(window.name);t=m&&m[1]}}if(t==='light'||t==='dark')document.documentElement.setAttribute('data-theme',t)}})()</script>
<link rel="stylesheet" href="{d}css/fonts.css">
<link rel="stylesheet" href="{d}css/site.css">
<link rel="stylesheet" href="{d}css/course.css">
</head>
<body{(' class="%s"' % body_class) if body_class else ''}>
{up(hdr, depth)}
{main}
{up(FOOTER, depth)}
{sc}
</body>
</html>
"""

# ------------------------------------------------------------------ dates / terms
MONTHS = "January February March April May June July August September October November December".split()
def nice_date(s):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(s))
    if not m: return str(s)
    return "%d %s %s" % (int(m.group(3)), MONTHS[int(m.group(2)) - 1], m.group(1))
SEASON = {"winter": 0, "spring": 1, "summer": 2, "fall": 3, "autumn": 3}
def term_key(t):
    m = re.match(r"(\w+)\s+(\d{4})", t or "")
    return (int(m.group(2)) * 10 + SEASON.get(m.group(1).lower(), 0)) if m else 0

# ------------------------------------------------------------------ course / essay body -> html
def cell_html(c):
    if re.fullmatch(r"\[[^\]]+\]\([^)\s]+\)", c.strip()): return [c.strip()]   # one link: keep it whole, even across a <br>
    parts = [p.strip() for p in re.split(r"<br>", c, flags=re.I) if p.strip()]
    return parts

def render_table(cells, cols):
    head, rows = cells[0], cells[1:]
    n = len(head)
    if head[0].lower() == "week":
        grid = cols or "3.5rem " + " ".join(["1fr"] * (n - 1))
        o = ['<div class="tbl" style="--cols:%s">' % esc(grid)]
        o.append('<div class="r head meta">%s</div>' % "".join("<div>%s</div>" % inline(h) for h in head))
        for r in rows:
            cs = []
            for i, c in enumerate(r):
                vals = cell_html(c)
                lbl = '<span class="lbl">%s</span>' % inline(head[i]) if i else ""
                body = "".join("<span>%s</span>" % inline(v) for v in vals) if vals else '<span class="dash">—</span>'
                cs.append('<div%s>%s%s</div>' % (' class="wk"' if i == 0 else "", lbl, body))
            o.append('<div class="r">%s</div>' % "".join(cs))
        o.append("</div>"); return "\n".join(o)
    grid = cols or "minmax(0,1fr) " + " ".join(["auto"] * (n - 1))
    o = ['<div class="fig" style="grid-template-columns:%s">' % esc(grid)]
    for i, h in enumerate(head): o.append('<div class="head meta%s">%s</div>' % (" num" if i else "", inline(h)))
    for r in rows:
        tot = all(c.startswith("**") for c in r if c)
        for i, c in enumerate(r):
            cls = " ".join(x for x in ("tot" if tot else "", "num" if i else "") if x)
            o.append('<div%s>%s</div>' % (' class="%s"' % cls if cls else "", inline(c)))
    o.append("</div>"); return "\n".join(o)

def render_blocks(bl, breaks=False):
    out, run = [], []
    def flush():
        if run:
            out.append('<div class="prose">\n%s\n</div>' % "\n".join("<p>%s</p>" % inline(p, breaks) for p in run)); run.clear()
    for kind, d in bl:
        if kind == "p": run.append(d); continue
        flush()
        if kind == "h3": out.append('<p class="meta sub">%s</p>' % inline(d))
        elif kind == "h2": out.append("<h3>%s</h3>" % inline(d))
        elif kind == "ol": out.append('<ol class="objectives">%s</ol>' % "".join("<li>%s</li>" % inline(x) for x in d))
        elif kind == "ul":
            if all(re.match(r"\[[^\]]+\]\([^)]+\)", x) and not x.startswith("[![") for x in d):
                lis = []
                for x in d:
                    m = re.match(r"\[([^\]]+)\]\(([^)\s]+)\)\s*(?:[—-]\s*(.*))?$", x)
                    note = '<small>%s</small>' % inline(m.group(3)) if m and m.group(3) else ""
                    lis.append('<li><a %s><span>%s%s</span><span class="meta">Open ↗</span></a></li>' % (link(m.group(2)), esc(m.group(1), quote=False), note))
                out.append('<ul class="link-list">%s</ul>' % "".join(lis))
            elif all(x.startswith("[![") for x in d):
                figs = []
                for x in d:
                    m = re.match(r"\[!\[([^\]]*)\]\(([^)]+)\)\]\(([^)]+)\)", x)
                    if m: figs.append('<a %s><figure><div class="grain-img"><img src="%s" alt="%s" loading="lazy"></div><figcaption class="meta">%s</figcaption></figure></a>' % (link(m.group(3)), esc(rel(m.group(2), 1)), esc(m.group(1)), esc(m.group(1))))
                out.append('<div class="work-grid">%s</div>' % "".join(figs))
            else: out.append('<ul class="bullets">%s</ul>' % "".join("<li>%s</li>" % inline(x) for x in d))
        elif kind == "dl":
            out.append('<dl class="dl-list">%s</dl>' % "".join("<div><dt>%s</dt><dd>%s</dd></div>" % (inline(t), "".join("<p>%s</p>" % inline(x) for x in dd)) for t, dd in d))
        elif kind == "table": out.append(render_table(*d))
        elif kind == "quote": out.append("<blockquote><p>%s</p></blockquote>" % inline(d))
        elif kind == "img":
            out.append('<figure class="essay-fig"><div class="grain-img"><img src="%s" alt="%s" loading="lazy"></div><figcaption class="meta">%s%s</figcaption></figure>' % (esc(rel(d[1], 1)), esc(d[0]), esc(d[0]), ('<span class="credit">%s</span>' % esc(d[2])) if d[2] else ""))
    flush(); return "\n".join(out)

def toc_nav(items, label):
    lis = "".join('<li><a href="#%s" data-spy-link="%s"><span class="n">%02d.</span>%s</a></li>' % (i, i, k + 1, esc(t, quote=False)) for k, (i, t) in enumerate(items))
    return '<nav class="toc" aria-label="%s"><ul>%s</ul></nav>' % (label, lis)

# ------------------------------------------------------------------ load content
def entries(folder):
    out = []
    for fn in sorted(os.listdir(os.path.join(C, folder))):
        if not fn.endswith(".md") or fn.startswith("_"): continue
        fm, body = parse_file(os.path.join(C, folder, fn))
        fm["_file"] = fn; fm["_body"] = body
        fm["_slug"] = fm.get("slug") or re.sub(r"^(\d{4}-\d{2}-\d{2}-|\d+-)", "", fn[:-3])
        kind = PAGE_FOLDERS.get(folder)
        fm["_page"] = bool(body.strip()) and (folder in PAGE_FOLDERS) and (kind != "terms" or bool(re.search(r"^## ", body, re.M)))
        out.append(fm)
    return out

PAGE_FOLDERS = {}   # folder -> section kind
sections = []
for folder in sorted(os.listdir(C)):
    p = os.path.join(C, folder, "_section.md")
    if os.path.isfile(p):
        fm, body = parse_file(p); fm["_folder"] = folder; fm["_body"] = body
        fm.setdefault("kind", "groups"); fm["_id"] = folder; fm.setdefault("page", "inquiry")
        sections.append(fm)
sections.sort(key=lambda s: (num(s.get("order")), s["_folder"]))
for s in sections:
    if s["kind"] in ("rows", "terms"): PAGE_FOLDERS[s["_folder"]] = s["kind"]
PAGES = {"inquiry": "inquiry.html", "etc": "etc.html"}

def page_url(folder, e, depth=0): return "%s%s/%s.html" % ("../" * depth, folder, e["_slug"])

# ------------------------------------------------------------------ Inquiry page
def item_html(e, folder, default_style):
    style = e.get("style") or default_style
    title = esc(e.get("title", ""), quote=False)
    url = page_url(folder, e) if e["_page"] else e.get("url")
    if url: title = "<a %s>%s</a>" % (link(url), title)
    detail = e.get("summary") if e["_page"] else e["_body"]
    detail = detail or ""
    d = inline(detail, breaks=True) if detail else ""
    grey = lambda s: '<span class="sqsrte-text-color--darkAccent">%s</span>' % s
    if style == "inline":
        return '<p class="sqsrte-small">%s %s</p>' % (title, grey(d))
    if style == "compact":
        return '<p class="sqsrte-small">%s%s</p>' % (title, "<br/>" + grey(d) if d else "")
    o = "<p>%s</p>" % title
    if d: o += '<p class="sqsrte-small">%s</p>' % grey(d)
    return o

def split_html(body, e):
    """text on the left (cols 2-3), images on the right (cols 4-6)"""
    imgs = [(m.group(1), m.group(2)) for m in re.finditer(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", body, re.M)]
    text = re.sub(r"^!\[[^\]]*\]\([^)]+\)\s*$", "", body, flags=re.M).strip()
    t = []
    if e:
        t.append('<p class="sqsrte-large">%s</p>' % esc(e.get("title", ""), quote=False))
        if text: t += ['<p class="sqsrte-small">%s</p>' % inline(p, True) for p in re.split(r"\n\s*\n", text)]
        det = [e.get("year"), e.get("medium")]
        det = [esc(x, quote=False) for x in det if x]
        grey = "<br>".join(det)
        if e.get("note"): grey += ("<br><br>" if grey else "") + inline(e["note"])
        if grey: t.append('<p class="sqsrte-small"><span class="sqsrte-text-color--darkAccent">%s</span></p>' % grey)
    elif text: t = [render_blocks(blocks(text), True)]
    def pfig(a, u):
        w, h = img_size(rel(u, 0))
        return '<figure style="flex:%.4f 1 0"><div class="grain-img"><img src="%s" alt="%s" loading="lazy"></div></figure>' % (w / h, esc(rel(u, 0)), esc(a, quote=True))
    rows, k = [], 0
    if len(imgs) % 2: rows.append([imgs[0]]); k = 1
    while k < len(imgs): rows.append(imgs[k:k + 2]); k += 2
    figs = "".join('<div class="pic-row">%s</div>' % "".join(pfig(a, u) for a, u in r) for r in rows)
    pics = '<div class="pics">%s</div>' % figs if imgs else ""
    return '<div class="split"><div class="b txt">%s</div>%s</div>' % ("".join(t), pics)

def build_section(s):
    folder = s["_folder"]; es = entries(folder)
    o = ['<section class="c-sec" id="%s">' % esc(s["_id"]), '  <h2 class="display">%s</h2>' % esc(s.get("title", folder), quote=False)]
    if s["_body"] and s["kind"] not in ("works", "blocks"): o.append('  <div class="b stmt">%s</div>' % "".join('<p class="sqsrte-small">%s</p>' % inline(p, True) for p in re.split(r"\n\s*\n", s["_body"])))
    if s["kind"] in ("works", "blocks"):
        if s["kind"] == "blocks": o.append(split_html(s["_body"], None))
        else:
            for e in sorted(es, key=lambda e: (num(e.get("order")), e["_file"])): o.append(split_html(e["_body"], e))
        o.append("</section>"); return "\n".join(o)
    if s["kind"] == "rows":
        es.sort(key=lambda e: str(e.get("date", "")), reverse=True)
        o.append('  <div class="rows">')
        for e in es:
            url = page_url(folder, e) if e["_page"] else e.get("url")
            t = esc(e.get("title", ""), quote=False)
            if url: t = "<a %s>%s</a>" % (link(url), t)
            o.append('    <div class="row"><div class="b"><p class="sqsrte-small">%s</p></div><div class="b date"><p class="sqsrte-small"><span class="sqsrte-text-color--darkAccent">%s</span></p></div></div>' % (t, esc(nice_date(e.get("date", "")))))
        o.append("  </div>")
    else:
        key = "term" if s["kind"] == "terms" else "group"
        groups = {}
        for e in es: groups.setdefault(e.get(key, "Other"), []).append(e)
        if s["kind"] == "terms": order = sorted(groups, key=term_key, reverse=True)
        else:
            order = [g for g in (s.get("groups") or []) if g in groups] + [g for g in groups if g not in (s.get("groups") or [])]
        for g in order:
            items = sorted(groups[g], key=lambda e: (num(e.get("order")), e["_file"]))
            html_items, prev_block = [], False
            for e in items:
                h = item_html(e, folder, s.get("style", "block"))
                is_block = h.startswith("<p>") and "<p class" in h
                if html_items and prev_block: html_items.append("<p></p>")
                html_items.append(h); prev_block = is_block
            o.append('  <div class="grp"><div class="b lab"><p class="sqsrte-large">%s</p></div><div class="b">%s</div></div>' % (esc(g, quote=False), "".join(html_items)))
    o.append("</section>")
    return "\n".join(o)

def build_home():
    fm, body = parse_file(os.path.join(C, "home.md"))
    body = body.strip()
    head, _, rest = body.partition("\n")
    head = head[2:] if head.startswith("# ") else head
    bl = blocks(rest)
    paras = [d for k, d in bl if k == "p"]
    lines = [l.strip() for l in head.split("|")]
    title = "".join("<span>%s</span>" % inline(l) for l in lines)
    small = "<br>".join(x for x in ("Currently: " + esc(fm["currently"], quote=False) if fm.get("currently") else "", "Previously: " + esc(fm["previously"], quote=False) if fm.get("previously") else "") if x)
    ps = "".join("<p>%s</p>" % inline(p) for p in paras)
    pause = '<svg class="i-pause" viewBox="0 0 20 20" aria-hidden="true"><rect x="3" y="2" width="5" height="16"/><rect x="12" y="2" width="5" height="16"/></svg><svg class="i-play" viewBox="0 0 20 20" aria-hidden="true"><path d="M4 2l13 8-13 8z"/></svg>'
    main = f"""<main id="main">
  <section class="hero">
    <video class="hero-video" src="{esc(fm['video'])}" poster="{esc(fm.get('poster', ''))}" autoplay muted loop playsinline preload="auto" aria-hidden="true"></video>
    <div class="hero-text">
      <h1 class="display hero-title">{title}</h1>
      <div class="hero-cols"><div class="copy b sqsrte-large">{ps}</div><div class="small b sqsrte-small"><p>{small}</p></div></div>
    </div>
    <button class="hero-pause" type="button" aria-label="Pause the background video">{pause}</button>
  </section>
</main>"""
    open("index.html", "w", encoding="utf8").write(page(fm.get("title", "None More Blue"), fm.get("description", ""), 0, main, ["common", "theme", "landing", "motion", "home"], current="", body_class="home"))
    print("wrote index.html")

def build_404():
    # Served by GitHub Pages for any missing address, at any depth, so paths are made root-relative with <base>.
    main = """<main id="main">
  <section class="c-top ruled">
    <h1 class="c-title">404</h1>
    <div class="b lead"><p class="sqsrte-large">This page doesn’t exist. Some things are like that.</p><p class="sqsrte-large">There’s always rice at <a href="index.html">home</a>.</p></div>
  </section>
  <div class="c-end"></div>
</main>"""
    html = page("404", "This page doesn’t exist.", 0, main, ["common", "theme", "landing", "motion", "page"], current="", body_class="err")
    html = html.replace("<head>", '<head>\n<base href="/">', 1)
    open("404.html", "w", encoding="utf8").write(html)
    print("wrote 404.html")

def build_listing(name):
    fm, body = parse_file(os.path.join(C, name + ".md"))
    secs = [s for s in sections if s["page"] == name]
    lead = '\n    <div class="b lead"><p class="sqsrte-large">%s</p></div>' % inline(body, True) if body else ""
    toc = toc_nav([(s["_id"], s.get("title", s["_folder"])) for s in secs], "Sections")
    out = PAGES[name]
    main = f"""<main id="main">
  <section class="c-top ruled">
    <h1 class="c-title">{esc(fm.get('title', name))}</h1>{lead}
  </section>
  <div class="c-layout"><div class="grid">
    {toc}
    <div class="c-body cols">
{chr(10).join(build_section(s) for s in secs)}
    </div>
  </div></div>
  <div class="c-end"></div>
</main>"""
    open(out, "w", encoding="utf8").write(page(fm.get("title", name), fm.get("description", ""), 0, main, ["common", "theme", "landing", "motion", "page"], current=out))
    print("wrote", out)

# ------------------------------------------------------------------ logos page
def build_logos():
    fm, body = parse_file(os.path.join(C, "logos.md"))
    intro, items = [], []
    for ln in body.split("\n"):
        m = re.match(r"-\s+(.+?)\s+\|\s+(\d{4})\s+\|\s+(\S+)\s*$", ln)
        if m: items.append(m.groups())
        elif ln.strip(): intro.append(ln)
    from PIL import Image
    cells = []
    # a logo with a separate mark (`x-word.png` + `x-mark.png`) is laid out in its original proportions;
    # in dark mode the mark stays black and sits on a light circle, because fine detail does not survive inversion
    LOCKUP = {"van-oort": dict(w=3509, h=748, mark=(0, 0, 943, 748), word=(1142, 47, 2367, 610))}
    cells = []
    for name, year, src in items:
        key = re.sub(r"-word$", "", os.path.splitext(os.path.basename(src))[0])
        if src.endswith("-word.png") and key in LOCKUP:
            g = LOCKUP[key]; pct = lambda v, t: "%.2f%%" % (v / t * 100)
            mx, my, mw, mh = g["mark"]; wx, wy, ww, wh = g["word"]
            mark = src.replace("-word.png", "-mark.png")
            art = (f'<span class="logo-mark lockup" role="img" aria-label="{esc(name)} logo" style="--w:{g["w"] / 3840 * 100:.1f}%;--r:{g["w"]} / {g["h"]}">'
                   f'<span class="lk-mark" style="left:{pct(mx, g["w"])};top:{pct(my, g["h"])};width:{pct(mw, g["w"])};height:{pct(mh, g["h"])}"><img src="{mark}" alt=""></span>'
                   f'<img class="lk-word" src="{src}" alt="" style="left:{pct(wx, g["w"])};top:{pct(wy, g["h"])};width:{pct(ww, g["w"])};height:{pct(wh, g["h"])}"></span>')
        else:
            w, h = Image.open(src).size
            art = f'<img class="logo-mark" src="{src}" alt="{esc(name)} logo" width="{w}" height="{h}" loading="lazy" style="--w:{w / 1200 * 100:.1f}%">'
        cells.append(f'<li class="logo-item"><div class="logo-head"><span class="logo-name">{esc(name, quote=False).upper()}</span><span>{esc(year)}</span></div>\n      <div class="logo-box">{art}</div></li>')
    lead = '<div class="b lead"><p class="sqsrte-large">%s</p></div>' % inline(" ".join(intro))
    main = f"""<main id="main">
  <section class="c-top ruled">
    <h1 class="c-title">{esc(fm.get('title', 'Logos'), quote=False)}</h1>
    {lead}
  </section>
  <ul class="logo-grid">
    {chr(10).join(cells)}
  </ul>
  <div class="c-end"></div>
</main>"""
    open("logos.html", "w", encoding="utf8").write(page(fm.get("title", "Logos"), fm.get("description", ""), 0, main, ["common", "theme", "landing", "motion", "page"], current=""))
    print("wrote logos.html")

# ------------------------------------------------------------------ output page
def build_output():
    fm, body = parse_file(os.path.join(C, "output.md"))
    items = []
    for fn in sorted(os.listdir(os.path.join(C, "output"))):
        if fn.endswith(".md") and not fn.startswith("_"):
            f, b = parse_file(os.path.join(C, "output", fn)); f["_body"] = b; items.append(f)
    groups = [g.strip() for g in str(fm.get("groups", "")).split(",") if g.strip()]
    secs = []
    for g in groups:
        rows = []
        for e in [x for x in items if x.get("group") == g]:
            t = '<a %s>%s</a>' % (link(e.get("url")), esc(e.get("title", ""), quote=False)) if e.get("url") else esc(e.get("title", ""), quote=False)
            meta = "<br>".join(esc(str(x), quote=False) for x in (e.get("year"), e.get("client")) if x)
            paras = "".join('<p class="sqsrte-small">%s</p>' % inline(p, True) for p in re.split(r"\n\s*\n", e["_body"]) if p.strip())
            fig = ""
            if e.get("image"):
                im = lambda src, cls="": '<img%s src="%s" alt="%s" loading="lazy">' % (' class="%s"' % cls if cls else "", esc(src), esc(e.get("alt", ""), quote=True))
                imgs = (im(e["image"], "th-light") + im(e["image_dark"], "th-dark")) if e.get("image_dark") else im(e["image"])
                fig = '<figure class="out-fig"><div class="grain-img">%s</div></figure>' % imgs
            blank = '' if e.get("image") else ' empty'
            metaline = "".join('<span>%s</span>' % esc(str(x), quote=False) for x in (e.get("year"), e.get("client")) if x)
            rows.append(f'<div class="grp out{blank}"><div class="b pic">{fig}</div><div class="b"><p class="sqsrte-large">{t}</p><p class="sqsrte-small meta-line">{metaline}</p><div class="desc">{paras}</div></div></div>')
        secs.append('<section class="c-sec" id="%s">\n  <h2 class="sr-only">%s</h2>\n%s\n</section>' % (slugify(g), esc(g, quote=False), "\n".join(rows)))
    toc = toc_nav([(slugify(g), g) for g in groups], "Sections")
    main = f"""<main id="main">
  <section class="c-top ruled">
    <h1 class="c-title">{esc(fm.get('title', 'Output'), quote=False)}</h1>
    <div class="b lead"><p class="sqsrte-large">{inline(body, True)}</p></div>
  </section>
  <div class="c-layout"><div class="grid">
    {toc}
    <div class="c-body cols">
{chr(10).join(secs)}
    </div>
  </div></div>
  <div class="c-end"></div>
</main>"""
    open("output.html", "w", encoding="utf8").write(page(fm.get("title", "Output"), fm.get("description", ""), 0, main, ["common", "theme", "landing", "motion", "page"], current="output.html"))
    print("wrote output.html")


# ------------------------------------------------------------------ project pages (content/projects/*.md)
def img_size(path):
    """(width, height) of a local jpg/png without any imaging library"""
    try:
        with open(path, "rb") as f:
            d = f.read(65536)
        if d[:8] == b"\x89PNG\r\n\x1a\n": return struct.unpack(">II", d[16:24])
        i = 2
        while i < len(d) - 9:
            if d[i] != 0xFF: i += 1; continue
            mk = d[i + 1]
            if mk in (0xC0, 0xC1, 0xC2): h, w = struct.unpack(">HH", d[i + 5:i + 9]); return (w, h)
            i += 2 + struct.unpack(">H", d[i + 2:i + 4])[0]
    except Exception: pass
    return (3, 2)

def build_projects():
    d = os.path.join(C, "projects")
    if not os.path.isdir(d): return
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".md") or fn.startswith("_"): continue
        fm, body = parse_file(os.path.join(d, fn))
        slug = fm.get("slug") or fn[:-3]
        P = lambda s: "".join('<p class="sqsrte-small">%s</p>' % inline(x, True) for x in s)
        def spec(s):
            f = [x.strip() for x in s.split("|")]
            f += [""] * (4 - len(f))
            w, h = img_size(f[0]); flags = f[3].split()
            return dict(src=f[0], alt=f[1], cap=f[2], flags=flags, ar=w / h)
        def fig(sp, cls="", style="", flex=False):
            img = '<img src="%s" alt="%s" loading="lazy">' % (esc(sp["src"]), esc(sp["alt"], quote=True))
            inner = img if "dim" in sp["flags"] else '<div class="grain-img">%s</div>' % img
            c = '<figcaption class="sqsrte-small">%s</figcaption>' % esc(sp["cap"], quote=False) if sp["cap"] else ""
            dim = " pj-dim" if "dim" in sp["flags"] else ""
            return '<figure class="pj-fig%s %s" style="%s">%s%s</figure>' % (dim, cls, style, inner, c)
        sections = []
        for part in re.split(r"^## ", body, flags=re.M)[1:]:
            head, _, rest = part.partition("\n")
            items, paras = [], []
            def flush():
                if paras: items.append(("text", list(paras))); paras.clear()
            for blk in [x.strip() for x in re.split(r"\n\s*\n", rest.strip()) if x.strip()]:
                for ln in blk.split("\n"):
                    m = re.match(r"::(side|fig|pair)\s+(.*)", ln.strip())
                    if m:
                        flush()
                        if m.group(1) == "pair": items.append(("pair", [spec(x) for x in m.group(2).split("||")]))
                        else: items.append((m.group(1), spec(m.group(2))))
                    else: paras.append(ln.strip())
                if blk and not blk.startswith("::"): pass
            flush()
            sections.append((head.strip(), items))
        out_secs, toc, side_flip = [], [], 0
        for title, items in sections:
            sid = slugify(title); toc.append((sid, title))
            has_side = any(k == "side" for k, _ in items)
            html_items, gal, first_text, flip = [], [], True, 0
            def flush_gal():
                if gal: html_items.append('<div class="pj-gallery">%s</div>' % "".join(gal)); gal.clear()
            for k, v in items:
                if k == "text":
                    flush_gal()
                    html_items.append('<div class="pj-text%s">%s</div>' % (" pj-first" if first_text else "", P(v))); first_text = False
                elif k == "side":
                    html_items.append(fig(v, "pj-side"))
                elif k == "fig":
                    if "dim" in v["flags"]: cls = "single dim"
                    else:
                        cls = "single " + ("L" if "left" in v["flags"] else "R" if "right" in v["flags"] else ("L" if flip % 2 == 0 else "R")); flip += 1
                    gal.append(fig(v, cls, "--ar:%.4f" % v["ar"]))
                elif k == "pair":
                    wide = " wide" if any("wide" in s["flags"] for s in v) else ""
                    gal.append('<div class="pj-pair%s">%s</div>' % (wide, "".join(fig(s, "", "flex:%.4f 1 0" % s["ar"]) for s in v)))
            flush_gal()
            out_secs.append('<section class="c-sec%s" id="%s">\n<h2 class="display">%s</h2>\n%s\n</section>' % (" has-side" if has_side else "", sid, esc(title, quote=False), "\n".join(html_items)))
        main = f"""<main id="main">
  <section class="c-top">
    <h1 class="display c-title">{esc(fm['title'], quote=False)}</h1>
    <p class="display c-title c-subtitle">{esc(fm.get('subtitle', ''), quote=False)}</p>
    <div class="c-sub"><div class="meta k1">{esc(str(fm.get('year', '')), quote=False)}</div><div class="meta k2">{esc(fm.get('discipline', ''), quote=False)}</div></div>
  </section>
  <div class="parallax"><img src="{esc(fm['hero'])}" alt="{esc(fm.get('hero_alt', ''), quote=True)}" width="{img_size(fm['hero'])[0]}" height="{img_size(fm['hero'])[1]}"></div>
  <div class="c-layout"><div class="grid">
    {toc_nav(toc, "Contents")}
    <div class="c-body pj">
{chr(10).join(out_secs)}
    </div>
  </div></div>
  <div class="c-end"></div>
</main>"""
        open(f"{slug}.html", "w", encoding="utf8").write(page(fm["title"], fm.get("subtitle", ""), 0, main, ["common", "theme", "landing", "motion", "page"], current="output.html"))
        print("wrote %s.html" % slug)

# ------------------------------------------------------------------ essay pages
def build_essay(s, e):
    folder = s["_folder"]
    main = f"""<main id="main">
  <section class="c-top ruled">
    <h1 class="display c-title">{esc(e['title'], quote=False)}</h1>
    <div class="c-sub">
      {('<div class="meta k1">%s</div>' % esc(e['genre'], quote=False)) if e.get('genre') else ''}<div class="meta k{2 if e.get('genre') else 1}">{esc(nice_date(e.get('date', '')))}</div>
    </div>
  </section>
  <div class="c-layout"><div class="grid">
    <nav class="toc" aria-label="Essay"><ul><li><a href="../{PAGES[s['page']]}#{esc(s['_id'])}">{esc(s.get('title', 'Essays'), quote=False)}</a></li></ul></nav>
    <article class="c-body essay">
{render_blocks(blocks(e['_body']))}
    </article>
  </div></div>
  <div class="c-end"></div>
</main>""".replace('<div class="prose">', '<div class="prose essay-text">')
    os.makedirs(folder, exist_ok=True)
    first = re.sub(r"\s+", " ", e["_body"])[:150]
    open(f"{folder}/{e['_slug']}.html", "w", encoding="utf8").write(page(e["title"], first, 1, main, ["common", "theme", "landing", "motion", "page"], current=PAGES[s["page"]]))

# ------------------------------------------------------------------ course pages
def build_course(s, e):
    folder = s["_folder"]; bl = blocks(e["_body"])
    secs, cur = [], None
    for kind, d in bl:
        if kind == "h2": cur = [d, []]; secs.append(cur)
        elif cur is not None: cur[1].append((kind, d))
    sec_html, toc = [], []
    for title, b in secs:
        sid = slugify(title); toc.append((sid, title))
        sec_html.append('<section class="c-sec" id="%s">\n<h2 class="display">%s</h2>\n%s\n</section>' % (sid, esc(title, quote=False), render_blocks(b)))
    if e.get("samples"):
        sid = "student-work-samples"; toc.append((sid, "Student Work Samples"))
        sec_html.append('<section class="c-sec c-samples" id="%s">\n<h2 class="display"><a %s>Student Work Samples</a></h2>\n</section>' % (sid, link(e["samples"])))
    codes = e.get("codes") or []; codes = [codes] if isinstance(codes, str) else codes
    school = e.get("school") or []; school = [school] if isinstance(school, str) else school
    sub = []
    if school: sub.append('<div class="meta k1">%s</div>' % "".join("<div>%s</div>" % esc(x, quote=False) for x in school))
    if codes: sub.append('<div class="meta k2">%s</div>' % "".join("<div>%s</div>" % esc(x, quote=False) for x in codes))
    if e.get("term"): sub.append('<div class="meta k3">%s</div>' % esc(e["term"], quote=False))
    if e.get("pdf"): sub.append('<p class="meta c-pdf"><a %s data-link="%s">Syllabus (PDF)</a></p>' % (link(rel(e["pdf"], 1)), "ext" if re.match(r"https?:", e["pdf"]) else "dl"))
    cover = ""
    if e.get("cover"):
        cover = '<div class="parallax"><img src="%s" alt="%s" width="1229" height="790"></div>' % (esc(rel(e["cover"], 1)), esc(e.get("cover_alt", ""), quote=True))
    main = f"""<main id="main">
  <section class="c-top">
    <h1 class="display c-title">{esc(e['title'], quote=False)}</h1>
    <div class="c-sub">{''.join(sub)}</div>
  </section>
  {cover}
  <div class="c-layout"><div class="grid">
    {toc_nav(toc, "Contents")}
    <div class="c-body">
{chr(10).join(sec_html)}
    </div>
  </div></div>
  <div class="c-end"></div>
</main>"""
    os.makedirs(folder, exist_ok=True)
    open(f"{folder}/{e['_slug']}.html", "w", encoding="utf8").write(page("%s (%s)" % (e["title"], e.get("term", "")) if e.get("term") else e["title"], "%s — %s" % (e["title"], e.get("term", "")), 1, main, ["common", "theme", "landing", "motion", "page"]))

# ------------------------------------------------------------------ run
def main():
    for d in PAGE_FOLDERS:                     # remove stale generated pages
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.endswith(".html"): os.remove(os.path.join(d, f))
    n = 0
    for s in sections:
        if s["kind"] not in ("rows", "terms"): continue
        for e in entries(s["_folder"]):
            if not e["_page"]: continue
            (build_essay if s["kind"] == "rows" else build_course)(s, e); n += 1
    build_home()
    build_404()
    build_logos()
    build_output()
    build_projects()
    for name in PAGES: build_listing(name)
    print("wrote %d page(s)" % n)

if __name__ == "__main__": main()
