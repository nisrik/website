# Teaching portfolio

Everything you write lives in **`content/`** as markdown. A small script (`build/build.py`, standard-library Python, nothing to install) turns it into the pages. GitHub runs that script for you every time you push, so for day-to-day work you only add or edit `.md` files.

## Adding things

| To add… | Add a file in… | What you get |
|---|---|---|
| an essay | `content/essays/` | a page at `essays/<name>.html` **and** a row in the Essays list |
| a course | `content/teaching/` | a page at `teaching/<name>.html` **and** an entry under its term in Teaching |
| a paper / presentation / service item | `content/research/` | an entry in its group |
| a case study | `content/case-studies/` | an entry in its group |
| an "In the oven" project | `content/in-the-oven/` | an entry in its group |
| a whole new section | a new folder with a `_section.md` | a new section + side-list link |

Every file starts with a few lines between `---` marks, then the text.

### Essay: `content/essays/2023-05-12-my-new-essay.md`
```
---
title: Cultural Affordances: Pace Layering
date: 2023-04-30
---
First paragraph. Blank line between paragraphs. [Links](https://example.com), **bold**, *italic*.

Another paragraph.

## An optional subheading

> A quotation.

![Caption for an image](images/essays/figure.jpg)
```
If a file has text below the `---`, it becomes a page. If it has none but has `url: https://…`, the list row just links there (that's how the not-yet-migrated essays work: when you move one over, paste the text in and delete the `url:` line). Newest essays are listed first.

### Course: `content/teaching/design-leadership-fa25.md`
```
---
title: Design Leadership
term: Fall 2025
codes: [HERV-601]
school: [Indiana University Indianapolis, Herron School of Art and Design]
cover: images/covers/HERV601-fa25-design-leadership.jpg
cover_alt: A school of fish swirling in blue water
pdf: syllabi/HERV601-fa25-design-leadership.pdf
order: 1
summary: One or two sentences shown under the title in the Teaching list.
---
## About this Course
Paragraphs…

### Learning Objectives
1. First
2. Second

## Course Mode
Intro paragraph.

Readings
: Definition-style entry: the term on one line, `: ` and its text on the next.

## Classes and Assignments
| Week | Topic | Assignment | Grade |
|---|---|---|---|
| 01 | Introduction | Self Reflection | 5 |
| 02 | People | Case Study | Assignment: 40 <br> Reflection: 10 |
{cols: 3.5rem 1fr 1.4fr 5rem}

## Grading
### Points
| Assignment Type | Points | Percentage of Total |
|---|---|---|
| Case Studies | 20 x 3 | 60% |
| **Total** | **100** | **100%** |
```
Each `## Heading` becomes a section and a side-list link; leave one out and it disappears. Lists of links to Google Drive work like this:
```
## Readings
- [Chapter 3, Organizational Behavior](https://drive.google.com/…) — week 2
```
and student work (with permission) as a grid: `- [![Project name](images/work/a.jpg)](https://drive.google.com/…)`.
Courses with no `##` sections (older terms) are just list entries; give them `url:` to link to a PDF. Terms are sorted automatically, newest first; `order:` sets the order within a term. `{cols: …}` after a table is optional (column widths).

### Research, case studies, in the oven: `content/research/12-my-paper.md`
```
---
group: Conference Proceedings
title: Title of the paper
url: http://doi.org/…
order: 4
---
In: Editors and book title.
Conference name and year.
```
Each line of the text is a line in grey under the title. `group:` must match a group name (they appear in the order listed in `groups:` in that folder's `_section.md`; an unknown name just starts a new group at the end). Optional `style: compact` (title and grey text together, as for Presentations) or `style: inline` (as for Case Studies: `title: Motivation:` plus text).

### The etc. page: `content/etc.md` + folders with `page: etc`
`content/etc.md` is the page title (and an optional intro). A folder joins the etc. page when its `_section.md` says `page: etc`. Three kinds:
- `kind: rows` (Fiction): one file per story, exactly like essays (`title`, `date`, `url:` or a body that becomes its own page).
- `kind: works` (Art): one file per work. Front matter `title`, `year`, `medium`, optional `note`; the text below is the description; each `![alt](images/etc/file.jpg)` line is a picture (an odd number of pictures makes the first one full width).
- `kind: blocks` (Music, Photography): the text in `_section.md` itself is the content: paragraphs on the left, picture(s) on the right.

### Section text and order: `content/<section>/_section.md`
Front matter: `title`, `order` (position on the page), `page` (`inquiry` by default, or `etc`), `kind` (`groups`, `terms` for Teaching, or `rows` for Essays), `groups: [A, B, C]`. The text below is the paragraph under the section heading. The page's own title and intro is `content/inquiry.md`.

## Previewing
```
python3 build/build.py
python3 -m http.server      # then open http://localhost:8000
```
(Opening `index.html` directly also works.) The generated `index.html`, `etc.html`, `essays/`, `teaching/` and any other generated folders are rebuilt every time; **don't edit them by hand**, edit the markdown.

## Publishing (GitHub Pages)
One-time: repo **Settings → Pages → Source: GitHub Actions**. After that, every push to `main` runs `.github/workflows/pages.yml`, which runs the build and publishes. You never need to commit the generated HTML, though it is harmless if you do.

## The rest
- `css/site.css` — colours, light/dark, header, menu, theme toggle, footer, link motion. `css/course.css` — the 6-column grid (130px margins, 50px gutters, 555px columns at 3840) and the page layouts. `css/fonts.css` — the font.
- `js/motion.js` (hairlines drawing in, link arrows, page transitions) · `js/page.js` (side-list highlight, cover parallax) · `js/theme.js` · `js/landing.js` (mobile menu, header hide/show) · `js/common.js`.
- `build/partials/header.html`, `footer.html` — shared header and footer (edit there, rebuild). `build/index.squarespace-copy.html` — untouched copy of the original Squarespace page, for reference only.
- `syllabi/`, `images/` — PDFs, covers, logos. Put new covers in `images/covers/`, PDFs in `syllabi/`.

## Before launch
1. **Font.** Squarespace serves Trade Gothic LT Std from its own host, so it won't come with the domain. See `css/fonts.css`: use Adobe Fonts or self-host files you hold a *web* licence for. Until then the page falls back to Helvetica/Arial.
2. **Old PDF links.** Links like `nonemoreblue.com/s/…pdf` (CV, FA24 syllabi) stop working when Squarespace is cancelled; download them into the repo and update the links (in `content/teaching/` and `build/partials/footer.html`).
3. **Syllabus typos** carried over from the PDFs: Framing week 7 assignment, "methods of to prototyping", "if you would like and feedback".
4. **Cover images** may be third-party artwork; confirm you can publish them.

## Home page

`content/home.md` drives `index.html`: front matter for the video, poster, and the Currently / Previously lines; the `#` heading is the headline and the paragraphs below it are the two columns. The Inquiry page is now `inquiry.html`. To swap the video, replace `videos/title-sequence.mp4` (about 1280px wide, no audio, under 3MB).

To add a "Student Work Samples" link to a course, add `samples: <folder url>` to its front matter.

A course's `pdf:` can be a local file (`syllabi/x.pdf`, shows a ↓) or a Drive link (opens in a new tab, shows a ↗).

Every course should have a one or two sentence `summary:` on its most recent term (older terms of the same course can leave it out). When a course gets its own page, move the blurb into `summary:` in its front matter.

### Image credits in essays
Add a credit under an essay image with a quoted title: `![Caption](images/essays/x.jpg "Credit line")`. The credit shows under the caption in a lighter tone. Avoid parentheses inside the credit.

### Palette
Colours are tokens at the top of `css/site.css`: Primer Black `#1a1a1a`, Bleached Linen `#faf9f6`, Primer Grey `#666666`, Grey `#a8a8a8`. Light mode is Primer Black on Linen; dark mode swaps them. The dark footer is a slightly deeper `#0f0f0f` so it still reads as a footer.
- Logos page: content/logos.md + build_logos() -> logos.html; marks are CSS masks in images/logos/
- Output page: content/output.md (intro, group order) + content/output/NN-slug.md (title, year, client, group, url, optional image/alt) -> output.html. Entries link to Squarespace until their pages are built here; no image = blank.
- Trade Gothic LT Std (Regular and Light, desktop licence) is loaded from fonts/TradeGothicLTStd*.otf via css/fonts.css for testing only: do not publish the file without a web licence.
