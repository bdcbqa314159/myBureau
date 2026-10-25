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
import json
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
    """PHOTO.JPG straight off a camera — capitals everywhere.

    Two paths have to be case-blind, not one: the FILE extension, which
    now decides whether a picture becomes the project's icon, and the
    TITLE extension, which still decides the drawn icon when a folder has
    no picture at all.
    """
    p = d / "content" / "da" / "criard"
    p.mkdir()
    (p / "index.md").write_text(FRONT.format(title="CRIARD.JPG", extra=""))
    shutil.copyfile(ROOT / "content/da/theodora/01.jpg", p / "GRANDE.JPG")
    q = d / "content" / "da" / "criard-vide"
    q.mkdir()
    (q / "index.md").write_text(FRONT.format(title="VIDE.JPG", extra=""))
    ok, log = build(d)
    h = page(d, "da/criard/index.html")
    desk = page(d, "da/index.html")

    def img_of(slug: str) -> str:
        m = re.search(r'<a class="icon[^"]*"[^>]*data-vt="' + re.escape(slug)
                      + r'"[^>]*>\s*(<img[^>]*>)', desk, re.S)
        return m.group(1) if m else ""

    return [
        ("builds", ok),
        ("the capitalised image is resized like any other", "processed_images" in h),
        ("GRANDE.JPG is recognised as a picture and becomes the icon",
         "is-photo" in img_of("da-criard")),
        ("with no picture at all, VIDE.JPG still picks the drawn photo icon",
         "icons/photo.svg" in img_of("da-criard-vide")),
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


def case_the_panel_sees_what_the_site_renders(d: pathlib.Path) -> list[tuple[str, bool]]:
    """The dashboard must not become a third opinion about the content.

    The templates decide what a desk holds and where. look.py has its own
    reading. tools/studio/model.py now has a third, and three readings of
    one set of rules drift — quietly, because each is self-consistent.

    So: whatever the panel says is on a desk, and where, is checked
    against the HTML the site actually rendered.
    """
    # An EMPTY folder inside a bureau: the one case where the rule bites.
    # It would open as a window if it had anything in it, and opens a
    # page because it does not. Without this in the tree the clause never
    # fires and the guard below cannot tell whether the panel knows.
    vide = d / "content" / "da" / "vide"
    vide.mkdir()
    (vide / "_index.md").write_text(FRONT.format(
        title="vide", extra='template = "section.html"\n'))
    (vide / "_index.en.md").write_text(FRONT.format(
        title="empty", extra='template = "section.html"\n'))

    ok, log = build(d)
    r = subprocess.run([sys.executable, "tools/studio/model.py"], cwd=d,
                       capture_output=True, text=True)
    if r.returncode != 0:
        return [("builds", ok), ("the model runs at all", False)]
    tree = json.loads(r.stdout)

    where = {"desk": None}
    wrong_count, wrong_spot, missing = [], [], []
    for desk in tree["desks"]:
        rel = desk["path"][len("content"):].strip("/")
        html = page(d, (rel + "/index.html") if rel else "index.html")
        if not html or desk["gallery"]:
            continue
        main = re.search(r'<main class="desk".*?</main>', html, re.S)
        if main is None:
            continue
        rendered = {}
        for m in re.finditer(r'<a class="icon[^"]*"([^>]*)>', main.group(0)):
            vt = re.search(r'data-vt="([^"]+)"', m.group(1))
            # a declared position is an integer; the loose grid used to
            # write a float. Accept either, or this silently matches
            # nothing and passes by seeing no icons at all.
            xy = re.search(r'--x:([\d.]+)%; --y:([\d.]+)%', m.group(1))
            if vt and xy:
                rendered[vt.group(1)] = (xy.group(1), xy.group(2))
        # every thing the panel would draw has to be on the real desk
        for it in desk["on"]:
            slug = it["path"][len("content/"):].replace("/", "-")
            if slug not in rendered:
                missing.append(slug)
            elif it["x"] is not None and (
                    float(rendered[slug][0]) != float(it["x"])
                    or float(rendered[slug][1]) != float(it["y"])):
                wrong_spot.append((slug, it["x"], it["y"], rendered[slug]))
        # and the panel must not be missing one the desk shows
        shown = {s for s in rendered if "-" in s or True}
        if len(desk["on"]) and len(shown) < len(desk["on"]):
            wrong_count.append(desk["path"])

    # What the panel SAYS a folder will do, against what the site did.
    # The rule has a clause that catches people out — an empty folder
    # opens a page wherever it is — so a panel that got this wrong would
    # promise a window and deliver a page.
    lied = []
    by_path = {k["path"]: k for k in tree["desks"]}
    for desk in tree["desks"]:
        rel = desk["path"][len("content"):].strip("/")
        html = page(d, (rel + "/index.html") if rel else "index.html")
        if not html:
            continue
        for child in desk["on"]:
            k = by_path.get(child["path"])
            if k is None:                       # not a folder
                continue
            slug = child["path"][len("content/"):].replace("/", "-")
            windowed = 'data-window="folder-{}"'.format(slug) in html
            said = k["opens_as"]
            if windowed != (said == "window"):
                lied.append((child["path"], said, "window" if windowed else "page"))

    return [
        ("builds", ok),
        ("the panel reads every desk the site has",
         len(tree["desks"]) == len(list((d / "content").rglob("_index.md")))),
        ("and what it says a folder will do is what the site does",
         lied == []),
        ("including the empty one, which opens a page where a window would be",
         by_path.get("content/da/vide", {}).get("opens_as") == "page"),
        ("everything it would draw is really on that desk", missing == []),
        ("and at the position the site actually rendered", wrong_spot == []),
        ("it is not missing icons the desk shows", wrong_count == []),
    ]


def case_wallpaper_lives_in_the_folder(d: pathlib.Path) -> list[tuple[str, bool]]:
    """A desk's background is a file in the desk's own folder.

    It used to be a path typed into the front matter — of BOTH language
    files, pointing at something in static/. Changing one and not the
    other left a language on the old picture with nothing to say so, and
    it was the only thing in this engine that did not live where the
    content lives.
    """
    photo = (ROOT / "content" / "da" / "theodora" / "01.jpg").read_bytes()
    other = (ROOT / "content" / "graphic-design" / "wallpaper.jpg").read_bytes()
    # a brand new bureau, with nothing but a wallpaper dropped in
    p = d / "content" / "scenographie"
    p.mkdir()
    (p / "_index.md").write_text(FRONT.format(
        title="scenographie", extra='template = "section.html"\n'))
    (p / "_index.en.md").write_text(FRONT.format(
        title="scenography", extra='template = "section.html"\n'))
    (p / "wallpaper.jpg").write_bytes(photo)
    q = p / "dedans"
    q.mkdir()
    (q / "_index.md").write_text(FRONT.format(
        title="dedans", extra='template = "section.html"\n'))
    # and one with nothing at all, anywhere above it
    n = d / "content" / "nue"
    n.mkdir()
    (n / "_index.md").write_text(FRONT.format(
        title="nue", extra='template = "section.html"\n'))
    ok, log = build(d)

    def wall(rel: str) -> str:
        m = re.search(r"--wallpaper:url\('([^']*)", page(d, rel))
        return m.group(1).split("/")[-1] if m else "none"

    fr, en = wall("scenographie/index.html"), wall("en/scenographie/index.html")
    return [
        ("builds", ok),
        ("dropping the file in is the whole of it", fr.startswith("wallpaper.")),
        ("and it serves BOTH languages, with nothing edited twice", fr == en),
        ("a bureau inside it inherits, rather than needing its own copy",
         wall("scenographie/dedans/index.html") == fr),
        ("a bureau with no wallpaper anywhere above it still is not black",
         wall("nue/index.html").startswith("wall-home")),
        ("the demo's own desks each kept their own",
         len({wall("da/index.html"), wall("graphic-design/index.html"),
              wall("travail-selectionne/index.html")}) == 3),
        ("and a sub-bureau of those follows its parent",
         wall("da/maison-cosette/index.html") == wall("da/index.html")),
        ("no front matter in the whole site still types a wallpaper path",
         not any("wallpaper =" in f.read_text(encoding="utf-8")
                 for f in (d / "content").rglob("_index*.md"))),
    ]


def case_declared_wallpaper(d: pathlib.Path) -> list[tuple[str, bool]]:
    """A bureau that declares a wallpaper the old way, by path.

    Dropping `wallpaper.jpg` into the folder is how this is done now, but
    the declared form still works and has to keep working — somebody will
    have it in a branch. This also caught a real one once: the pellicules
    gallery declared a wallpaper for months and it was never rendered,
    because body.gallery is a deliberate dark room. A line in a content
    file that quietly does nothing is what this contract exists to
    prevent."""
    p = d / "content" / "tapisserie"
    p.mkdir()
    (p / "_index.md").write_text(FRONT.format(
        title="tapisserie",
        extra='template = "section.html"\n\n[extra]\nwallpaper = "img/wall-home.jpg"\n'))
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


def case_top_level_navigates(d: pathlib.Path) -> list[tuple[str, bool]]:
    """A bureau on the HOME desk goes to its own page with its own wallpaper.

    The brief is explicit: "les dossiers comme DA ouvre une nouvelle page,
    comme un nouveau bureau". The home desk is also the one place the
    bandeau reaches, and the two have to agree.
    """
    p = d / "content" / "scenographie"
    p.mkdir()
    (p / "_index.md").write_text(FRONT.format(
        title="scenographie", extra='template = "section.html"\n'))
    q = p / "les-planches"
    q.mkdir()
    (q / "index.md").write_text(FRONT.format(title="les planches.pdf", extra=""))
    ok, log = build(d)
    h = page(d, "index.html")
    desk = re.search(r'<main class="desk".*?</main>', h, re.S)
    return [
        ("builds", ok),
        ("it is on the home desk", bool(desk) and "scenographie" in desk.group(0)),
        ("it navigates rather than opening a window",
         'data-window="folder-scenographie"' not in h),
        ("no folder window is built for it on the home desk",
         'id="folder-scenographie"' not in h),
        ("it is a link to its own desk",
         bool(re.search(r'<a class="icon"[^>]*href="[^"]*scenographie/"', h))),
        ("that desk exists and shows what is in it",
         "les planches.pdf" in page(d, "scenographie/index.html")),
        ("nothing on the home desk points at a window that is not there",
         dangling(h) == []),
    ]


def case_second_level_window(d: pathlib.Path) -> list[tuple[str, bool]]:
    """A folder INSIDE a bureau opens as a window on that bureau's desk."""
    p = d / "content" / "graphic-design" / "sous-dossier"
    p.mkdir()
    (p / "_index.md").write_text(FRONT.format(
        title="sous dossier", extra='template = "section.html"\n'))
    q = p / "une-chose"
    q.mkdir()
    (q / "index.md").write_text(FRONT.format(title="une chose.pdf", extra=""))
    ok, log = build(d)
    h = page(d, "graphic-design/index.html")
    win = re.search(
        r'<dialog class="win win-folder" id="folder-graphic-design-sous-dossier">.*?</dialog>',
        h, re.S)
    return [
        ("builds", ok),
        ("the window is on the bureau's desk", bool(win)),
        ("the folder icon opens it",
         'data-window="folder-graphic-design-sous-dossier"' in h),
        ("what is inside is in the window",
         bool(win) and "une chose.pdf" in win.group(0)),
        ("the contents flow rather than being pinned to the desk",
         bool(win) and "icon is-flow" in win.group(0)),
        ("the folder is still a link, so it works without JavaScript",
         bool(re.search(r'href="[^"]*graphic-design/sous-dossier/"', h))),
        ("the home desk is untouched by it",
         'id="folder-graphic-design-sous-dossier"' not in page(d, "index.html")),
        ("no dangling window reference", dangling(h) == []),
    ]


def case_three_deep(d: pathlib.Path) -> list[tuple[str, bool]]:
    """A folder inside a window navigates — one level of windows per desk.

    There is no recursion in this template engine, so there has to be a
    floor. The floor must NAVIGATE rather than leave an icon wired to a
    dialog nobody built.
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
    (s / "index.md").write_text(FRONT.format(title="projet.pdf", extra=""))
    ok, log = build(d)
    un = page(d, "un/index.html")
    deux = re.search(r'<dialog class="win win-folder" id="folder-un-deux">.*?</dialog>',
                     un, re.S)
    every = list((d / "public").rglob("*.html"))
    return [
        ("builds", ok),
        ("a folder on a bureau's desk gets a window", bool(deux)),
        ("a folder inside that window navigates instead",
         bool(deux) and 'data-window="folder-un-deux-trois"' not in deux.group(0)
                     and "un/deux/trois/" in deux.group(0)),
        ("the deepest bureau is still reachable as its own desk",
         "projet.pdf" in page(d, "un/deux/trois/index.html")),
        ("no page anywhere has a dangling window reference",
         all(dangling(f.read_text(encoding="utf-8")) == [] for f in every)),
    ]


def case_what_a_file_does(d: pathlib.Path) -> list[tuple[str, bool]]:
    """One rule: a click shows you the thing.

    Whatever she called it, a project with a picture in it previews on the
    desk. The exceptions are the two that cannot work: a folder with a
    video is a film, and a folder with nothing to show has nothing to
    preview. `opens = "page"` is the one way to ask for the page instead.
    """
    base = d / "content" / "da"
    for name, title, extra, files in (
        ("une-image", "une image.png", "", ("01.jpg",)),
        ("un-dossier-pdf", "un dossier.pdf", "", ("01.jpg",)),
        ("sans-extension", "sans extension", "", ("01.jpg",)),
        ("plein-ecran", "plein ecran.png", 'opens = "page"\n', ("01.jpg",)),
        ("rien-a-voir", "rien a voir.txt", "", ()),
        ("un-clip", "un clip.png", "", ("01.jpg", "clip.mp4")),
    ):
        q = base / name
        q.mkdir()
        (q / "index.md").write_text(
            FRONT.format(title=title, extra=("[extra]\n" + extra) if extra else ""))
        for f in files:
            (q / f).write_bytes(
                b"\x00\x00\x00\x18ftypmp42" if f.endswith(".mp4")
                else (ROOT / "content" / "da" / "theodora" / "01.jpg").read_bytes())
    ok, log = build(d)
    h = page(d, "da/index.html")
    desk = re.search(r'<main class="desk".*?</main>', h, re.S)
    body = desk.group(0) if desk else ""

    found: dict[str, str] = {}
    for m in re.finditer(r'<a class="icon[^"]*"([^>]*)>', body):
        attrs = m.group(1)
        vt = re.search(r'data-vt="([^"]+)"', attrs)
        if vt is None:
            continue
        w = re.search(r'data-window="([^"]+)"', attrs)
        found[vt.group(1)] = w.group(1).split("-")[0] if w else "page"

    return [
        ("builds", ok),
        ("a .png previews", found.get("da-une-image") == "preview"),
        ("a .pdf previews too — the name does not decide this",
         found.get("da-un-dossier-pdf") == "preview"),
        ("no extension previews as well", found.get("da-sans-extension") == "preview"),
        ('opens = "page" goes straight to the page',
         found.get("da-plein-ecran") == "page"),
        ("a project with nothing to show navigates rather than opening an empty window",
         found.get("da-rien-a-voir") == "page"),
        ("a folder with a video is still a film", found.get("da-un-clip") == "film"),
        ("every window promised was built", dangling(h) == []),
    ]


def case_prune_keeps_what_the_site_asks_for(d: pathlib.Path) -> list[tuple[str, bool]]:
    """The deploy step deletes files. This is the net under it.

    tools/prune.py drops what the built site never requests. It runs
    between the build and the upload, so a prune that takes one file too
    many produces a site that builds, deploys, and is quietly missing a
    photograph. Everything here is about what must SURVIVE.
    """
    ok, log = build(d)
    pub = d / "public"
    before = {p for p in pub.rglob("*") if p.is_file()}
    html_before = {p: p.read_bytes() for p in pub.rglob("*.html")}

    r = subprocess.run([sys.executable, "tools/prune.py"], cwd=d,
                       capture_output=True, text=True)
    after = {p for p in pub.rglob("*") if p.is_file()}

    MEDIA = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif",
             ".mp4", ".webm", ".mov", ".m4v"}
    on_disk = {str(p.relative_to(pub)) for p in after}
    broken = []
    for p in list(pub.rglob("*.html")) + list(pub.rglob("*.css")):
        txt = p.read_text(encoding="utf-8", errors="replace")
        urls = set(re.findall(r'(?:src|href)="([^"]+)"', txt))
        urls |= {m.group(1) for m in re.finditer(r'url\(\s*[\'"]?([^)\'"]+)', txt)}
        for m in re.finditer(r'srcset="([^"]+)"', txt):
            urls |= {b.strip().split(" ")[0] for b in m.group(1).split(",") if b.strip()}
        for u in urls:
            tail = u.split("?")[0]
            if pathlib.PurePosixPath(tail).suffix.lower() not in MEDIA:
                continue
            if not any(tail.endswith("/" + x) or tail == x for x in on_disk):
                broken.append(tail)

    survived = lambda frag: any(frag in str(p) for p in after)
    return [
        ("builds", ok),
        ("prune succeeds", r.returncode == 0),
        ("it actually removed something", len(after) < len(before)),
        ("every page is still there",
         len([p for p in after if p.suffix == ".html"]) == len(html_before)),
        ("and byte-for-byte unchanged",
         all(p.exists() and p.read_bytes() == b for p, b in html_before.items())),
        ("nothing the site asks for is missing", broken == []),
        ("the cursors survived — they are referenced only from CSS",
         survived("cursors/open.png") and survived("cursors/no.png")),
        ("the brand marks survived", survived("brand/youtube-white.png")),
        ("the images the pages actually load survived",
         any("processed_images" in str(p) for p in after)),
        ("what the image pipeline made was never even a candidate",
         "generated file(s) never considered" in r.stdout
         and " 0 generated" not in r.stdout),
    ]


def case_every_page_can_say_what_it_is(d: pathlib.Path) -> list[tuple[str, bool]]:
    """Headings and link names — the two things a screen reader needs.

    Both were missing and neither showed: the site had no <h1> anywhere,
    and every photograph in the gallery was a link called nothing. Nothing
    looks wrong either way, which is exactly why it stayed broken.
    """
    photo = (ROOT / "content" / "da" / "theodora" / "01.jpg").read_bytes()
    g = d / "content" / "pellicules"
    (g / "sans-alt.jpg").write_bytes(photo)
    # one WITH alt text, to prove the label is not doubled up
    # [extra.alt] is a sub-table of [extra], so it goes last, just before
    # the closing fence. This file has no body at all.
    idx = g / "_index.md"
    txt = idx.read_text(encoding="utf-8").rstrip()
    assert txt.endswith("+++"), "the gallery front matter is not shaped as expected"
    idx.write_text(txt[: -3] + '[extra.alt]\n"01.jpg" = "Une description."\n+++\n',
                   encoding="utf-8")
    ok, log = build(d)
    pages = list((d / "public").rglob("*.html"))
    gal = page(d, "pellicules/index.html")
    unnamed = [a for a in re.findall(r'<a\b[^>]*>(?:\s*<img[^>]*>\s*)*</a>', gal)
               if "aria-label" not in a and not re.search(r'alt="[^"]+"', a)]
    described = re.search(r'<a class="shot"[^>]*>\s*<img[^>]*alt="Une description\."', gal, re.S)
    return [
        ("builds", ok),
        ("every page has an h1",
         all(re.search(r"<h1\b", p.read_text(encoding='utf-8')) for p in pages)),
        ("a project page's h1 is its title",
         bool(re.search(r'<h1[^>]*>theodora\.jpeg</h1>', page(d, "da/theodora/index.html")))),
        ("a desk's h1 is the bureau's name",
         bool(re.search(r'<h1[^>]*>DA</h1>', page(d, "da/index.html")))),
        ("no photograph in the gallery is a link called nothing", unnamed == []),
        ("where she wrote alt text, the photograph speaks for itself",
         bool(described) and 'aria-label' not in described.group(0)),
    ]


def case_about_is_a_screen(d: pathlib.Path) -> list[tuple[str, bool]]:
    """about me.txt opens at a size worth reading, and shows her words.

    The text comes from the body of the home page's own content file. If
    that ever stops being passed in, the window still opens, still looks
    right, and is empty — which nobody notices until a visitor does.
    """
    home = d / "content" / "_index.md"
    t = home.read_text(encoding="utf-8")
    home.write_text(t.replace("Texte de présentation à venir.",
                              "Je suis directrice artistique. MARQUEUR-ABOUT."))
    # A PORTRAIT, the way every other colocated file works: a file called
    # about.* beside _index.md, nothing declared. One file for both
    # languages, so the English window has to find it too — a translated
    # section reports its assets under /en/, and reaching for a file that
    # was never there is how the wallpaper broke twice.
    shutil.copyfile(ROOT / "content/da/theodora/01.jpg",
                    d / "content" / "about.jpg")
    ok, log = build(d)
    h = page(d, "index.html")
    win = re.search(r'<dialog class="win win-about" id="about">.*?</dialog>', h, re.S)
    en = re.search(r'<dialog class="win win-about" id="about">.*?</dialog>',
                   page(d, "en/index.html"), re.S)
    return [
        ("builds", ok),
        ("it opens as a screen rather than a dialog box", bool(win)),
        ("its body is the one that holds its size when the text is short",
         bool(win) and "about-body" in win.group(0)),
        ("the icon on the desk opens it", 'data-window="about"' in h),
        ("her text is actually in it",
         bool(win) and "MARQUEUR-ABOUT" in win.group(0)),
        ("the English desk has its own, with the English text",
         bool(en) and "MARQUEUR-ABOUT" not in en.group(0)),
        ("her portrait is in the window", bool(win) and "about-face" in win.group(0)),
        ("and ABOVE the words, not after them",
         bool(win) and win.group(0).index("about-face")
                     < win.group(0).index("MARQUEUR-ABOUT")),
        ("it went through the image pipeline rather than at full size",
         bool(win) and "processed_images" in re.search(
             r'about-face.*?</figure>', win.group(0), re.S).group(0)),
        ("the English window shows the same portrait",
         bool(en) and "about-face" in en.group(0)),
        ("and does not reach for it under /en/, where it is not",
         "/en/about." not in page(d, "en/index.html")),
        ("it is not also sitting on the desk as an icon",
         'about.jpg' not in re.sub(r'<dialog.*?</dialog>', '', h, flags=re.S)),
    ]


def case_gallery_photographs_open(d: pathlib.Path) -> list[tuple[str, bool]]:
    """Every photograph in the gallery opens, and opens its OWN window.

    Two windows sharing an id, or a link pointing at one that was never
    rendered, both build perfectly and both end in a click that does
    nothing — and in a gallery that is every photograph after the first.
    """
    photo = (ROOT / "content" / "da" / "theodora" / "01.jpg").read_bytes()
    g = d / "content" / "pellicules"
    # two names that slugify close to each other, plus one already there
    (g / "Vue 13.JPG").write_bytes(photo)
    (g / "vue-13.jpg").write_bytes(photo)
    ok, log = build(d)
    h = page(d, "pellicules/index.html")
    links = re.findall(r'<a class="shot" href="#([^"]+)"', h)
    ids = re.findall(r'<dialog[^>]*id="(shot-[^"]+)"', h)
    imgs = len(re.findall(r'<a class="shot"[^>]*>\s*<img', h))
    return [
        ("builds", ok),
        ("every photograph is a link", len(links) > 0 and imgs == len(links)),
        ("every link has a window to open", set(links) <= set(ids)),
        ("one window per photograph", len(ids) == len(links)),
        ("no two photographs share a window id", len(ids) == len(set(ids))),
        ("the large file is lazy, so a closed window costs nothing",
         all('loading="lazy"' in m for m in
             re.findall(r'<dialog[^>]*class="[^"]*win-shot[^"]*"[^>]*>.*?</dialog>', h, re.S))),
        ("a capitalised extension is a photograph too", "Vue 13.JPG" in h),
    ]


def case_the_project_page_has_a_rhythm(d: pathlib.Path) -> list[tuple[str, bool]]:
    """One big thing, then quieter ones — and never a broken container.

    The pairs block is opened and closed inside a loop with a flag,
    because this template engine has no macros. A flag that is set and
    never cleared leaves an unclosed <div>, which browsers paper over and
    nobody notices until a layout goes strange three pages later.
    """
    photo = (ROOT / "content" / "da" / "theodora" / "01.jpg").read_bytes()
    base = d / "content" / "da"
    for name, n in (("une-seule", 1), ("quatre", 4), ("aucune", 0)):
        q = base / name
        q.mkdir()
        (q / "index.md").write_text(FRONT.format(title=f"{name}.jpg", extra=""))
        for i in range(1, n + 1):
            (q / f"{i:02d}.jpg").write_bytes(photo)
    ok, log = build(d)

    def main_of(rel: str) -> str:
        m = re.search(r'<main class="proj".*?</main>', page(d, rel), re.S)
        return m.group(0) if m else ""

    one, four, none = main_of("da/une-seule/index.html"), main_of("da/quatre/index.html"), main_of("da/aucune/index.html")

    def balanced(s: str) -> bool:
        return len(re.findall(r"<div\b", s)) == len(re.findall(r"</div>", s))

    return [
        ("builds", ok),
        ("the first photograph opens the page",
         four.count('class="proj-open"') == 1),
        ("the rest sit in pairs", four.count('class="proj-pairs"') == 1
                                  and four.count('class="proj-fig"') == 3),
        ("one photograph gets an opener and no empty pairs block",
         one.count('class="proj-open"') == 1 and 'proj-pairs' not in one),
        ("the pairs container is closed on every shape of project",
         all(balanced(s) for s in (one, four, none))),
        ("a project with no photographs still renders its text",
         "Un texte." in none),
        ("the opener is the one image fetched eagerly",
         four.count('fetchpriority="high"') == 1),
        ("the paired images ask for half the page, not all of it",
         'sizes="(max-width: 52rem) 100vw, 44vw"' in four),
        ("every photograph still carries its real proportions",
         len(re.findall(r'<img[^>]*width="\d+" height="\d+"', four)) == 4),
    ]


def case_icon_is_the_work(d: pathlib.Path) -> list[tuple[str, bool]]:
    """A project wears its own first photograph.

    The prototype has no generic icons anywhere — every one is the work.
    Nothing should have to be drawn or named for that to be true, so the
    first picture in the folder is the icon unless she says otherwise.
    """
    photo = (ROOT / "content" / "da" / "theodora" / "01.jpg").read_bytes()
    base = d / "content" / "da"
    for name, files in (
        ("par-defaut", ("01.jpg", "02.jpg")),
        ("choisie", ("icon.png", "01.jpg")),
        ("sans-image", ()),
    ):
        q = base / name
        q.mkdir()
        (q / "index.md").write_text(FRONT.format(title=f"{name}.jpg", extra=""))
        for f in files:
            (q / f).write_bytes(photo)
    ok, log = build(d)
    h = page(d, "da/index.html")

    def img_of(slug: str) -> str:
        m = re.search(r'<a class="icon[^"]*"[^>]*data-vt="' + re.escape(slug)
                      + r'"[^>]*>\s*(<img[^>]*>)', h, re.S)
        return m.group(1) if m else ""

    first, chosen, bare = img_of("da-par-defaut"), img_of("da-choisie"), img_of("da-sans-image")
    return [
        ("builds", ok),
        ("the first photograph becomes the icon",
         "is-photo" in first and "/icons/" not in first),
        ("it carries the real proportions, so nothing reflows",
         bool(re.search(r'width="\d+" height="\d+"', first))
         and 'width="160" height="160"' not in first),
        ("an icon.* in the folder wins over it", "icon" in chosen and "is-photo" not in chosen),
        ("that icon is not also shown among the project's photographs",
         "icon.png" not in page(d, "da/choisie/index.html")),
        ("a project with no images falls back to a drawn icon",
         "/icons/" in bare and "is-photo" not in bare),
        ("a folder still looks like a folder",
         "/icons/folder" in img_of("da-maison-cosette")),
    ]


def case_a_film_can_ask_for_its_page(d: pathlib.Path) -> list[tuple[str, bool]]:
    """`opens = "page"` means the same thing on every kind of project.

    It used to be tested below the video check, so it was the one
    override that silently did nothing on the one kind of project most
    likely to want a page — a film with a lot to say about it. And the
    page it would have reached did not show the film at all, which is
    also what a visitor with no JavaScript has always been given.
    """
    photo = (ROOT / "content" / "da" / "theodora" / "01.jpg").read_bytes()
    base = d / "content" / "da"
    for name, extra in (("film-page", 'opens = "page"\n'), ("film-normal", "")):
        q = base / name
        q.mkdir()
        (q / "index.md").write_text(
            FRONT.format(title=f"{name}.mov", extra=("[extra]\n" + extra) if extra else ""))
        (q / "01.jpg").write_bytes(photo)
        (q / "poster.jpg").write_bytes(photo)
        (q / "clip.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
    ok, log = build(d)
    desk = page(d, "da/index.html")
    opened = dict()
    for m in re.finditer(r'<a class="icon[^"]*"([^>]*)>', desk):
        vt = re.search(r'data-vt="([^"]+)"', m.group(1))
        w = re.search(r'data-window="([^"]+)"', m.group(1))
        if vt:
            opened[vt.group(1)] = w.group(1) if w else "page"
    page_html = page(d, "da/film-page/index.html")
    normal_html = page(d, "da/film-normal/index.html")
    main = re.search(r'<main class="proj".*?</main>', page_html, re.S)
    return [
        ("builds", ok),
        ('opens = "page" sends a film to its page', opened.get("da-film-page") == "page"),
        ("a film without it still opens as a film",
         opened.get("da-film-normal", "").startswith("film-")),
        ("no film window is built for the one nobody will open",
         'id="film-da-film-page"' not in desk),
        ("and one still is for the other", 'id="film-da-film-normal"' in desk),
        ("the page it reaches actually shows the film",
         bool(main) and "<video" in main.group(0)),
        ("the film's own still is its poster, not a photograph underneath it",
         bool(main) and "poster=" in main.group(0)
         and main.group(0).count("proj-fig") == 1),
        ("a film page works without JavaScript too — the video is in the page",
         "<video" in normal_html),
        ("nothing dangles", dangling(desk) == []),
    ]


def case_film_in_a_folder(d: pathlib.Path) -> list[tuple[str, bool]]:
    """A video inside a folder, opened from the window rather than a desk.

    The dialog lives on whichever page shows the icon. An icon in the
    `maison cosette` window on the DA desk needs its film on the DA desk,
    or the click does nothing.
    """
    q = d / "content" / "da" / "maison-cosette" / "un-film"
    q.mkdir()
    (q / "index.md").write_text(FRONT.format(title="un film.mov", extra=""))
    (q / "clip.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
    ok, log = build(d)
    h = page(d, "da/index.html")
    win = re.search(
        r'<dialog class="win win-folder" id="folder-da-maison-cosette">.*?</dialog>',
        h, re.S)
    return [
        ("builds", ok),
        ("the maison cosette window is on the DA desk", bool(win)),
        ("the film inside it points at a film window",
         bool(win) and 'data-window="film-da-maison-cosette-un-film"' in win.group(0)),
        ("and that film window is on the DA desk too",
         'id="film-da-maison-cosette-un-film"' in h),
        ("no page has a dangling window reference",
         all(dangling(f.read_text(encoding="utf-8")) == []
             for f in (d / "public").rglob("*.html"))),
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
    ("the panel sees what the site renders", case_the_panel_sees_what_the_site_renders),
    ("the wallpaper lives in the folder", case_wallpaper_lives_in_the_folder),
    ("a bureau that declares a wallpaper", case_declared_wallpaper),
    ("alt text written in front matter", case_alt_text),
    ("a bureau on the home desk goes to its own page", case_top_level_navigates),
    ("a folder inside a bureau opens as a window", case_second_level_window),
    ("a folder three levels down", case_three_deep),
    ("what a file does when you click it", case_what_a_file_does),
    ("prune keeps what the site asks for", case_prune_keeps_what_the_site_asks_for),
    ("every page can say what it is", case_every_page_can_say_what_it_is),
    ("about me opens as a screen", case_about_is_a_screen),
    ("every photograph in the gallery opens", case_gallery_photographs_open),
    ("the project page has a rhythm", case_the_project_page_has_a_rhythm),
    ("a project wears its own first photograph", case_icon_is_the_work),
    ("a film can ask for its page", case_a_film_can_ask_for_its_page),
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
