# myBureau

A desktop-metaphor site engine: every section is a *bureau* of draggable
folders, and the filesystem is the CMS.

First deployment: **valentina for STUDIO S**.

Engine by Bernardo Cohen — proprietary, **not** open source, and **not** work
for hire. See [LICENSE](LICENSE).
Design and creative assets belong to the client. See [NOTICE](NOTICE).

---

## Previewing the site

```bash
./preview.sh
```

That is the whole thing. It installs what is missing, builds, opens your
browser, and reloads the page whenever you change a file. Press `Ctrl-C`
to stop.

If it asks you to install Homebrew or Node first, do that once and run it
again.

## What the site works out for itself

The filesystem is the structure. You should never have to edit a template:

| you do | the site does |
|---|---|
| add a directory with `_index.md` | a **folder** appears, opening a new bureau |
| add a directory with `index.md` | a **file** appears, opening a project page |
| drop images into a project | they become the page, in filename order |
| drop photos into `pellicules/` | they fill the gallery |
| add a top-level bureau | it appears on the desktop **and in the top bar** |
| forget `icon.png` | a generic folder or file picture is used |
| forget `x` / `y` | the icon is placed on a free grid slot, never stacked |
| export `PHOTO.JPG` in capitals | matched the same as lowercase |
| name two projects the same in different bureaus | kept distinct, no transition clash |

Only things that are **neither** a folder nor a file — the windows — are
declared by hand, in `config.toml`.

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

### Icons

You rarely need to set one. The extension in the **title** decides, the
way a real desktop works:

| title ends in | icon |
|---|---|
| `.mov` `.mp4` `.m4v` `.avi` `.webm` | film strip |
| `.jpg` `.png` `.gif` `.webp` `.tif` … | Polaroid |
| anything else | document |
| (it is a folder) | folder |

So naming a project `june's cry.mov` gets you a film strip and
`12 regards.pdf` gets you a document, with nothing to configure.

To override, most explicit wins:

1. a file named `icon.*` in the project folder — her artwork
2. `icon = "img/icons/folder-rust.svg"` in the front matter
3. the extension rule above

Folders ship in four colourways — `folder.svg` (amber), `folder-rust`,
`folder-olive`, `folder-slate`.

### Regenerating the art

```bash
python3 tools/icons.py           # icons + wallpapers
python3 tools/icons.py --check   # validate, write nothing
```

Icons and wallpapers are **code**, for the same reason the cursors are:
an SVG diff in a pull request is readable, a binary diff is two blobs.

Wallpapers are SVG too — a duotone wash, film grain from
`feTurbulence`, and a vignette. Under 1 KB each instead of ~380 KB, and
the grain is computed rather than compressed, so it never bands. Point a
section at a photograph instead whenever you have one:

```toml
[extra]
wallpaper = "img/my-photo.jpg"
```

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

### Arriving

Every page waits behind a small overlay until it is worth showing, then
reveals at once. What counts as ready depends on the page:

| page | waits for |
|---|---|
| a bureau | the wallpaper and every icon — it is a composed scene and must appear whole |
| a project page | the fonts and the first picture; the rest are `loading="lazy"` |
| the gallery | the fonts; every photograph is lazy |

A scroll page that waited for all its images would mean staring at dots
for seconds, so only what is not deferred counts. Pictures arriving later
fade in, so a photograph appearing below the fold reads as intentional.

Three failure modes, all handled:

- **no JavaScript** — the `booting` class is added *by script*, so nothing
  is ever hidden and no overlay appears
- **the script fails to load** — an inline failsafe clears `booting` after
  six seconds. A portfolio must never stay blank because a script died
- **an image is broken or slow** — `onerror` settles like `onload`, and the
  whole wait is capped at four seconds

This hides the lag; it does not remove it. 8.8 MB of content images with
no resizing, no WebP and no `srcset` is the real cause — see the image
pipeline work still outstanding.

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

## The contact form

### Where it sends

Nowhere yet. `config.toml`:

```toml
[extra.contact]
endpoint = ""
```

Empty on purpose — the form tells the visitor it is not connected rather
than silently swallowing their message. Set it when a backend is chosen
and the form starts working; that is the only line that changes.

### What is checked, and what that is worth

`src/contact.ts` rejects, before sending:

| field | rejected |
|---|---|
| mail | newlines, control characters, commas, semicolons, `Bcc:`-style headers, over 254 chars, anything not shaped like one address |
| objet | newlines, control characters, headers, over 150 chars |
| message | control characters, headers, over 4000 chars, more than six links |

The newline rules are the important ones. **A newline in a field that
lands in a mail header lets an attacker append their own** — `Bcc:`
followed by five thousand addresses — and the mail goes out in her name.
That is how a contact form becomes a spam relay, and it is why the
subject gets the same treatment as the address: the subject *is* a header.

Bots get a honeypot field placed off-screen (not `display:none`, which
some bots skip and some screen readers announce), a two-and-a-half second
floor on how fast a form can be submitted, and a submit button that
disables after one click.

Nothing the visitor typed is ever echoed back into the page. A
"thanks, you said X" confirmation would be a stored-XSS vector for free.

### Handing the form over

The form POSTs to one endpoint that is the same for every user of the
service. **The access key is the only thing that says where a submission
goes.** There is no per-site URL to migrate.

Two keys live in `config.toml`, picked by the same `live` flag that swaps
the name and the robots policy:

```toml
[extra.contact.demo]
access_key = ""      # receives while live = false

[extra.contact.real]
access_key = ""      # receives once live = true
```

They are deliberately tied together. With a single key, flipping
`live = true` would put her name up, let crawlers in, and leave her
enquiries arriving in the developer's inbox — silently, until a client
says they never heard back. Identity and destination change together or
not at all.

To hand over:

1. **she** registers at web3forms.com with her address — the key is
   emailed to the destination, so it has to be her
2. she sends the key
3. it goes in `[extra.contact.real]`
4. `live = true` on launch

Same site, same URL, same form, same validation. One value moves.

An empty key means the form says it is not connected rather than posting
into a void. The key is public by design: it sits in the page HTML so the
browser can submit it. It is a destination, not a secret.

### Verifying a backend

```bash
./tools/injection-probe.sh
```

Sends three submissions straight at the endpoint with `curl`, bypassing
the page exactly as an attacker would, then you read the raw source of
what arrives. One control, one `Bcc:` injected through the mail field,
one through the subject.

**Pass** — only the control arrives intact, and no received message
carries a `Bcc:` or `Content-Type:` header we did not write.
**Fail** — pick a different backend.

It probes whichever key is live, and warns before touching a client
inbox. Every address in the payloads is under `example.com`, which
RFC 2606 reserves for documentation.

### Read this before trusting any of it

**All of the above runs in the visitor's browser.** An attacker does not
use the form — they POST straight at the endpoint with `curl`, and none
of this code executes.

This is the sign on the door. The lock is whatever validates on the
receiving side. Pick the backend for **its** server-side validation, rate
limiting and spam filtering, not for how pleasant its API is.

### Checking it

```bash
npm test     # compiles, then runs the validators against hostile input
```

Thirty cases, including every header-injection shape. CI runs it on every
pull request, so a change that loosens the email rule fails the build.

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
