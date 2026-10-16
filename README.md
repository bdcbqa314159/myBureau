# myBureau

A desktop-metaphor site engine: every section is a *bureau* of draggable
folders, and the filesystem is the CMS.

First deployment: **valentina for STUDIO S**.

Engine by Bernardo Cohen — proprietary, **not** open source, and **not** work
for hire. See [LICENSE](LICENSE).
Design and creative assets belong to the client. See [NOTICE](NOTICE).

---

## Adding content — no code required

The site reads the filesystem. Drop files in, they appear.

### Add a project

Create a folder under `content/da/` or `content/graphic-design/`:

```
content/graphic-design/my-project/
    index.md          ← title, position, description
    icon.png          ← the icon shown on the desktop
    01.jpg            ← page images, shown in filename order
    02.jpg
    03.jpg
```

`index.md`:

```toml
+++
title = "my project.pdf"      # the label under the desktop icon

[extra]
x = 40                         # icon position, % from the left
y = 55                         # icon position, % from the top
+++

The description paragraph that opens the project page.
```

That is the whole contract. The desktop icon, the project page, the
image list and the navigation are all derived from it. Nothing else to edit.

### Folders and files

The filesystem is the structure. There is no flag to set:

| on disk | is | opens |
|---|---|---|
| a directory with `_index.md` | a **folder** | a new bureau |
| a directory with `index.md` | a **file** | a project page |

So a folder is a directory that has things in it, exactly as in Finder.
Nesting works to any depth — a bureau inside a bureau inside a bureau.

To turn a project into a folder, rename its `index.md` to `_index.md`,
add `template = "section.html"`, and put project directories inside it.

### Leaving and coming back

Icons you move are remembered **for the session**, per bureau. Leave a
bureau and return, and they are put back where you dropped them and then
walked home — a visible tidy-up rather than a reset that already
happened. Close the tab and the memory goes with it.

The walk is a FLIP animation: the icon is never actually laid out in the
wrong place, only its transform moves, so the page is correct from the
first frame.

### Add photos to `pellicules`

Drop image files straight into `content/pellicules/`. The gallery picks
them up in filename order. Name them `01.jpg`, `02.jpg` … to control order.

### Change a wallpaper

Replace the file in `static/img/`, or point a section at a different one:

```toml
[extra]
wallpaper = "img/my-wallpaper.jpg"
```

### Move an icon

Edit `x` / `y` in that project's `index.md`. Visitors can drag icons around
in the browser, but those moves are not saved — `x`/`y` is the resting layout.

### Supported image types

`jpg` `jpeg` `png` `webp` `avif` `gif` — set in `config.toml` under
`image_types`.

---

## Changing the typeface

All typography lives in one block at the top of `static/css/site.css`,
marked `TYPE SYSTEM`. Nothing below it names a font or a pixel size — every
rule reads a token. To re-skin the site:

1. drop the `.woff2` files into `static/fonts/`
2. rewrite the `@font-face` rules under `FACES`
3. point `--font-display`, `--font-body`, `--font-ui` at the new family
4. adjust `--tracking-display` — a different face will want different spacing

Three families, because the site has three jobs:

| token | used for |
|---|---|
| `--font-display` | wordmarks, nav, icon labels, page titles |
| `--font-body` | running text (defaults to display) |
| `--font-ui` | the Win95 window only |

Two weights, per the brief — `--w-light` (300) and `--w-bold` (700). No
others exist. `font-synthesis-weight: none` means a missing weight fails
visibly instead of being faked by the browser.

**Which weight prose gets is still open.** The rule we are proposing:

> Bold for what you glance at. Light for what you read.

Wordmarks, nav, icon labels and page titles are glanced — they stay bold.
Project descriptions and the about-me text are read, which argues for
light. The proto shows them bold, so bold is the default. Change
`--w-prose` and every piece of running text moves together; nothing else
does.

The Win95 window follows the same split: the **chrome** (title bar,
buttons, form controls) stays pixel-monospace because that is the 1995
artifact, while the **content** is set in the body face, because it is
writing rather than UI furniture.

Five sizes, one fluid ramp — `--f-1` (fine print) through `--f-5`
(wordmark). Each scales with the viewport. Adding a sixth size is a
decision, not a reflex.

