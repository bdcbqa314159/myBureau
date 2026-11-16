#!/usr/bin/env python3
"""Break the code on purpose and ask whether anything notices.

    python3 tools/mutate.py

NOT part of CI — it edits the working tree and puts it back, which is
not a thing to run beside a build. It is the instrument audit 3 used,
kept because the question it answers cannot be answered by reading:
484 expectations in content-check alone, and the useful question about
each is "could this ever fail?", which only a break can settle.

Four of the first eighteen went unnoticed, and are now covered — the
gallery's dark room and its lazy loading, our own files appearing
among her photographs, and a dragged icon also opening its window.

BREAK WHAT THE SUITES CONSUME. One mutation edited `src/desk.ts` while
`desk-check` runs the compiled `static/js/desk.js`, so it reported a
gap that was not there. A sweep that mutates the wrong file invents
work.

Add a row to M when a rule is worth keeping honest. Restore is in a
`finally`, and the originals are copied before anything is touched.
"""
import pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SUITES = [
    ("content", [sys.executable, "tools/content-check.py"]),
    ("panel",   [sys.executable, "tools/studio/check.py"]),
    ("app",     ["node", "tools/studio/app-check.mjs"]),
    ("desk",    ["node", "tools/desk-check.mjs"]),
    ("look",    [sys.executable, "tools/look.py"]),
    ("zola",    ["zola", "build"]),
]

