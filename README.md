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

## Placeholders

Every image currently in the repo is machine-generated noise, for testing
layout and loading only. They carry no creative content and get deleted as
the client's real work lands.
