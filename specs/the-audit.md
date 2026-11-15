# The audit

**Status:** audits 1–4 done and fixed — twenty-seven findings.
**Date:** 2026-11-15

Seven architectures, ordered by **what a bug in each one costs**. Not by
size, and not by how interesting it is to read.

| # | architecture | lines | a bug here costs |
|---|---|---|---|
| 1 | **the write side** — `verbs.py`, `server.py` | 2,380 | her files |
| 2 | **the shape** — `content/`, `model.py`, the readers | 1,247 | silent disagreement between three modules |
| 3 | **the checks** — five suites | 7,914 | everything else, unverified |
| 4 | **the panel** — `app.js`, `app.html`, `app.css` | 2,164 | a tool she cannot use |
| 5 | **the engine** — eleven templates | 1,691 | a page nobody can see is wrong |
| 6 | **the browser** — `desk.ts`, `contact.ts`, `site.css` | 2,506 | a desk that does not move |
| 7 | **her path** — `preview.sh`, `GUIDE.fr.md`, `kit.py`, CI | 1,272 | a handover that does not happen |

## How each audit runs

The same four steps every time, and the third is the one that is
usually skipped.

1. **Read the whole thing.** Not the diff, not the entry points — every
   line of the architecture under audit. An audit that reads what it
   expects to find is a review of my own memory.
2. **List the findings**, each with the one-line defect and the input
   that shows it. No fixes yet.
3. **Prove each one.** A finding that cannot be made to fail a check is
   a hypothesis, not a finding. This is where most of them die, and the
   ones that die are worth the reading.
4. **Fix in order of cost**, one PR each, every fix carrying the check
   that fails without it. Reversed expectations are rewritten with the
   reason beside them, never deleted.

**The bar for a finding:** it names the input, the wrong output, and
what it costs her. "This is complicated" is not a finding. "This is
duplicated" is only a finding if the two copies can drift — and then
the finding is the drift, not the duplication.

## What each audit asks

### 1. The write side — `verbs.py` (1,854), `server.py` (526)

Everything that touches her files. The closed verb list, the write
gate, the journal and undo, the lock, the token, the staleness guard.

- **Can a verb lose work?** Every path that moves, replaces or deletes
  a file, against the bin and the journal. `undo` must reach every one.
- **Can a verb write a file zola will not read?** The gate catches a
  fence that is not alone on its line. What else gets past it — a
  duplicate table, an unclosed string, a key written twice?
- **Is every refusal actionable?** A sentence in French naming what to
  do instead, not what went wrong.
- **Does the closed list still close?** Every entry point into
  `verbs.py` reachable from `server.py`, and nothing else.
- **Known debt:** 1,854 lines in one module; `is_gallery` and
  `is_canvas` read the TEMPLATE to decide what a folder is, which
  `specs/the-four-types.md` already says should move to a written-down
  note; `_one_of_a_kind` reads it too.

### 2. The shape — `content/`, `model.py` (344), `frontmatter.py`,
`filetypes.py`, `look.py`, `prune.py`, `i18n.py`

What a content file IS, and whether everyone agrees. **This is where
this project's bugs come from**: a template, a verb and the model each
holding their own copy of the same fact.

- **Every `[extra]` key: who writes it, who reads it, who validates
  it.** The current surface is `alt, band, column, contact, demo, doc,
  icon, items, kind, live, nav_extra, offset, opens, place, shot,
  social, studio, wallpaper, x, y` — and `angle`, `offset` and `column`
  are retired. Is the tree clean of them, and does writing one by hand
  still do nothing?
- **Three readers of the same table.** `model.alt_of`, `model.place_of`
  and the templates each parse `[extra.*]` their own way;
  `verbs.set_map_key` writes it. A fourth shape and they drift.
- **Does the model say what the verb will do?** `can_receive` already
  drifted once — the panel offered a destination the server refused.
  Every boolean the model exports gets the same question.
