# The four types

**Status:** stored, enforced at the verbs, and the panel offers one set
of controls per type.
**Date:** 2026-11-14

## What a thing is

Four types. She picks one when she makes it, it is **written into the
file**, and it is read from there for ever after.

| type | holds | a click |
|---|---|---|
| **photo** | one photograph | opens it in place |
| **video** | a film and its affiche | opens its window |
| **page** | a title, her words, photographs and PDFs | goes to its page |
| **folder** | things, which become a desktop | the desktop |

A **folder** is only a folder on the main desktop. Made anywhere else
it is a page — which is why `maison cosette` is a page and not a third
desk, and why a folder picture on an icon inside a desktop is an icon
and nothing more.

## The name decides nothing

She may call a page `quelquechose.pdf` and it is still a page. She may
call it `quelquechose.mov` and it is still a page. The name is hers.

## What each type accepts

Anything else is refused, with a sentence saying what to do instead.

| type | accepts | refuses |
|---|---|---|
| photo | one image | a second image, a PDF, a video |
| video | a video, an affiche | an image, a PDF |
| page | images, PDFs | a video |
| folder | things | files |

**A photo is a photo.** A second image on it is refused rather than
quietly turning it into a page. An object that changes type under her
is how all of this went wrong.

**A page refuses a video** so that it cannot become a film by accident.
An empty page used to accept one, and from then on behaved like a film.

## What this replaced, and why it kept going wrong

The type she chose was used to append an extension to the title and
then thrown away:

```python
title = name + NEW_KINDS[kind]["suffix"]      # "x" + ".mov"
atomic(f, '+++\ntitle = "{}"\n+++\n\n\n')     # and that is all
```

After that, **three letters in a name she can rename were the only
record of her choice.** Every later decision re-derived the type from
the title's extension or from what happened to be in the folder. That
single fact caused, in order:

- `12 regards.pdf` had somewhere to drop a PDF and `logofolio` did not
- *"Ce dossier attend son PDF"* told her a name had committed her
- a lone photograph and a page were told apart by counting files
- renaming a thing changed what it **was**
- the panel offered five kinds — *des photos*, *un film*, *un
  document*, *une page*, *un dossier* — three of which were one thing

## Where it is stored

`kind` under `[extra]`, beside `x`, `y`, `icon`, `wallpaper`, `alt`.

**Not at the top level.** Zola allows only its own keys there and
refuses the file outright:

```
Reason: TOML parse error at line 3, column 1
3 | kind = "folder"
```

One reader: `verbs.kind_of()`. One enforcer: `verbs.must_accept()`.

## The eleven that already existed

They were made before the type was written down, so what they are had
to be worked out once, by hand, and `tools/label-types.py` did it:

| | |
|---|---|
| `theodora 01/02`, `confidence glow 01/02` | photo |
| `june's cry` | video |
| `maison cosette`, `logofolio`, `atelier mirabelle`, `grocery list`, `calendar`, `douze regards` | page |
| `DA`, `graphic design` | folder |

`pellicules` and `travail sélectionné` are not labelled: they are their
own things on the main desktop — a gallery and the road — and their
templates already say so.

That script used exactly the inference being retired, one last time, to
seed the answer. **It has no reason to run again**, and must not become
a fallback: the whole point of writing the type down is that nothing
re-derives it.

## Acceptance criteria

| # | criterion | oracle |
|---|---|---|
| 1 | a new thing says what it is, in its own file | `kind_of()` returns what she picked |
| 2 | its name is hers, with no type bolted on | the title is exactly what she typed |
| 3 | a folder on the main desktop holds a desktop; elsewhere it is a page | `new_bureau` writes `folder` or `page` by position |
| 4 | each type refuses what it cannot hold | a sentence naming what to do instead |
| 5 | a photo holds one photograph | a second is refused |
| 6 | renaming decides nothing | `.pdf` and `.mov` on a page change neither |

| 7 | the panel offers each type its own controls, and no others | one table read both ways in app-check |
| 8 | it says what a thing is from its type, not its contents | an empty film is still a film |

1–8 hold.

## What the panel offers

| type | name | text | photographs | a film | an affiche | a dossier |
|---|---|---|---|---|---|---|
| **photo** | ✓ | — | one, then nowhere to drop a second | — | — | — |
| **video** | ✓ | ✓ | — | ✓ | ✓ | — |
| **page** | ✓ | ✓ | ✓ | — | — | ✓ |
| **folder** | ✓ | — | — | — | — | — |

Every one of those used to be worked out from the folder's contents or
the title's extension, so **a thing she had not filled in yet was
offered the wrong boxes**: an empty film had nowhere to put its film
unless she had typed `.mov`, and a photo with no image was treated as a
page.

A photo that already holds its photograph has **no drop zone** — the
verb would refuse a second — and says so instead: *"une photo seule
n'en tient qu'une. Jette celle-ci pour en mettre une autre, ou fais-en
une page."*

## What would change this

- **A fifth type.** Then `TYPES`, `ACCEPTS` and `TYPE_IS` gain a row
  each and the panel a line. Nothing else should need touching — that
  is the test of whether this was done right.
- **She wants a photo to become a page by dropping a second picture.**
  Then `add_image` rewrites `kind` instead of refusing, and the refusal
  above becomes a conversion. I would ask twice before building it: an
  object that changes type under her is the thing this file exists to
  stop.
- **A folder inside a desktop should hold a desktop after all.** Then
  position stops deciding and depth becomes unbounded, and the desk
  that the brief asks to be "the size of a screen" has to answer for
  children it cannot show.
