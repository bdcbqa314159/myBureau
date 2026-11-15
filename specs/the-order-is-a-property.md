# The order is a property

**Status:** `[extra.place]`, written by `reorder`, read by all three
displays and by the panel's own list.
**Date:** 2026-11-15

## What she asked for

> you need to play with the position property not the name

She drags a photograph in the gallery, it appears to move, and it
springs back where it was.

## Why it sprang back

`reorder` renamed her files into `01, 02, 03 …` in the order she had
arranged them, so that zola's alphabetical listing was her order.

**zola names a resized image from the SOURCE PATH and the resize
parameters, and caches the result in `static/processed_images`.** Rename
`03.jpg` to `01.jpg` and the page asks for `01.<hash>.webp` — which is
already in the cache from the last build, holding the old photograph. So
the sources swapped and the published page came back byte for byte
identical.

Verified by building a copy of the site before and after a reorder:

| | before | after |
|---|---|---|
| `01.jpg` on disk | `229fa2b8` | `72359edc` |
| its published thumbnail | `c1fa7577` | **`c1fa7577`** |

Replacing a file under the same name *does* come through — the cache
notices a write, not a rename — which is why this stayed invisible until
her photographs were already `01…12` and a second arrangement had
nothing left to rename.

So renaming was not merely rude about her names. **It could not work.**

## What it is now

```toml
[extra.place]
"vue sur la mer.jpg" = 1
"theodora.jpg" = 2
```

A rank per file, beside `[extra.alt]` and `[extra.column]`, written to
every language file. **No file is touched.**

## How a template reads it

zola hands over `assets` alphabetically and Tera cannot sort a list by a
value looked up elsewhere — no `concat`, no sort-by-key. So the list is
walked **once per turn**, and each photograph waits for its own:

```
{% set turns = w.assets | length + 1 %}
{% for turn in range(start=1, end=turns + 1) %}
{% for asset in w.assets %}
  {% if rank != turn and not (rank == 0 and turn == turns) %}{% continue %}{% endif %}
```

Turn 1 emits rank 1. **The last turn emits everything she has never
arranged**, in the order zola gave it — which is what a file dropped in
through Finder is, and it appears rather than vanishing. A rank naming a
photograph that is gone is never matched.

In `gallery.html` the closed windows are **not** put in her order: a
closed dialog has no position. Only their ids have to agree with the
links, and `loop.index` is each photograph's place in `assets`, which
the turn loop does not change.

| display | what it shows |
|---|---|
| `gallery.html` | pellicules, the grid |
| `page.html` | a page's photographs, and so which one is the wide one |
| `_place.html` | the stops on the road |
| `model.photographs` | the panel's own list — a list in a different order would be a list that lies |

## Acceptance criteria

| # | criterion | oracle |
|---|---|---|
| 1 | she arranges, and the site comes out in that order | two builds compared, all three displays |
| 2 | not one file is renamed | the listing before equals the listing after |
| 3 | a name of her own survives being arranged | `vue sur la mer.jpg` is still called that |
| 4 | the panel's list agrees with the site | `model.photographs` sorts by rank |
| 5 | a photograph with no rank still appears | it comes last, not nowhere |
| 6 | a project holding a dossier can be arranged | it was refused: see below |
| 7 | undo takes the arrangement back | the rank is gone from the header |

1–7 hold. The oracle for 1 is `content-check`'s
`the order is a property, not a name`, which **builds twice** — nothing
short of a build could ever have seen this.

## Found on the way

`reorder` had its own file listing that kept `page-NN` — a dossier's
pages, drawn from the PDF. The panel never sends those, so on any
project holding a PDF the order it was given was short by however many
pages the document had, and **every arrangement came back "ce ne sont
pas les mêmes photos"**. Nothing in the tree has dossier pages yet,
which is the only reason it was never seen. One listing now:
`photographs_in`.

## What would change this

- **Hundreds of photographs in one folder.** The turn loop is quadratic.
  The fix is to read the ranks in Python and hand the templates a sorted
  list, which means a build step this site does not otherwise have.
- **She wants to keep the names she drops.** `add_image` still renumbers
  an arriving photograph to `NN.jpg`. That is a separate decision from
  this one and no longer load-bearing: the order no longer depends on
  it, so it can go whenever she says so.
- **Two photographs end up sharing a rank.** Nothing prevents it today
  and the consequence is that they come out in zola's order within that
  turn, which is harmless. A verb that wrote ranks for a subset of a
  folder could cause it; `reorder` always writes the whole list.