- **Known debt:** the model re-derives from the filesystem what the
  verbs know; `kind` is written down but `gallery`/`canvas` are still
  inferred from the template.

### 3. The checks — `content-check.py` (3,672), `studio/check.py`
(1,978), `app-check.mjs` (1,768), `desk-check` and `contact-check`

They are bigger than what they check. If they lie, nothing else here is
verified.

- **Which expectations cannot fail?** Every one, broken on purpose.
  This has found tautologies three times already.
- **Which fixtures lack the shape the guard is about?** The recurring
  one: a check passes because the fixture has no folder-page, no lone
  photograph, no empty project.
- **Where does a check parse HTML by position rather than by name?**
  The `--tall` anchor broke three times in two days for reasons with
  nothing to do with what it asserts.
- **What is asserted about the SOURCE that should be asserted about a
  BUILD, and the reverse?** zola is not deterministic about a bad image
  path — see `specs/the-canvas.md` — so some rules can only be checked
  at the source.
- **Known debt:** 3,672 lines in one file with no structure; several
  cases now carry history longer than their assertions.

### 4. The panel — `app.js` (1,884), `app.html`, `app.css` (2,164 in all)

- **Ten module-level `let`s hold the whole state.** `seen, waiting,
  site, model, chosen, bySlug, narrowView, dragging, mode, stale`. None
  of them is reachable from the test context, which has already forced
  two checks to be rewritten to read the DOM instead. Does that state
  have an owner, or ten?
- **Every control, against the four types.** The table in
  `specs/the-four-types.md` read both ways: what is offered, and what
  the verb accepts.
- **Every gesture.** Drag an icon, drag in the gallery, drag on the
  canvas, resize, drop a file, right-click. Each one: what happens on a
  phone, on a refusal, on a second drag before the first saved.
- **What does she see when something fails?** Every `tell()` and every
  refusal path.

### 5. The engine — eleven templates (1,691)

- **Do the partials agree?** `_icon.html`, `_preview.html` and
  `_film.html` answer overlapping questions about the same folder, and
  have disagreed before — a `data-window` with no dialog behind it.
- **Every loop over a section's assets strips the language.** Now
  asserted; what else is per-language and silently is not?
- **What does each template do with an empty folder, a folder holding
  only our files, a name that slugifies to the same as another?**

### 6. The browser — `src/desk.ts` (922), `contact.ts`, `site.css`
(1,383)

- **The dragging, the windows, the transitions**, against a keyboard
  and against a phone.
- **One set of breakpoints**, already asserted; one set of grounds, one
  set of cursors — are they?
- **No runtime dependency**, which is law. Still true?

### 7. Her path — `preview.sh`, `preview.command`, `kit.py`,
`GUIDE.fr.md`, `.github/workflows/deploy.yml`

- **Three steps, on a Mac she has not set up.** Homebrew, GitHub
  Desktop, double-click. Every failure in that chain, and what it says
  when it fails.
- **Does the guide describe the panel that exists?** It was written
  before the canvas, before right-click creation, before the order
  became a property.
- **What happens when she pulls while the panel is open** — now
  guarded; what else survives a pull?

## The order, and why

1 before 2 because a verb that loses a file is worse than two modules
disagreeing. 2 before 3 because a check cannot be trusted to describe a
shape nobody has settled. 3 before 4 because fixing the panel without
trustworthy checks is how the gallery drag passed twice while doing
nothing. 5, 6 and 7 last: the engine and the browser are the
best-covered code here, and her path changes only when the rest stops
moving.

**They may be re-ordered by what the earlier ones find.** An audit that
finds nothing in its own area but names a fault in the next one has
done its job.

## What would change this

- **A finding that crosses two architectures** — then the boundary is
  wrong and the two are audited together. The most likely pair is 1 and
  2: `verbs.py` and `model.py` already hold two copies of several
  facts.
- **A whole area comes back clean.** Then the audit after it gets the
  time, and this file records that it was read and found sound — which
  is worth as much as a list of defects, and is the part people skip
  writing down.

