# The audit

**Status:** the plan. Nothing audited yet.
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
