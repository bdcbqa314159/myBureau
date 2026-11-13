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
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT / "tools"))
import filetypes  # noqa: E402
import frontmatter  # noqa: E402
CONTENT = ROOT / "content"
STATIC = ROOT / "static"

# config.toml owns these, and tools/filetypes.py is the one reader.
# look.py prints "everything in content/ will do what it says",
# so it must not hold its own idea of what a photograph is.
IMAGE_TYPES = filetypes.IMAGE_TYPES
VIDEO_TYPES = filetypes.VIDEO_TYPES
DOC_TYPES = filetypes.DOC_TYPES
SPOKEN_FOR = filetypes.SPOKEN_FOR
# things a design program exports that this site will not show
LOOKS_LIKE_AN_IMAGE = {"tif", "tiff", "bmp", "heic", "heif", "psd", "ai", "svg", "raw", "dng", "cr2", "nef"}


def front_matter(p: pathlib.Path) -> str:
    t = p.read_text(encoding="utf-8", errors="replace")
    return frontmatter.header(t)


def unseen_by_git() -> list:
    """Files under content/ that git is ignoring.

    HIDDEN FILES ARE NOT HERS. macOS writes a `.DS_Store` into every
    folder a Finder window has ever been opened on, and those are
    ignored by git exactly as they should be. Reporting them said three
    files were missing from the site and told her to commit Finder's
    droppings — advice that is worse than the problem it describes, on a
    run it refused to let through at all.

    Nothing this site shows is a hidden file: a content file is a `.md`
    or a photograph she dropped in. So the scan looks at what she put
    there and nothing else. This also covers `._name.jpg`, the other
    half AppleDouble leaves on a non-Mac disk.
    """
    files = [p for p in CONTENT.rglob("*")
             if p.is_file() and not p.name.startswith(".")]
    if not files or not (ROOT / ".git").exists():
        return []                 # a scratch copy of the site, not a clone
    done = subprocess.run(
        ["git", "check-ignore", "--stdin"], cwd=ROOT, text=True,
        input="\n".join(str(f.relative_to(ROOT)) for f in files),
        capture_output=True)
    # 0 = some were ignored, 1 = none were, anything else = no git to ask
    if done.returncode not in (0, 1):
        return []
    out = []
    for line in done.stdout.splitlines():
        if line.strip():
            out.append((line.strip(), [
                "git is ignoring this file, so it is not in the repository.",
                "The deploy builds from a checkout, so the live site will not"
                " have it — however right the preview looks.",
                "fix: add an exception for it in .gitignore",
            ]))
    return out


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

        # 3b. a wallpaper line AND a wallpaper file -> the line does nothing
        if re.search(r"^\s*wallpaper\s*=", fm, re.M):
            folder = md.parent
            if any(f.is_file() and f.stem.lower() == "wallpaper" for f in folder.iterdir()):
                lines.append("wallpaper = … — there is also a wallpaper file in this"
                             " folder, and the file wins. This line does nothing.")
                lines.append("   fix: delete the line, or delete the file")

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
            # SPOKEN_FOR, not ("icon", "poster"): a folder holding
            # nothing but a wallpaper counted as a folder with work in
            # it, so this warning could never fire on a converted desk
            # — the one shape that most needs telling.
            and f.stem.lower() not in SPOKEN_FOR
            for f in folder.iterdir() if f.is_file()
        )
        body = frontmatter.body(md.read_text(encoding="utf-8", errors="replace"))
        if not has_media and len(body) < 40:
            notes.append((str(md.relative_to(ROOT)), [
                "no pictures and almost no text — this page is empty",
                "   fix: add images to the folder, or write something under the +++",
            ]))

    # 5b. two photographs behind one icon -> the second is unreachable
    #
    # A thing on a desk that opens as a photograph is ONE photograph.
    # Put two in, and the desk shows one icon: the second exists, is
    # built, and can only be reached by opening the first. A film, a
    # document and a page are all allowed to hold several — each says so
    # in a way the engine already reads, so none of them lands here.
    for md in sorted(CONTENT.rglob("index.md")):
        folder = md.parent
        if 'opens = "page"' in md.read_text(encoding="utf-8", errors="replace"):
            continue
        files = [f for f in folder.iterdir() if f.is_file()]
        exts = {f.suffix.lstrip(".").lower() for f in files}
        if exts & VIDEO_TYPES or exts & DOC_TYPES:
            continue
        pictures = [f for f in files
                    if f.suffix.lstrip(".").lower() in IMAGE_TYPES
                    and f.stem.lower() not in SPOKEN_FOR]
        if len(pictures) > 1:
            notes.append((str(folder.relative_to(ROOT)), [
                f"{len(pictures)} photos ici, mais une seule icone sur le"
                " bureau — on ne peut ouvrir les autres qu'en passant par"
                " la premiere",
                "   fix: un dossier par photo, chacune avec son nom",
                '   ou, si c\'est une page avec plusieurs images voulues :'
                ' ajoute opens = "page" dans [extra]',
            ]))

    # 6. a text file that is nearly index.md -> the folder is not on the site
    #    TextEdit saves `index.md` as `index.md.txt` unless you insist, and
    #    the build is perfectly happy: it just never sees the folder.
    for folder in sorted(d for d in CONTENT.rglob("*") if d.is_dir()):
        if (folder / "index.md").exists() or (folder / "_index.md").exists():
            continue
        for f in sorted(folder.iterdir()):
            if f.is_file() and re.fullmatch(r"_?index\..+", f.name) and f.suffix.lower() != ".md":
                notes.append((str(f.relative_to(ROOT)), [
                    f"{f.name} is not index.md, so this folder is not on the site at all",
                    "   fix: rename it to index.md",
                ]))

    # 7. two projects in the same folder with the same title -> almost
    #    always a duplicated folder whose other language file was never
    #    renamed. The desk then shows the old name twice.
    titles: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for md in sorted(CONTENT.rglob("*index*.md")):
        if md.parent == CONTENT:
            continue
        title = re.search(r'^\s*title\s*=\s*"([^"]+)"', front_matter(md), re.M)
        if title is None:
            continue
        titles.setdefault((str(md.parent.parent), md.name), []).append(
            (title.group(1), str(md.relative_to(ROOT)))
        )
    for group in titles.values():
        seen: dict[str, str] = {}
        for title, where in group:
            if title in seen:
                notes.append((where, [
                    f'title = "{title}" — the same title as {seen[title]},'
                    " so the desk shows that name twice",
                    "   fix: change this title (a duplicated folder has one"
                    " file per language, and both need renaming)",
                ]))
            seen[title] = where

    # ---- is anything in content/ invisible to git? ------------------
    # The deploy builds from a CHECKOUT, not from this disk. A file under
    # content/ that .gitignore swallows is therefore a page referring to
    # something nobody ever committed: right in the preview, 404 on the
    # live site, and nothing anywhere announcing it.
    #
    # This exists because `*.pdf` — written to keep a client's brief out
    # of a public repository — also swallowed every dossier the panel
    # writes, from the day the engine learned to show PDFs.
    # This one is not advice. Everything else look.py reports is a thing
    # that looks wrong; this is a thing that WILL be wrong the moment it
    # is deployed, and the deploy runs this. So it stops the run.
    # ---- a file zola will not read -----------------------------------
    # Not advice either: the site does not build at all. It happened —
    # a content file turned up with its front matter gone and the only
    # thing that said so was zola, in the middle of a build log, while
    # this tool said "nothing to report".
    unreadable = []
    for md in sorted(CONTENT.rglob("*.md")):
        text = md.read_text(encoding="utf-8", errors="replace")
        why = ("le fichier est vide" if not text.strip()
               else "ne commence pas par +++" if not text.startswith("+++")
               else "pas de second +++ pour fermer l'en-tête"
               if text.count("+++") < 2 else "")
        if why:
            unreadable.append((str(md.relative_to(ROOT)), [
                "no front matter — " + why,
                "zola cannot build the site at all while this is true:"
                ' "Couldn\'t find front matter in ..."',
                "fix: the file needs +++ on its own line, the title and any"
                " other settings, then a closing +++",
            ]))
    if unreadable:
        print("\n  REFUSED: {} file(s) under content/ have no front"
              " matter.\n".format(len(unreadable)))
        for where, lines in unreadable:
            print("  " + where)
            for line in lines:
                print("    " + line)
        print()
        return 1

    hidden = unseen_by_git()
    if hidden:
        print("\n  REFUSED: {} file(s) under content/ are not in the"
              " repository.\n".format(len(hidden)))
        for where, lines in hidden:
            print("  " + where)
            for line in lines:
                print("    " + line)
        print()
        return 1

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
