#!/usr/bin/env python3
"""What is on the desks, read from the filesystem.

    python3 tools/studio/model.py        # print the model as JSON

The dashboard needs to know what a desk holds and where each icon sits.
That is already decided in three places — the templates, look.py, and the
content files themselves — so this reads the SAME source the templates
read, the front matter, and nothing else. It never caches: the filesystem
is the truth, and somebody editing a file in TextEdit has to win.

Deliberately small. It knows what a desk holds and where things sit. It
does not know what a click opens — the templates decide that, and a
second opinion about it would be a second thing to keep in step.
"""
from __future__ import annotations   # macOS ships 3.9

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
CONTENT = ROOT / "content"

IMAGE = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif"}
VIDEO = {".mp4", ".webm", ".mov", ".m4v"}
# a file the engine gives a job to, so it is never one of the photographs
SPOKEN_FOR = {"icon", "poster", "wallpaper"}


def front(p: pathlib.Path) -> str:
    t = p.read_text(encoding="utf-8", errors="replace")
    parts = t.split("+++")
    return parts[1] if len(parts) >= 3 else ""


def body(p: pathlib.Path) -> str:
    t = p.read_text(encoding="utf-8", errors="replace")
    parts = t.split("+++")
    return parts[2].strip() if len(parts) >= 3 else ""


def key(fm: str, name: str) -> "str | None":
    m = re.search(r'^\s*' + name + r'\s*=\s*"([^"]*)"', fm, re.M)
    if m:
        return m.group(1)
    m = re.search(r'^\s*' + name + r'\s*=\s*([0-9]+)\s*$', fm, re.M)
    return m.group(1) if m else None


def langs(folder: pathlib.Path, stem: str) -> dict:
    """Every language file for one thing, keyed by language code.

    `index.md` is the default language and `index.en.md` is English; the
    pair is one object as far as the dashboard is concerned, because
    editing one and forgetting the other is the mistake this whole tool
    exists to remove.
    """
    out = {}
    for f in sorted(folder.glob(stem + "*.md")):
        bits = f.name[len(stem):-3].strip(".")
        out[bits or "fr"] = f
    return out


def photographs(folder: pathlib.Path) -> list:
    out = []
    for f in sorted(folder.iterdir()):
        if not f.is_file() or f.suffix.lower() not in IMAGE:
            continue
        if f.stem.lower() in SPOKEN_FOR:
            continue
        out.append(f.name)
    return out


def special(folder: pathlib.Path, kind: str) -> "str | None":
    for f in sorted(folder.iterdir()):
        if f.is_file() and f.stem.lower() == kind:
            return f.name
    return None


def video(folder: pathlib.Path) -> "str | None":
    for f in sorted(folder.iterdir()):
        if f.is_file() and f.suffix.lower() in VIDEO:
            return f.name
    return None


def thing(folder: pathlib.Path, stem: str, kind: str) -> dict:
    files = langs(folder, stem)
    fm = {code: front(f) for code, f in files.items()}
    first = fm.get("fr", "")
    return {
        "kind": kind,
        "path": str(folder.relative_to(ROOT)),
        "name": folder.name,
        "titles": {code: (key(t, "title") or folder.name) for code, t in fm.items()},
        "bodies": {code: body(f) for code, f in files.items()},
        "x": key(first, "x"),
        "y": key(first, "y"),
        "opens": key(first, "opens"),
        "icon": special(folder, "icon") or key(first, "icon"),
        "wallpaper": special(folder, "wallpaper"),
        "photographs": photographs(folder),
        "video": video(folder),
        # which language files exist, so the dashboard can say "English is
        # missing" rather than silently editing one of two
        "languages": sorted(files),
    }


def desk(folder: pathlib.Path) -> dict:
    d = thing(folder, "_index", "desk")
    fm = front(next(iter(langs(folder, "_index").values())))
    d["gallery"] = (key(fm, "template") or "") == "gallery.html"
    d["on"] = []
    for child in sorted(folder.iterdir()):
        if not child.is_dir():
            continue
        if (child / "_index.md").exists():
            d["on"].append(thing(child, "_index", "folder"))
        elif (child / "index.md").exists():
            d["on"].append(thing(child, "index", "project"))
    return d


def tree() -> dict:
    desks = []
    for f in sorted(CONTENT.rglob("_index.md")):
        desks.append(desk(f.parent))
    return {"desks": desks}


if __name__ == "__main__":
    json.dump(tree(), sys.stdout, indent=2, ensure_ascii=False)
    print()
