# myBureau

A desktop-metaphor site engine: every section is a *bureau* of draggable
folders, and the filesystem is the CMS.

First deployment: **valentina for STUDIO S**.

Engine by Bernardo Cohen — proprietary, **not** open source, and **not** work
for hire. See [LICENSE](LICENSE).
Design and creative assets belong to the client. See [NOTICE](NOTICE).

---

## For the client

**[GUIDE.fr.md](GUIDE.fr.md)** — in French, written for a Mac with
nothing installed and a GitHub account. Homebrew, GitHub Desktop, then
double-click `preview.command`. No SSH keys, no Node, and exactly one
command typed in a terminal in the whole document.

Every snippet in it was run verbatim against a scratch copy of the site
and checked in the built HTML, accented folder names included.

### What it costs her, counted

| | steps |
|---|---|
| first time, on a Mac with nothing | **3** — Homebrew, GitHub Desktop, double-click |
| see the site | 1 — double-click `preview.command` |
| add a project | 2 — a folder with an `index.md`, then the images |
| add a bureau | 1 — a folder with an `_index.md` |
| write a text | 1 — type under the `+++` |
| position an icon | 1, optional — `x`/`y`, or leave it to the grid |
| describe a photo | 1, optional — one line per photo |
| add a language | 2 config blocks, one command |
| publish | 2 clicks — Commit, Push |
| undo everything | 1 — Discard all changes |

The first row used to be eight, and two of those eight — installing Node
from a web page, and generating an SSH key — are exactly where someone
who does not do this for a living stops.

### Why the compiled JS is in the repo

`static/js/*.js` is committed, which is unusual and deliberate. It is the
difference between her needing Node, npm and a build step to look at her
own site, and her needing none of them: 35 KB in git against 23 MB of
`node_modules` and two more things to install.

`tools/js-is-current.sh` runs `tsc` and fails if the committed output
differs from `src/`. It runs in CI, which is where drift would otherwise
arrive unnoticed. Source maps stay ignored.

### Where a typo fails silently

Found by trying them, one at a time, on a copy of the site — not by
reading the templates. Each one **builds fine** and then does nothing:

| the mistake | what happens | now |
|---|---|---|
| `icon =` names a file that is not there | broken image on the desk | named by `tools/look.py` |
| a `url` with no `https://` | points inside the site, 404 | named |
| a `.tiff` or `.psd` in a project folder | the page has no images | named |
| a `wallpaper` on the gallery | ignored, it is a dark room | named |
| a project folder with no images and no text | an empty page | named |

`title` misspelt as `titel` fails the build outright, which is correct.

`tools/look.py` runs inside `./preview.sh`, so she sees these before
anyone else does. It warns and exits 0 — the site still works, it is
just not doing what the content file asked for.

---

## Previewing the site

```bash
./preview.sh          # or double-click preview.command in Finder
```

That is the whole thing. It needs **Zola and nothing else** — the
compiled JavaScript is committed, so there is no Node, no npm and no
build step in this path. It offers to install Zola on first run, reads
over the content and says what will not work, builds once so a mistake
is reported rather than silently served, then opens your browser and
reloads the page whenever you change a file. `Ctrl-C` to stop.

If it asks for Homebrew, paste the line it prints, then run it again.

Working on the TypeScript or the tools is the other path, and that one
does want Node:

