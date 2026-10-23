#!/usr/bin/env python3
"""Does the site survive the mistakes a person actually makes?

    python3 tools/content-check.py          # run every case
    python3 tools/content-check.py --keep   # leave the scratch build to inspect

The content contract is "drop a folder in and it works". That promise is
only worth something if it holds when the folder is wrong — and the
templates have been rewritten several times since anyone last checked.

Each case copies the whole site into a scratch directory, adds one
realistic mistake, builds, and reads the HTML. Nothing here touches the
real content/ — a case that corrupts something corrupts a copy.

A case is not "does it build". A build can succeed and still have lost
the icon, stacked two folders on the same pixel, or given two pages the
same view-transition-name so the morph silently dies. So each case says
what it expects to SEE.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
COPY = ["content", "templates", "static", "tools", "config.toml", "sass"]

FRONT = '+++\ntitle = "{title}"\n{extra}+++\n\nUn texte.\n'


def site(tmp: pathlib.Path) -> pathlib.Path:
    """A disposable copy of the site, minus the heavy placeholder photos
    we do not need to rebuild for every case."""
    d = tmp / "site"
    d.mkdir()
    for name in COPY:
        src = ROOT / name
        if not src.exists():
            continue
        if src.is_dir():
            shutil.copytree(src, d / name, symlinks=True)
        else:
            shutil.copyfile(src, d / name)
    return d


def build(d: pathlib.Path) -> tuple[bool, str]:
    r = subprocess.run(["zola", "build"], cwd=d, capture_output=True, text=True)
    return r.returncode == 0, (r.stderr or "") + (r.stdout or "")


def page(d: pathlib.Path, rel: str) -> str:
    p = d / "public" / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


# ---------------------------------------------------------------------
# the cases. each returns a list of (what was expected, did it hold)
# ---------------------------------------------------------------------

def case_no_icon(d: pathlib.Path) -> list[tuple[str, bool]]:
    """A project with no icon file and no declared icon."""
    p = d / "content" / "da" / "sans-icone"
    p.mkdir()
    (p / "index.md").write_text(FRONT.format(title="sans icone.png", extra=""))
    ok, log = build(d)
    h = page(d, "da/index.html")
    return [
        ("builds", ok),
        ("the project appears on the bureau", "sans icone.png" in h),
        ("a generic icon stands in", bool(re.search(r'sans-icone.*?<img[^>]+src="[^"]*icons/', h, re.S))
                                      or "icons/photo.svg" in h),
    ]


def case_shouting_extension(d: pathlib.Path) -> list[tuple[str, bool]]:
    """PHOTO.JPG straight off a camera — capitals everywhere."""
    p = d / "content" / "da" / "criard"
    p.mkdir()
    (p / "index.md").write_text(FRONT.format(title="CRIARD.JPG", extra=""))
    shutil.copyfile(ROOT / "content/da/theodora/01.jpg", p / "GRANDE.JPG")
    ok, log = build(d)
    h = page(d, "da/criard/index.html")
    return [
        ("builds", ok),
        ("the capitalised image is resized like any other", "processed_images" in h),
        ("the title's capitalised extension still picks the photo icon",
         "icons/photo.svg" in page(d, "da/index.html")),
    ]


def case_same_name_twice(d: pathlib.Path) -> list[tuple[str, bool]]:
    """The same project name in two different bureaus."""
    for parent in ("da", "graphic-design"):
        p = d / "content" / parent / "jumeau"
        p.mkdir()
        (p / "index.md").write_text(FRONT.format(title="jumeau.pdf", extra=""))
    ok, log = build(d)
    a = re.findall(r"view-transition-name:([\w-]+)", page(d, "da/jumeau/index.html"))
    b = re.findall(r"view-transition-name:([\w-]+)", page(d, "graphic-design/jumeau/index.html"))
    return [
        ("builds", ok),
        ("both pages exist", bool(a) and bool(b)),
        ("their transition names differ, so the morph is not ambiguous", a != b),
    ]


def case_new_bureau(d: pathlib.Path) -> list[tuple[str, bool]]:
    """A new top-level bureau, which nobody remembered to add to the nav."""
    p = d / "content" / "scenographie"
    p.mkdir()
    (p / "_index.md").write_text(FRONT.format(
        title="scenographie", extra='template = "section.html"\n'))
    ok, log = build(d)
    h = page(d, "index.html")
    nav = re.search(r'<nav class="bar-nav">.*?</nav>', h, re.S)
    return [
        ("builds", ok),
        ("it appears on the desktop", "scenographie" in h),
        ("it appears in the bandeau without anyone editing a list",
         bool(nav) and "scenographie" in nav.group(0)),
    ]


def case_no_position(d: pathlib.Path) -> list[tuple[str, bool]]:
    """Three folders with no x/y — the stacking case."""
    for n in ("un", "deux", "trois"):
        p = d / "content" / f"libre-{n}"
        p.mkdir()
        (p / "_index.md").write_text(FRONT.format(
            title=f"libre {n}", extra='template = "section.html"\n'))
    ok, log = build(d)
    h = page(d, "index.html")
    # an unplaced icon is given a slot, which _icon.html turns into a
    # percentage pair — so "did it stack" is "are any two identical"
    spots = re.findall(r"--x:\s*([\d.]+)%?;\s*--y:\s*([\d.]+)", h)
    mine = [s for s in spots if s not in
            [(str(x), str(y)) for x, y in ((66, 66), (14, 52), (78, 22),
                                           (28, 26), (52, 30), (52, 58), (30, 72))]]
    return [
        ("builds", ok),
        ("three new icons were placed", len(mine) >= 3),
        ("no two icons landed on the same spot", len(spots) == len(set(spots))),
    ]


def case_awkward_name(d: pathlib.Path) -> list[tuple[str, bool]]:
    """Spaces, an apostrophe and an accent in a folder name."""
    p = d / "content" / "da" / "l'ete prochain"
    p.mkdir()
    (p / "index.md").write_text(FRONT.format(title="l'été prochain.jpg", extra=""))
    ok, log = build(d)
    h = page(d, "da/index.html")
    href = re.search(r'href="([^"]*ete-prochain[^"]*)"', h)
    landed = href and (d / "public" / href.group(1).split("/myBureau/")[-1] / "index.html").exists()
    return [
        ("builds", ok),
        ("the link is slugified, not left with spaces", bool(href)),
        ("and it points at a page that exists", bool(landed)),
    ]


def case_empty_project(d: pathlib.Path) -> list[tuple[str, bool]]:
    """A project page with no images at all — the half-finished one."""
    p = d / "content" / "da" / "a-venir"
    p.mkdir()
    (p / "index.md").write_text(FRONT.format(title="a venir.txt", extra=""))
    ok, log = build(d)
    h = page(d, "da/a-venir/index.html")
    return [
        ("builds", ok),
        ("the page still renders its text", "Un texte." in h),
        ("and still offers a way back", "←" in h),
    ]


def case_untranslated_page(d: pathlib.Path) -> list[tuple[str, bool]]:
    """A page added in French only, after the English site exists."""
    p = d / "content" / "da" / "nouveau"
    p.mkdir()
    (p / "index.md").write_text(FRONT.format(title="nouveau.jpg", extra=""))
    ok, log = build(d)
    return [
        ("builds", ok),
        ("it is on the French bureau", "nouveau.jpg" in page(d, "da/index.html")),
        ("the English bureau is not broken by its absence",
         "<nav" in page(d, "en/da/index.html")),
        ("tools/i18n.py names it as missing",
         "da/nouveau" in subprocess.run([sys.executable, str(d / "tools/i18n.py")],
                                        cwd=d, capture_output=True, text=True).stdout),
    ]


def case_declared_wallpaper(d: pathlib.Path) -> list[tuple[str, bool]]:
    """A bureau that declares a wallpaper. This caught a real one: the
    pellicules gallery declared one for months and it was never rendered,
    because body.gallery is a deliberate dark room. A line in a content
    file that quietly does nothing is exactly what this contract exists
    to prevent."""
    p = d / "content" / "tapisserie"
    p.mkdir()
    (p / "_index.md").write_text(FRONT.format(
        title="tapisserie",
        extra='template = "section.html"\n\n[extra]\nwallpaper = "img/wall-da.jpg"\n'))
    ok, log = build(d)
    h = page(d, "tapisserie/index.html")
    used = re.search(r"--wallpaper:url\('([^']+)'\)", h)
    return [
        ("builds", ok),
        ("the declared wallpaper is actually rendered", bool(used)),
        ("it went through the resize pipeline rather than being served raw",
         bool(used) and "processed_images" in used.group(1)),
        ("a phone gets a smaller one", "--wallpaper-narrow" in h),
    ]


def case_alt_text(d: pathlib.Path) -> list[tuple[str, bool]]:
    """Alt text written in front matter reaches the image."""
    p = d / "content" / "da" / "decrit"
    p.mkdir()
    (p / "index.md").write_text(
        '+++\ntitle = "decrit.jpg"\n\n[extra.alt]\n"01.jpg" = "Une plage au crepuscule."\n+++\n\nUn texte.\n')
    shutil.copyfile(ROOT / "content/da/theodora/01.jpg", p / "01.jpg")
    shutil.copyfile(ROOT / "content/da/theodora/02.jpg", p / "02.jpg")
    ok, log = build(d)
    h = page(d, "da/decrit/index.html")
    return [
        ("builds", ok),
        ("the described photograph carries its description",
         'alt="Une plage au crepuscule."' in h),
        ("the one with no description stays alt=\"\" rather than inventing one",
         h.count('alt=""') >= 1),
    ]


def dangling(h: str) -> list[str]:
    """Every data-window on a page that has no dialog to open.

    This is the failure mode folder windows are built on top of: the icon
    renders, the build is clean, and the click does nothing at all. Worth
    asserting on every page of every case rather than once.
    """
    have = set(re.findall(r'<dialog[^>]*id="([^"]+)"', h))
    return [w for w in re.findall(r'data-window="([^"]+)"', h) if w not in have]


def case_folder_window(d: pathlib.Path) -> list[tuple[str, bool]]:
    """A new bureau with a project in it opens as a window on the desk."""
    p = d / "content" / "scenographie"
    p.mkdir()
    (p / "_index.md").write_text(FRONT.format(
        title="scenographie", extra='template = "section.html"\n'))
    q = p / "les-planches"
    q.mkdir()
    (q / "index.md").write_text(FRONT.format(title="les planches.jpg", extra=""))
    ok, log = build(d)
    h = page(d, "index.html")
    win = re.search(r'<dialog class="win win-folder" id="folder-scenographie">.*?</dialog>',
                    h, re.S)
    return [
        ("builds", ok),
        ("the folder has a window on the home desk", bool(win)),
        ("the folder icon opens it",
         'data-window="folder-scenographie"' in h),
        ("the project inside is in the window",
         bool(win) and "les planches.jpg" in win.group(0)),
        ("the project inside flows rather than being pinned to the desk",
         bool(win) and "icon is-flow" in win.group(0)),
        ("the folder is still a link, so it works without JavaScript",
         bool(re.search(r'<a class="icon"[^>]*href="[^"]*scenographie/"', h))),
        ("nothing on the home desk points at a window that is not there",
         dangling(h) == []),
    ]


def case_three_deep(d: pathlib.Path) -> list[tuple[str, bool]]:
    """A folder three levels down — deeper than the windows are rendered.

    The windows are written out to two levels because the template engine
    has no recursion. The third level must then NAVIGATE, not render an
    icon wired to a dialog nobody made.
    """
    p = d / "content" / "un"
    p.mkdir()
    (p / "_index.md").write_text(FRONT.format(
        title="un", extra='template = "section.html"\n'))
    q = p / "deux"
    q.mkdir()
    (q / "_index.md").write_text(FRONT.format(
        title="deux", extra='template = "section.html"\n'))
    r = q / "trois"
    r.mkdir()
    (r / "_index.md").write_text(FRONT.format(
        title="trois", extra='template = "section.html"\n'))
    s = r / "projet"
    s.mkdir()
    (s / "index.md").write_text(FRONT.format(title="projet.jpg", extra=""))
    ok, log = build(d)
    home = page(d, "index.html")
    deux = re.search(r'<dialog class="win win-folder" id="folder-un-deux">.*?</dialog>',
                     home, re.S)
    return [
        ("builds", ok),
        ("the home desk has no dangling window reference", dangling(home) == []),
        ("depth 2 still gets a window", bool(deux)),
        ("depth 3 inside it is a link and not a dead icon",
         bool(deux) and 'data-window="folder-un-deux-trois"' not in deux.group(0)
                     and "un/deux/trois/" in deux.group(0)),
        ("the deepest bureau is still reachable as its own desk",
         "projet.jpg" in page(d, "un/deux/trois/index.html")),
        ("and that desk has no dangling reference either",
         dangling(page(d, "un/deux/trois/index.html")) == []),
    ]


def case_film_in_a_folder(d: pathlib.Path) -> list[tuple[str, bool]]:
    """A video inside a folder, opened from the window rather than the desk.

    The film dialog lives on whichever page shows the icon. An icon in the
    `da` window on the HOME page needs its film on the home page too, or
    the click does nothing.
    """
    ok, log = build(d)
    home = page(d, "index.html")
    da = re.search(r'<dialog class="win win-folder" id="folder-da">.*?</dialog>',
                   home, re.S)
    return [
        ("builds", ok),
        ("the da window is on the home desk", bool(da)),
        ("the film inside it points at a film window",
         bool(da) and 'data-window="film-da-junes-cry"' in da.group(0)),
        ("and that film window is on the home desk too",
         'id="film-da-junes-cry"' in home),
        ("no page has a dangling window reference",
         all(dangling(page(d, str(f.relative_to(d / "public")))) == []
             for f in (d / "public").rglob("index.html"))),
    ]


CASES = [
    ("a project with no icon", case_no_icon),
    ("PHOTO.JPG in capitals", case_shouting_extension),
    ("the same name in two bureaus", case_same_name_twice),
    ("a new bureau nobody added to the nav", case_new_bureau),
    ("three folders with no x/y", case_no_position),
    ("spaces, an apostrophe and an accent", case_awkward_name),
    ("a project with no images", case_empty_project),
    ("a page added in French only", case_untranslated_page),
    ("a bureau that declares a wallpaper", case_declared_wallpaper),
    ("alt text written in front matter", case_alt_text),
    ("a bureau with a project opens as a window", case_folder_window),
    ("a folder three levels down", case_three_deep),
    ("a film opened from inside a folder window", case_film_in_a_folder),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keep", action="store_true", help="leave the scratch builds behind")
    args = ap.parse_args()

    failed = 0
    print()
    for name, fn in CASES:
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="mybureau-"))
        try:
            results = fn(site(tmp))
        except Exception as exc:                       # noqa: BLE001
            print(f"  FAIL  {name}\n          raised {exc!r}")
            failed += 1
            continue
        finally:
            if args.keep:
                print(f"        scratch: {tmp}")
            else:
                shutil.rmtree(tmp, ignore_errors=True)

        bad = [w for w, held in results if not held]
        if bad:
            failed += 1
            print(f"  FAIL  {name}")
            for w, held in results:
                print(f"          {'ok ' if held else 'NO '} {w}")
        else:
            print(f"  ok    {name}  ({len(results)} expectations)")

    total = sum(1 for _ in CASES)
    print(f"\n  {total - failed}/{total} cases hold\n" if failed
          else f"\n  all {total} cases hold\n")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
