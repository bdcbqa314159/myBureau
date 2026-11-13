#!/usr/bin/env python3
"""Which files are photographs, which are films, which are documents.

`config.toml` owns the answer — the site's templates read it from
there, and it is the thing somebody edits when a new format is wanted.
It was also written out by hand in four more places:

    model.py    IMAGE / VIDEO / DOC
    verbs.py    the same three again
    look.py     its own reader
    content-check.py  another reader

The two in the panel were hardcoded sets. They agreed with the config
on the day this was written — checked, not assumed — but the panel is
the thing she uses: add `heic` to config.toml and the site would render
it while the panel refused to accept the file.

So there is one reader. Adding a format stays a one-line change in
config.toml, and everything follows.

TWO SPELLINGS, because the callers genuinely differ. The panel compares
`pathlib.Path.suffix`, which carries the dot; the site's templates and
look.py split on "." and compare what follows. Returning both is
cheaper than making half the callers strip a dot.
"""
from __future__ import annotations   # macOS ships 3.9

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent

KEYS = {"image": "image_types", "video": "video_types", "doc": "doc_types"}

# Names the engine has taken for itself, whatever the extension —
# `icon`, `poster`, `wallpaper`, `about`. Same story as the three lists
# above: config.toml owns it, the templates read it from there, and the
# panel and look.py each kept a copy that had drifted.
NAMES = "not_photographs"


def read(root: "pathlib.Path | None" = None) -> dict:
    """The three lists, from config.toml, without the dots.

    `root` lets a check read the config of a scratch copy rather than
    this repository's own — which is the difference between testing a
    fixture and testing the machine the test runs on.
    """
    base = ROOT if root is None else pathlib.Path(root)
    text = (base / "config.toml").read_text(encoding="utf-8")
    out = {}
    for name, key in KEYS.items():
        m = re.search(r"^" + key + r"\s*=\s*\[([^\]]*)\]", text, re.M)
        out[name] = set(re.findall(r'"([^"]+)"', m.group(1))) if m else set()
    return out


def dotted(root: "pathlib.Path | None" = None) -> dict:
    """The same three, spelled the way `Path.suffix` spells them."""
    return {k: {"." + e for e in v} for k, v in read(root).items()}


def spoken_for(root: "pathlib.Path | None" = None) -> set:
    """The names that are ours rather than hers, lower-cased.

    A file called `poster.jpg` is a film's still wherever it sits; one
    called `01.jpg` is her work. Everything that lists photographs —
    the site's templates, the panel, look.py — has to agree about
    which, or the panel offers to delete a wallpaper as if it were a
    photograph nobody wanted.
    """
    base = ROOT if root is None else pathlib.Path(root)
    text = (base / "config.toml").read_text(encoding="utf-8")
    m = re.search(r"^" + NAMES + r"\s*=\s*\[([^\]]*)\]", text, re.M)
    return {s.lower() for s in re.findall(r'"([^"]+)"', m.group(1))} if m else set()


_bare = read()
_dot = dotted()

IMAGE = _dot["image"]
VIDEO = _dot["video"]
DOC = _dot["doc"]

# Everything the site serves as media, which is what a tool deciding
# "is this file still wanted?" needs. prune.py and the check beside it
# both spelled this union out; a matcher that misses one deletes a file
# the page asks for.
MEDIA = IMAGE | VIDEO | DOC

# The one copy. model.py and verbs.py each had their own; look.py had
# a shorter one.
SPOKEN_FOR = spoken_for()

IMAGE_TYPES = _bare["image"]
VIDEO_TYPES = _bare["video"]
DOC_TYPES = _bare["doc"]
