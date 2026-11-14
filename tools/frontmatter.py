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
    """Her words, after the closing fence. Empty when there is none."""
    pieces = parts(text)
    return pieces[2].strip() if len(pieces) >= 3 else ""
