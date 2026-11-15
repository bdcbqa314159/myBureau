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

sys.path.insert(0, str(ROOT / "tools"))
import filetypes  # noqa: E402
import frontmatter  # noqa: E402
CONTENT = ROOT / "content"

# config.toml owns these. See tools/filetypes.py.
IMAGE, VIDEO, DOC = filetypes.IMAGE, filetypes.VIDEO, filetypes.DOC
# a file the engine gives a job to, so it is never one of the photographs
# config.toml owns these too. See tools/filetypes.py — this was a
# fourth copy of the list, and the panel never read the config at all.
SPOKEN_FOR = filetypes.SPOKEN_FOR


def front(p: pathlib.Path) -> str:
    return frontmatter.header(p.read_text(encoding="utf-8", errors="replace"))


def body(p: pathlib.Path) -> str:
    return frontmatter.body(p.read_text(encoding="utf-8", errors="replace"))


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


def place_of(fm: str) -> dict:
    """`[extra.place]` as a plain map — file name to rank, a number.

    THROUGH frontmatter.map_of, which is the same reader the escaping
    was written for. This had its own regex, `"([^"]+)"`, which stops
    at the first escaped quote — so a photograph named `vue "x".jpg`
    came back as no entry at all and the panel showed none of what the
    site showed. Found by audit 2.
    """
    out = {}
    for name, value in frontmatter.map_of(fm, "extra.place").items():
        try:
            out[name] = int(value)
        except ValueError:
            continue                 # a rank that is not a number is no rank
    return out


def shot_of(fm: str) -> dict:
    """`[extra.shot]` as a map — file name to its left, top and width.

    An inline table, so the values come back as one string and the
    three numbers are picked out of it. Only `top` is read today, to
    put the panel's list in the order the canvas shows; the other two
    are there because a reader that returns half a fact invites a
    second reader for the other half.
    """
    out = {}
    for name, value in frontmatter.map_of(fm, "extra.shot").items():
        got = {}
        for part in ("left", "top", "width"):
            m = re.search(part + r"\s*=\s*(-?[\d.]+)", value)
            if m:
                try:
                    got[part] = float(m.group(1))
                except ValueError:
                    pass
        if got:
            out[name] = got
    return out


def photographs(folder: pathlib.Path, fm: str = "") -> list:
    """Her photographs, IN THE ORDER THE PAGE SHOWS THEM.

    The panel's list is how she rearranges a page's photographs, so a
    list in a different order from the site is a list that lies.

    TWO ORDERS, because there are two kinds of page. A gallery and a
    project page read a RANK — `[extra.place]`, rank first and then
    everything unarranged by name, exactly what the turn loop in the
    templates does. A CANVAS reads no rank at all: it places each
    picture by a top, so reading down the page is reading down the
    tops. The panel listed a canvas by rank, which is an order its
    page does not have. Found by audit 2.
    """
    out = []
    for f in sorted(folder.iterdir()):
        if not f.is_file() or f.suffix.lower() not in IMAGE:
            continue
        if f.stem.lower() in SPOKEN_FOR:
            continue
        # A DOSSIER'S PAGE, drawn from the PDF — not a photograph she
        # dropped, so the panel must not offer it for reordering or a
        # description, and must not let her throw one away on its own.
        # See verbs.pages_of for the `page-NN` convention.
        if f.stem.lower().split("-")[0] == "page":
            continue
        out.append(f.name)
    placed = shot_of(fm)
    if placed:
        out.sort(key=lambda n: (placed.get(n, {}).get("top", 10 ** 6), n))
        return out
    rank = place_of(fm)
    out.sort(key=lambda n: (rank.get(n, 10 ** 6), n))
    return out


def face_of(folder: pathlib.Path, fm: str) -> str:
    """Which of the three icon slots holds this thing's face.

    HER NOTE FIRST. A folder she drew and a photograph are the same
    kind of file, so the bytes cannot say which slot a dropped image
    belongs to — only she can, and `set_icon` writes it down.

    The guesses below are the fallback for anything she set before the
    note existed: a `.gif` moves so it is the GIF slot, another
    colocated file is a photograph, a declared `img/icons/folder…` is
    one of ours.
    """
    said = key(fm, "face") or ""
    if said in ("folder", "photo", "gif"):
        return said
    got = special(folder, "icon")
    if got:
        return "gif" if got.lower().endswith(".gif") else "photo"
    if "/icons/folder" in (key(fm, "icon") or ""):
        return "folder"
    return ""


