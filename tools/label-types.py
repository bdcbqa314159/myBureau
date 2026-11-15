#!/usr/bin/env python3
"""Write `kind` into the things that were made before it existed.

    python3 tools/label-types.py            # say what it would do
    python3 tools/label-types.py --write    # do it

A thing's TYPE is now written into its front matter when she makes it,
and read from there for ever after — see TYPES in tools/studio/verbs.py.
Everything made before that has no `kind`, and what it is has to be
worked out once, by hand, from what is in the folder.

ONCE. This is not a fallback and must not become one: the whole point
of writing the type down is that nothing re-derives it from a name or
from a file listing. The guesses below are exactly the inference being
retired, used one last time to seed the answer, and then this script
has no reason to run again.

    a video in it                  -> video
    a PDF, or more than one image   -> page
    exactly one image              -> photo
    an `_index.md` on the home desk -> folder

`travail sélectionné` and `pellicules` are NOT labelled: they are their
own things on the main desktop — a road and a gallery — and their
templates already say so.
"""
from __future__ import annotations   # macOS ships 3.9

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import filetypes      # noqa: E402
import frontmatter    # noqa: E402

CONTENT = ROOT / "content"
# PELLICULES AND TRAVAIL SÉLECTIONNÉ ARE FOLDERS TOO. They were left
# out of this as "their own things", and that was the same mistake in a
# smaller shape: with no `kind` the panel did not know they were
# folders, so it offered them a photo slot and a GIF slot for an icon
# that is a folder's icon.
#
# They ARE folders on the main desktop — a face, no wallpaper — and
# one of a kind: at most one gallery and at most one selection. What
# makes them special is still their template, until their own edition
# is designed.
LEAVE = set()


def guess(folder: pathlib.Path) -> str:
    """What this folder is, from what is in it. Used once, by this file."""
    files = [f for f in folder.iterdir() if f.is_file()]
    exts = {f.suffix.lower() for f in files}
    if exts & filetypes.VIDEO:
        return "video"
    pics = [f for f in files
            if f.suffix.lower() in filetypes.IMAGE
            and f.stem.lower() not in filetypes.SPOKEN_FOR
            and f.stem.lower().split("-")[0] != "page"]
    if exts & filetypes.DOC or len(pics) > 1:
        return "page"
    if len(pics) == 1:
        return "photo"
    # nothing in it yet. A folder sitting on the HOME desk holds a
    # desktop; anywhere else an empty thing is a page waiting for work.
    return "folder" if folder.parent == CONTENT else "page"


def label(text: str, kind: str) -> str:
    """Add `kind = "..."` under [extra], leaving every other byte.

    UNDER [extra], not at the top. Zola allows only its own keys at the
    top level of front matter and refuses the file outright:

        Reason: TOML parse error at line 3, column 1
        3 | kind = "folder"

    Everything of ours already lives under [extra] — x, y, icon,
    wallpaper, alt — and this is one more.
    """
    parts = frontmatter.parts(text)
    if len(parts) < 3:
        raise SystemExit("no front matter to write into")
    fm = parts[1]
    if re.search(r'^\s*kind\s*=', fm, re.M):
        return text                              # already labelled
    line = 'kind = "' + kind + '"'
    if re.search(r'^\[extra\][ \t]*$', fm, re.M):
        fm = re.sub(r'^(\[extra\][ \t]*)$', r'\1\n' + line,
                    fm, count=1, flags=re.M)
    else:
        # no [extra] yet. It goes at the END, because a bare key written
        # after a sub-table would silently belong to that table instead
        # — the same reason set_alt_key appends.
        fm = fm.rstrip("\n") + "\n\n[extra]\n" + line + "\n"
    parts[1] = fm
    return frontmatter.rejoin(parts)


def main() -> int:
    write = "--write" in sys.argv
    done = 0
    for md in sorted(list(CONTENT.rglob("index.md"))
                     + list(CONTENT.rglob("_index.md"))):
        folder = md.parent
        rel = str(folder.relative_to(ROOT))
        if folder == CONTENT or rel in LEAVE:
            continue
        # a desktop-holding folder on the main desk, or a thing inside one
        kind = "folder" if folder.parent == CONTENT else guess(folder)
        for f in sorted(folder.glob(md.stem + "*.md")):
            was = f.read_text(encoding="utf-8")
            now = label(was, kind)
            if now == was:
                continue
            print("  {:<46} {}".format(str(f.relative_to(ROOT)), kind))
            done += 1
            if write:
                f.write_text(now, encoding="utf-8")
    print("\n  {} file(s) {}\n".format(done, "written" if write else "to write"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