---

# Audit 1 — the write side

`verbs.py` (1,854) and `server.py` (526), read end to end on
2026-11-15. Eight candidates, **seven proven** by making them happen on
a scratch copy of the real tree. Ordered by what each costs her.

## The findings

### F2 · a PDF poppler cannot read takes the dossier she had  **· fixed**

`add_doc` bins the old dossier and its rendered pages, writes the new
file, and THEN rasterises — and `pages_of` raises on a PDF it cannot
read. `record()` never runs.

| | |
|---|---|
| input | drop a corrupt PDF on a project that already has one |
| output | "je n'ai pas pu lire les pages de ce PDF" — and `calendar.pdf` plus both its pages are in the bin, `dossier.pdf` (the corrupt one) is on disk, the journal gained nothing |
| costs her | the dossier she had, with **Annuler unable to reach it**, after being told the drop was refused |

### F1 · a refusal that changes her icon anyway  **· fixed**

`set_icon` calls `_unface`, which bins the old `icon.*` and rewrites
the front matter, and only then writes the `face` key — which raises if
any language file is malformed. `record()` never runs.

| | |
|---|---|
| input | drop an icon on a project whose `index.en.md` somebody broke by hand |
| output | it reports a refusal; the icon on disk has **changed**; `undo` answers *il n'y a rien à annuler* |
| costs her | the face she had chosen, after being told nothing happened |

### F5 · a quote in a file name breaks the site  **· fixed**

`set_map_key` writes `"{name}" = …` with the name interpolated raw.
A photograph called `vue "x".jpg` produces TOML zola refuses, and the
gate in `atomic()` only checks the fences.

| | |
|---|---|
| input | rename a photograph in the Finder to include a `"`, then describe it in the panel |
| output | the write succeeds; `zola build` fails |
| costs her | the whole site, from a rename the Finder allows |

### F4 · a newline in a title breaks the site  **· fixed**

`retitle`, `new_project` and `new_bureau` refuse a `"` and not a
newline. `title = "a\nb"` is not TOML.

| | |
|---|---|
| input | a title containing a line break |
| output | the file is written, the build fails |
| costs her | the whole site. The gate exists to stop exactly this class and checks only the fences |

### F3 · `remove_image` bins any file under `content/`  **· fixed**

It validates the project and then never checks that `name` is one of
its photographs — unlike `place_shot`, which does.

| | |
|---|---|
| input | `{"verb":"remove_image","item":"content/da/theodora-01","name":"../../_index.md"}` |
| output | the home desk's content file is in the bin |
| costs her | her home page's title, its windows and their positions. Undo reaches it, and nothing else does |

Not reachable from the panel, which only ever sends a name from the
photographs list. It is an input-validation hole at a trust boundary,
in the one module whose job is to be a closed list.

### F7 · the one unlink in a design whose rule is "to the bin"  **· fixed**

`pages_of` does `stale.unlink()` on `draw-*.png` left from an earlier
run. A file of hers with that name is deleted outright.

### F8 · a position that is not a number is a Python error  **· fixed**

`place` does `int(x)` unguarded, so `x = "beaucoup"` reaches her as
`ValueError: invalid literal for int() with base 10`. `place_shot`
refuses the same input in French.

### F6 · the English file decides what a thing IS  **· fixed**

`kind_of` and `template_of` read the first file that `sorted()` hands
back — and `index.en.md` sorts before `index.md`. Set them to disagree
and the English one wins. Nothing writes them separately today and
nothing checks they agree, so this is a latent hazard rather than a
live bug.

## What they have in common

F1 and F2 are the same defect in two verbs: **something irreversible
happens before everything that can refuse has refused.** Six verbs bin
an old file and write a new one, and the journal entry is written last.

