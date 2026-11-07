# Pages and the road

**Status:** the four behaviours are built. The panel's half is not.
**Date:** 2026-11-07, replacing *DA as a road*

## What each thing is

This file previously proposed turning `DA` into a road. **That was
wrong and is withdrawn.** The brief pairs DA with graphic design —
*"Page DA : même concept que la page graphic design"* — and both are
desks. The road belongs to `travail sélectionné` alone.

| folder | is | work shown as |
|---|---|---|
| `DA` | a desktop | icons on a wallpaper |
| `graphic design` | a desktop | icons on a wallpaper |
| `travail sélectionné` | the **only** road | photographs pinned down a vertical route |
| `pellicules` | a gallery | its grid |
| a **subfolder** (`maison cosette`, `Atelier Mirabelle`, `Logofolio`) | a blank page | title, text, work in **one column** |
| a **project** (`grocery list`) | a page | the prototype's rhythm: one opener, then pairs |

Four different things. None of them is the default, and the drift that
produced this file happened because two of them were treated as one.

## The blank page of a subfolder

Its name, its text, and then its work. **Every photograph takes the
whole width** — each picture gets all the space there is — and you keep
going down.

No pairs. No pinning, no offset, no angle: the fridge is reserved to
the road.

## The road — `travail sélectionné` only

Each photograph is a stop. A stop takes three numbers, declared **per
file** in the front matter of the folder holding it, in the shape
`[extra.alt]` already uses:

```toml
[extra.width]
"02.jpg" = 72        # per cent of the page
[extra.offset]
"02.jpg" = 8         # per cent off the centre line, + is right
[extra.angle]
"02.jpg" = -3        # degrees, how it hangs
```

| field | type | default | range |
|---|---|---|---|
| `width` | integer, per cent | from the rhythm | 20–100 |
| `offset` | integer, per cent | from the rhythm | −30 to 30 |
| `angle` | integer, degrees | from the rhythm | −8 to 8 |

- **All three optional, per file, independent.** An angle may be given
  with no width: one photograph hung crooked, nothing else changed.
- **They never interfere with `x`/`y`.** A thing has a position on a
  desk; its photographs have places on a road.
- **Order is filename order.** Rearranging is renumbering, which the
  panel already does.
- **Written to every language file.** Wide in French and narrow in
  English is a bug.
- **Out of range is clamped, not refused.** A number she drags to is
  never an error.
- **Below 46rem the road straightens** — full width, no offset, no
  angle. A picture at 24 per cent of a phone is a stamp.

## What the panel still has to do

The machinery mostly exists, which is the point of writing it down:

| needed | what is already there |
|---|---|
| write a per-file key into `[extra.*]`, every language | `verbs.set_alt()` does exactly this |
| put the sub-table where TOML survives it | `set_alt_key()` appends at the END — a bare key after a sub-table silently joins it |
| never half-write across languages | `place()` works out every file first and writes nothing until all parse |
| report the numbers to the panel | `model.py` reports `x`/`y` already |

Still to build: `set_alt_key` taking the table name (one parameter), a
`pin` verb that **clamps rather than refuses**, the three numbers in
`model.py`, and the gesture in `app.js`.

**On a blank page the panel offers a place, not a pin.** The page is a
column, so what she needs there is: *put a picture here, or keep going
down.* A slot between photographs and one at the foot. No width, no
offset, no angle — those belong to the road.

## Acceptance criteria

| # | criterion | oracle |
|---|---|---|
| 1 | a subfolder page is one column | every figure full width, no pairs container |
| 2 | a project page keeps opener-then-pairs | the pairs container is still built |
| 3 | a subfolder carries no pinning | no inline `--w`/`--x`/`--r` on its figures |
| 4 | the road is on travail sélectionné and nowhere else | asserted against each of the four |
| 5 | a pin reaches the stop | inline custom properties rendered |
| 6 | the three are independent | an angle alone renders an angle alone |
| 7 | a desk is a desk | DA and graphic design keep wallpaper and icons |

1–7 hold today. The panel's half has none yet.

## What would change this

- **She wants a second road.** Then `template` becomes the switch and
  the road stops being one folder's privilege. The model does not
  change, only which folders use it.
- **She wants two columns on a subfolder page.** Then "all the space
  for a picture" was not what was meant, and the column becomes a
  setting rather than the rule.
- **Width per screen size.** One number cannot say "wide on a laptop,
  full width on a phone". If that is wanted, `width` becomes a maximum.