def special(folder: pathlib.Path, kind: str) -> "str | None":
    for f in sorted(folder.iterdir()):
        if f.is_file() and f.stem.lower() == kind:
            return f.name
    return None


def alt_of(fm: str) -> dict:
    """`[extra.alt]` as a plain map, keyed by file name. See place_of."""
    return frontmatter.map_of(fm, "extra.alt")


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
        # `kind` here is the MODEL's own word for where a row came from
        # — "desk", "folder", "project", "about" — and it is about
        # structure, not about what she made.
        "kind": kind,
        # `type` is HERS: photo, video, page, folder, written into the
        # file when she made it. See specs/the-four-types.md. Empty for
        # anything that predates it, and for the home desk, which is
        # not a thing she made.
        #
        # The two are deliberately separate words. Merging them is
        # tempting and wrong: the model's `kind` says a folder appears
        # twice in the tree, hers says what the folder IS.
        "type": key(first, "kind") or "",
        "path": str(folder.relative_to(ROOT)),
        "name": folder.name,
        "titles": {code: (key(t, "title") or folder.name) for code, t in fm.items()},
        "bodies": {code: body(f) for code, f in files.items()},
        "x": key(first, "x"),
        "y": key(first, "y"),
        "opens": key(first, "opens"),
        # WHICH TEMPLATE RENDERS THIS, because it is the fact that
        # decides what the object can even show. `desk()` read it,
        # tested it for "gallery.html" and threw it away — so the panel
        # could not tell a DESK (icons on a wallpaper) from a
        # FOLDER-PAGE (a title, a text and the work below it), and
        # offered both of them everything.
        #
        # Empty for a project, which declares none and gets page.html.
        "template": key(first, "template") or "",
        "icon": special(folder, "icon") or key(first, "icon"),
        # WHICH OF THE THREE SLOTS holds the face, so the panel can
        # show one chosen and two empty rather than one box whose
        # meaning depends on what is in the folder.
        #
        #   "gif"     a colocated icon.gif — it moves on the desk
        #   "photo"   any other colocated icon.*
        #   "folder"  a drawn one declared in the front matter
        #   ""        none of the three; the engine falls back
        #
        # Read in _icon.html's own order of precedence: a colocated
        # file beats a declared path. If that order ever changes this
        # becomes a lie — which is why `set_icon` and `set_face` each
        # clear the other two rather than relying on it.
        "face": face_of(folder, first),
        "wallpaper": special(folder, "wallpaper"),
        "about": special(folder, "about"),
        # the affiche — the panel shows it as the proof a film landed
        "poster": special(folder, "poster"),
        "photographs": photographs(folder, first),
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
    d["gallery"] = d["template"] == "gallery.html"
    # THE CANVAS: travail sélectionné. The same object as a gallery —
    # a folder that holds photographs itself — with a different page:
    # there she places each picture rather than ordering them. The
    # panel offers the photographs pane for both and the placing
    # gesture only here. See specs/the-canvas.md.
    d["canvas"] = d["template"] == "selection.html"
    d["holds_photographs"] = d["gallery"] or d["canvas"]
    d["on"] = []
    for child in sorted(folder.iterdir()):
        if not child.is_dir():
            continue
        if (child / "_index.md").exists():
            d["on"].append(thing(child, "_index", "folder"))
        elif (child / "index.md").exists():
            d["on"].append(thing(child, "index", "project"))
    return d


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
        d["empty"] = not d["on"]
        d["holds"] = len(d["on"])
        # Whether anything may be filed into it. A folder that holds
        # PHOTOGRAPHS renders its own and nothing else, so a thing put
        # there would be built and shown nowhere — verbs.move refuses
        # it, and the panel reads this rather than restating the rule
        # and drifting from it. BOTH of them: travail sélectionné
        # joined pellicules on 2026-11-15, and the panel went on
        # offering it as a destination the server would refuse.
        d["can_receive"] = not d["holds_photographs"]
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
            for field in ("gallery", "canvas", "holds_photographs",
                          "depth", "empty", "holds",
                          "can_receive", "template", "type"):
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
            # it is a <dialog> on the home page, not a template of its
            # own; the panel keys off `kind` for this row, and the field
            # is here so every row carries the same set
            "template": "", "type": "", "face": "",
        })
    return {"desks": desks, "identity": identity()}


if __name__ == "__main__":
    json.dump(tree(), sys.stdout, indent=2, ensure_ascii=False)
    print()
