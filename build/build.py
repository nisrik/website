#!/usr/bin/env python3
"""Builds the whole site from the markdown files in content/.

    python3 build/build.py          (run from the project root; standard library only)

  content/inquiry.md                the Inquiry page title + intro
  content/<section>/_section.md     one folder per section on the Inquiry page
  content/<section>/*.md            one file per entry (paper, course, essay, ...)

Writes: index.html, essays/<slug>.html, teaching/<slug>.html. See README.md.
GitHub Actions runs this on every push (.github/workflows/pages.yml), so adding a file is all you do.
"""
import html, os, re, sys, shutil
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
    s = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?!\w)", r"<em>\1</em>", s)
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
            m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", ln); out.append(("img", (m.group(1), m.group(2)))); i += 1; continue
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

def page(title, desc, depth, main, scripts):
    d = "../" * depth
    sc = "\n".join('<script src="%sjs/%s.js"></script>' % (d, s) for s in scripts)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} — None More Blue</title>
<meta name="description" content="{esc(desc, quote=True)}">
<link rel="icon" href="{d}images/logo/nmb-black.png">
<script>try{{var t=localStorage.getItem('theme');if(t==='light'||t==='dark')document.documentElement.setAttribute('data-theme',t)}}catch(e){{}}</script>
<link rel="stylesheet" href="{d}css/fonts.css">
<link rel="stylesheet" href="{d}css/site.css">
<link rel="stylesheet" href="{d}css/course.css">
</head>
<body>
{up(HEADER, depth)}
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
            out.append('<figure class="essay-fig"><div class="grain-img"><img src="%s" alt="%s" loading="lazy"></div><figcaption class="meta">%s</figcaption></figure>' % (esc(rel(d[1], 1)), esc(d[0]), esc(d[0])))
    flush(); return "\n".join(out)

def toc_nav(items, label):
    lis = "".join('<li><a href="#%s" data-spy-link="%s">%s</a></li>' % (i, i, esc(t, quote=False)) for i, t in items)
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
        fm.setdefault("kind", "groups"); fm["_id"] = folder
        sections.append(fm)
sections.sort(key=lambda s: (num(s.get("order")), s["_folder"]))
for s in sections:
    if s["kind"] in ("rows", "terms"): PAGE_FOLDERS[s["_folder"]] = s["kind"]

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

def build_section(s):
    folder = s["_folder"]; es = entries(folder)
    o = ['<section class="c-sec" id="%s">' % esc(s["_id"]), '  <h2 class="display">%s</h2>' % esc(s.get("title", folder), quote=False)]
    if s["_body"]: o.append('  <div class="b stmt">%s</div>' % "".join('<p class="sqsrte-small">%s</p>' % inline(p, True) for p in re.split(r"\n\s*\n", s["_body"])))
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

def build_index():
    fm, body = parse_file(os.path.join(C, "inquiry.md"))
    lead = inline(body, True)
    toc = toc_nav([(s["_id"], s.get("title", s["_folder"])) for s in sections], "Sections")
    main = f"""<main id="main">
  <section class="c-top ruled">
    <h1 class="c-title">{esc(fm.get('title', 'Inquiry'))}</h1>
    <div class="b lead"><p class="sqsrte-large">{lead}</p></div>
  </section>
  <div class="c-layout"><div class="grid">
    {toc}
    <div class="c-body cols">
{chr(10).join(build_section(s) for s in sections)}
    </div>
  </div></div>
  <div class="c-end"></div>
</main>"""
    open("index.html", "w", encoding="utf8").write(page(fm.get("title", "Inquiry"), fm.get("description", ""), 0, main, ["common", "theme", "landing", "motion", "page"]))
    print("wrote index.html")

# ------------------------------------------------------------------ essay pages
def build_essay(s, e):
    folder = s["_folder"]
    main = f"""<main id="main">
  <section class="c-top ruled">
    <h1 class="display c-title">{esc(e['title'], quote=False)}</h1>
    <div class="c-sub">
      <div class="meta k1">{esc(nice_date(e.get('date', '')))}</div>
    </div>
  </section>
  <div class="c-layout"><div class="grid">
    <nav class="toc" aria-label="Essay"><ul><li><a href="../index.html#{esc(s['_id'])}">{esc(s.get('title', 'Essays'), quote=False)}</a></li></ul></nav>
    <article class="c-body essay">
{render_blocks(blocks(e['_body']))}
    </article>
  </div></div>
  <div class="c-end"></div>
</main>""".replace('<div class="prose">', '<div class="prose essay-text">')
    os.makedirs(folder, exist_ok=True)
    first = re.sub(r"\s+", " ", e["_body"])[:150]
    open(f"{folder}/{e['_slug']}.html", "w", encoding="utf8").write(page(e["title"], first, 1, main, ["common", "theme", "landing", "motion", "page"]))

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
    codes = e.get("codes") or []; codes = [codes] if isinstance(codes, str) else codes
    school = e.get("school") or []; school = [school] if isinstance(school, str) else school
    sub = []
    if school: sub.append('<div class="meta k1">%s</div>' % "".join("<div>%s</div>" % esc(x, quote=False) for x in school))
    if codes: sub.append('<div class="meta k2">%s</div>' % "".join("<div>%s</div>" % esc(x, quote=False) for x in codes))
    if e.get("term"): sub.append('<div class="meta k3">%s</div>' % esc(e["term"], quote=False))
    if e.get("pdf"): sub.append('<p class="meta c-pdf"><a %s data-link="dl">Syllabus (PDF)</a></p>' % link(rel(e["pdf"], 1)))
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
    build_index()
    print("wrote %d page(s)" % n)

if __name__ == "__main__": main()
