#!/usr/bin/env python3
"""The only things the dashboard is allowed to do.

A closed list, not a file manager. Every verb is small, validated before
it touches anything, and recorded so it can be taken back — which is what
makes the thing safe to play with, and playing with it is the point.

    place(item, x, y)             move an icon on its desk
    add_image(item, name, data)   a photograph arrives
    reorder(item, names)          01, 02, 03 — and so the icon, which is
                                  the first one
    remove_image(item, name)      to the bin, never unlink
    undo()                        take back the last thing

TWO RULES THAT ARE NOT NEGOTIABLE, because both have bitten this project:

  Every verb touching a project touches EVERY language file it has. A
  position written to `index.md` and not `index.en.md` leaves one language
  on the old spot with nothing to say so.

  Front matter is edited SURGICALLY — the one line, by regex, leaving the
  rest of the file byte for byte. These files carry load-bearing comments
  (read content/_index.md). A parse-and-rewrite would eat them silently.
"""
from __future__ import annotations   # macOS ships 3.9

import json
import os
import pathlib
import re
import shutil
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
CONTENT = ROOT / "content"
STUDIO = ROOT / ".studio"
JOURNAL = STUDIO / "journal.jsonl"
TRASH = STUDIO / "trash"

IMAGE = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif"}
SPOKEN_FOR = {"icon", "poster", "wallpaper"}


class Refused(Exception):
    """The verb was not allowed. The message is shown to the person."""


# ---------------------------------------------------------------------
# where things may happen
# ---------------------------------------------------------------------

def rel(p: "pathlib.Path | str") -> str:
    """A path as the journal records it: relative to the repository.

    Both sides are resolved first. On macOS /var is a symlink to
    /private/var, so a resolved path and an unresolved root do not compare
    — and the same is true of any repository reached through a symlink.
    """
    return str(pathlib.Path(p).resolve().relative_to(ROOT.resolve()))


def inside(p: "pathlib.Path | str") -> pathlib.Path:
    """Resolve a path and refuse anything outside content/.

    The dashboard is a web server that writes to disk. This is the only
    thing standing between a crafted request and the rest of the disk, so
    it resolves symlinks and compares real paths rather than trusting the
    string it was handed.
    """
    q = (ROOT / pathlib.Path(p)).resolve()
    try:
        q.relative_to(CONTENT.resolve())
    except ValueError:
        raise Refused("that is not in content/")
    return q


def a_project(p: "pathlib.Path | str") -> pathlib.Path:
    d = inside(p)
    if not d.is_dir():
        raise Refused("there is no folder there")
    if not any(d.glob("index*.md")) and not any(d.glob("_index*.md")):
        raise Refused("that folder is not a project or a bureau")
    return d


def language_files(d: pathlib.Path) -> list:
    stem = "_index" if (d / "_index.md").exists() else "index"
    return sorted(d.glob(stem + "*.md"))


# ---------------------------------------------------------------------
# writing, carefully
# ---------------------------------------------------------------------