`place`, `set_alt`, `reorder` and `place_shot` already do it the other
way — *"WORK OUT EVERY FILE FIRST, WRITE NOTHING UNTIL ALL OF THEM
PARSE"* — and that comment was written after the same bug bit in
`place`. It was never carried across.

F3, F4, F5 and F8 are one defect too: **the trust boundary checks some
inputs and not others.** A quote is refused in a title and allowed in a
file name; a number is validated in `place_shot` and not in `place`.

## What was read and found sound

Worth recording, because an audit that only lists faults reads as
though everything it did not mention was examined and condemned:

- `inside()` resolves symlinks and compares real paths; every verb goes
  through it. No path escaped `content/` in any probe.
- The token, the loopback bind, the cross-site refusal and the
  `flock` in `only_one()` hold up.
- `undo` stages every move through a holding name, so a permutation
  cannot eat a file halfway round the cycle.
- The journal and the bin are trimmed together, bin after journal, so
  nothing is swept while an entry can still ask for it.
- `atomic()` is the only writer of content files, and its gate catches
  the fence bug that caused the original damage.
- `must_really_be` reads the first bytes rather than trusting the
  extension, and deliberately allows bytes it does not recognise.

## Fixed, and how

**F2, F1 and F7 in one change, because they are one rule:** nothing
irreversible happens until everything that can refuse has refused.

- `add_doc` rasterises FIRST, from the bytes she handed over, straight
  through a pipe — `pdftoppm` reads `-` as standard input, so the
  document never becomes a file until it is going to stay. Only once
  there are pages does anything of hers move.
- `_unface` became `_face_plan` + `_apply_face`. The plan includes the
  step that can refuse — writing the `face` key — so it raises while
  the plan is still only a plan. `set_icon` and `set_face` both go
  through it.
- The pages are drawn in a temporary directory, so her folder is never
  the scratch space and `draw-*.png` of hers is never in the way.

The first version of the `add_doc` fix wrote the PDF to a temp file,
and `every write goes through the gate` in content-check caught it
within the minute — a check written for a different reason, holding a
line it was not aimed at. That is what they are for.

**F3, F4, F5, F6 and F8 are fixed too**, in the slice after. Four of
them were one defect: the trust boundary validated some inputs and not
others. There is one place each now, so the next verb cannot forget.

### F9 · a default argument that cannot work  **· fixed**

Found while writing the check for F4, which passed `"photos"` and was
refused for the wrong reason.

`new_project(into, name, kind="photos")` — and `"photos"` is not one of
the three kinds, so every caller that leaned on the default got *je ne
connais pas ce genre de projet* and no project. The panel always sends
one explicitly, which is why nobody saw it. `kind` has no default now,
and `server.py` says *il manque le genre de projet à créer* rather than
naming the wrong problem.

## Two things wrong with the suite, found by using it

Neither is a verb, and both were in the way of this audit, so they are
fixed here and belong to audit 3 when it comes.

**A crash printed no failure.** `check.py` died partway through with a
traceback and NO `FAIL` line, so every habit built on reading failures
— mine included — reported a clean run. It has happened four times in
this project. `run()` now reports a crash as a failure and still
prints the traceback.

**Six copies of `refused()`.** Each defined inside `main()`, each
shadowing the last, so improving the helper improved only the block it
sat in: a fix made in the first copy did nothing for the call six
hundred lines later. One, at module level, and it now reports a Python
error as text rather than letting it stop the suite — which is what a
check about "does this refuse in French" is for.


---

# Audit 2 — the shape

`content/`, `model.py`, `frontmatter.py`, `filetypes.py`, `look.py`,
`prune.py` and `i18n.py`, read end to end on 2026-11-15. **Five
candidates, four proven**, all four fixed. One was disproven by the
probe, which is recorded below because a candidate that dies is worth
as much as one that lives.

Every one of the four was the same defect the plan predicted for this
area: **the same knowledge kept in two places, and the copies drifted.**

### A2-F1 · the panel could not read back what the panel had written