If the replacement face is **not** variable, change `font-weight: 300 700`
in the `@font-face` rules to a single value and add one rule per weight.

## Changing the cursors

Four 16×16 pixel-art cursors live in `static/img/cursors/`, each at 1x
(16px) and 2x (32px, for retina):

| file | shown on | hotspot |
|---|---|---|
| `arrow` | everything | corner `0 0` |
| `point` | links, buttons | fingertip `5 0` |
| `open` | icons and window title bars — things you can pick up | centre `8 8` |
| `grab` | whatever you are currently holding | centre `8 8` |

The art is **ASCII in `tools/cursors.py`**, not only PNG — a binary diff
in a pull request tells you nothing, an ASCII diff shows exactly which
pixels moved.

```bash
python3 tools/cursors.py --show    # preview in the terminal
python3 tools/cursors.py           # regenerate the PNGs
python3 tools/cursors.py --check   # verify the art, write nothing
```

Edit the grid (`#` outline, `*` fill, `.` transparent), preview, regenerate,
commit both the source and the PNGs. `--check` enforces 16×16 and that every
hand still has four fingers and a thumb.

Prefer a pixel editor? Replace the `.png` and `@2x.png` directly, keeping
16×16 / 32×32 and the transparency, and export nearest-neighbour — never
bicubic, or the retro read is lost. Update the ASCII to match if you do.

If a new cursor's visual anchor moves, update its hotspot in the
`CURSORS` block of `site.css`. The hotspot is where the click actually
lands, in CSS pixels of the 16px image. Get it wrong and the cursor
looks fine but clicks land somewhere else.

## Running it locally

```bash
npm install          # once
npm run watch &      # TypeScript → static/js
zola serve           # http://127.0.0.1:1111
```

Both watch for changes. Edit anything and the browser reloads.

## Checks

```bash
npm run check        # tsc --noEmit, strict
zola build           # fails on broken templates and links
```

CI runs both on every pull request; `main` deploys to GitHub Pages on merge.

---

## Layout

```
content/          the site — folders mirror the desktops
templates/        Tera templates (base, section, index, page, gallery)
src/desk.ts       drag + window behaviour, the only script
static/css/       one stylesheet
static/img/       wallpapers and generic icons
_ref/             design references, git-ignored (local only)
```

## Stack

Zola (Rust) builds static HTML. TypeScript compiles to ~3 KB of plain
JS for dragging and windows. Transitions are native CSS — View Transitions
and scroll-driven animation. No frontend framework, no bundler, no runtime
dependencies.

## Client material

This repository is public. Briefs, proto decks, mood boards and design
source files are the client's property and must never be committed —
they live in `_ref/`, which is git-ignored and local only.

Design source extensions (`.pdf`, `.psd`, `.ai`, `.fig`, …) are ignored
repo-wide as a backstop, but the rule is the convention, not the
pattern list: **if a client sent it, it goes in `_ref/`.**

## Going live

This deployment is a **demo of the engine**, not a client's site. While
`live = false` in `config.toml`:

- the site is called `myBureau`, not the client's name
- every page carries `<meta name="robots" content="noindex, nofollow">`
- `robots.txt` is `Disallow: /`

That is deliberate. A public URL with a real person's name over
placeholder content misrepresents them — a visitor cannot tell a
placeholder from a portfolio piece, and a search engine certainly
cannot. No name goes on this until the work on it is theirs.

When the real assets and the real name are both in:

```toml
live = true
```

One flag changes the title, the wordmark, the owner line, the robots
meta and `robots.txt` together. Verify afterwards:

```bash
zola build
grep -c 'noindex' public/index.html    # must be 0
head -2 public/robots.txt              # must allow crawling
```

### Launch checklist

1. every placeholder image deleted — `find content static/img -name '*.png'` should show only real work and the UI art
2. `live = true`
3. the client's own domain in `base_url`, plus a `static/CNAME`
4. `noindex` gone, `robots.txt` allowing crawlers
5. the contact form pointed at a real backend
6. the `site by` credit present — it is a condition of the licence, see LICENSE §4

## Placeholders

Every image currently in the repo is machine-generated noise, for testing
layout and loading only. They carry no creative content and get deleted as
the client's real work lands.
