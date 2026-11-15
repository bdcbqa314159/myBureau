# Pages and the road

**Status:** the four behaviours are built. The panel's half is not.
**Date:** 2026-11-07, replacing *DA as a road*; amended 2026-11-12,
when the client asked for the road straightened — see *The road is
straight now*; amended again 2026-11-13, when the two rhythms became
one — see *One class, one page*.

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
| a **project** (`grocery list`, `calendar`, `douze regards`) | the same blank page | the same one column — see *One class, one page* |

Four different things, and the last two are now one. None of them is
the default, and the drift that produced this file happened because
two of them were treated as one.

## One class, one page

**2026-11-13, from the client via Bernardo.** Everything sitting on DA
or graphic design is one class. What an object IS still differs — a
photo, a video, a folder — and so does what clicking it does:

| object | is | click |
|---|---|---|
| theodora 01, confidence glow 01/02 | **one** photo | opens in place, on the desk |
| june's cry | a video | plays in its window, on the desk |
| maison cosette, atelier mirabelle, logofolio | a folder | its page |
| grocery list, calendar, douze regards | neither | its page |

**One photograph, or it is not a preview** (2026-11-13). A preview is
one screen with one picture on it — pressing space on a Mac, which is
what the brief asks for by name. Several photographs is a body of work
rather than something to glance at, so it goes to the page, where they
are a column.

The rule was "is there a picture at all", and the dialog rendered every
photograph in the folder into a flex row that clips what will not fit.
Nothing was in that position, so it would have arrived the day she
added a second photograph to a project.

**And what it exposed** (2026-11-13). A photograph that opens in
place shows the picture and nothing else: the preview carries no way
to the page, by her own decision, and the icon's own link is
intercepted. So **the paragraph she writes about a photograph is
reachable by nothing on the site.**

`opens = "page"` was made writable from the panel for exactly that
reason — and **that was the wrong answer, withdrawn two days later.**

**A photograph is a photograph** (2026-11-14, from the client via
Bernardo). One lying alone on a desk is offered what a photograph has:
a name, the picture, what the picture shows, and the bin. Not a text
box, not a choice about what a click opens, not a face other than
itself.

The text box was the root of it. Every content file has a body, so
every object got one — and on a photograph that body appears on a page
nothing links to. The switch existed only to rescue it. With no text
there is nothing to rescue, so the switch and the `set_opens` verb are
gone with it: two controls for one decision, and the decision was
"a photograph should not have had words in the first place".

**Desks only.** The gallery and `travail sélectionné` hold photographs
that behave differently — a grid, a road — and this is about the ones
dropped alone on DA and graphic design.

**The engine still honours `opens = "page"`** written by hand, which
`grocery list` uses. What went is the panel's ability to write it.

**What would change this:** she asks to say something about a single
photograph. Then the question is not a switch — it is where a
photograph's words belong, and the honest answers are a caption under
the picture in the preview, or the desk's own page.

**What this withdrew** (2026-11-13). Two photographs behind one icon
used to be an error: the second was reachable only by opening the
first. `look.py` told her so and advised one folder per photograph,
and `content-check` enforced it. Neither is true now — every
photograph in a folder is shown on its page — so the warning and the
check are gone. `grocery list` is six photographs in one folder and is
exactly right.

**Photos and videos are unchanged.** What changed is the page: there
used to be two of them.

A subfolder got a plain column; a project got the prototype's rhythm —
one photograph full width, then pairs with cream around them. From the
desk that difference had no visible cause: `grocery list` and `maison
cosette` are two icons side by side that gave two different pages.

So the rhythm is withdrawn. `page.html` has one shape, and the pairs
container, its flag, `.proj-pairs` and `.proj-fig` are gone with it.
`.proj-open` keeps its name although every photograph is an opener
now — renaming it would touch every template and check that spells it,
for nothing a visitor can see.

**What stayed:** only the first image is eager. Nine photographs all
marked urgent is the same as none marked urgent, and that is how the
subfolder page once became the heaviest on the site.

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

## Three columns — `travail sélectionné` only

**2026-11-14, from the client.** *Three columns within the blank space
where we can sit one picture, a display per column taken by the width
of a picture, and the three columns setting the limits of expression.*

The blank space is three columns. A photograph sits in one and is the
width of that column, so **the column decides the size and the choice
of column decides the place**. One number, declared per file in the
shape `[extra.alt]` already uses:

```toml
[extra.column]
"02.jpg" = 3         # 1, 2 or 3
```

| field | type | default | range |
|---|---|---|---|
| `column` | integer | from the rhythm | 1–3, anything else dropped |

- **Optional, per file.** Without one, the rhythm places it.
- **Out of range is DROPPED, not clamped** — and this is the one that
  bites: `grid-column: 7` in a three-column grid does not fail, the
  browser grows implicit columns and the whole route silently becomes
  seven wide. So the template refuses it and the rhythm places the
  photograph instead.
- **Placement is sparse**, which is the browser's default and is what
  makes this a composition rather than a gallery: a photograph goes in
  the next free row of its own column, so two in different columns can
  share a row and two in the same column cannot. The gaps are the
  composition.
- **The rhythm is 1, 3, 2, 1, 3** — five steps over three columns, so
  no row comes out full. `content-check` works out the row counts the
  way a browser would rather than asserting the sequence: "the
  sequence repeats a column" was tried and is a tautology.
- **It never interferes with `x`/`y`.** A thing has a position on a
  desk; its photographs have columns on a road.
- **Order is a rank she arranged**, `[extra.place]`, keyed by file
  name — not the file names themselves. It WAS filename order, and
  rearranging was renumbering: see the-order-is-a-property.md for why
  that could not work even in principle.
- **Written to every language file.** Wide in French and narrow in
  English is a bug.
- **Out of range is clamped, not refused.** A number she drags to is
  never an error.
- **A phone has one column.** Three columns of a 390px screen is three
  slivers, so below 52rem they collapse into one and every photograph
  takes the whole width. A stop asks for `grid-column: 1` down there
  rather than `auto`, or her declared column would ask for a track
  that does not exist and the grid would grow one to hold it.

**What this replaced, in order:** a width, an offset and a lean, all
per file — the fridge. The lean and the offset were rejected; then the
free width was squeezed on a phone, then flattened; then the width
itself went, because a column that sets the size is the same idea with
a limit on it, and the limit is what she asked for.

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
| 2 | a project page is the same page as a subfolder's | no pairs container anywhere, every figure full width |
| 3 | a subfolder carries no pinning | no inline `--w` on its figures |
| 4 | the road is on travail sélectionné and nowhere else | asserted against each of the four |
| 5 | a column she chose reaches the stop | `--c` rendered inline; out of range dropped |
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
- **She misses the pairs.** The rhythm was the prototype's and it was
  liked; it was dropped because it applied to a class of object rather
  than to a choice she made. If it comes back it comes back as a
  setting per object, not as a consequence of whether a folder has an
  `_index.md`.