# (name, file, old, new) — each a regression a person could plausibly make
M = [
 # ---- audit 6: the browser ----------------------------------------
 ("the page never stops booting", "static/js/desk.js",
  'document.documentElement.classList.remove("booting");',
  '/* booting left on */'),
 ("a window she opened cannot be closed by clicking the dark",
  "static/js/desk.js", "if (t === win)\n            return win.close();",
  "if (false)\n            return win.close();"),
 ("a link to a window stops opening it", "static/js/desk.js",
  "if (!target.open)\n            target.showModal();", "if (false) target.showModal();"),
 ("the bar's height is no longer published", "static/js/desk.js",
  'document.documentElement.style.setProperty("--bar-h", `${ceiling}px`);', ""),
 ("a film keeps playing after its window is closed", "static/js/desk.js",
  'win.querySelector("video")?.pause();', ""),
 ("the desk stops becoming a grid on a phone", "static/css/site.css",
  "@media (max-width: 40rem) {\n  .desk {", "@media (max-width: 1rem) {\n  .desk {"),
 ("an off-site script is added to every page", "templates/base.html",
  "<body class=", '<script src="https://cdn.example.com/x.js"></script>\n<body class='),
 ("the content security policy is removed", "templates/base.html",
  '<meta http-equiv="Content-Security-Policy"', '<meta name="was-the-policy"'),
 ("the panel stops sending its token", "tools/studio/app.js",
  'const q = (p) => p + (p.includes("?") ? "&" : "?") + "t=" + encodeURIComponent(TOKEN);',
  'const q = (p) => p;'),
 ("the gallery stops lazy-loading", "templates/gallery.html",
  'alt="{{ alt }}" loading="lazy" decoding="async"></a>',
  'alt="{{ alt }}" decoding="async"></a>'),
 ("a photograph loses its alt", "templates/gallery.html",
  'width="{{ shape.width }}" height="{{ shape.height }}"\n             alt="{{ alt }}"',
  'width="{{ shape.width }}" height="{{ shape.height }}"\n             alt=""'),
 ("the canvas drops a picture's width", "templates/selection.html",
  '--w:{{ wide }}; --o:{{ rank }};', '--o:{{ rank }};'),
 ("a desk stops saying which desk it is", "templates/section.html",
  'data-desk="content/{{ section.colocated_path }}"', ''),
 ("the canvas loses its reserved shape", "static/css/site.css",
  "aspect-ratio: 100 / var(--tall, 100);", ""),
 ("a cursor becomes the system arrow", "static/css/site.css",
  'body                                   { cursor: url("../img/cursors/arrow.png") 0 0, auto; }',
  'body                                   { cursor: default; }'),
 ("the gallery stops being a dark room", "static/css/site.css",
  "body.gallery { background: #0d0b0a; }", "body.gallery { background: #fff; }"),
 ("a photo accepts a second image", "tools/studio/verbs.py",
  '    if kind_of(d) == "photo" and photographs_in(d):\n'
  '        raise Refused("c\'est une photo seule, et elle en a déjà une."\n'
  '                      " Pour en montrer plusieurs, fais-en une page.")\n', ""),
 ("a thrown photograph is unlinked, not binned", "tools/studio/verbs.py",
  '    shutil.move(str(f), str(dest))\n    record("remove_image"',
  '    f.unlink()\n    shutil.copyfile(str(dest), str(dest)) if False else None\n    record("remove_image"'),
 ("the write gate stops checking the fence", "tools/studio/verbs.py",
  '    if p.suffix == ".md" and _under_content(p):',
  '    if False and p.suffix == ".md" and _under_content(p):'),
 ("a verb writes only the French file", "tools/studio/verbs.py",
  "def language_files(d: pathlib.Path) -> list:\n"
  '    stem = "_index" if (d / "_index.md").exists() else "index"\n'
  '    return sorted(d.glob(stem + "*.md"))',
  "def language_files(d: pathlib.Path) -> list:\n"
  '    stem = "_index" if (d / "_index.md").exists() else "index"\n'
  '    return [d / (stem + ".md")]'),
 ("the model counts our files as her photographs", "tools/studio/model.py",
  "        if f.stem.lower() in SPOKEN_FOR:\n            continue\n", ""),
 ("the desk drag works in the phone view", "tools/studio/app.js",
  "      if (e.button !== 0 || narrowView) return;",
  "      if (e.button !== 0) return;"),
 # THE COMPILED FILE, not src/ — see the docstring. And it has to
 # REMOVE the suppression rather than add one: the first attempt
 # inserted a `preventDefault()` into a branch that already had one,
 # which changes nothing and reported a gap that was not there. A
 # mutation nobody notices is either a hole or a no-op, and telling
 # them apart is the whole discipline.
 ("a dragged icon also opens its window", "static/js/desk.js",
  "if (byPointer && justDragged.has(icon)) {\n            e.preventDefault();",
  "if (byPointer && justDragged.has(icon)) {"),
 ("the order is read from the file names again", "templates/gallery.html",
  "    {% if rank != turn and not (rank == 0 and turn == turns) %}{% continue %}{% endif %}\n", ""),
 ("a page stops reading her description", "templates/page.html",
  '{% if w.extra.alt and w.extra.alt[file] %}{% set alt = w.extra.alt[file] %}{% endif %}',
  '{% set alt = "" %}'),
 ("the phone keeps the composition's widths", "static/css/site.css",
  "    width: calc(var(--pw, 100) * 1%);", "    width: 100%;"),
]

keep = pathlib.Path(tempfile.mkdtemp())
touched = sorted({m[1] for m in M})
for f in touched:
    (keep / f.replace("/", "__")).write_bytes((ROOT / f).read_bytes())

def restore():
    for f in touched:
        (ROOT / f).write_bytes((keep / f.replace("/", "__")).read_bytes())

print("  %-44s %s" % ("mutation", "noticed by"))
missed = []
try:
    for name, f, old, new in M:
        p = ROOT / f
        text = p.read_text(encoding="utf-8")
        if text.count(old) < 1:
            print("  %-44s  ?? the text to break was not found" % name[:44])
            continue
        p.write_text(text.replace(old, new, 1), encoding="utf-8")
        caught = []
        for tag, cmd in SUITES:
            r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            if r.returncode != 0:
                caught.append(tag)
        restore()
        if not caught:
            missed.append(name)
        print("  %-44s %s" % (name[:44], ", ".join(caught) or "** NOBODY **"))
finally:
    restore()
    shutil.rmtree(keep, ignore_errors=True)
print("\n  %d of %d went unnoticed" % (len(missed), len(M)))
for m in missed:
    print("    -", m)