def atomic(p: pathlib.Path, text: str) -> None:
    """Write via a temp file in the same directory, then rename.

    `zola serve` is watching this directory. A plain write is visible
    half-finished, and zola will occasionally read it and flash an error
    at her for something she did not do.
    """
    tmp = p.with_name(p.name + ".studio-tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, p)


def set_key(text: str, name: str, value) -> str:
    """Set one key in the front matter, leaving every other byte alone.

    Three cases, in order: the key is already there; there is an [extra]
    block to put it in; there is neither and one has to be made. Only the
    front matter is ever touched — the split on `+++` is what keeps an
    `x = ` in the body text from being rewritten.
    """
    parts = text.split("+++")
    if len(parts) < 3:
        raise Refused("that file has no front matter")
    fm = parts[1]
    line = "{} = {}".format(name, value if isinstance(value, int)
                            else '"{}"'.format(value))
    pattern = re.compile(r'^\s*' + re.escape(name) + r'\s*=.*$', re.M)
    if pattern.search(fm):
        fm = pattern.sub(line, fm, count=1)
    elif re.search(r'^\[extra\]\s*$', fm, re.M):
        fm = re.sub(r'^(\[extra\]\s*)$', r'\1\n' + line, fm, count=1, flags=re.M)
    else:
        fm = fm.rstrip("\n") + "\n\n[extra]\n" + line + "\n"
    parts[1] = fm
    return "+++".join(parts)


# ---------------------------------------------------------------------
# taking it back
# ---------------------------------------------------------------------

def record(verb: str, texts: list, moves: list) -> None:
    """One line per action, holding enough to reverse it.

    The .md files are under a kilobyte, so the whole previous text is
    kept rather than a diff — reversing is then "put it back", with
    nothing to get subtly wrong.
    """
    STUDIO.mkdir(exist_ok=True)
    entry = {"at": time.time(), "verb": verb, "texts": texts, "moves": moves}
    with JOURNAL.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def undo() -> str:
    if not JOURNAL.exists():
        raise Refused("nothing to take back")
    lines = JOURNAL.read_text(encoding="utf-8").splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        raise Refused("nothing to take back")
    entry = json.loads(lines[-1])
    for t in entry["texts"]:
        atomic(ROOT / t["path"], t["before"])

    # THROUGH A HOLDING NAME, every one of them, before anything lands.
    # A reorder is a permutation — 01 became 02 while 02 became 03 — and
    # undoing that with plain renames overwrites a photograph halfway
    # round the cycle. The forward verb stages for the same reason.
    staged = []
    for i, m in enumerate(entry["moves"]):
        src = ROOT / m["to"]
        if not src.exists():
            continue
        if not m["from"]:
            # it did not exist before this verb, so taking the verb back
            # means taking it away — to the bin, like everything else here
            TRASH.mkdir(parents=True, exist_ok=True)
            bin_ = TRASH / str(int(time.time() * 1000))
            bin_.mkdir(exist_ok=True)
            shutil.move(str(src), str(bin_ / src.name))
            continue
        hold = src.with_name(src.name + ".studio-undo-{}".format(i))
        os.replace(src, hold)
        staged.append((hold, ROOT / m["from"]))
    for hold, dst in staged:
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.replace(hold, dst)
    JOURNAL.write_text("\n".join(lines[:-1]) + ("\n" if lines[:-1] else ""),
                       encoding="utf-8")
    return entry["verb"]


# ---------------------------------------------------------------------
# the verbs
# ---------------------------------------------------------------------

def place(item: str, x: int, y: int) -> dict:
    d = a_project(item)
    x, y = int(x), int(y)
    if not (0 <= x <= 100 and 0 <= y <= 100):
        raise Refused("a position is a percentage of the desk, 0 to 100")
    texts = []
    for f in language_files(d):
        before = f.read_text(encoding="utf-8")
        after = set_key(set_key(before, "x", x), "y", y)
        if after != before:
            texts.append({"path": rel(f), "before": before})
            atomic(f, after)
    if texts:
        record("place", texts, [])
    return {"x": x, "y": y, "files": len(texts)}


def _next_number(d: pathlib.Path) -> int:
    taken = []
    for f in d.iterdir():
        if f.is_file() and f.suffix.lower() in IMAGE and f.stem.isdigit():
            taken.append(int(f.stem))
    return (max(taken) + 1) if taken else 1


def add_image(item: str, name: str, data: bytes) -> dict:
    d = a_project(item)
    ext = pathlib.Path(name).suffix.lower()
    if ext not in IMAGE:
        raise Refused("the site shows " + ", ".join(sorted(e[1:] for e in IMAGE)))
    if not data:
        raise Refused("that file is empty")
    dest = d / "{:02d}{}".format(_next_number(d), ext)
    tmp = dest.with_name(dest.name + ".studio-tmp")
    tmp.write_bytes(data)
    os.replace(tmp, dest)
    record("add_image", [], [{"from": "", "to": rel(dest)}])
    return {"named": dest.name}


def reorder(item: str, names: list) -> dict:
    """Renumber the photographs into the order given.

    Two phases, through a temporary name each: renaming 02 to 01 while 01
    still exists would lose one, and the order the browser sends is
    exactly the order that collides.
    """
    d = a_project(item)
    have = [f.name for f in sorted(d.iterdir())
            if f.is_file() and f.suffix.lower() in IMAGE
            and f.stem.lower() not in SPOKEN_FOR]
    if sorted(names) != sorted(have):
        raise Refused("that is not the same set of photographs")
    moves = []
    staged = []
    for i, n in enumerate(names, start=1):
        src = d / n
        hold = d / ("studio-hold-{}{}".format(i, src.suffix.lower()))
        os.replace(src, hold)
        staged.append((hold, "{:02d}{}".format(i, src.suffix.lower()), n))
    for hold, final, was in staged:
        os.replace(hold, d / final)
        if final != was:
            moves.append({"from": rel(d / was), "to": rel(d / final)})
    if moves:
        record("reorder", [], moves)
    return {"order": [s[1] for s in staged]}


def remove_image(item: str, name: str) -> dict:
    d = a_project(item)
    f = inside(pathlib.Path(item) / name)
    if not f.is_file():
        raise Refused("there is no such photograph")
    TRASH.mkdir(parents=True, exist_ok=True)
    bin_ = TRASH / str(int(time.time() * 1000))
    bin_.mkdir()
    dest = bin_ / f.name
    shutil.move(str(f), str(dest))
    record("remove_image", [], [{"from": rel(f), "to": rel(dest)}])
    return {"binned": f.name}