Audit 1 taught `set_map_key` to escape a quote in a file name, so the
site could show a description for `vue "x".jpg`. `model.alt_of` and
`model.place_of` each had their own regex, `"([^"]+)"`, which stops at
the first escaped quote.

| | |
|---|---|
| input | describe a photograph whose name holds a `"` |
| output | the site shows the description; the panel reads back `{}` |
| costs her | the description looks lost, so she writes it again — into a file that already has it |

A fix of mine, four days old, that drifted the moment it landed.

### A2-F2 · an order written on a page that has none

`travail sélectionné` places each picture by a left, a top and a
width; `selection.html` reads no rank at all. The panel still offered
the list drag, and `reorder` still wrote `[extra.place]`.

| | |
|---|---|
| input | drag a photograph in the panel's list, on the canvas |
| output | "ordre enregistré" — and the page is unchanged. The panel's list then shows `08, 01, 02` while the page shows `01, 02, 03` |
| costs her | the panel lying about the page, which is the one thing it must not do |

### A2-F3 · the tool that says what will not work, saying nothing

`look.py` kept its own front-matter test: does it start with `+++` and
hold two of them. `+++title = "x"` satisfies both — it is the file that
broke the site twice.

| | |
|---|---|
| input | a content file whose opening fence is not alone on its line |
| output | `look.py` exits 0, "Nothing to report"; `zola build` exits 1 |
| costs her | the one tool written to catch this, clearing it |

### A2-F5 · her words, cut off at a `+++`

`frontmatter.body()` returned the text between the second fence and a
third, so a paragraph containing `+++` came back short — and the panel
writes back what it shows.

| | |
|---|---|
| input | a paragraph containing `+++` |
| output | 32 characters written, 6 read back |
| costs her | the rest of the paragraph, the next time she saves anything on that page |

### A2-F4 · a space in a photograph's name — NOT a finding

The guess was that `prune.py` matches urls against file names, so a
photograph called `vue sur la mer.jpg` would be percent-encoded in the
HTML, unmatched, and either pruned or reported missing — stopping the
deploy. Tried: prune exits 0 and the site is whole. The original is
never requested at all, because every page serves a resized copy, so
pruning it is correct. **Recorded because the next person to have the
same idea should not have to run it again.**

## Fixed, and how

One module knows what a content file is, and now it knows all of it:

| `frontmatter.py` gained | who had a copy |
|---|---|
| `why_zola_refuses(text)` | `verbs._no_front_matter` and a weaker one in `look.py` |
| `toml_name(name)` | `verbs.toml_name`, with no reader that understood it |
| `map_of(header, table)` | `model.alt_of` and `model.place_of`, one regex each |
| `body()`, fixed | — |

And the canvas: `reorder` refuses an order where none is read,
`model.photographs` lists a canvas by the tops its page uses, and the
panel does not offer the drag there at all — a gesture that can only
be refused is worse than no gesture.

## What was read and found sound

- `filetypes.py` is already the one reader of `config.toml`'s lists,
  and every module takes them from it.
- `prune.py`'s safety is the check after the matcher, not the matcher,
  and that check resolves by suffix so it survives the site moving to
  her own domain.
- `i18n.py` adds a language with two edits in `config.toml` and no
  template change, which is what its docstring promises.
- `look.py`'s refusals — a file git ignores, a file zola cannot read —
  stop the run rather than printing advice, which is the right shape
  for the two things that are not advice.


---

# Audit 3 — the checks

`content-check.py` (3,672), `studio/check.py` (1,978),
`app-check.mjs` (1,768), `desk-check.mjs`, `contact-check.mjs`, read
and — more usefully — **measured**, on 2026-11-15.

484 expectations across 58 cases in content-check alone, 341 `check()`
calls in the panel's suite. Reading all of that for "could this ever
fail?" is the wrong instrument. So the audit ran a **mutation sweep**:
eighteen plausible regressions, applied one at a time to the real
code, with all five suites and the build asked whether they noticed.

