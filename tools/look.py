#!/usr/bin/env python3
"""Look over the content and say what will not work.

    python3 tools/look.py

./preview.sh runs this for you. It reports things the build cannot:
a build either works or it does not, and all of these BUILD FINE and
then quietly do nothing. They were found by trying them, one at a time,
on a copy of the site.

Nothing here is an error. It prints and exits 0 — the site still works,
it is just not doing what the content file asked for. The repair is on
the line under each one.
"""
from __future__ import annotations   # macOS ships 3.9; `X | Y` needs 3.10

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
STATIC = ROOT / "static"

IMAGE_TYPES = {"jpg", "jpeg", "png", "webp", "avif", "gif"}
VIDEO_TYPES = {"mp4", "webm", "mov", "m4v"}
# things a design program exports that this site will not show
LOOKS_LIKE_AN_IMAGE = {"tif", "tiff", "bmp", "heic", "heif", "psd", "ai", "svg", "raw", "dng", "cr2", "nef"}


def front_matter(p: pathlib.Path) -> str:
    t = p.read_text(encoding="utf-8", errors="replace")
    parts = t.split("+++")
    return parts[1] if len(parts) >= 3 else ""


def main() -> int:
    notes: list[tuple[str, list[str]]] = []

    for md in sorted(CONTENT.rglob("*.md")):
        where = str(md.relative_to(ROOT))
        fm = front_matter(md)
        lines: list[str] = []

        # 1. an icon that is not there -> a broken picture on the desk
        for icon in re.findall(r'^\s*icon\s*=\s*"([^"]+)"', fm, re.M):
            if not (STATIC / icon).exists() and not (md.parent / icon).exists():
                lines.append(f'icon = "{icon}" — there is no such file')
                lines.append("   fix: check the spelling, or delete the line and a standard icon is used")

        # 2. a link with no https:// -> the browser reads it as a page here
        for url in re.findall(r'url\s*=\s*"([^"]+)"', fm):
            if url.startswith(("#", "/")) or "://" in url:
                continue
            lines.append(f'url = "{url}" — no https://, so this points inside the site, not out')
            lines.append(f'   fix: url = "https://{url}"')

        # 3. a wallpaper on the gallery -> the gallery is a dark room
        if 'template = "gallery.html"' in fm and re.search(r"^\s*wallpaper\s*=", fm, re.M):
            lines.append("wallpaper = … — a gallery has no wallpaper, this line does nothing")
            lines.append("   fix: delete the line")

        if lines:
            notes.append((where, lines))

    # 4. a picture in a format the site does not show
    for f in sorted(CONTENT.rglob("*")):
        if not f.is_file():
            continue
        ext = f.suffix.lstrip(".").lower()
        if ext in LOOKS_LIKE_AN_IMAGE and ext not in IMAGE_TYPES:
            notes.append((str(f.relative_to(ROOT)), [
                f"a .{ext} is not shown on the site — only "
                + ", ".join(sorted(IMAGE_TYPES)),
                "   fix: export it again as JPEG or PNG",
            ]))

    # 5. a project folder with nothing in it to look at
    for md in sorted(CONTENT.rglob("index.md")):
        folder = md.parent
        has_media = any(
            f.suffix.lstrip(".").lower() in IMAGE_TYPES | VIDEO_TYPES
            and f.stem.lower() not in ("icon", "poster")
            for f in folder.iterdir() if f.is_file()
        )
        body = md.read_text(encoding="utf-8", errors="replace").split("+++")[-1].strip()
        if not has_media and len(body) < 40:
            notes.append((str(md.relative_to(ROOT)), [
                "no pictures and almost no text — this page is empty",
                "   fix: add images to the folder, or write something under the +++",
            ]))

    if not notes:
        print("\n  Nothing to report — everything in content/ will do what it says.\n")
        return 0

    print(f"\n  {len(notes)} thing(s) worth a look. None of them stop the site working.\n")
    for where, lines in notes:
        print(f"  {where}")
        for line in lines:
            print(f"    {line}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
