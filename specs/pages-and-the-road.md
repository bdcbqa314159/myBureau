# Pages and the road

**Status:** the four behaviours are built. The panel's half is not.
**Date:** 2026-11-07, replacing *DA as a road*; amended 2026-11-12,
when the client asked for the road straightened — see *The road is
straight now*.

## What each thing is

This file previously proposed turning `DA` into a road. **That was
wrong and is withdrawn.** The brief pairs DA with graphic design —
*"Page DA : même concept que la page graphic design"* — and both are
desks. The road belongs to `travail sélectionné` alone.

| folder | is | work shown as |
|---|---|---|
| `DA` | a desktop | icons on a wallpaper |
| `graphic design` | a desktop | icons on a wallpaper |
| `travail sélectionné` | the **only** road | photographs down a vertical route, at varying widths |
| `pellicules` | a gallery | its grid |
| a **subfolder** (`maison cosette`, `Atelier Mirabelle`, `Logofolio`) | a blank page | title, text, work in **one column** |
| a **project** (`grocery list`) | a page | the prototype's rhythm: one opener, then pairs |

Four different things. None of them is the default, and the drift that
produced this file happened because two of them were treated as one.

## The blank page of a subfolder

Its name, its text, and then its work. **Every photograph takes the
whole width** — each picture gets all the space there is — and you keep
going down.

No pairs and no pinning. The road once had offsets and angles and no
longer does, so the difference between the two is now only the width.

## The road is straight now

**2026-11-12, from the client.** She does not like the fridge — not on
a phone and not on `travail sélectionné`. What she asked for, in
Bernardo's words: *the photos redressed, no inclination and no
possibility to add one; visitors can only see and scroll, nothing
more; images do not pop up; no name of the file either; a blank space
with the minimal title and explanatory on top.*

So three things went:

| was | is |
|---|---|
| `offset`, per file, ±30 per cent off the centre line | gone; every stop is centred |
| `angle`, per file, ±8 degrees | gone, and there is no way to add one |
| each stop a link wearing the file's name | a `<figure>`: nothing to click, nothing named |

**The width stays.** "Redress" is straighten, and a centred column of
differently-sized photographs is what her own reference does. If she
wants every photograph the same width too, that is one number here.

**Why a `<figure>` and not a link that ignores its click.** A link
that does nothing is still focusable, still announced as a link, still
shows a target in the status bar. Removing the element is the only
version that is true for a keyboard as well as a mouse.

**What it costs, and it is real.** The route was the only thing linking
a child project. A child that shows no photograph — a film, a document
— is now built and reached from nowhere. Nothing in the content is in
that position today: the single film sits on the DA desk as its own
icon. `content-check` holds an expectation naming this, so it is
noticed rather than discovered.

## The road — `travail sélectionné` only

Each photograph is a stop. A stop takes one number, declared **per
file** in the front matter of the folder holding it, in the shape
`[extra.alt]` already uses:

```toml
[extra.width]
"02.jpg" = 72        # per cent of the page, as a NUMBER — no %
```

| field | type | default | range |
|---|---|---|---|
| `width` | integer, per cent | from the rhythm | 20–100 |

- **Optional, per file.** Without one, the rhythm gives a width.
- **It never interferes with `x`/`y`.** A thing has a position on a
  desk; its photographs have widths on a road.
- **Order is filename order.** Rearranging is renumbering, which the
  panel already does.
- **Written to every language file.** Wide in French and narrow in
  English is a bug.
- **Out of range is clamped, not refused.** A number she drags to is
  never an error.
- **A phone narrows the range rather than erasing it.** The number is
  unitless so CSS can scale it; a picture at 24 per cent of a phone is
  a stamp, and the answer to values too extreme is smaller values, not
  none.

## What the panel still has to do

The machinery mostly exists, which is the point of writing it down:

| needed | what is already there |
|---|---|
| write a per-file key into `[extra.*]`, every language | `verbs.set_alt()` does exactly this |
| put the sub-table where TOML survives it | `set_alt_key()` appends at the END — a bare key after a sub-table silently joins it |
| never half-write across languages | `place()` works out every file first and writes nothing until all parse |
| report the numbers to the panel | `model.py` reports `x`/`y` already |

Still to build: `set_alt_key` taking the table name (one parameter), a
`pin` verb that **clamps rather than refuses**, the width in
`model.py`, and the gesture in `app.js`. It was three numbers; it is
one.

**On a blank page the panel offers a place, not a pin.** The page is a
column, so what she needs there is: *put a picture here, or keep going
down.* A slot between photographs and one at the foot. No width —
that belongs to the road.

## Acceptance criteria

| # | criterion | oracle |
|---|---|---|
| 1 | a subfolder page is one column | every figure full width, no pairs container |
| 2 | a project page keeps opener-then-pairs | the pairs container is still built |
| 3 | a subfolder carries no pinning | no inline `--w` on its figures |
| 4 | the road is on travail sélectionné and nowhere else | asserted against each of the four |
| 5 | a pin reaches the stop | inline custom properties rendered |
| 6 | nothing on the road can be clicked or names a file | no `<a>` and no `<span>` inside `.proj-route` |
| 7 | a desk is a desk | DA and graphic design keep wallpaper and icons |
| 8 | an angle cannot be declared at all | `--r` appears nowhere, even when front matter asks |

1–8 hold today. The panel's half has none yet.

## What would change this

- **She wants a second road.** Then `template` becomes the switch and
  the road stops being one folder's privilege. The model does not
  change, only which folders use it.
- **She wants two columns on a subfolder page.** Then "all the space
  for a picture" was not what was meant, and the column becomes a
  setting rather than the rule.
- **Width per screen size.** One number cannot say "wide on a laptop,
  full width on a phone". If that is wanted, `width` becomes a maximum.
- **A child of a road needs reaching.** The day she puts a film or a
  dossier inside `travail sélectionné`, the route has to carry it
  without becoming a menu again — a film playing inline would keep
  "only look and scroll" and still be reachable.
- **She wants every photograph the same width.** Then `width` goes too
  and the rhythm with it, and the road is a plain column.