```bash
npm install && npm test
```

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
| add a language to `config.toml` | the bandeau grows an `EN` link, `hreflang` appears, the strings follow — see [Languages](#languages) |

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

**A project's icon is its own first photograph.** `01.jpg` is already in
the folder, so there is nothing to draw, name or configure — and the desk
fills with the work rather than with grey symbols.

Most explicit wins:

1. a file named `icon.*` in the project folder — her artwork. It is the
   icon and it is never shown among the project's photographs.
2. `icon = "img/icons/folder-rust.svg"` in the front matter
3. the first image in the folder
4. the extension in the **title**, when the folder holds no image at all:

| title ends in | icon |
|---|---|
| `.mov` `.mp4` `.m4v` `.avi` `.webm` | film strip |
| `.jpg` `.png` `.gif` `.webp` `.tif` … | Polaroid |
| anything else | document |

A folder keeps its folder: one that looked like a photograph would stop
reading as somewhere you can go into. Her textured folders are an
`icon.png` beside the `_index.md`.

Folders ship in four colourways — `folder.svg` (amber), `folder-rust`,
`folder-olive`, `folder-slate`.

### What a click does

One rule, and two exceptions that fall out of it rather than being
configured.

> **A click shows you the thing.** It does not take you anywhere. The ⬜
> in a window's title bar is the deliberate second step to the page.

| you click | you get |
|---|---|
| a folder **on the home desk** | its own desk, its own wallpaper — a new page |
| a folder **anywhere else** | a window on the desk it sits on, translucent, several at once |
| a project with a **video** in it | the film window, text beside it, minimisable |
| any other project | a **preview** window, modal, Escape closes it |
| a project with **no image at all** | its page — there is nothing to preview |
| a photograph in **pellicules** | that photograph, in a window |

`opens = "page"` in a project's front matter skips the window and goes
straight to the page — **including for a film**, where the page shows the
video at the top and the photographs below it. It is tested before
anything else, so it means the same thing on every kind of project.

The project page renders the video whether or not the override is set,
which is also what a visitor with no JavaScript gets: for them this page
*is* the film window.

One level of windows per desk. A folder inside a window navigates to its
own desk, because this template engine has no macros and so nothing can
render itself — there has to be a floor, and a floor that navigates is a
floor that works. `tools/content-check.py` asserts there is never a
`data-window` without a dialog to open, which is what keeps the icon
template and the window templates agreeing.

### Along the bottom

`site by …` in the right corner (LICENSE §4), the social marks in the
centre, on every page. The marks are their owners' trademarks, taken
unmodified from each owner's own brand kit — `static/img/brand/SOURCES.md`
names the exact asset behind every file and what may not be done to them.

### Regenerating the art

```bash
python3 tools/icons.py           # icons + wallpapers
python3 tools/icons.py --check   # validate, write nothing
```

Icons and wallpapers are **code**, for the same reason the cursors are:
an SVG diff in a pull request is readable, a binary diff is two blobs.

Wallpapers are SVG too — a duotone wash, film grain from
`feTurbulence`, and a vignette. Under 1 KB each instead of ~380 KB, and
the grain is computed rather than compressed, so it never bands.

### A desk's wallpaper

**Drop a file called `wallpaper.*` beside the bureau's `_index.md`.**
That is the whole of it — the same way an icon is `icon.png` in the
project folder and a film's still is `poster.jpg` beside it.

```
content/da/
    _index.md
    _index.en.md
    wallpaper.jpg     ← the desk's background
```

It serves **every language**, because one photograph has no language.
And a bureau **inside** that one inherits it, so `maison cosette` looks
like the `da` it sits in without carrying its own copy of the same
picture. Declare one of its own to break the inheritance.

Most explicit wins: the file, then `wallpaper = "..."` in the front
matter (a path under `static/`, still supported), then the home desk's,
so a new bureau is never a black rectangle. Having both the file and the
line is a line that does nothing, and `look.py` says so.

This used to be the one thing in the engine that did not live where the
content lives: a path typed into **both** `_index.md` and `_index.en.md`,
pointing at `static/img/`. Changing one and forgetting the other left a
language on the old picture, silently.

> A photograph's built url is derived from its PATH, not its contents.
> Replace `wallpaper.jpg` with a different picture and the url does not
> change — so a browser that already has it keeps showing the old one
> until its cache expires. Not a bug to fix here, but the reason "I
> changed it and it still looks the same" is usually a hard refresh away.

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

### On a phone

The gallery and the project pages already worked — they were always
scroll pages. Two things did not:

- **the bandeau** collided, the centre label running into the wordmark on
  one side and the nav on the other. It now stacks in reading order: who
  this is, where you are, where you can go.
- **the bureau** overlapped. Percentage positions that compose nicely on
  a wide screen crowd into each other at 390px, so icons sat on top of
  one another and some were unreachable.

A bureau needs room to arrange things in, and a phone has none. So below
`40rem` the desk stops being a scatter and becomes a three-column grid —
same icons, same labels, same destinations, tidied because there is no
space to be untidy in. `x` and `y` are simply ignored there.

**Icons can be picked up on a phone too.** The script measures where the
grid put everything, pins those positions as absolute and adds
`arranged` — nothing moves on screen, but the icons stop being laid out
and start being objects again. Dragging, the nesting guardrail and the
tidy-up on return all work exactly as they do with a pointer.

No long-press is needed, because a bureau does not scroll: there is
nothing for a drag to fight. A short movement threshold keeps a tap from
counting as a drag, so tapping still opens things.

Without JavaScript the grid simply stays a grid — tidy, reachable, not
draggable.

### Content passing under the bandeau

The bandeau is fixed, so on a page that scrolls everything slides beneath
it — paragraphs crossing the wordmark, photographs running into the nav.

The scrim that prevents it is the page's **own ground colour** faded to
nothing. At rest there is only background underneath, so it is invisible;
it appears only as something rises into it. No scroll listener, no
measuring, no state — it is self-regulating because it is the same colour
as whatever it is hiding.

Not on a bureau: there the wallpaper *is* the content and must not be
veiled. That surface has its own much shorter scrim under the bar, for
legibility rather than for scrolling.

### Leaving and coming back

Icons you move are remembered **for the session**, per bureau. Leave a
bureau and return, and they are put back where you dropped them and then
walked home — a visible tidy-up rather than a reset that already
happened. Close the tab and the memory goes with it.

The walk is a FLIP animation: the icon is never actually laid out in the
wrong place, only its transform moves, so the page is correct from the
first frame.

### Link to somewhere else

Any desktop item with an `http` or `https` address becomes a shortcut.
Add one to the `items` list in `content/_index.md`:

```toml
items = [
  { name = "instagram", icon = "img/icons/shortcut.svg", url = "https://instagram.com/HER_HANDLE", x = 52, y = 30 },
  { name = "youtube",   icon = "img/icons/shortcut.svg", url = "https://youtube.com/@HER_CHANNEL", x = 52, y = 58 },
]
```

| field | what it does |
|---|---|
| `name` | the label under the icon — this is what a visitor reads |
| `url` | where it goes. Replace the placeholder with the real account |
| `icon` | `shortcut.svg` for anything off-site |
| `x` `y` | position in percent. Omit both and it takes a free grid slot |

The accounts shipped today are **placeholders pointing at the bare
instagram.com and youtube.com homepages**. Put the real handles in before
launch:

```toml
url = "https://instagram.com/studio.s"        # not instagram.com/
url = "https://youtube.com/@studios"          # not youtube.com/
```

Any service works the same way — Vimeo, Behance, LinkedIn, a Linktree, a
PDF portfolio. It is a url and a label.

Links that leave the site get `target="_blank"` and
`rel="noopener noreferrer"` automatically. Internal links do not: the
test is whether the address contains this site's own `base_url`, because
`get_url` makes internal links absolute too and a scheme alone proves
nothing.

**Why a shortcut icon and not the brand logos.** The Instagram and
YouTube marks are trademarks with published guidelines — do not alter,
do not recolour, minimum sizes. A drawn approximation would breach both
the guidelines and the trademark. A flat modern logo would also look
wrong on a 1995 desktop, where a shortcut with a filename does not.

If the real marks are wanted, download the official brand assets from
each service and point `icon` at them. Do not use a logo pack from a
third-party site — see NOTICE.

### Add a film

Drop a video into a project folder and it stops being a page and becomes
a window on the bureau:

```
content/da/junes-cry/
    index.md      title, position, and the text that explains the film
    clip.mp4      ← this is what makes it a film
    poster.jpg    optional still, shown before it plays
```

Supported: `mp4` `webm` `mov` `m4v` — set in `config.toml` under
`video_types`.

Expanded, the window is a spread: the film on the left, your text on the
right, divided like an open book. The text is simply the body of
`index.md`, so it is written where everything else is written.

**Minimised**, it stops being modal, shrinks to the corner, drops the
text and keeps playing — so the bureau underneath is usable again and
folders can still be dragged around while the film runs. The same button
brings it back up; it is a toggle, and it says which way it goes. Closing
it stops the sound.

(The title bar does not restore it, and cannot: a window drags by its
bar, a drag captures the pointer, and the capture retargets the click. A
handler there never fires — see the comment in `src/desk.ts`.)

The project page still exists, so without JavaScript the icon simply
navigates there. Nothing is lost, it is just less fun.

### The placeholder photographs

Every photograph in this repository is a stand-in, fetched from Lorem
Picsum (which serves Unsplash photography) and seeded so the same seed
returns the same picture on every machine and every build.

```bash
python3 tools/placeholders.py           # fetch what is missing
python3 tools/placeholders.py --check   # report, write nothing
python3 tools/placeholders.py --purge   # delete every one of them
```

Real pictures, because procedural noise cannot answer the questions that
matter. Swapping them in immediately exposed one: **white text over a
bright sky was barely legible.** The shadow had been tuned against dark
synthetic gradients and failed the first time it met a cloud. It now uses
three layers — one hugging each glyph, one for the edge, one for
separation — and the top bar sits on a scrim, the way a menu bar survives
a light wallpaper.

**They must all go before launch.** Not for licensing — the Unsplash
License permits this — but because a portfolio built from someone else's
photographs misrepresents the photographer whose name is on it. Every
path is listed in `tools/placeholders.py`, so `--purge` removes the lot.
See NOTICE.

### Images are resized at build time

Photographs are not served as they were exported. Every one is resized
and converted to WebP during the build, at two widths, and the browser
picks:

| where | widths served |
|---|---|
| `pellicules` gallery | 560 and 1120 |
| project pages | 900 and 1800 |

The originals stay in `content/` untouched — drop in whatever came out of
the camera. Nothing is overwritten and nothing needs preparing.

Every image also carries its **original** `width` and `height`. That is
not decoration: it is what lets the browser reserve the right space
before the file arrives. Without it a masonry of lazily-loaded images
reflows every time one lands, which is what made the gallery feel like it
was struggling. The bytes were part of it; the jumping was the rest.

Generated files live in `public/processed_images/` and are rebuilt by
`zola build`, so nothing extra is committed.

### Add photos to `pellicules`

Drop image files straight into `content/pellicules/`. The gallery picks
them up in filename order. Name them `01.jpg`, `02.jpg` … to control order.

### Change a wallpaper

The wallpaper goes through the same resize pipeline as every other
photograph — two WebP sizes, 2000px and 1280px, the smaller one served
on phones. Drop in a 6 MB camera JPEG and the visitor still gets about
80 KB. Measured on the current placeholders: 145 KB → 76 KB on a
desktop, 36 KB on a phone.

A wallpaper declared on the `pellicules` gallery does nothing — that
page is a deliberate dark room (`body.gallery`), not a desk. The content
check asserts a declared wallpaper actually renders, so if that ever
silently stops being true, it fails rather than going quiet.


Replace the file in `static/img/`, or point a section at a different one:

```toml
[extra]
wallpaper = "img/my-wallpaper.jpg"
```

### One pass decides where things sit

Layout runs through a single function, and running it twice gives the
same answer as running it once. It runs on load, on resize and on every
orientation change.

For each icon, always in this order:

1. **a base position** — the grid on a narrow screen, the position in the
   content file on a wide one
2. **the visitor's own** — if they dragged it, that wins over the base
3. **a clamp** — nudged back on if it would hang off the desk or hide
   under the bandeau

Step 2 is stored as a **fraction of where the icon was allowed to go**,
not as a count of pixels. 1180px from the left is the right-hand side of
a laptop and off the edge of a phone; "nine tenths of the way across" is
the same place on both. A fraction of the *placeable area* rather than
of the desk, which is the part that makes corners work — `1` means "as
far right as it goes" at any size, instead of "past the edge, and then
clamped back by the icon's own width".

So the clamp is now the exception rather than the mechanism. A position
restored from a fraction is already inside the bounds by construction,
and on an ordinary resize the clamp changes nothing at all. It stays as
a guard for the cases a fraction cannot cover — a landscape phone from a
desktop is a different enough shape that something may still need
nudging.

The same fractions go into `sessionStorage`, so coming back to a bureau
in a window you have since resized animates from where you actually
left things rather than from somewhere they have never been.

Nothing in that pipeline destroys the position written in the content
file, so turning a phone sideways and back puts everything exactly where
it started.

The walk-home animation on returning to a bureau writes no positions at
all. It only animates the gap between where you left something and where
this pass has put it.

### Icons stay on the desk

`x` and `y` are percentages of the desk, but an icon is a fixed number of
pixels wide. At 1440px an icon is about 11% of the width, so `x = 82%`
sits comfortably inside; at 820px the same icon is 18% wide and its right
edge lands at 101% — half on, half off. The same applies vertically, and
the bandeau is fixed on top, so an icon placed high on a short window
disappears underneath it.

Anything out of bounds is nudged back on, on load and on resize. Icons
that already fit are never touched, so a deliberate arrangement stays
exactly where it was put.

That is about `x`/`y` from the content file, which are percentages of
the desk and so cannot account for the icon's own width. A position the
*visitor* chose is stored differently — see the fractions above — and
does not need the clamp on an ordinary resize.

### Move an icon

Edit `x` / `y` in that project's `index.md`. Visitors can drag icons around
in the browser, but those moves are not saved — `x`/`y` is the resting layout.

### Describing a photograph

Every image ships with `alt=""`, which tells a screen reader there is
nothing there. For an icon that is right — the name beside it is the
link text. For a photograph in a portfolio it is wrong, and inventing a
description for someone else's photograph is worse than silence.

So there is a place to put one, and it is empty until she fills it:

```toml
+++
title = "theodora.jpeg"

[extra.alt]
"01.jpg" = "Deux silhouettes sur une plage, au crépuscule."
+++
```

Keyed by file name, in the page's own front matter — which means it is
already per-language, since each language has its own content file. An
image with no entry keeps `alt=""`. Works the same on a project page and
in the `pellicules` gallery.

### Supported image types

`jpg` `jpeg` `png` `webp` `avif` `gif` — set in `config.toml` under
`image_types`.

---

## Languages

The site is French. Adding another one is two edits in `config.toml` and
one command — no template, no code, no new build step. If adding a
language ever means editing a template, that is a bug worth reporting.

### Add a language

Say Spanish. In `config.toml`:

```toml
[languages.es]
title = "myBureau"

[languages.es.translations]
```

Then:

```bash
python3 tools/i18n.py --sync
```

That writes every missing string into `[languages.es.translations]` and a
Spanish copy of every page into `content/`, each one still in French and
marked `# TODO translate`. **The site builds and works from that moment**
— `/es/` exists, the bandeau carries an `ES` link, every page is
reachable. Translating is then editing text in place, at whatever pace.

```bash
python3 tools/i18n.py          # what is still in French
```

```
  [es]
    words  1/30 translated
             still in fr: nav_contact
             still in fr: window_close
    pages  19/19 exist
```

Nothing is ever overwritten. Run `--sync` as often as you like — a
translation already made is not up for revision.

### Two kinds of text, two places

| | where | example |
|---|---|---|
| words the engine says | `config.toml`, `[translations]` | buttons, errors, `back to` |
| words she writes | `content/*.md` | titles, project text |

A page in one language is a file next to the original with the language in
its name: `index.md` → `index.es.md`, `_index.md` → `_index.es.md`.
Photographs are **not** copied — one file serves every language, so
translating a page never touches an image.

### What happens when something is missing

| missing | what happens |
|---|---|
| a word | **the build fails.** Zola will not guess. `--sync` fills it with the French so it never gets to that point |
| a page | that page is simply not in that language, and drops off that language's desktop without a word of complaint |
| a key nothing asks for | `tools/i18n.py` names it, and exits non-zero |
| a key asked for that nobody wrote | same — and `zola build` fails too, if it is in a template |

The last two are the typos. `python3 tools/i18n.py` runs in CI and in
`./preview.sh`, so a misspelled key stops the build rather than quietly
rendering as `err_mail_shap` in a language nobody on the team reads.

Untranslated is not an error — it is a stage of work, and it only prints.

### Remove a language

Delete its two blocks from `config.toml`, then:

```bash
find content -name '*.es.md' -delete
```

`--prune` does the same thing for pages whose original has been deleted.

### What the engine does with the language list

Read from the list, never written by hand:

- the `ES` / `EN` / `FR` links in the bandeau — to **the same page** when
  it has been translated, to that language's desktop when it has not
- `<html lang>` on every page
- `<link rel="alternate" hreflang>` for each language, so the two are not
  read as duplicate pages
- the strings the browser needs, written onto each page's `<body>` as
  `data-i18n` — the only way `desk.js` and `contact.js` get words, since
  they cannot call `trans()`. An attribute rather than a `<script>` block
  because Tera escapes attribute values, so a string containing
  `</script>` cannot end the element early

Validation messages are **keys**, not sentences: `checkEmail` returns
`err_mail_shape`, and the page supplies the words. That is what keeps
`tools/contact-check.mjs` runnable in Node, where there is no language.

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

### Verdict on Web3Forms — tested, 17 Oct 2026

**Safe. Fail-closed.** Two tests, read from the raw source of what arrived.

**1. Server-side POSTs are refused outright.** Every `curl` request returns
403 — tested bare, with a browser User-Agent, with a matching `Origin`,
with a `Referer`, and with all three:

> This method is not allowed. Use our API in client side...

So the cheap attack — point `curl` at the endpoint and fire payloads —
does not work. That is a heuristic rather than a proof (a headless browser
is still a browser), but it removes the drive-by scanners.

**2. Injected headers never become headers.** Submitted from a real
browser, bypassing our own validation, with a newline and `Bcc:` in the
mail field. The DKIM `h=` lists settle it, because they enumerate every
header that was signed:

```
clean     h=From:Reply-To:To:Subject:MIME-Version:Content-Type:Message-ID:Date
poisoned  h=From:         To:Subject:MIME-Version:Content-Type:Message-ID:Date
```

Exactly one header differs. Given a poisoned value they **drop `Reply-To`
altogether** rather than sanitise it and send. Fail-closed: they would
rather lose reply-ability than emit a header they cannot vouch for.

The payload appeared only in the body, with the colon HTML-escaped
(`Bcc&#x3A;`) — deliberate output encoding, not luck.

**Also confirmed:** a clean submission does set `Reply-To` to the
visitor's address, so replying works normally. The sending domain is
theirs (`web3forms.com` via Amazon SES, SPF/DKIM/DMARC all pass), so
abuse would burn their reputation and not the client's.

**3. A poisoned subject cannot inject either** — and it is handled
differently, which is the interesting part:

| field | poisoned with | what they do |
|---|---|---|
| email → `Reply-To` | newline + `Bcc:` | **drop the header entirely** |
| subject → `Subject` | newline + `Bcc:` | **strip the newline, keep the value** |

```
Subject: PROBE subject injectionBcc: attacker@example.net
h=From:Reply-To:To:Subject:MIME-Version:Content-Type:Message-ID:Date
```

`Subject` is present, no `Bcc` in the signed list, and the payload sits
inside the subject's *value* as literal text — note `injectionBcc:` run
together where the newline was removed.

Two strategies, each right for its field. An address containing a newline
is definitionally invalid, so there is nothing to salvage and dropping it
is correct. A subject is free text someone legitimately typed, so
stripping the newline preserves their message. That is considered design,
not one blunt rule applied twice.

**They log the visitor's IP** and print it in the notification footer. IP
addresses are personal data under GDPR, which is why the privacy line
beside the form names it.

### Testing a browser-only backend

Web3Forms refuses every request that does not come from a browser. Tested
from `curl` with a browser User-Agent, a matching `Origin`, a `Referer`,
and all three together — **403 in every case**:

> This method is not allowed. Use our API in client side or contact
> support with server IP address (Pro plan is required)

That is a genuine defence: the cheap attack — point `curl` at the
endpoint and fire injection payloads — simply does not work. It is a
heuristic rather than a proof, so a headless browser could still get
through, but it removes the trivial path and the drive-by scanners that
use it.

It also means `tools/injection-probe.sh` cannot test them. To check
whether they strip injected headers, you need a real browser:

1. open the live site, open the contact window
2. open DevTools → Console
3. paste this and run it

```js
fetch("https://api.web3forms.com/submit", {
  method: "POST",
  body: new URLSearchParams({
    access_key: document.querySelector('[name="access_key"]').value,
    email: "probe@example.com\nBcc: should-not-exist@example.net",
    subject: "PROBE header injection",
    message: "If the received headers carry a Bcc, this backend is unsafe.",
  }),
}).then(r => r.json()).then(console.log);
```

This runs from the page's own origin, so it reaches them — and it
bypasses our validation entirely, which is the point: it tests **their**
handling, not ours.

Then open what arrives and read the raw source (Gmail: ⋯ → Show
original). **A `Bcc:` header we did not write means the backend is
unsafe.** No such header means they strip or escape newlines correctly.

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
npm run check             # tsc --noEmit, strict
npm test                  # the above, plus the contact and language checks
python3 tools/i18n.py     # every string asked for was written; what is untranslated
zola build                # fails on broken templates, links and missing strings
```

```bash
node tools/desk-check.mjs        # a remembered position survives a resize
python3 tools/content-check.py   # the content contract against real mistakes
./tools/ready.sh                 # is this repo ready to be somebody's real site
python3 tools/prune.py --check   # what the built site carries and never asks for
```

### The panel

`preview.command` starts two things: `zola serve` as before, and
`tools/studio/server.py` — a panel for editing `content/` by hand.

```
double-click preview.command
   ├── studio   127.0.0.1:1112   python stdlib, writes content/
   └── zola     127.0.0.1:1111   builds the site, watches content/
```

#### The middle of the panel is the site

Not a drawing of it. The panel **proxies zola onto its own address** and
frames the result, so the page in the middle is the page zola built —
same wallpaper, same icons, same layout, because it is the same renderer.

Being same-origin is the point: the panel can reach into the real page,
find the icons it really rendered, and let you move them. **The site's own
`desk.js` still does the dragging** — with the collision walk and the
clamping that are already correct — and the panel only writes down where
it ended up. There is one renderer in this project and one dragger, and
neither of them is in the panel.

Every absolute url is rewritten on the way through, not just the links:
the page carries `default-src 'self'`, and once the document sits on the
panel's address, `self` means the panel. A stylesheet still pointing at
zola's port would be blocked by the site's own policy.

The cost is zola's live-reload, whose socket no longer finds its way
home. The panel reloads the frame itself — one mechanism rather than two,
and one it can be careful with.

#### The loop, measured

The panel is not the slow part and never was:

```
the panel writes a change        ~13 ms
zola rebuilds the site           ~1.3 s
and answers 404 for part of it   3 edits in 4
```

Three rules fall out of those numbers:

- **a drag reloads nothing.** The site's own `desk.js` moved the icon
  before the write was sent, so the frame is already correct. Reloading
  would throw a correct view away to fetch an identical one — and land in
  the 404 while doing it. `NOTHING_TO_SEE` in `app.js` is that list.
- **everything else waits rather than races.** The frame is reloaded only
  once the page answers, so the blank flash cannot happen.
- **reloads are debounced.** Four photographs dropped at once is one
  reload.

And the server does not report its own writes back: a verb leaves its
fingerprint behind so the watcher does not announce, a moment later, a
change the panel made itself and already has on screen. Without that the
counter moved twice per edit and every careful rule above was defeated.

#### What it may do

A closed list in `tools/studio/verbs.py`, not a file manager:
`new_project`, `new_bureau`, `place`, `retitle`, `set_body`, `set_icon`,
`set_wallpaper`, `add_image`, `reorder`, `remove_image`, `undo`.

#### Making one, and what it will look like

A new project is a folder and **one file per language its neighbours
have** — a project born in French only, on a bilingual site, is a
half-translated site by construction, and nothing would say so until
somebody switched language.

The kind picked when making it is written into the name as an extension,
because that is how the engine gives a face to a project with no
photograph yet: `.jpg` a photo, `.mov` a film strip, `.pdf` a document,
nothing at all a page. It is a starting point, not a decision — the
appearance can be replaced with her own artwork at any time, and a
project with photographs wears its first one regardless.

`set_icon` writes `icon.<ext>` beside the content file. It is the only
way a **bureau** can be given a face: a bureau has no photographs to take
one from, so until this verb existed its appearance could not be changed
from the panel at all.
Two rules in that file are not negotiable, because both have bitten this
project:

- **every verb touching a project touches every language file it has** —
  a position written to one and not the other is the oldest trap here.
  A *title* is the exception and is deliberately per-language: French and
  English names are not the same words.
- **front matter is edited surgically**, one line by regex, leaving the
  rest byte for byte. These files carry load-bearing comments; a
  parse-and-rewrite would eat them silently.

Writes go through a temp file and `os.replace`, or `zola serve` reads a
half-written file and flashes an error at her for something she did not
do. Every verb is journalled to `.studio/` with the previous text, so
**Annuler** takes it back; a deleted photograph goes to `.studio/trash/`
rather than being unlinked. `.studio/` is git-ignored.

#### What kind of thing is this?

The engine has more objects than folders and photographs, and the panel
names which it is looking at, because they do not behave alike:

| | |
|---|---|
| **bureau** | a wallpaper and icons you can move |
| **galerie** | photographs in columns; no icons to move |
| **projet · photos** | opens as a preview; first photograph is the icon |
| **projet · page** | `opens = "page"`; goes straight to its own page |
| **film** | a video, with the photographs under it |
| *(window / shortcut)* | declared in `config.toml`, not a folder — the panel shows them on the desk because the site does, and leaves them alone |

#### Why it is not a hole in her machine

Bound to loopback. A token minted at startup and required on every
request that reads or writes her work — `/api/*` and `/media/*` — so a
page that cannot read the address bar cannot act.

`/site/*` is **not** behind the token, and cannot be: the frame's `src`
is written in the markup and every link inside the page is a plain href.
That opens nothing — `zola serve` is already serving those exact bytes on
its own port with no token at all, on the same loopback address.

The panel sends `X-Frame-Options: SAMEORIGIN`, not `DENY`. It frames its
own proxy, and `DENY` refused it — Firefox said so plainly. Cross-site
requests refused even with a token. Every path through `verbs.inside()`,
which resolves symlinks and refuses anything outside `content/`.

The panel's own `app.css` and `app.js` are served **without** a token,
because a `<link>` and a `<script>` cannot carry one — the browser asks
for exactly the url in the markup. That was once a bug: with the token
required there, the page loaded naked and every button was dead.
`tools/studio/check.py` now fetches the page, parses out every `href` and
`src`, and requests each one the way a browser would.

`tools/studio/app-check.mjs` runs `app.js` in a stubbed DOM — the trick
`desk-check.mjs` uses for `desk.js` — and takes the element ids **from
app.html**, so a renamed element fails the check instead of silently
breaking the panel.

### What gets deployed, and what does not

Zola copies every photograph sitting beside a content file into the
output — and again into each translated output, byte for byte. The
templates serve what `resize_image` made, so those originals are shipped
and never requested: **19.5 MB of 35.3 MB** on the demo, more than half.

`tools/prune.py` drops them, in CI, between `zola build` and the artifact
upload. It never runs on her machine; `preview.sh` does not call it, and
it only ever touches `public/`, which is generated and git-ignored. The
photographs stay in the repository, which is where they belong.

Two things keep it from eating the site. Anything the image pipeline
produced is **never a candidate** — so the worst a bad matcher can do is
delete an original, not the visible site. And every media url the built
pages ask for is resolved against the pruned tree afterwards: if one
cannot be found it exits non-zero and nothing is uploaded.

Matched by url **suffix**, not by parsing off a base_url prefix, so it
keeps working the day the site moves from a github.io subpath to her own
domain.

`desk-check` runs the real `static/js/desk.js` in a Node vm with a
stubbed document — so it is a smoke test that the script loads at all,
and then it calls the script's own geometry functions rather than a copy
of the arithmetic. A copy drifts, and drift in that file is what three
of the last four pull requests were fixing. It walks every pair of five
screen sizes, nine drop points each, and checks that a remembered
position is never left outside the area it is allowed to occupy. Against
the previous pixel storage, 16 of those 20 pairs fail.

The last one is the interesting one. It copies the whole site into a
scratch directory ten times, and each time adds one mistake a person
actually makes — a project with no icon, `PHOTO.JPG` in capitals, the
same name in two bureaus, three folders with no `x`/`y`, an apostrophe in
a folder name, a page added in French only, a bureau that declares a
wallpaper, alt text in front matter — then builds and reads the HTML.

"It builds" is not the test. A build can succeed and still have lost the
icon, stacked two folders on one pixel, or given two pages the same
`view-transition-name` so the morph silently dies. Each case says what it
expects to **see**.

### Opening a built page from disk

You cannot, any more — the Content-Security-Policy means a `file://`
page loads with no CSS and no script. Use `./preview.sh`. (The policy is
explained where it is written, at the top of `templates/base.html`.)

CI runs all of them on every pull request; `main` deploys to GitHub Pages on merge.

---

## Layout

```
content/          the site — folders mirror the desktops
templates/        Tera templates (base, section, index, page, gallery)
src/desk.ts       drag + window behaviour, the only script
src/contact.ts    contact form validation (returns translation keys)
tools/i18n.py     languages: what is missing, and the files to fill in
static/css/       one stylesheet
static/img/       wallpapers and generic icons
_ref/             design references, git-ignored (local only)
```

## Stack

Zola (Rust) builds static HTML. TypeScript compiles to plain JS for
dragging and windows — 28 KB raw, 9 KB over the wire, plus 7 KB raw for
the contact form. Transitions are native CSS — View Transitions and
scroll-driven animation. No frontend framework, no bundler, no runtime
dependencies.

What a visitor downloads, measured, not estimated:

| | shell | wallpaper | images |
|---|---|---|---|
| a bureau (desktop) | 98 KB | 149 KB | icons, ~3 KB |
| a bureau (phone) | 98 KB | 76 KB | icons, ~3 KB |
| the gallery | 98 KB | — | 537 KB, all lazy |
| a project page | 98 KB | — | 134 KB, first one eager |

The shell is CSS + JS + one font. Wallpapers go through the same resize
pipeline as the photographs, at two sizes.

## Client material

This repository is public. Briefs, proto decks, mood boards and design
source files are the client's property and must never be committed —
they live in `_ref/`, which is git-ignored and local only.

Design source extensions (`.pdf`, `.psd`, `.ai`, `.fig`, …) are ignored
repo-wide as a backstop, but the rule is the convention, not the
pattern list: **if a client sent it, it goes in `_ref/`.**

## Handing the site over

The demo stays here, with placeholder content and `live = false`. Her
site becomes a **separate repository under her own account**, created
from this one as a template.

```bash
./tools/ready.sh
```

Run that in whichever repository is about to go live. It compares what
`config.toml` claims against what the repository actually is, and prints
what is left, in order.

### Where a GitHub Pages site lives

Two shapes, and the repository name is what decides:

| repository name | the site is served at |
|---|---|
| `hername.github.io` | `https://hername.github.io/` — **the root** |
| anything else, e.g. `studio-s` | `https://hername.github.io/studio-s/` |

The first is a **user site**: one per account, and the repository name is
not a choice — it has to be exactly her username followed by
`.github.io`. The second is a **project site**: any name she likes, but
the name then appears in the URL.

So "at the root" and "named whatever she wants" are the same thing only
if her username is the name she wants.

A **custom domain** removes the question. Attached to either shape, the
site serves at the domain root and the repository name stops mattering
to the URL. Put the domain in `base_url`, put it again in
`static/CNAME`, and point the DNS at GitHub. If a domain is coming,
pick whichever repository name reads best and do not think about this
table again.

Either way `base_url` has to match. If it does not, nothing errors —
every link and every image on her published site quietly points at this
repository's Pages instead. `ready.sh` is mostly there to catch that.

### Creating her repository from this one

Once, here: **Settings → General → Template repository**, ticked. That
puts a green **Use this template** button on the front page.

Then, from her account:

1. open this repository on github.com
2. **Use this template → Create a new repository**
3. owner: her account; repository name: see the table above; **Public**
   (GitHub Pages needs a paid plan to publish from a private repository)
4. **Create repository**
5. **Settings → Collaborators → Add people** — add whoever is doing the
   switchover, with the **Admin** role, because enabling Pages needs it
6. **Settings → Pages → Build and deployment → Source: GitHub Actions**

A template is not a fork. There is no "forked from" banner on her
repository, it can be made private later, and it is hers from the first
commit. The engine files (`templates/`, `src/`, `static/css/`, `tools/`)
stay separate from hers (`content/`, `config.toml`), so a later engine
improvement is a diff applied to those paths — it does not need a shared
git history.

### Turning an existing repository into a user site

Nothing in GitHub asks whether a site is a user site or a project site —
it reads the repository's **name** and works the URL out. So changing
your mind later is a rename, and nothing else:

1. **Check the name is free.** One user site per account, so if a
   repository called `hername.github.io` already exists — an old
   experiment, usually — that name is taken. Rename or delete it first.
2. **Settings → General → Repository name** → `hername.github.io` →
   **Rename**. The site moves to the root within a minute or two.
3. **Settings → Pages** — confirm *Your site is live at
   `https://hername.github.io/`*. That line is the ground truth, not
   this README.
4. **`base_url` in `config.toml`** → `https://hername.github.io`, with
   no path after it. Commit and push.
5. `./tools/ready.sh` to confirm.

Step 4 is the one that is easy to forget, and forgetting it does not
break loudly: the pages still load, with every link and image pointing
at a path that no longer exists.

Between the rename and the push there are a few minutes where the site
is wrong. On a site nobody has bookmarked yet this does not matter —
but it is why the rename belongs before the launch, not after it.

> **Renaming does not change the local clone.** GitHub keeps serving the
> old address by redirect, so GitHub Desktop carries on pushing and
> nothing announces that the name has moved. `ready.sh` asks GitHub what
> the repository is called now and says so — but only if the `gh`
> command is installed. Without it, it can only trust the old name. The
> repair it prints is one line:
> `git remote set-url origin git@github.com:owner/newname.git`

### The switchover, in order

1. `base_url` → her Pages URL (`./tools/ready.sh` prints the right one)
2. `python3 tools/placeholders.py --purge`, then her real work into `content/`
3. her own Web3Forms key into `[extra.contact.real]`
4. **`live = true` last**

Four after two is the only hard ordering constraint. `live = true` is the
moment her name goes on the site; if the placeholders are still there it
publishes stock photographs under her byline, which is the exact thing
the flag exists to prevent.

---

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
6. `python3 tools/i18n.py` clean — nothing half-translated that she did not choose to leave
7. the `site by` credit present — it is a condition of the licence, see LICENSE §4

## Placeholders

Every image currently in the repo is machine-generated noise, for testing
layout and loading only. They carry no creative content and get deleted as
the client's real work lands.