**Four of eighteen went completely unnoticed.** One of those four was
the sweep's own mistake, which is worth as much as the rest.

## What the sweep found

| broken on purpose | noticed by |
|---|---|
| a photograph loses its alt | content |
| the canvas drops a picture's width | content |
| a desk stops saying which desk it is | content |
| the canvas loses its reserved shape | content |
| a cursor becomes the system arrow | content |
| a photo accepts a second image | panel |
| a thrown photograph is unlinked, not binned | panel |
| the write gate stops checking the fence | panel |
| a verb writes only the French file | content, panel |
| the desk drag works in the phone view | app |
| the order is read from file names again | content |
| a page stops reading her description | content |
| the phone keeps the composition's widths | content |
| the panel stops sending its token | app |
| **the gallery stops lazy-loading** | **nobody** |
| **the gallery stops being a dark room** | **nobody** |
| **the model counts our files as her photographs** | **nobody** |
| **a dragged icon also opens its window** | **nobody** |

### A3-F1 · the gallery had checks for what it holds and none for what it is

Twelve full-size photographs loading at once, and a white ground
instead of a dark room — her brief, and the whole of what the page
is. Every suite stayed green for both.

### A3-F2 · the panel would have offered her a film's affiche to throw away

`model.photographs` skips `icon`, `poster`, `wallpaper`, `about` and a
dossier's `page-NN`. Remove the skip and nothing notices: the panel
lists a film's affiche among her photographs, to drag into an order,
to describe, and to bin.

### A3-F3 · a dragged icon also opening its window

`desk-check` drives a click on an icon — but never a click that
arrives **after a drag**, which is the handler's first branch and the
one that stops a move from also being an open. Comment out its
`preventDefault()` and nothing anywhere sees it.

### A3-F4 · the sweep's own mistake, which is the useful one

The nineteenth result said "nobody" for that same mutation after it
was fixed. It was wrong: the sweep had edited `src/desk.ts`, and
`desk-check` runs the COMPILED `static/js/desk.js`. The mutation never
reached the code under test.

**A mutation sweep must break what the suites actually consume**, or
it reports gaps that are not there — and the first instinct on reading
"nobody noticed" is to write a check for a hole that does not exist.

It happened a second time, on the same row: rewritten to edit the
compiled file, the mutation INSERTED a `preventDefault()` into a
branch that already had one. A no-op, reported as a gap. **A mutation
nobody notices is either a hole or a no-op, and telling the two apart
is the whole discipline** — the sweep is only as honest as the breaks
in it. The row removes the suppression now, and `desk-check` fails on
it.

All eighteen are covered. `tools/mutate.py` is kept so the question
can be asked again; it is not in CI, because it edits the working
tree.

## A3-F5 · a fixture that lacked four shapes, and hid a live bug

Listing every field `app.js` reads against every field its fixture
ever sets to something gave four that were never set at all:
`canvas`, `doc`, `opens`, `holds`. Four branches the panel takes that
nothing had ever taken.

Giving the fixture a real canvas failed a check at once — and the
check was right. `whatFitsIn` tested for an existing selection with
`x.template === "page.html"`, which is how a selection was spelled
until travail sélectionné became a canvas on `selection.html`. **Since
that day the panel has offered "une sélection" on a desktop that
already has one**, and the server refuses it. The fixture hid it by
still saying `page.html`: the panel's wrong answer matched a wrong
world.

It asks the model now — `x.canvas`, the same fact the server reads.

## A3-F6 · thirteen patterns that pinned attribute order

`<main class="desk" data-desk="…"`, `<dialog class="win win-about"
id="about">`, `width="\d+" height="\d+"` — patterns that break when
anything is inserted between two attributes. The `--tall` anchor broke
three times in two days this way, each time failing a check for a
reason with nothing to do with what it asserts. Eight rewritten to
`[^>]*`; proven by adding an attribute to a template and watching the
suite stay green.

