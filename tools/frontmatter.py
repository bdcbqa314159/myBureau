#!/usr/bin/env python3
"""What a content file is, in one place.

A content file is `+++`, a TOML header, `+++`, and then her words:

    +++
    title = "theodora 01.jpeg"
    +++

    Texte de présentation à venir.

That sentence was written out by hand in nine places across four
modules — look.py, model.py, verbs.py and the panel's own suite — each
splitting on `+++` and each deciding for itself what a malformed file
meant. None of them disagreed yet. They were nine chances to.

It matters more here than duplication usually does: a content file
turned up twice with its header gone and the site stopped building.
The cause was found on 2026-11-14 — `verbs.set_key` anchored its
pattern with `^\s*` and ate the newline after the opening fence — and
the gate in verbs.atomic() now refuses a fence that is not alone on
its line. Knowledge like that belongs in one module.

NOTE WHAT parts() HANDS BACK, because it is what the bug turned on:
pieces[1] BEGINS with the newline that follows the opening `+++`. A
caller rewriting the header has to leave that newline alone.

THE SPLIT IS DELIBERATELY NAIVE, and must stay so: `text.split("+++")`
is what every caller already did, and a stricter parser would change
which files are accepted on a tree nobody has audited. This module
moves the knowledge; it does not get to redefine it.
"""
from __future__ import annotations   # macOS ships 3.9

import re

FENCE = "+++"


def parts(text: str) -> list:
    """The raw pieces, for a caller that is going to put them back.

    `["", header, body]` for a well-formed file. Anything shorter than
    three pieces has no closing fence and is for the caller to refuse —
    this returns what is there rather than deciding on its behalf.
    """
    return text.split(FENCE)


def rejoin(pieces: list) -> str:
    """The inverse of parts(), so a rewrite cannot invent a fence."""
    return FENCE.join(pieces)


def is_whole(text: str) -> bool:
    """Does this have a header between two fences at all?"""
    return len(parts(text)) >= 3


def header(text: str) -> str:
    """Between the fences. Empty when there is no closing one."""
    pieces = parts(text)
    return pieces[1] if len(pieces) >= 3 else ""


def body(text: str) -> str:
    """Her words, after the closing fence. Empty when there is none.

    SPLIT TWICE AND NO MORE. This returned `parts(text)[2]`, which is
    the text between the second fence and a THIRD one — so a paragraph
    containing `+++` came back cut off at it. The panel showed the
    short version, and saving anything then wrote the short version to
    disk: her words, silently shortened by a sequence she is perfectly
    entitled to type. Found by audit 2.
    """
    pieces = text.split(FENCE, 2)
    return pieces[2].strip() if len(pieces) >= 3 else ""


def why_zola_refuses(text: str) -> str:
    """Why zola would not read this, in her words, or "" if it would.

    THE ONE READER. There were two: this test, and a weaker one in
    look.py that asked only whether the text STARTED with `+++` and
    held two of them. `+++title = "x"` satisfies both — it is the file
    that broke the site twice — so the tool whose whole job is to say
    what will not work reported "nothing to report" while zola refused
    the build. Found by audit 2; see specs/the-audit.md.
    """
    if not text.strip():
        return "le fichier est vide"
    if not text.startswith(FENCE):
        return "il ne commence pas par +++"
    # A FENCE IS A LINE OF ITS OWN. `+++title = "x"` starts with +++
    # and holds two of them, which is why the weaker test passed it.
    first = text.split("\n", 1)[0].rstrip("\r")
    if first != FENCE:
        return "il y a autre chose que +++ sur la première ligne"
    if text.count(FENCE) < 2:
        return "l'en-tête n'est pas fermée par un second +++"
    rest = text.split("\n", 1)[1] if "\n" in text else ""
    if not any(l.rstrip("\r") == FENCE for l in rest.split("\n")):
        return "le second +++ n'est pas seul sur sa ligne"
    return ""


def toml_name(name: str) -> str:
    """A FILE NAME as a TOML key, with its own quotes escaped.

    Her names are hers, and the Finder lets her put a `"` in one. It
    went into `[extra.alt]` raw — `"vue "x".jpg" = "…"` — which zola
    refuses, so describing a photograph could stop the site building.

    HERE RATHER THAN IN verbs.py, because the panel WRITES these keys
    and the model READS them back: escaping in one place and parsing in
    the other is how the panel came to show no description at all for a
    photograph the site described perfectly well. One spelling, one
    module. See `map_of`.
    """
    return name.replace("\\", "\\\\").replace('"', '\\"')


def map_of(header: str, table: str) -> dict:
    """A `[extra.<table>]` block as a plain map, keyed by file name.

    The inverse of `toml_name` for the key, and the values come back as
    strings — the caller knows whether it wants a number.

    `model.alt_of` and `model.place_of` were two copies of this with
    their own regexes, and neither understood an escaped name.
    """
    block = re.search(r'^\[' + re.escape(table) + r'\]\s*$(.*?)(?=^\[|\Z)',
                      header, re.M | re.S)
    if not block:
        return {}
    out = {}
    # `(?:[^"\\]|\\.)*` — anything but a quote or a backslash, or an
    # escaped pair. A plain `[^"]+` stops at the first escaped quote and
    # reads half a name.
    for m in re.finditer(r'^\s*"((?:[^"\\]|\\.)*)"\s*=\s*(.+?)\s*$',
                         block.group(1), re.M):
        name = m.group(1).replace('\\"', '"').replace("\\\\", "\\")
        value = m.group(2).strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        out[name] = value
    return out
