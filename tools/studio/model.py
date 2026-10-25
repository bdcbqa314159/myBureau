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
DOC = {".pdf"}
# a file the engine gives a job to, so it is never one of the photographs
SPOKEN_FOR = {"icon", "poster", "wallpaper", "about"}


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


def alt_of(fm: str) -> dict:
    """`[extra.alt]` as a plain map, keyed by file name."""
    block = re.search(r'^\[extra\.alt\]\s*$(.*?)(?=^\[|\Z)', fm, re.M | re.S)
    if not block:
        return {}
    return {m.group(1): m.group(2) for m in
            re.finditer(r'^\s*"([^"]+)"\s*=\s*"([^"]*)"', block.group(1), re.M)}


def video(folder: pathlib.Path) -> "str | None":
    for f in sorted(folder.iterdir()):
        if f.is_file() and f.suffix.lower() in VIDEO:
            return f.name
    return None


def doc(folder: pathlib.Path) -> "str | None":
    """The dossier, if this project is one. The engine takes the first it
    finds, so this reports the same one the page will show."""
    for f in sorted(folder.iterdir()):
        if f.is_file() and f.suffix.lower() in DOC:
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
        "about": special(folder, "about"),
        # the affiche — the panel shows it as the proof a film landed
        "poster": special(folder, "poster"),
        "photographs": photographs(folder),
        # what each photograph shows, for a screen reader — the map
        # page.html reads, so the panel can show what is already written
        "alt": alt_of(first),
        "video": video(folder),
        "doc": doc(folder),
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


def opens_as(d: dict, depth: int) -> str:
    """What clicking this folder does — which depends on WHERE it is.

    Straight out of section.html, and the last clause is the one that
    surprises people:

        on the home desk   a page of its own, and a place in the bandeau
        anywhere else      a window on the desk it sits on
        a gallery          a page, wherever it is
        EMPTY              a page, wherever it is — a window listing
                           nothing is worse than the page

    So a folder just created is empty and therefore opens a page, even
    where a window was wanted. It becomes a window the moment something
    is put in it. Without being told that, making a folder inside a
    bureau and clicking it looks broken while being exactly right.
    """
    if d["gallery"]:
        return "page"
    if not d["on"]:
        return "page"
    return "page" if depth <= 1 else "window"


def identity() -> dict:
    """What the top bar says, and which of the two blocks is in use."""
    text = (ROOT / "config.toml").read_text(encoding="utf-8")
    which = "real" if re.search(r'^\s*live\s*=\s*true', text, re.M) else "demo"
    block = re.search(r'^\[extra\.' + which + r'\]\s*$(.*?)(?=^\[|\Z)',
                      text, re.M | re.S)
    out = {"block": which, "owner": "", "studio": "", "live": which == "real"}
    if block:
        for key in ("owner", "studio"):
            got = re.search(r'^\s*' + key + r'\s*=\s*"(.*)"', block.group(1), re.M)
            if got:
                out[key] = got.group(1)
    return out


def tree() -> dict:
    desks = []
    for f in sorted(CONTENT.rglob("_index.md")):
        d = desk(f.parent)
        rel = str(f.parent.relative_to(CONTENT))
        d["depth"] = 0 if rel == "." else len(rel.split("/"))
        d["opens_as"] = opens_as(d, d["depth"])
        d["empty"] = not d["on"]
        d["holds"] = len(d["on"])
        # Whether anything may be filed into it. A gallery renders its own
        # photographs and nothing else, so a thing put there would be
        # built and shown nowhere — verbs.move refuses it, and the panel
        # reads this rather than restating the rule and drifting from it.
        d["can_receive"] = not d["gallery"]
        desks.append(d)

    # ONE FOLDER, ONE SET OF FACTS.
    #
    # A bureau appears twice: once as a child of the bureau it sits on,
    # and once as a desk in its own right. Those were two different
    # objects, and only the desk one knew whether it was a gallery, how
    # deep it sat, or what a click would do.
    #
    # So choosing `pellicules` in the list gave something that did not
    # know it was a gallery, and the panel hid its twelve photographs —
    # while arriving at the same folder another way showed them. The
    # inconsistency was not in the panel's rules but in it being handed
    # two different descriptions of one thing.
    known = {d["path"]: d for d in desks}
    for d in desks:
        for child in d["on"]:
            if child["kind"] == "about":
                continue                      # shares the home desk's path
            k = known.get(child["path"])
            if k is None:
                continue                      # a project: not a desk anywhere
            for field in ("gallery", "depth", "opens_as", "empty", "holds",
                          "can_receive"):
                child[field] = k[field]

    # ---- about me.txt ------------------------------------------------
    # It is not a folder and not a project: it is a window declared in
    # [extra.items], so nothing in content/ represents it and it had no
    # row. Its portrait and its words are the home page's, which is why
    # they were reachable only by knowing to select the home desk — and
    # then they sat under that desk's own name and text, two fields that
    # mean something else entirely.
    #
    # It carries the home desk's path, because that is the file its two
    # verbs write. The panel keys it as "about" so the two rows stay
    # distinct; see keyOf() in app.js.
    home = known.get("content")
    if home is not None:
        home["on"].append({
            "kind": "about",
            "path": home["path"],
            "name": "about me.txt",
            "titles": {code: "about me.txt" for code in home["languages"]},
            "bodies": home["bodies"],
            "about": home["about"],
            "languages": home["languages"],
            # it has no desk of its own, nothing in it, and its position
            # is declared in config-like front matter we do not rewrite
            "x": None, "y": None, "opens": None, "icon": None,
            "wallpaper": None, "photographs": [], "video": None, "doc": None,
        })
    return {"desks": desks, "identity": identity()}


if __name__ == "__main__":
    json.dump(tree(), sys.stdout, indent=2, ensure_ascii=False)
    print()