## What was read and found sound

- **No tautologies.** Every expectation whose predicate is a literal
  was checked by hand: 19 in the panel's suite are `check(…, False)`
  in a `try` with `check(…, True)` in its `except`, which is the "it
  must refuse" idiom. The two in content-check are an early-return
  failure path and an honest skip whose label says it checked nothing.
- **No case builds without asserting the build.** Two looked like it
  and both assert it under another name.
- `js-is-current.sh` recompiles before comparing, so it cannot be
  fooled by a stale `static/js` — tested by mutating the compiled file
  and watching it repair and report.
- `prune.py`'s own guard refuses the run rather than uploading a site
  missing a file it asks for.


---

# Audit 4 — the panel

`app.js` (1,907), `app.html`, `app.css`, read end to end on
2026-11-15. **Seven findings, all proven, all fixed.** Six of them are
one sentence: **the panel asked "is this a gallery?" where the
question is "does this hold photographs?"**

A canvas is the same object as a gallery with a different page — audit
2 settled that — and three separate places had not been told.

### A4-F1 · a right-click inside the canvas offered three things the server refuses

`whatFitsIn` returned `[]` for a gallery and the full menu for a
canvas. Right-click inside travail sélectionné and it offered *une
photo, un film, une page*; `new_project` refuses all three with
*cette page ne montre que ses photos*.

### A4-F2 · the create button aimed at the canvas

`intoNow` asked the same gallery-only question, so choosing travail
sélectionné made it the destination — a refusal after she had typed a
name.

### A4-F3 · two sentences that stopped being true

*"Elles s'affichent dans l'ordre de leur nom"* on the gallery, which
stopped being true the day the order became `[extra.place]`. And a
canvas fell through to *"La première est l'icône"*, false twice over:
it is a folder, so its face is a drawing, and its pictures are placed
rather than ordered.

### A4-F4 · a canvas reported holding nothing

`· 0 choses dedans` on a folder holding eight photographs, because the
photograph count was offered to a gallery only.

### A4-F5 · a refusal left on screen · **the one that costs her work**

Both drags move the picture first and ask the server second, which is
right — she sees it move under her hand. But a REFUSAL left it where
she dropped it: the page showed one composition and the file held
another, until some later reload threw her arrangement away.

That is the "it springs back" she reported in the gallery, with a
different cause. Both put it back now, after `act` has said why.

### A4-F6 · a local `chosen` shadowing the selected path

Inside `inspect()`, `const chosen = o.face || ""` — one of "folder",
"photo", "gif" — declared in the same function that reads the
module-level `chosen`, the path of the thing being inspected. Two
different things, one name, one scope apart. Nothing read the wrong
one yet; the next line written in there would have. This is the
hazard the plan predicted for ten module-level `let`s, and the first
one to actually appear.

### A4-F7 · a check keeping an old version of the site true

`app-check` asserted the panel says a thing on a page *"s'affiche dans
l'ordre de son nom de dossier"* — true while travail sélectionné laid
its children out in a route, and the route went when it became a
canvas. The check held the old words, so it was keeping a description
of a site that no longer exists.

## Two fixtures for one desktop, again

`app-check` holds **two** descriptions of the desktop — the tree the
panel reads, and `DESKS_IN_FIXTURE` for the menu checks. Audit 3 fixed
the first; the second still said travail sélectionné was a
`page.html` with no `canvas`. Every answer taken from it was an answer
about a world that no longer exists.

## And a stub that modelled a DOM nobody has

`nextSibling` is live in a browser. The harness set it once when the
fixture was built and never again — so the check for A4-F5, which is
about putting a photograph back where it was, failed against the stub
rather than against the panel. It relinks on every insert now.

The same check was **vacuous** in its first spelling: it dragged
`children[0]`, which by then was the photograph an earlier check had
moved to the front, and `elementFromPoint` found that same
photograph — so the handler returned without moving anything and the
check passed against a drag that never happened.
