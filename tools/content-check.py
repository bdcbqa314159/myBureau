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

sys.path.insert(0, str(ROOT / "tools"))
import filetypes  # noqa: E402
import gif  # noqa: E402
COPY = ["content", "templates", "static", "tools", "config.toml", "sass"]

FRONT = '+++\ntitle = "{title}"\n{extra}+++\n\nUn texte.\n'

# The smallest thing a browser will accept as a PDF. The build only copies
# it, but a file that is not a PDF would make the cases that use it prove
# nothing about the one thing they are for.
# The smallest thing that is recognisably a GIF, written here rather
# than drawn, so the bytes are ours and identical on every machine. It
# carries the NETSCAPE2.0 block, which is what makes a GIF loop — the
# point of the whole convention.
TINY_GIF = (b"GIF89a" + bytes([2, 0, 2, 0, 0x80, 0, 0])
            + b"\xff\xff\xff\x00\x00\x00"
            + b"\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00"
            + b"\x3b")

TINY_PDF = (b"%PDF-1.4\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]>>endobj\n"
            b"trailer<</Root 1 0 R>>\n%%EOF\n")


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
    shutil.copyfile(ROOT / "content/da/theodora-01/01.jpg", p / "GRANDE.JPG")
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
            # about me.txt is a window declared in [extra.items], so it
            # has no path of its own and carries the home desk's. Zola
            # slugifies the NAME she typed there. If that name is ever
            # changed and the panel is not, this is where it shows up: the
            # row would point at an icon the desk does not render.
            slug = ("about-me-txt" if it["kind"] == "about"
                    else it["path"][len("content/"):].replace("/", "-"))
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

    # NO FOLDER OPENS A WINDOW. A second-class folder used to open a
    # little window listing its contents; it goes to its own page now,
    # which is what the brief asked for. Two ways that could come back —
    # a data-window left on a folder icon, or a folder navigating to a
    # page nobody built — and the second is silent in a browser.
    windowed, pageless = [], []
    by_path = {k["path"]: k for k in tree["desks"]}
    for desk in tree["desks"]:
        rel = desk["path"][len("content"):].strip("/")
        html = page(d, (rel + "/index.html") if rel else "index.html")
        if not html:
            continue
        for child in desk["on"]:
            # about me.txt is a window and carries the home desk's own
            # path, so by_path would find it and call it a folder.
            if child["kind"] != "folder":
                continue
            here = child["path"][len("content/"):]
            if 'data-window="folder-{}"'.format(here.replace("/", "-")) in html:
                windowed.append(child["path"])
            if not page(d, here + "/index.html"):
                pageless.append(child["path"])

    return [
        ("builds", ok),
        ("the panel reads every desk the site has",
         len(tree["desks"]) == len(list((d / "content").rglob("_index.md")))),
        ("no folder on any desk opens a window", windowed == []),
        ("and every folder navigates to a page that was really built",
         pageless == []),
        ("everything it would draw is really on that desk", missing == []),
        ("about me.txt is one of the things it draws, and the desk has it",
         any(c["kind"] == "about" for c in by_path["content"]["on"])
         and "about-me-txt" not in missing),
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
    photo = (ROOT / "content" / "da" / "theodora-01" / "01.jpg").read_bytes()
    other = (ROOT / "content" / "da" / "wallpaper.jpg").read_bytes()
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
    # A FOLDER THAT OPENS A PAGE, with a wallpaper still beside it —
    # which is the state every converted desk is in. Without a rule the
    # wallpaper is rendered as her first photograph, full width, at the
    # top of the page. The real content cannot test this: its dead
    # wallpapers were deleted, so the check would pass by having
    # nothing to find.
    w = d / "content" / "affiche"
    w.mkdir()
    (w / "_index.md").write_text(FRONT.format(
        title="affiche", extra='template = "page.html"\n'), encoding="utf-8")
    (w / "wallpaper.jpg").write_bytes(other)
    (w / "01.jpg").write_bytes(photo)
    # A folder inside it holding NOTHING BUT a wallpaper, which is the
    # only arrangement where the listing rule bites: `01.jpg` sorts
    # before `wallpaper.jpg`, so wherever a real photograph exists it
    # wins on order alone and the rule is never consulted. A converted
    # desk with no photographs of its own is exactly this folder.
    wd = w / "dedans"
    wd.mkdir()
    (wd / "_index.md").write_text(FRONT.format(
        title="dedans", extra='template = "page.html"\n'), encoding="utf-8")
    (wd / "wallpaper.jpg").write_bytes(other)

    # and one with nothing at all, anywhere above it
    n = d / "content" / "nue"
    n.mkdir()
    (n / "_index.md").write_text(FRONT.format(
        title="nue", extra='template = "section.html"\n'))
    ok, log = build(d)

    wall_route = re.search(r'<div class="proj-route".*?</div>',
                           page(d, "affiche/index.html"), re.S)

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
        # THE THREE BEHAVIOURS, named here because they drifted once:
        # the brief puts DA and graphic design together — "Page DA :
        # même concept que la page graphic design" — and both are
        # desks. travail sélectionné is the page with the route on it,
        # and pellicules is the gallery. Each is a different thing and
        # none of them is the default.
        ("DA is a desk and keeps its own wallpaper",
         wall("da/index.html").startswith("wallpaper.")),
        ("graphic design is a desk too, as the brief pairs it with DA",
         wall("graphic-design/index.html").startswith("wallpaper.")
         and '<main class="desk"' in page(d, "graphic-design/index.html")),
        ("travail sélectionné is the PAGE, so it has no wallpaper",
         wall("travail-selectionne/index.html") == "none"
         and 'class="proj-route"' in page(d, "travail-selectionne/index.html")),
        ("and the route belongs to it alone, not to a desk",
         'class="proj-route"' not in page(d, "graphic-design/index.html")),
        ("and neither does a folder on a desk — it is a page too",
         wall("da/maison-cosette/index.html") == "none"),
        ("a wallpaper left beside a page is not rendered as one of her"
         " photographs, which is what it would be without the rule",
         page(d, "affiche/index.html").count("<figure") == 1),
        # A folder holding nothing but a wallpaper now contributes
        # NOTHING to a route. It used to arrive as a named placeholder
        # so it stayed reachable; the route carries no links at all
        # since she asked for a place to look rather than to navigate,
        # so there is nothing for a nameless folder to be.
        # The route must EXIST for this to say anything — `affiche` has
        # a child, so it does — and then hold no stop of any kind. Not
        # `class="stop"` with its closing quote: a stop may carry a
        # second class, and the first spelling of this check passed
        # happily against `class="stop is-bare"`.
        ("nor does it put anything on the route wearing a wallpaper",
         bool(wall_route) and 'class="stop' not in wall_route.group(0)),
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
    shutil.copyfile(ROOT / "content/da/theodora-01/01.jpg", p / "01.jpg")
    shutil.copyfile(ROOT / "content/da/theodora-02/01.jpg", p / "02.jpg")
    ok, log = build(d)
    h = page(d, "da/decrit/index.html")
    return [
        ("builds", ok),
        ("the described photograph carries its description",
         'alt="Une plage au crepuscule."' in h),
        ("the one with no description stays alt=\"\" rather than inventing one",
         h.count('alt=""') >= 1),
    ]


def _uncommented(src: str) -> str:
    """Python source with its `#` comments removed.

    A comment explaining that a list USED to be `("icon", "poster")` is
    not a list. Without this the check caught its own explanation.
    """
    return "\n".join(re.sub(r"#.*$", "", line) for line in src.splitlines())


def dangling(h: str) -> list[str]:
    """Every data-window on a page that has no dialog to open.

    The icon renders, the build is clean, and the click does nothing at
    all — which is why this is asserted on every page of every case
    rather than once. It is also what now proves folder windows are
    gone: nothing may point at one.
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


def case_second_level_page(d: pathlib.Path) -> list[tuple[str, bool]]:
    """A folder INSIDE a bureau opens its own page, not a window.

    It used to open a little window listing its contents, on top of the
    bureau's wallpaper. Neither was asked for: "les dossiers ou certains
    elements ouvriront une nouvelle page qui presentera le projet de
    maniere tres simple". So a folder at that depth is a piece of work,
    and it gets the project page — title, description, photographs.
    """
    p = d / "content" / "graphic-design" / "sous-dossier"
    p.mkdir()
    (p / "_index.md").write_text(
        FRONT.format(title="sous dossier", extra='template = "page.html"\n')
        + "Une description, deux lignes.\n", encoding="utf-8")
    shutil.copyfile(ROOT / "content/da/theodora-01/01.jpg", p / "01.jpg")
    shutil.copyfile(ROOT / "content/da/theodora-02/01.jpg", p / "02.jpg")
    ok, log = build(d)
    desk = page(d, "graphic-design/index.html")
    own = page(d, "graphic-design/sous-dossier/index.html")
    return [
        ("builds", ok),
        ("no window is built for it on the bureau's desk",
         "win-folder" not in desk),
        ("and its icon does not try to open one",
         'data-window="folder-graphic-design-sous-dossier"' not in desk),
        ("the icon is a plain link to its page, so it works without JavaScript",
         bool(re.search(r'href="[^"]*graphic-design/sous-dossier/"', desk))),
        ("that page is the project page, not another desk",
         'class="project"' in own and '<main class="desk"' not in own),
        ("it carries no wallpaper", "--wallpaper" not in own),
        ("its description is on it", "Une description, deux lignes." in own),
        ("and its photographs are, every one of them at full width",
         own.count("proj-open") == 2 and "proj-pairs" not in own),
        ("no dangling window reference", dangling(desk) == []),
    ]


def case_three_deep(d: pathlib.Path) -> list[tuple[str, bool]]:
    """Depth has no floor any more, because nothing opens a window.

    There is no recursion in this template engine, which is why the old
    rule needed one: a window per desk, and the level below it had to
    navigate or be an icon wired to a dialog nobody built. Every folder
    under the home desk goes to its own page now, so the floor is gone —
    and what still has to hold is that no page at any depth points at a
    window that is not there.
    """
    p = d / "content" / "un"
    p.mkdir()
    (p / "_index.md").write_text(FRONT.format(
        title="un", extra='template = "section.html"\n'), encoding="utf-8")
    q = p / "deux"
    q.mkdir()
    (q / "_index.md").write_text(FRONT.format(
        title="deux", extra='template = "page.html"\n'), encoding="utf-8")
    r = q / "trois"
    r.mkdir()
    (r / "_index.md").write_text(FRONT.format(
        title="trois", extra='template = "page.html"\n'), encoding="utf-8")
    s = r / "projet"
    s.mkdir()
    (s / "index.md").write_text(FRONT.format(title="projet.pdf", extra=""),
                                encoding="utf-8")
    ok, log = build(d)
    un = page(d, "un/index.html")
    every = list((d / "public").rglob("*.html"))
    return [
        ("builds", ok),
        ("a folder on a bureau's desk opens a page, not a window",
         "win-folder" not in un and 'data-window="folder-un-deux"' not in un),
        ("and it is a plain link to that page", "un/deux/" in un),
        ("the folder below it is a page too, at whatever depth",
         'class="project"' in page(d, "un/deux/trois/index.html")),
        ("the project at the bottom still has its own page",
         "projet.pdf" in page(d, "un/deux/trois/projet/index.html")),
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
                else (ROOT / "content" / "da" / "theodora-01" / "01.jpg").read_bytes())
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
    # A DOSSIER, because the url that frames one carries a fragment
    # (#toolbar=0&navpanes=0) and that is what broke this: prune matched
    # the url against the file on disk with the fragment still attached,
    # found nothing, and deleted a PDF the page frames. The check below
    # had its own copy of the same matching, with the same blind spot, so
    # it agreed.
    doc = d / "content" / "da" / "dossier"
    doc.mkdir()
    (doc / "index.md").write_text(FRONT.format(title="le dossier.pdf", extra=""))
    (doc / "dossier.pdf").write_bytes(TINY_PDF)

    ok, log = build(d)
    pub = d / "public"
    before = {p for p in pub.rglob("*") if p.is_file()}
    html_before = {p: p.read_bytes() for p in pub.rglob("*.html")}

    r = subprocess.run([sys.executable, "tools/prune.py"], cwd=d,
                       capture_output=True, text=True)
    after = {p for p in pub.rglob("*") if p.is_file()}

    MEDIA = filetypes.MEDIA
    on_disk = {str(p.relative_to(pub)) for p in after}
    broken = []
    for p in list(pub.rglob("*.html")) + list(pub.rglob("*.css")):
        txt = p.read_text(encoding="utf-8", errors="replace")
        urls = set(re.findall(r'(?:src|href)="([^"]+)"', txt))
        urls |= {m.group(1) for m in re.finditer(r'url\(\s*[\'"]?([^)\'"]+)', txt)}
        for m in re.finditer(r'srcset="([^"]+)"', txt):
            urls |= {b.strip().split(" ")[0] for b in m.group(1).split(",") if b.strip()}
        for u in urls:
            # fragment AND query — a url names a file, neither of them do
            tail = u.split("#")[0].split("?")[0]
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
        ("a framed document survived, fragment in its url and all",
         survived("dossier/dossier.pdf")),
    ]


def case_every_page_can_say_what_it_is(d: pathlib.Path) -> list[tuple[str, bool]]:
    """Headings and link names — the two things a screen reader needs.

    Both were missing and neither showed: the site had no <h1> anywhere,
    and every photograph in the gallery was a link called nothing. Nothing
    looks wrong either way, which is exactly why it stayed broken.
    """
    photo = (ROOT / "content" / "da" / "theodora-01" / "01.jpg").read_bytes()
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
         bool(re.search(r'<h1[^>]*>theodora 01\.jpeg</h1>', page(d, "da/theodora-01/index.html")))),
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
    shutil.copyfile(ROOT / "content/da/theodora-01/01.jpg",
                    d / "content" / "about.jpg")
    ok, log = build(d)
    h = page(d, "index.html")
    win = re.search(r'<dialog class="win win-about" id="about">.*?</dialog>', h, re.S)
    en = re.search(r'<dialog class="win win-about" id="about">.*?</dialog>',
                   page(d, "en/index.html"), re.S)

    # Captured BEFORE the photograph is taken away below — a page()
    # call inside an expectation reads the tree as it is at return
    # time, which is the bare state, not this one.
    en_home = page(d, "en/index.html")

    # AND THE STATE BEFORE SHE HAS GIVEN ONE. Take the photograph away
    # and build again: the desk falls back to the drawn icon, and the
    # window — which never held it — is unchanged.
    (d / "content" / "about.jpg").unlink()
    build(d)
    bare = page(d, "index.html")
    m = re.search(r'<a class="icon"[^>]*data-vt="about-me-txt"[^>]*>.*?'
                  r'<img[^>]*src="([^"]+)"', bare, re.S)
    gone_icon = m.group(1) if m else ""
    gone_win = re.search(r'<dialog class="win win-about" id="about">.*?</dialog>',
                         bare, re.S)
    gone_sheet = bool(gone_win) and "about-sheet" in gone_win.group(0)

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
        # REVERSED, DELIBERATELY. This used to assert the portrait was
        # IN the window and emphatically NOT on the desk. It is the
        # other way round now: `about me.txt` is a .txt, so the window
        # is her words and the four buttons, and the photograph is what
        # the desk wears. The old expectations are rewritten rather than
        # deleted, so the reversal is visible to whoever reads this next.
        ("the window shows no picture", bool(win) and "<img" not in win.group(0)),
        ("it is her words and the buttons",
         bool(win) and "about-sheet" in win.group(0)
                   and "sheet-tools" in win.group(0)),
        ("the desk wears her photograph",
         bool(re.search(r'<a class="icon"[^>]*data-vt="about-me-txt"[^>]*>'
                        r'.*?<img[^>]*src="[^"]*about\.', h, re.S))),
        ("the English desk wears it too",
         bool(re.search(r'<a class="icon"[^>]*data-vt="about-me-txt"[^>]*>'
                        r'.*?<img[^>]*src="[^"]*about\.',
                        en_home, re.S))),
        ("and does not reach for it under /en/, where it is not",
         "/en/about." not in en_home),
    ]


def case_a_film_wears_its_own_frame(d: pathlib.Path) -> list[tuple[str, bool]]:
    """A film with an affiche and nothing else wears the affiche.

    "How come the preview of a video is not the original image of the
    video?" The panel writes `poster.*` from the film's first frame now,
    and this is the half that has to be true for that to be worth
    anything: the engine has to USE it — as the desk icon, as the
    window's poster, and on the page — for a project that has no
    photographs at all.

    The rule it leans on is in _icon.html: a project is its own first
    picture. `poster` is not one of the project's photographs (it is
    SPOKEN_FOR, so it never appears among them) but it IS a picture in
    the folder, and that is what makes this work.
    """
    bureau = d / "content" / "da"
    film = bureau / "clip-sans-photo"
    film.mkdir()
    (film / "index.md").write_text(FRONT.format(title="un film.mov", extra=""))
    (film / "index.en.md").write_text(FRONT.format(title="a film.mov", extra=""))
    shutil.copyfile(ROOT / "kit/films/clip-3s.mp4", film / "film.mp4")
    shutil.copyfile(ROOT / "kit/films/affiche-1600x900.jpg", film / "poster.jpg")

    ok, log = build(d)
    desk = page(d, "da/index.html")
    icons = re.findall(r'<a class="icon".*?</a>', desk, re.S)
    mine = next((i for i in icons if 'data-vt="da-clip-sans-photo"' in i), "")
    win = re.search(r'<dialog class="win win-film" id="film-da-clip-sans-photo">.*?</dialog>',
                    desk, re.S)
    inner = page(d, "da/clip-sans-photo/index.html")
    return [
        ("builds", ok),
        ("the film has an icon on the desk", bool(mine)),
        ("and it is the affiche, not a drawn film strip",
         "processed_images" in mine and "movie.svg" not in mine),
        ("clicking it opens the film window", 'data-window="film-da-clip-sans-photo"' in mine),
        ("the window exists to be opened", bool(win)),
        ("and shows the frame before anything is played",
         bool(win) and "poster=" in win.group(0)),
        ("the page shows it too",
         "poster=" in inner and "<video" in inner),
        ("and the affiche is not ALSO one of the project's photographs",
         len(re.findall(r'<figure class="proj-fig"', inner)) == 0),
    ]


def case_a_document_is_shown(d: pathlib.Path) -> list[tuple[str, bool]]:
    """A PDF is SHOWN, in its own page, and never offered as a download.

    The engine could not display one at all: a .pdf in a project folder
    was copied to the build and referenced by nothing. The panel offered
    to make "un document", which produced a project named X.pdf and then
    asked for photographs.

    Two of them here, because the hard one is the brochure that also has
    a cover: the cover must be the ICON and the dossier must be what the
    click opens. Previewing the cover and never showing the document is
    exactly the medley this is meant to end.
    """
    bureau = d / "content" / "da"
    plain = bureau / "dossier-nu"
    plain.mkdir()
    (plain / "index.md").write_text(FRONT.format(title="le dossier.pdf", extra=""))
    (plain / "dossier.pdf").write_bytes(TINY_PDF)

    cover = bureau / "dossier-couverture"
    cover.mkdir()
    (cover / "index.md").write_text(FRONT.format(title="grocery.pdf", extra=""))
    (cover / "grocery.pdf").write_bytes(TINY_PDF)
    shutil.copyfile(ROOT / "content/da/theodora-01/01.jpg", cover / "01.jpg")

    ok, log = build(d)
    desk = page(d, "da/index.html")
    nu = page(d, "da/dossier-nu/index.html")
    cv = page(d, "da/dossier-couverture/index.html")
    icons = re.findall(r'<a class="icon".*?</a>', desk, re.S)
    icon_of = lambda slug: next(
        (i for i in icons if 'data-vt="{}"'.format(slug) in i), "")

    # Nothing anywhere may LINK to the file — that is the download.
    links = re.findall(r'<a [^>]*href="[^"]*\.pdf[^"]*"', desk + nu + cv)

    return [
        ("builds", ok),
        ("the file reaches the build at all",
         (d / "public" / "da" / "dossier-nu" / "dossier.pdf").is_file()),
        ("the page shows it in a frame",
         bool(re.search(r'<iframe[^>]*src="[^"]*dossier\.pdf', nu))),
        ("not through <object> or <embed>, which the CSP refuses",
         "<object" not in nu and "<embed" not in nu),
        ("and the CSP still refuses them, so that stays true",
         "object-src 'none'" in nu),
        ("nothing links to the file, so nothing offers to download it",
         links == []),
        ("nor asks for one with a download attribute",
         "download" not in re.sub(r'<img[^>]*>', '', nu)),
        ("its icon goes to its page rather than opening a window",
         bool(icon_of("da-dossier-nu"))
         and "data-window" not in icon_of("da-dossier-nu")),
        ("and no dialog was rendered for it either",
         'id="preview-da-dossier-nu"' not in desk),
        # the brochure WITH a cover — the one that used to go wrong
        ("a dossier with a cover still goes to its page",
         bool(icon_of("da-dossier-couverture"))
         and "data-window" not in icon_of("da-dossier-couverture")),
        ("and no preview dialog is left behind for it",
         'id="preview-da-dossier-couverture"' not in desk),
        ("but the cover is what the icon looks like",
         "processed_images" in icon_of("da-dossier-couverture")),
        ("its page shows the document",
         bool(re.search(r'<iframe[^>]*src="[^"]*grocery\.pdf', cv))),
        # The cover used to be below the document BECAUSE it fell into
        # the pairs block. There is no pairs block now, so the order is
        # what the template writes: document first, photographs after.
        ("and the cover below it, not competing with it",
         'class="proj-open"' in cv
         and cv.index("grocery.pdf") < cv.index('class="proj-open"')),
    ]


def case_gallery_photographs_open(d: pathlib.Path) -> list[tuple[str, bool]]:
    """Every photograph in the gallery opens, and opens its OWN window.

    Two windows sharing an id, or a link pointing at one that was never
    rendered, both build perfectly and both end in a click that does
    nothing — and in a gallery that is every photograph after the first.
    """
    photo = (ROOT / "content" / "da" / "theodora-01" / "01.jpg").read_bytes()
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


def case_the_project_page_is_a_column(d: pathlib.Path) -> list[tuple[str, bool]]:
    """Every page on a desk is the same page.

    THIS CASE IS REVERSED. It asserted the prototype's rhythm — one
    photograph full width, then pairs with cream around them — against
    a subfolder's plain column, and the difference was invisible from
    the desk: `grocery list` and `maison cosette` are two icons side by
    side that gave two different pages.

    2026-11-13, from the client via Bernardo: everything on DA and
    graphic design is one class, and anything that goes to a page goes
    to THAT page. A photo still opens in place and a video still plays
    in its window — what changed is only what a page looks like.

    The pairs container is gone with the rhythm, and the flag that
    opened and closed it inside the loop with it. That flag was the
    reason for half this case: there are no macros in this engine, so
    an unclosed <div> was one missed branch away. The balance check
    stays anyway — it costs nothing and the template still has
    containers.
    """
    photo = (ROOT / "content" / "da" / "theodora-01" / "01.jpg").read_bytes()
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
        ("every photograph takes the whole width",
         four.count('class="proj-open"') == 4),
        ("and none of them is half a page",
         "proj-pairs" not in four and "proj-fig" not in four),
        ("a project of one photograph is the same page as a project of four",
         one.count('class="proj-open"') == 1 and "proj-pairs" not in one),
        ("every container the template opens is closed",
         all(balanced(s) for s in (one, four, none))),
        ("a project with no photographs still renders its text",
         "Un texte." in none),
        # STILL ONE EAGER IMAGE. Nine photographs all marked urgent is
        # the same as none marked urgent, and that is how the subfolder
        # page became the heaviest on the site. The rhythm went; the
        # rule that only the top one is urgent did not.
        ("only the first image is fetched eagerly, however many there are",
         four.count('fetchpriority="high"') == 1
         and four.count('loading="lazy"') == 3),
        ("and every one of them asks for the full width",
         four.count('sizes="100vw"') == 4),
        ("every photograph still carries its real proportions",
         len(re.findall(r'<img[^>]*width="\d+" height="\d+"', four)) == 4),
    ]


def case_icon_is_the_work(d: pathlib.Path) -> list[tuple[str, bool]]:
    """A project wears its own first photograph.

    The prototype has no generic icons anywhere — every one is the work.
    Nothing should have to be drawn or named for that to be true, so the
    first picture in the folder is the icon unless she says otherwise.
    """
    photo = (ROOT / "content" / "da" / "theodora-01" / "01.jpg").read_bytes()
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
        ("an icon.* in the folder wins over it", "icon" in chosen),
        # REVERSED, DELIBERATELY. This asserted that a dropped icon is
        # NOT a photograph — it was treated as one of our drawn
        # symbols, so it got none of a photograph's treatment and was
        # rendered at a square 160×160 whatever shape it really was.
        # A file SHE dropped is her work. Only a drawn `.svg` is a
        # symbol now.
        ("and it is her work, so it is treated as a photograph",
         "is-photo" in chosen),
        ("measured rather than assumed to be square",
         'width="160" height="160"' not in chosen),
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
    photo = (ROOT / "content" / "da" / "theodora-01" / "01.jpg").read_bytes()
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
        # One photograph under the film, and it is 01.jpg: `poster.jpg`
        # is the film's still, so rendering it again below would be the
        # same frame twice. It was counted as a PAIRED figure until the
        # page became one column; the count is what matters, not which
        # container it landed in.
        ("the film's own still is its poster, not a photograph underneath it",
         bool(main) and "poster=" in main.group(0)
         and main.group(0).count('class="proj-open"') == 1),
        ("a film page works without JavaScript too — the video is in the page",
         "<video" in normal_html),
        ("nothing dangles", dangling(desk) == []),
    ]


def case_only_the_opener_is_urgent(d: pathlib.Path) -> list[tuple[str, bool]]:
    """One photograph is fetched first. The rest wait their turn.

    The opener branch carries `loading="eager" fetchpriority="high"`
    because it was written for ONE picture: the first on the page,
    worth having before anything else. When a subfolder page became one
    column, every photograph started taking that branch — nine of them
    arrived marked `high`, which tells a browser nothing is urgent
    because everything is. That page was 544 KB on arrival, the
    heaviest on the site, on the device this work is about.
    """
    folder = d / "content" / "da" / "une-serie"
    folder.mkdir()
    (folder / "_index.md").write_text(FRONT.format(
        title="une série", extra='template = "page.html"\n'), encoding="utf-8")
    for n in ("01.jpg", "02.jpg", "03.jpg", "04.jpg"):
        shutil.copyfile(ROOT / "content/da/theodora-01/01.jpg", folder / n)
    ok, log = build(d)
    html = page(d, "da/une-serie/index.html")
    # ONLY THE WORK. The dock's social marks are images too, and
    # counting them made "the rest wait" assert a number that had
    # nothing to do with her photographs.
    work = re.search(r'<main class="proj".*?</main>', html, re.S)
    tags = re.findall(r"<img[^>]*>", work.group(0) if work else "")
    eager = [x for x in tags if 'loading="lazy"' not in x]
    return [
        ("builds", ok),
        ("all four photographs are on the page", html.count("proj-open") == 4),
        ("exactly one of them is fetched eagerly", len(eager) == 1),
        ("and only that one is called urgent",
         sum('fetchpriority="high"' in x for x in tags) == 1),
        ("the rest wait", sum('loading="lazy"' in x for x in tags) == 3),
    ]


def case_one_list_of_what_is_not_her_work(d: pathlib.Path) -> list[tuple[str, bool]]:
    """`icon`, `poster`, `wallpaper` are named once, not five times.

    This was written out in five templates with THREE different
    answers: a preview did not skip `wallpaper`, the gallery did not
    skip `poster`. So a folder's wallpaper could appear inside a
    preview of her work, and a film's still inside the gallery.

    `_icon.html` is the one deliberate exception and it is checked for
    separately: it is choosing a FACE rather than listing her work, and
    a film's poster is exactly the right face. Excluding it there would
    send every film back to a drawn symbol.
    """
    conf = (d / "config.toml").read_text(encoding="utf-8")
    tpl = {f.name: f.read_text(encoding="utf-8")
           for f in (d / "templates").glob("*.html")}
    listing = ("page.html", "_place.html", "_preview.html", "gallery.html")
    hardcoded = [n for n, s in tpl.items()
                 if n != "_icon.html"
                 and re.search(r'!=\s*"(poster|wallpaper)"', s)]
    ok, log = build(d)
    desk = page(d, "da/index.html")
    return [
        ("builds", ok),
        ("the list exists where the other file types already live",
         "not_photographs" in conf),
        ("every template that lists her work reads it",
         all("not_photographs" in tpl[n] for n in listing)),
        ("and none of them still names the files by hand", hardcoded == []),
        ("the icon chooser is the exception, and says why",
         "_icon.html" in tpl and "not_photographs" in tpl["_icon.html"]),
        ("so a film still wears its own poster on the desk",
         bool(re.search(r'<a class="icon"[^>]*junes-cry[^>]*>.*?<img', desk, re.S))),
    ]


def case_about_has_a_face(d: pathlib.Path) -> list[tuple[str, bool]]:
    """`about me.txt` shows a portrait, as the prototype does.

    The template looked for `about.*`, the stylesheet styled the
    polaroid, and no such file existed — so a built feature was
    invisible and the window was prose alone.

    It is DRAWN rather than fetched. Every other placeholder here comes
    from a random seed, and the one thing a portrait slot would draw is
    a stranger's face: exactly what the hand-picked seeds in
    placeholders.py exist to keep off a client's demo.
    """
    ok, log = build(d)
    home = page(d, "index.html")
    win = re.search(r'<dialog class="win win-about".*?</dialog>', home, re.S)
    inside = win.group(0) if win else ""
    return [
        ("builds", ok),
        # THE PHOTOGRAPH IS THE ICON, NOT THE WINDOW. `about me.txt` is
        # a .txt and a .txt is words: the window shows her text and the
        # four buttons, and her portrait is what the desk wears.
        ("the window shows no picture at all", "<img" not in inside),
        ("her words are in it", "<p>" in inside),
        ("and the buttons above them", "sheet-tools" in inside),
        ("the desk wears her photograph instead",
         bool(re.search(r'<a class="icon"[^>]*data-vt="about-me-txt"[^>]*>'
                        r'.*?<img[^>]*src="[^"]*about\.', home, re.S))),
    ]


def case_a_photograph_has_no_close_box(d: pathlib.Path) -> list[tuple[str, bool]]:
    """The gallery's photograph lost its cross and is still dismissible.

    Taking a close box off a window is only safe because something else
    closes it. Two things do: Escape, which a modal dialog handles
    itself, and a tap anywhere off the picture, which desk.ts wires for
    every `.win-preview` — and this dialog carries that class.

    So this asserts the pair. A change that removed the cross AND the
    class, or the cross AND the handler, would leave a visitor on a
    phone holding a photograph with no way out and no keyboard to press
    Escape with. That is a trap, not a window.

    The bar and the file's name stay on purpose, to be looked at.
    """
    ok, log = build(d)
    html = page(d, "pellicules/index.html")
    shot = re.search(r'<dialog class="win win-preview win-shot".*?</dialog>',
                     html, re.S)
    inside = shot.group(0) if shot else ""
    desk_js = (ROOT / "src" / "desk.ts").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", " ",
                 (d / "static" / "css" / "site.css").read_text(encoding="utf-8"),
                 flags=re.S)
    rules = {}
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        rules.setdefault(sel.strip(), []).append(body)
    shot_body = rules.get(".win-shot .preview-body", [])

    return [
        ("builds", ok),
        ("the gallery still opens a photograph in a window", bool(shot)),
        ("there is no close box on it",
         inside != "" and "<button" not in inside),
        ("the bar and the file's name are still there",
         "<div class=\"win-bar\">" in inside
         and bool(re.search(r"<span>[^<]+\.\w+</span>", inside))),
        ("it is a preview, which is the class that closes on a tap off it",
         'class="win win-preview win-shot"' in inside),
        ("and that handler really exists, so the class means something",
         '.win-preview' in desk_js and "win.close()" in desk_js),
        # NO BLACK FRAME. Two things drew one: a dark ground behind the
        # picture and `.win-body`'s padding holding it off its own
        # edges. The blue band stays — she asked for it by name.
        ("the picture sits on nothing, not on a dark mount",
         not any(re.search(r"background:\s*#0", b) for b in shot_body)),
        ("and nothing holds it away from its own edges",
         any("padding: 0" in b for b in shot_body)),
        ("the band takes its share and the picture takes the rest",
         any("minmax(0, 1fr)" in b for b in rules.get(".win-shot", []))),
        # CLICKING A PHOTOGRAPH GIVES YOU THE PHOTOGRAPH, NOT A
        # SCROLLBAR. Two earlier attempts bounded it with percentages
        # and both failed the same way: inside a grid whose rows are
        # sized by their content, `max-height: 100%` asks the box how
        # tall it is and the box answers "as tall as the picture". The
        # picture kept its size and `overflow-y: auto` turned that into
        # a scrollbar.
        ("the box takes the row it was given rather than its contents",
         any("align-self: stretch" in b for b in shot_body)),
        ("it never scrolls — a picture is not a document",
         any("overflow: hidden" in b for b in shot_body)),
        ("the picture is bounded by the room, in both directions",
         any("max-width: 100%" in b and "max-height: 100%" in b
             for b in rules.get(".win-shot .preview-body img", []))),
        # THE ELEMENT IS THE PICTURE, NOT THE BOX. With `object-fit`
        # and a full-size element the empty space BESIDE the photograph
        # was inside the image — so a click there landed on the
        # photograph and nothing happened, while a click above or below
        # it closed. Two strips that look identical, behaving
        # differently.
        ("and the element is the picture itself, so what is beside it is not",
         any("width: auto" in b and "height: auto" in b
             for b in rules.get(".win-shot .preview-body img", []))),
        ("which means the box has to centre it",
         any("justify-content: center" in b and "align-items: center" in b
             for b in shot_body)),
        ("a click anywhere that is not the picture closes it",
         'closest("img, .win-bar, a, button")' in desk_js),
        ("but the band keeps its clicks — it is the handle and the name",
         '.win-bar' in desk_js),
    ]


def case_a_picture_fits_the_screen(d: pathlib.Path) -> list[tuple[str, bool]]:
    """An opened photograph is bounded by the screen, not by itself.

    On a phone a picture opened from a desk ran off the side. The cause
    was two rules agreeing with each other and both being wrong:

      the dialog was a grid with an AUTO track, which grows to its
      content — and the content is a photograph 1800 pixels wide, so
      the track blew out past the screen

      the body inside it was `width: max-content`, so it sized to the
      picture too

    Every percentage inside then resolved against 1800 rather than
    against the phone. The height was bounded in viewport units and was
    fine; the width was bounded against a box the picture had sized
    itself, which is no bound at all.

    So the picture is measured against the VIEWPORT in both directions.
    A rule that measures one axis against the screen and the other
    against its own parent will fit on the machine it was written on
    and nowhere else.
    """
    css = (d / "static" / "css" / "site.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)
    rules = {}
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        rules.setdefault(sel.strip(), []).append(body)

    img = " ".join(rules.get(".preview-body img", []))
    body = " ".join(rules.get(".preview-body", []))
    dialog = " ".join(rules.get(".win-preview[open]", []))

    return [
        # MEASURED BY THE BOX, NOT GUESSED FROM THE VIEWPORT. The
        # viewport units were right when nothing else could be trusted
        # to have a size. The box is stretched to the dialog now, so it
        # has one — and `100%` of the room the picture actually has is
        # more honest than `100dvh` minus a padding this rule has to
        # remember.
        ("the picture is bounded by the room it has, both ways",
         "max-width: 100%" in img and "max-height: 100%" in img),
        ("and the box has a size of its own to be that percentage of",
         any("align-self: stretch" in b for b in rules.get(".preview-body", []))),
        ("it never scrolls — one click should show the whole picture",
         any("overflow: hidden" in b for b in rules.get(".preview-body", []))),
        ("nothing sizes the box to the picture it holds",
         "max-content" not in body),
        ("and the track it sits in cannot grow past the screen",
         "minmax(0" in dialog),
        ("the picture is still free to keep its shape",
         "width: auto" in img and "height: auto" in img),
    ]


def case_the_road_survives_a_phone(d: pathlib.Path) -> list[tuple[str, bool]]:
    """A phone compresses her arrangement; it does not delete it.

    The rule here used to set every stop to full width below 52rem,
    which turned a page of varied photographs into one column of
    identical ones — nothing of the composition left on the device most
    people read it on.

    THE OFFSETS AND THE LEAN ARE GONE, by her ask, on every screen: she
    did not want the fridge. What survives is the width, and a phone
    narrows the range of widths rather than erasing it.

    The reasoning was half right: a picture at 24 per cent of a phone
    IS a stamp. The answer to values too extreme is smaller values, not
    none.

    THE NUMBER IS UNITLESS so this is possible at all. A
    percentage cannot be scaled by CSS; a number can. If anyone puts
    the `%` back in the template, the phone silently stops compressing
    — `calc(55 + 52% * 0.6)` is not a length — and the road flattens
    again with nothing to show for it.
    """
    ok, log = build(d)
    css = (d / "static" / "css" / "site.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)
    rules = {}
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        rules.setdefault(sel.strip(), []).append(body)

    stop = " ".join(rules.get(".stop", []))
    rhythm = " ".join(one for sel, bodies in rules.items()
                      if sel.startswith(".stop:nth-child")
                      for one in bodies)
    road = page(d, "travail-selectionne/index.html")
    pins = re.findall(r'<figure class="stop"[^>]*style="([^"]*)"', road)

    return [
        ("builds", ok),
        ("the stop puts the units on itself, so the numbers can be scaled",
         "calc(var(--w" in stop and "* 1%" in stop),
        ("the rhythm is numbers, not percentages",
         rhythm != "" and "%" not in rhythm and "deg" not in rhythm),
        ("a phone narrows the range rather than erasing it",
         any("calc((55 + var(--w" in b for b in rules.get(".stop", []))),
        ("and nothing resets a stop to full width any more",
         "--w: 100%" not in css),
        ("the demo road really is pinned, so the idea can be seen",
         len(pins) >= 5),
        ("and what it writes is unitless, which is what the maths needs",
         pins != [] and all("%" not in s and "deg" not in s for s in pins)),
        # WIDTH ONLY. The offsets and the lean are gone by her ask —
        # the fridge was not what she wanted, here or on a phone — so a
        # pin carries the one number that is left.
        ("and it is a width, not a place or an angle",
         pins != [] and all("--x" not in s and "--r" not in s for s in pins)),
    ]


def case_the_phone_agrees_with_the_desk(d: pathlib.Path) -> list[tuple[str, bool]]:
    """What she arranges on a desk is the order a phone shows.

    A phone has no room for a surface, so the desk becomes a grid. It
    used to be the filesystem's order — folders first, then files,
    alphabetically — which on DA put the thing she placed at the BOTTOM
    first and the thing she placed at the TOP fifth. She arranged a
    desk and the phone ignored her.

    `order` fixes it with nothing new to learn: y first and x second, so
    the grid reads the way the desk reads, down and then across. On a
    wide screen the property does nothing at all, because the icons are
    placed by --x/--y and are not grid items.
    """
    ok, log = build(d)
    desk = page(d, "da/index.html")
    main = re.search(r'<main class="desk".*?</main>', desk, re.S)
    seen = []
    for a in re.findall(r'<a class="icon"[^>]*>', main.group(0) if main else ""):
        vt = re.search(r'data-vt="([^"]+)"', a)
        o = re.search(r"order:(-?[0-9]+)(;| )", a)
        y = re.search(r"--y:([0-9.]+)%", a)
        if vt and o and y:
            seen.append((int(o.group(1)), float(y.group(1)), vt.group(1)))

    by_order = [n for _, _, n in sorted(seen)]
    by_place = [n for _, _, n in sorted(seen, key=lambda r: r[1])]

    return [
        ("builds", ok),
        ("every icon carries an order", len(seen) == 6),
        ("the order is a whole number, which is all CSS accepts",
         all(isinstance(o, int) for o, _, _ in seen)),
        ("reading the phone's order gives her arrangement, top to bottom",
         by_order == by_place),
        ("the thing she put at the top comes first, not fifth",
         by_order and by_order[0] == "da-theodora-01"),
        ("and the folder she put at the bottom is last, not first",
         by_order and by_order[-1] == "da-maison-cosette"),
    ]


def case_a_phone_desk_is_not_a_file_list(d: pathlib.Path) -> list[tuple[str, bool]]:
    """The grid is softened, and the lean never touches a measured box.

    Evenly spaced icons in rows with labels underneath is a file
    manager. A desk is not tidy. The icons are smaller, every other one
    sits lower, and the pictures lean about a degree.

    THE LEAN IS ON THE PICTURE, NEVER THE ICON. arrange() measures each
    icon with getBoundingClientRect to pin it in place, and the measured
    box of a rotated element is its bounding box — bigger than the
    element, and wrong. Rotating the icon itself would put a quiet error
    into every position on a phone.
    """
    css = (d / "static" / "css" / "site.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)
    rules = {}
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        rules.setdefault(sel.strip(), []).append(body)

    # the page assertions below need a built site, not only a stylesheet
    ok, log = build(d)
    leaning = {s: b for s, b in rules.items()
               if ".desk .icon" in s and any("rotate" in x for x in b)}
    on_the_box = [s for s in leaning if not s.rstrip().endswith("img")]
    staggered = [s for s, b in rules.items()
                 if ".desk .icon" in s and any("margin-top" in x for x in b)]
    narrow = [b for b in rules.get(".desk", []) if "grid-template-columns" in b]

    return [
        ("builds", ok),
        ("the pictures lean", leaning != {}),
        ("and the lean is on the picture, never on the box that is measured",
         on_the_box == []),
        ("every other icon sits lower, so they are not in rows",
         staggered != []),
        ("the icons are smaller than a column of the old grid",
         any("minmax(5.2rem" in b for b in narrow)),
        # A PHOTOGRAPH ON A DESK IS THE WORK, NOT A PRINT OF IT. The
        # white ground and the padding around it made every picture
        # wear a little mount.
        ("a photograph on a desk wears no white mount",
         not any("background: #fff" in b or "padding: 3px" in b
                 for b in rules.get(".icon img.is-photo", []))),
        # but it still has to be told apart from the wallpaper, which
        # is itself one of her photographs
        ("and is still separated from the wallpaper under it",
         any("box-shadow" in b for b in rules.get(".icon img.is-photo", []))),
        # EVERY image she drops onto ANY desk, not just the one the
        # rule was written for. A first photograph, a cover she put on
        # a project, her portrait on about me.txt — all her work, all
        # treated the same. Only a drawn `.svg` is one of our symbols.
        ("every photograph on every desk is one of them",
         all(len(re.findall(r'<img class="is-photo"',
                            re.search(r'<main class="desk".*?</main>',
                                      page(d, pg), re.S).group(0))) == n
             for pg, n in (("index.html", 1),
                           ("da/index.html", 5),
                           ("graphic-design/index.html", 3)))),
        ("her portrait among them, at its own shape and not a square",
         bool(re.search(r'data-vt="about-me-txt"[^>]*>\s*<img class="is-photo"'
                        r'[^>]*about\.[^>]*width="(?!160")',
                        page(d, "index.html"), re.S))),
        # and the symbols are still symbols: the home desk has more
        # icons than photographs on it, which is only true while the
        # drawn ones are left alone
        ("a drawn symbol is still a symbol",
         len(re.findall(r'<a class="icon"',
                        re.search(r'<main class="desk".*?</main>',
                                  page(d, "index.html"), re.S).group(0)))
         > len(re.findall(r'<img class="is-photo"',
                          re.search(r'<main class="desk".*?</main>',
                                    page(d, "index.html"), re.S).group(0)))),
    ]


def case_a_phone_desk_can_grow(d: pathlib.Path) -> list[tuple[str, bool]]:
    """With no JavaScript, a phone desk must not hide its own icons.

    The script is what turns the grid into objects you can pick up.
    Without it the grid is all there is — and a grid of fifteen icons
    inside a box pinned to one screen, with no `overflow`, simply ends.
    The icons below the fold are built, laid out, and unreachable, with
    nothing on screen saying so.

    `min-height` is the whole fix: the desk is still one screen when
    one screen is enough, and grows when it is not. The brief asks for
    a page "de la taille d'un écran qui ne s'étend pas" and that still
    holds on a laptop, which is where it was asked for.

    The desk-check covers the half this cannot see — that the script
    pins the grown height before making the icons absolute.
    """
    css = (d / "static" / "css" / "site.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)
    rules = {}
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        rules.setdefault(sel.strip(), []).append(body)

    # the narrow .desk is the one inside the 40rem band; a brace-naive
    # parse reaches it because @media bodies are never innermost
    narrow = [b for b in rules.get(".desk", []) if "grid-template-columns" in b]
    wide = [b for b in rules.get(".desk", []) if "grid-template-columns" not in b]

    def pins_height(bodies: list) -> bool:
        return any(re.search(r"(^|[;\s])height\s*:", b) for b in bodies)

    return [
        ("the narrow desk rule was found at all", narrow != []),
        ("a phone desk may grow past one screen",
         any("min-height" in b for b in narrow)),
        ("and it does not pin a height, which is what hid the icons",
         not pins_height(narrow)),
        ("a wide desk is still exactly one screen, as the brief asks",
         wide != [] and pins_height(wide)),
        ("a phone's first row clears the bandeau by its MEASURED height,"
         " not by a number somebody guessed",
         any("var(--bar-h" in b for b in narrow)),
        ("and there is still an answer for a visitor with no script",
         any(re.search(r"var\(--bar-h,\s*[0-9.]+rem\)", b) for b in narrow)),
        ("the grid adapts across the band rather than always being three",
         any("auto-fill" in b for b in narrow)),
    ]


def case_one_set_of_breakpoints(d: pathlib.Path) -> list[tuple[str, bool]]:
    """Every breakpoint in the stylesheet is one of the four named ones.

    CSS has no variables in a media query, so the numbers are typed out
    wherever they are used — which is how four of them became four
    accidents, none named, each an independent decision. One of them
    sat at 46rem for no reason anybody had written down.

    This does not stop a fifth band. It stops a fifth being added
    WITHOUT SAYING WHAT IT MEANS: the header at the top of site.css is
    the list, and a number missing from it fails here until somebody
    writes the line explaining it.

    Only width and height bands are counted. `prefers-reduced-motion`,
    `prefers-reduced-transparency` and `hover` are not screen sizes and
    are nobody's accident.
    """
    css = (d / "static" / "css" / "site.css").read_text(encoding="utf-8")
    named = {"56rem", "52rem", "40rem"}
    tall = {"30rem"}

    widths = set(re.findall(r"@media\s*\(\s*max-width:\s*([0-9.]+rem)\s*\)", css))
    heights = set(re.findall(r"@media\s*\(\s*max-height:\s*([0-9.]+rem)\s*\)", css))
    # a band is only named if the header actually explains it
    header = css[:css.index("last resort on narrow laptops")] if \
        "last resort on narrow laptops" in css else ""
    explained = {b for b in named | tall if b.replace("rem", "") in header}

    # pixels are the other way to smuggle one in
    pixels = re.findall(r"@media[^{]*\b(?:max|min)-(?:width|height):\s*[0-9.]+px", css)

    return [
        ("every width band is one of the named ones", widths <= named),
        ("and every height band is too", heights <= tall),
        ("each one is explained where they are listed",
         explained == named | tall),
        ("nothing smuggles a band in as pixels", pixels == []),
        ("the stray at 46rem is gone", "46rem" not in widths),
    ]


def case_a_gif_she_made_loops(d: pathlib.Path) -> list[tuple[str, bool]]:
    """tools/gif.py writes a GIF that actually repeats.

    The loop is the whole feature. A GIF written without the
    NETSCAPE2.0 block plays once and stops, which on a desk looks like
    a still that twitched as the page loaded — and converters hand that
    back without mentioning it. kit/wrong/plays-once.gif is that file,
    kept on purpose.

    ffmpeg is what reads the photographs, and it is not on her machine
    by default. Where it is absent this says so and checks nothing,
    rather than passing quietly and reporting a tool that was never
    run.
    """
    if not gif.have_ffmpeg():
        return [("ffmpeg is not on this machine, so the gif maker was"
                 " NOT checked — everything else here was", True)]

    frames = [d / "content/da/theodora-01/01.jpg",
              d / "content/da/theodora-02/01.jpg"]
    out = d / "made.gif"
    gif.make(out, frames, width=120)

    refused_one = refused_missing = False
    try:
        gif.make(d / "nope.gif", [frames[0]], width=120)
    except gif.Refused:
        refused_one = True
    try:
        gif.make(d / "nope.gif", [frames[0], d / "not-here.jpg"], width=120)
    except gif.Refused:
        refused_missing = True

    ok, log = build(d)
    desk = page(d, "graphic-design/index.html")
    m = re.search(r'<a class="icon"[^>]*douze-regards[^>]*>.*?<img[^>]*src="([^"]+)"',
                  desk, re.S)
    src = m.group(1) if m else ""
    return [
        ("it writes a gif at all", out.is_file() and out.stat().st_size > 0),
        ("and that gif carries the block that makes it repeat", gif.loops(out)),
        ("one picture is refused — one picture does not move",
         refused_one),
        ("and so is a frame that is not there, rather than half a gif",
         refused_missing),
        ("the demo wears one, so the desk shows the idea rather than"
         " only supporting it", src.endswith("/icon.gif")),
        ("and the site still builds with it in", ok),
        ("the one kept on the wrong shelf really does not loop",
         not gif.loops(ROOT / "kit" / "wrong" / "plays-once.gif")),
    ]


def case_an_animated_icon_survives(d: pathlib.Path) -> list[tuple[str, bool]]:
    """A GIF dropped in as the icon reaches the desk untouched.

    A dense piece of work — a twenty-page dossier — has nothing to show
    on a desk but a document icon. So she drops `icon.gif` beside it:
    a few of its pages looping, and the click still opens the document.

    This works today only because an icon SHE names is served through
    `get_url`, while the first-photograph fallback goes through
    `resize_image`. The day anyone routes icons through the resizer for
    consistency, every animation on the site becomes a still frame and
    nothing says so — the page builds, the icon appears, and only she
    notices it stopped moving.

    What is asserted is that the file survives: referenced directly and
    copied byte for byte. Whether it ANIMATES is the browser's business
    and no check here can see it.
    """
    p = d / "content" / "graphic-design" / "dossier"
    p.mkdir()
    (p / "index.md").write_text(FRONT.format(title="dossier.pdf", extra=""),
                                encoding="utf-8")
    (p / "brochure.pdf").write_bytes(TINY_PDF)
    (p / "icon.gif").write_bytes(TINY_GIF)
    # a photograph too, which the icon must WIN over — otherwise the
    # resized still would be chosen and this would pass by accident
    shutil.copyfile(ROOT / "content/da/theodora-01/01.jpg", p / "01.jpg")
    ok, log = build(d)
    desk = page(d, "graphic-design/index.html")
    m = re.search(r'<a class="icon"[^>]*dossier[^>]*>.*?<img[^>]*src="([^"]+)"',
                  desk, re.S)
    src = m.group(1) if m else ""
    out = d / "public" / "graphic-design" / "dossier" / "icon.gif"
    return [
        ("builds", ok),
        ("the desk points straight at the gif she dropped in",
         src.endswith("/icon.gif")),
        ("it did NOT go through the resizer, which would flatten it",
         "processed_images" not in src),
        ("and the file arrives byte for byte, loop block and all",
         out.is_file() and out.read_bytes() == TINY_GIF),
        ("her icon beats the photograph beside it",
         ".jpg" not in src and ".webp" not in src),
        ("and the click still opens the document, not the gif",
         'href="https://bdcbqa314159.github.io/myBureau/graphic-design/dossier/"'
         in desk),
    ]


def case_every_write_goes_through_the_gate(d: pathlib.Path) -> list[tuple[str, bool]]:
    """verbs.atomic() is the last gate, and nothing may step around it.

    It writes through a temp file and renames, because `zola serve` is
    watching and a plain write is visible half-finished. It also
    refuses a content .md that would have no front matter — which is
    the gate standing in for a corruption whose cause was never found.

    Its docstring said every write came through it. Three did not:
    `new_project`, `new_bureau` and the journal rewrite inside `undo`.
    A false promise about a safety gate is worse than a missing gate,
    because it is the sentence the next person reads instead of
    checking. This asserts the sentence.

    The one exception is appending a single line to the journal, which
    is append-only by design and named here so it cannot be mistaken
    for a fourth bypass.
    """
    src = (ROOT / "tools" / "studio" / "verbs.py").read_text(encoding="utf-8")
    direct = []
    for n, line in enumerate(src.splitlines(), 1):
        if ".write_text(" in line or ".write_bytes(" in line:
            # the gate's own temp file is how it does its job
            if "tmp.write_text" in line or "tmp.write_bytes" in line:
                continue
            direct.append("{}: {}".format(n, line.strip()[:60]))
    return [
        ("nothing in verbs.py writes to disk around the gate", direct == []),
        ("the gate still refuses a file with no front matter",
         "_no_front_matter" in src and "raise Refused" in src),
        ("and still writes through a temp file it renames into place",
         "os.replace(tmp, p)" in src),
        ("the journal's one append is the only exception, and it is named",
         'JOURNAL.open("a"' in src),
    ]


def case_the_band_says_what_she_asked_for(d: pathlib.Path) -> list[tuple[str, bool]]:
    """The bandeau holds her brief's words, and nothing it collected.

    Her brief names four: *"DA / Graphic Design / pellicules /
    contact"*. The band was built from every first-class folder, so
    `travail sélectionné` arrived in it by existing — it comes from her
    own portfolio, where it is a page rather than a heading.

    `band = false` keeps a folder out of it. **Out of the band is not
    out of the site**: it is still on the desk, still has its page,
    still reachable — which is what the second half of this asserts,
    because "removed from the band" would otherwise be satisfied by
    deleting the folder.

    The language link is the fifth word and is now the same word as the
    others: it was uppercased, shrunk and faded, three ways of saying
    "this one is different" in a band whose other words are none of
    those things.
    """
    ok, log = build(d)
    home = page(d, "index.html")
    nav = re.search(r'<nav class="bar-nav">.*?</nav>', home, re.S)
    words = [w.strip() for w in re.findall(r"<a[^>]*>([^<]*)</a>",
                                           nav.group(0) if nav else "")]
    css = re.sub(r"/\*.*?\*/", " ",
                 (d / "static" / "css" / "site.css").read_text(encoding="utf-8"),
                 flags=re.S)
    rules = {}
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        rules.setdefault(sel.strip(), []).append(body)
    lang = " ".join(rules.get(".bar-lang", []))
    desk = re.search(r'<main class="desk".*?</main>', home, re.S)

    return [
        ("builds", ok),
        ("the band is her four words, and the language",
         words == ["DA", "graphic design", "pellicules", "contact", "en"]),
        ("travail sélectionné is not among them",
         not any("travail" in w for w in words)),
        # out of the band, not out of the site
        ("but it is still on the desk",
         bool(desk) and "travail-selectionne" in desk.group(0)),
        ("and its page is still built",
         'class="proj-route"' in page(d, "travail-selectionne/index.html")),
        ("the language link is not shouted, shrunk or faded",
         "uppercase" not in lang and "font-size" not in lang
         and "opacity" not in lang),
        ("and the band's own words are untouched by that",
         "graphic design" in words and "contact" in words),
    ]


def case_the_form_can_be_filled_on_a_phone(d: pathlib.Path) -> list[tuple[str, bool]]:
    """Tapping a field must not zoom the page.

    iOS enlarges the whole document when a field smaller than 16px
    takes focus, and leaves the visitor to pinch back out. The form
    inherits `--f-2`, which is about 13px on a phone, through
    `font: inherit` — so tapping "mail" zoomed her contact form on
    every iPhone.

    This is the one surface on the site that takes typed input, and the
    one place where a visitor giving up costs her an enquiry rather
    than a second click. The keyboard matters too: `type="email"` is
    what puts the @ on it.
    """
    css = (d / "static" / "css" / "site.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)
    rules = {}
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        rules.setdefault(sel.strip(), []).append(body)
    fields = " ".join(rules.get(".contact-form input, .contact-form textarea", []))
    ok, log = build(d)
    html = page(d, "index.html")
    form = re.search(r"<form[^>]*contact-form.*?</form>", html, re.S)
    inside = form.group(0) if form else ""

    return [
        ("builds", ok),
        ("a field is never smaller than the size that makes iOS zoom",
         "max(16px" in fields),
        ("and it is set after `font: inherit`, which would undo it",
         fields.find("font: inherit") < fields.find("max(16px")),
        ("the address field asks for the keyboard with an @ on it",
         'type="email"' in inside),
        ("and offers the address the phone already knows",
         'autocomplete="email"' in inside),
        ("on a phone the fields are tall enough to hit with a thumb",
         any(".contact-form input" in sel and "padding: .55rem" in " ".join(b)
             for sel, b in rules.items())),
    ]


def _reads_the_config(d: pathlib.Path) -> bool:
    """Change the list in the scratch config; the reader must change."""
    cfg = d / "config.toml"
    was = cfg.read_text(encoding="utf-8")
    try:
        cfg.write_text(was.replace('not_photographs = ["icon", "poster",'
                                   ' "wallpaper", "about"]',
                                   'not_photographs = ["vignette"]'),
                       encoding="utf-8")
        return filetypes.spoken_for(d) == {"vignette"}
    finally:
        cfg.write_text(was, encoding="utf-8")


def case_one_reader_for_the_file_types(d: pathlib.Path) -> list[tuple[str, bool]]:
    """Which files are photographs is answered in one place.

    `config.toml` owns it — the templates read it from there, and it is
    what somebody edits to add a format. It was also written out in
    four more: hardcoded sets in `model.py` and `verbs.py`, and a
    reader each in `look.py` and this file.

    They agreed on the day it was found, which is the whole danger: add
    `heic` to config.toml and the site would render it while the panel
    refused the file, with nothing saying why. The panel is the thing
    she uses.

    tools/filetypes.py is the one reader now. This is what stops a
    sixth copy.

    THE NAMES ARE THE SAME STORY. `icon`, `poster`, `wallpaper`,
    `about` — the files that are ours rather than hers — were a list in
    config.toml with three names, a hardcoded set in model.py with
    four, another in verbs.py with four, and a two-name tuple in
    look.py written out twice.

    look.py's was live rather than theoretical: with `wallpaper`
    missing, a folder holding nothing but a wallpaper counted as a
    folder with work in it, so "no pictures and almost no text — this
    page is empty" could never fire on a converted desk, which is the
    shape that most needs telling.
    """
    owner = ROOT / "tools" / "filetypes.py"
    here = sorted(list((ROOT / "tools").glob("*.py"))
                  + list((ROOT / "tools" / "studio").glob("*.py")))
    # BY THE NAME, NOT BY THE CONTENTS. A first version matched any set
    # holding an extension, which caught `SHOWS_AS_IMAGE` in verbs.py —
    # and that one must stay. It answers a different question: what a
    # browser can decode from SNIFFED BYTES. It holds `svg`, which the
    # site does not list, and omits `jpg`, because the sniffed subtype
    # of a JPEG is "jpeg". Merging it into this would be the DRY rule
    # applied to characters rather than to knowledge.
    #
    # So this names the four that really were copies of one answer.
    pattern = re.compile(r"^\s*(IMAGE|VIDEO|DOC|MEDIA)\s*=\s*\{", re.M)
    copies = [str(f.relative_to(ROOT)) for f in here
              if f != owner and pattern.search(f.read_text(encoding="utf-8"))]
    conf = filetypes.read(d)
    # A COLLECTION HOLDING TWO OF THE NAMES. Not any mention of them:
    # `f.stem.lower() == "poster"` is a module naming the one file it
    # is about to write, which is a different thing and must stay. Two
    # together in one literal is a list, and a list is a copy.
    pair = re.compile(r'[\{\(\[][^\{\}\(\)\[\]]*"(?:icon|poster|wallpaper|about)"'
                      r'[^\{\}\(\)\[\]]*,[^\{\}\(\)\[\]]*'
                      r'"(?:icon|poster|wallpaper|about)"')
    # THIS FILE IS EXEMPT, and only this file: a check has to write the
    # names down to assert them, which is what the expectation below
    # does three lines from here. Everything else that holds two of
    # them in one literal is keeping a list.
    name_copies = [str(f.relative_to(ROOT)) for f in here
                   if f not in (owner, ROOT / "tools" / "content-check.py")
                   and pair.search(_uncommented(f.read_text(encoding="utf-8")))]
    return [
        ("the one reader exists", owner.is_file()),
        ("and nothing else spells that answer out", copies == []),
        ("the byte-sniffing sets are left alone, being a different question",
         "SHOWS_AS_IMAGE" in (ROOT / "tools" / "studio" / "verbs.py").read_text(encoding="utf-8")),
        ("it reads the config it is pointed at, not this repository's",
         conf["image"] == filetypes.read(d)["image"]),
        ("the panel's two modules take their answer from it",
         all("filetypes." in (ROOT / m).read_text(encoding="utf-8")
             for m in ("tools/studio/model.py", "tools/studio/verbs.py"))),
        ("and so does the tool that tells her the site is sound",
         "filetypes." in (ROOT / "tools" / "look.py").read_text(encoding="utf-8")),
        ("the names that are ours live in the config as well",
         "not_photographs" in (d / "config.toml").read_text(encoding="utf-8")),
        ("and the reader hands back all four",
         filetypes.spoken_for(d) == {"icon", "poster", "wallpaper", "about"}),
        ("nothing in tools/ keeps a second list of them",
         name_copies == []),
        # THE CONTROL. Without it, a reader that returned an empty set
        # would satisfy every expectation above — nothing would hold a
        # second list because there would be no list to hold. So: edit
        # the fixture's config and the answer must follow it.
        ("and it is really read from there, not built into the reader",
         _reads_the_config(d)),
    ]


def case_one_module_knows_what_a_content_file_is(d: pathlib.Path) -> list[tuple[str, bool]]:
    """Nobody splits on the fence by hand any more.

    A content file is `+++`, a header, `+++`, her words. That was
    written out in nine places across four modules, each deciding for
    itself what a malformed file meant. They never disagreed — they
    were nine chances to, and the one bug nobody could explain was a
    header going missing.

    tools/frontmatter.py owns it now. This is what stops the tenth
    copy: a new hand-rolled split is a failing check rather than
    something noticed years later, when two of them have drifted.
    """
    here = sorted(list((ROOT / "tools").glob("*.py"))
                  + list((ROOT / "tools" / "studio").glob("*.py")))
    owner = ROOT / "tools" / "frontmatter.py"
    rolled = []
    for f in here:
        if f == owner:
            continue
        text = f.read_text(encoding="utf-8")
        # the docstring of the owner is allowed to name it; code is not
        if re.search(r'split\(\s*["\']\+\+\+["\']\s*\)', text):
            rolled.append(str(f.relative_to(ROOT)))
    return [
        ("the module that knows what a content file is exists", owner.is_file()),
        ("and nothing else splits on the fence by hand", rolled == []),
        ("the four that used to are reading from it now",
         all("import frontmatter" in (ROOT / m).read_text(encoding="utf-8")
             for m in ("tools/look.py", "tools/studio/model.py",
                       "tools/studio/verbs.py", "tools/studio/check.py"))),
    ]


def case_a_subfolder_page_is_one_column(d: pathlib.Path) -> list[tuple[str, bool]]:
    """A subfolder is a blank page: title, text, work in ONE COLUMN.

    Every photograph takes the whole width — all the space there is for
    a picture — and you keep going down. A project is the other
    rhythm, the prototype's: one opener and then pairs. Both are
    asserted, because a change that collapsed everything to one column
    would satisfy the first and quietly ruin the second.

    And no pinning here. Varying widths are travail sélectionné's and
    nowhere else's, so a subfolder's photographs carry no width of
    their own.
    """
    folder = d / "content" / "da" / "une-serie"
    folder.mkdir()
    (folder / "_index.md").write_text(FRONT.format(
        title="une série", extra='template = "page.html"\n'), encoding="utf-8")
    for n in ("01.jpg", "02.jpg", "03.jpg"):
        shutil.copyfile(ROOT / "content/da/theodora-01/01.jpg", folder / n)
    ok, log = build(d)
    sub = page(d, "da/une-serie/index.html")
    project = page(d, "graphic-design/grocery-list/index.html")
    return [
        ("builds", ok),
        ("every photograph on a subfolder page takes the whole width",
         sub.count('class="proj-open"') == 3),
        ("so there is no pairs container on it at all",
         "proj-pairs" not in sub),
        ("and nothing on it is pinned — that is the road's business",
         "--w:" not in sub and "--x:" not in sub and "--r:" not in sub),
        # REVERSED with the rhythm: a project is this same page now.
        # The expectation is kept rather than deleted because the thing
        # it guards is still worth guarding — that both kinds of thing
        # on a desk reach the SAME page, which is the whole ask.
        # Not a count: grocery list holds six photographs today and may
        # hold ten tomorrow. What is asserted is the SHAPE — the same
        # shape the subfolder above has.
        ("and a PROJECT is the very same page, not a second rhythm",
         'class="proj-open"' in project
         and "proj-pairs" not in project and "proj-fig" not in project),
        ("the route is on travail sélectionné and on nothing else",
         'class="proj-route"' in page(d, "travail-selectionne/index.html")
         and 'class="proj-route"' not in sub
         and 'class="proj-route"' not in page(d, "da/index.html")),
    ]


def case_the_sheet_has_buttons(d: pathlib.Path) -> list[tuple[str, bool]]:
    """Four buttons that change the STATE of her text, never a word.

    Bold, italic and two sizes — the toolbar every plain editor has
    had for thirty years, and each one a class on the sheet. The promise is the second half: these
    cannot edit. That is asserted against the source rather than
    guessed, because "it only toggles a class" is true right up until
    somebody adds a feature.

    They are also asserted to be absent without a script. A row of
    controls that cannot work is worse than no row, and `html.js` is
    set before first paint precisely so this can be decided in CSS.
    """
    ok, log = build(d)
    home = page(d, "index.html")
    win = re.search(r'<dialog class="win win-about".*?</dialog>', home, re.S)
    strip = re.search(r'<div class="sheet-tools">.*?</div>',
                      win.group(0) if win else "", re.S)

    css = (d / "static" / "css" / "site.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)
    rules = {}
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        rules.setdefault(sel.strip(), []).append(body)

    src = (d / "src" / "desk.ts").read_text(encoding="utf-8") if (d / "src").exists() \
        else (ROOT / "src" / "desk.ts").read_text(encoding="utf-8")
    start = src.find("The four buttons above about me.txt")
    end = src.find('[data-close]', start)
    block = src[start:end] if start != -1 else ""
    writes = ("innerHTML", "textContent", "innerText", "insertAdjacent",
              "appendChild", "createTextNode", ".remove()")

    return [
        ("builds", ok),
        ("the buttons are in the window, above her words", bool(strip)),
        ("there are four of them",
         bool(strip) and strip.group(0).count("<button") == 4),
        ("bold and italic are states, and say so to a screen reader",
         bool(strip) and strip.group(0).count("aria-pressed") == 2),
        ("every one of them carries a real name — a face of one letter is not one",
         bool(strip) and strip.group(0).count("aria-label=") == 4),
        ("bold and italic reach the text, rather than only lighting the button",
         any("font-weight" in b for sel, bs in rules.items()
             if ".about-sheet.is-bold" in sel for b in bs)
         and any("font-style" in b for sel, bs in rules.items()
                 if ".about-sheet.is-italic" in sel for b in bs)),
        ("the sheet states a resting weight, so bold is a real jump and not one step",
         any("font-weight" in b for b in rules.get(".about-sheet", []))),
        ("bold reaches the paragraphs too, which is where her words are",
         any(".about-sheet.is-bold *" in sel for sel in rules)),
        ("the buttons line up with the portrait and the text, on the left",
         any("justify-content: flex-start" in b
             for b in rules.get(".js .sheet-tools", []))),
        ("and nothing in that window is centred against the rest",
         not any("justify-content: center" in b
                 for b in rules.get(".js .sheet-tools", []))
         and not any("text-align: center" in b
                     for b in rules.get(".about-sheet", []) + rules.get(".about-body", []))),
        ("and each button's face does what the button does",
         '.sheet-tools button[data-style="bold"]' in rules
         and '.sheet-tools button[data-style="italic"]' in rules),
        ("they are hidden when there is no script to work them",
         any("display: none" in b for b in rules.get(".sheet-tools", []))
         and ".js .sheet-tools" in rules),
        ("each language gets its own words, not the French ones twice",
         'aria-label="Gras"' in home
         and 'aria-label="Bold"' in page(d, "en/index.html")),
        ("and nothing in that script can write to her text",
         block != "" and not any(w in block for w in writes)),
    ]


def case_about_is_read_as_a_text_file(d: pathlib.Path) -> list[tuple[str, bool]]:
    """`about me.txt` is a .txt, and is read as one.

    Her prototype shows it as a screenshot of a plain-text editor. The
    window holds a sheet: sunken, monospace, with a caret blinking after
    the last line. Each of those is one declaration, and each is the
    kind of thing that disappears in a refactor without anything else
    noticing — the page still builds and her words are still there.

    The reduced-motion rule is asserted on purpose, and it lives inside
    a media query: a blinking block is exactly what somebody who asked
    for less motion asked to be rid of, and a CSS check that cannot see
    into @media would report this file clean while the rule was gone.
    """
    ok, log = build(d)
    home = page(d, "index.html")
    win = re.search(r'<dialog class="win win-about".*?</dialog>', home, re.S)

    css = (d / "static" / "css" / "site.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)
    rules = {}
    for sel, bodytext in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        rules.setdefault(sel.strip(), []).append(bodytext)
    sheet = " ".join(rules.get(".about-sheet", []))
    caret = " ".join(rules.get(".about-sheet > :last-child::after", []))

    return [
        ("builds", ok),
        ("her words are on a sheet inside the window",
         bool(win) and 'class="about-sheet"' in win.group(0)),
        ("and they are still her words, not swallowed by the markup",
         bool(win) and "Texte de présentation à venir." in win.group(0)),
        ("the sheet is monospace, from the stack the chrome already uses",
         "var(--font-ui)" in sheet),
        ("it is sunken, so it reads as a document and not a panel",
         "inset" in sheet and "box-shadow" in sheet),
        ("there is a caret after the last line", "animation" in caret),
        ("and it stops blinking for anyone who asked for less motion",
         any("animation: none" in b
             for sel, bodies in rules.items() if "about-sheet" in sel
             for b in bodies)
         and "prefers-reduced-motion" in css),
    ]


def case_a_closed_dialog_stays_closed(d: pathlib.Path) -> list[tuple[str, bool]]:
    """No stylesheet may set `display` on a window that is not open.

    A closed <dialog> is hidden by exactly one rule, and it is in the
    BROWSER's stylesheet: `dialog:not([open]) { display: none }`. Any
    author rule that sets display on the same element beats it —
    whatever the specificity, because author styles win over the user
    agent's. There is no warning. The build is clean, every check here
    was green, and the site opened with every photograph on the desk at
    once, full-screen and stacked, with nothing reachable underneath.

    The dialog class names are read from the built HTML rather than
    typed here, so a window added later is covered without anyone
    remembering this. A rule for something INSIDE a window is fine; it
    is the window's own element that must stay hidden.
    """
    ok, log = build(d)
    dialogs = set()
    for f in (d / "public").rglob("*.html"):
        for cls in re.findall(r'<dialog[^>]*class="([^"]*)"',
                              f.read_text(encoding="utf-8")):
            dialogs.update(cls.split())

    css = (d / "static" / "css" / "site.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)
    # INNERMOST BLOCKS ONLY, which is what reaches inside @media: an
    # @media's own body still contains braces, so it never matches as a
    # rule, and the rules within it do. A check that split on braces
    # instead was blind to every rule in a media query, and that is how
    # a display: none on the editor shipped once before.
    offences = []
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        if not re.search(r"(^|[;\s])display\s*:", body):
            continue
        for one in sel.split(","):
            last = re.split(r"[\s>+~]+", one.strip())[-1]
            classes = set(re.findall(r"\.([A-Za-z0-9_-]+)", last))
            if classes & dialogs and "[open]" not in last:
                offences.append(one.strip())

    inside_a_window = [s for s in offences if " " in s]
    return [
        ("builds", ok),
        ("the site really does have windows to check",
         len(dialogs) > 1),
        ("no stylesheet sets display on a window that is not open",
         offences == []),
        ("and the rule did not pass by looking at the wrong thing",
         inside_a_window == []),
    ]


def case_finder_droppings(d: pathlib.Path) -> list[tuple[str, bool]]:
    """A .DS_Store under content/ must not stop the preview.

    macOS writes one into every folder a Finder window has been opened
    on. look.py refuses the run on any file under content/ that git is
    ignoring — a good rule, aimed at a real failure: a photograph the
    deploy will never see, in a preview that looks right. A .DS_Store is
    not that. It stopped her preview three times over and told her to
    commit Finder's droppings.

    So the rule has to keep biting on what it is for. Both halves are
    checked here, because a fix that silenced the whole scan would pass
    the first and fail nobody.
    """
    subprocess.run(["git", "init", "-q"], cwd=d, capture_output=True)
    (d / ".gitignore").write_text(".DS_Store\ncontent/brouillon/\n",
                                  encoding="utf-8")
    for where in (".", "da"):
        (d / "content" / where / ".DS_Store").write_bytes(b"\x00\x01Bud1")

    def look() -> tuple[int, str]:
        r = subprocess.run([sys.executable, "tools/look.py"], cwd=d,
                           capture_output=True, text=True)
        return r.returncode, (r.stdout or "") + (r.stderr or "")

    quiet_code, quiet = look()

    # and now one that really is hers, and really will not deploy
    hers = d / "content" / "brouillon"
    hers.mkdir()
    (hers / "_index.md").write_text(FRONT.format(
        title="brouillon", extra='template = "section.html"\n'), encoding="utf-8")
    loud_code, loud = look()

    return [
        ("a .DS_Store does not refuse the run", quiet_code == 0),
        ("and is not even mentioned", ".DS_Store" not in quiet),
        ("but a content file git is ignoring still refuses", loud_code == 1),
        ("and it is named, so she knows which one",
         "content/brouillon" in loud),
    ]


def case_a_picture_opens_plain(d: pathlib.Path) -> list[tuple[str, bool]]:
    """A photograph opens with nothing around it; a film keeps its frame.

    She asked for the picture plain — no title bar, no close box, no
    bevel. That is a deletion, and a deletion is the easy thing to put
    back by accident, so what the frame used to carry is asserted here
    one piece at a time: the name a screen reader reads, the way out,
    and the step to the page.

    The film is the control. It has controls of its own, a minimise and
    a thought written beside it, so it keeps its bar — and a change that
    strips BOTH would otherwise look exactly like a change that worked.
    """
    p = d / "content" / "da" / "une-photo"
    p.mkdir()
    (p / "index.md").write_text(FRONT.format(title="une photo.jpg", extra=""),
                                encoding="utf-8")
    shutil.copyfile(ROOT / "content/da/theodora-01/01.jpg", p / "01.jpg")
    q = d / "content" / "da" / "un-clip"
    q.mkdir()
    (q / "index.md").write_text(FRONT.format(title="un clip.mov", extra=""),
                                encoding="utf-8")
    (q / "clip.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
    ok, log = build(d)
    h = page(d, "da/index.html")
    pic = re.search(r'<dialog class="win win-preview" id="preview-da-une-photo".*?</dialog>',
                    h, re.S)
    film = re.search(r'<dialog class="win win-film" id="film-da-un-clip".*?</dialog>',
                     h, re.S)
    return [
        ("builds", ok),
        ("the photograph still opens on the desk", bool(pic)),
        ("with no title bar around it",
         bool(pic) and "win-bar" not in pic.group(0)),
        ("no close box and no page button either",
         bool(pic) and "win-expand" not in pic.group(0)
                   and "<button" not in pic.group(0)),
        ("but it still says what it is, for a screen reader",
         bool(pic) and 'aria-label="une photo.jpg"' in pic.group(0)),
        # REVERSED, DELIBERATELY. The picture WAS a link to the
        # project's page — the second step kept when the frame came off
        # in #94, and flagged then as the one judgement call in it.
        # For a photograph lying on a desk there is no second step to
        # want: the page behind it is the same picture with a line of
        # text, and arriving there by clicking the thing you just
        # opened reads as a mistake. One click opens, a click outside
        # closes, the picture does nothing.
        ("the picture is not a link, so clicking it goes nowhere",
         bool(pic) and "<a " not in pic.group(0)),
        ("its page is still reachable without a script, from the icon",
         bool(re.search(r'<a class="icon"[^>]*href="[^"]*da/une-photo/"', h))),
        ("the film is the control, and keeps its frame",
         bool(film) and "win-bar" in film.group(0)),
        ("nothing on the desk points at a window that is not there",
         dangling(h) == []),
    ]


def case_film_in_a_folder(d: pathlib.Path) -> list[tuple[str, bool]]:
    """A project inside a folder that is now a page.

    The folder used to open a window, and the film's dialog had to be on
    the desk that showed the window. The folder is a page now, and the
    hole that replaces that one is quieter: a project inside it would be
    BUILT and linked from nowhere at all. So the page lists what is
    inside it, and the film plays on its own page.
    """
    q = d / "content" / "da" / "maison-cosette" / "un-film"
    q.mkdir()
    (q / "index.md").write_text(FRONT.format(title="un film.mov", extra=""),
                                encoding="utf-8")
    (q / "clip.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
    (q / "poster.jpg").write_bytes(
        (ROOT / "content" / "da" / "theodora-01" / "01.jpg").read_bytes())
    # one with a photograph, so a face can be found
    r = d / "content" / "da" / "maison-cosette" / "une-photo"
    r.mkdir()
    (r / "index.md").write_text(FRONT.format(title="une photo.jpg", extra=""),
                                encoding="utf-8")
    shutil.copyfile(ROOT / "content/da/theodora-01/01.jpg", r / "01.jpg")
    # a second photograph in the SAME project: the route must show both,
    # which is the whole change — one face per thing was the old answer
    shutil.copyfile(ROOT / "content/da/theodora-02/01.jpg", r / "02.jpg")
    # a third that nothing declares anything about, so the rhythm case
    # has a photograph of its own to be true about
    shutil.copyfile(ROOT / "content/da/theodora-01/01.jpg", r / "03.jpg")
    # and it SIZES one of them by hand, which is the whole point of
    # the route being more than a column. Nothing in the real
    # content had to declare this when the code was written, so without
    # a fixture that does, the path is never executed and the check
    # passes by finding nothing.
    (r / "index.md").write_text(
        '+++\ntitle = "une photo.jpg"\n\n[extra.width]\n"02.jpg" = 37\n\n'
        # offset and angle are DECLARED and must be IGNORED. She asked
        # for no lean and no way to add one, and "no way to add one" is
        # only true if writing the old keys by hand does nothing — the
        # files still exist in her folders and in older copies.
        '[extra.offset]\n"02.jpg" = -18\n\n'
        '[extra.angle]\n"01.jpg" = 5\n\n'
        # WHAT THE PHOTOGRAPH SHOWS. With no links and no names, this
        # is the only thing on the route a screen reader can reach: the
        # page is otherwise a title, a paragraph and silence. The route
        # hardcoded alt="" until the names came off, so nothing had
        # ever carried this value from front matter to the img.
        '[extra.alt]\n"03.jpg" = "une main sur une table"\n'
        '+++\n\nUn texte.\n', encoding="utf-8")
    # and one with nothing to show at all, which is where a broken
    # picture would appear if the partial assumed there was always one
    s = d / "content" / "da" / "maison-cosette" / "rien"
    s.mkdir()
    (s / "_index.md").write_text(FRONT.format(
        title="rien", extra='template = "page.html"\n'), encoding="utf-8")
    ok, log = build(d)
    folder = page(d, "da/maison-cosette/index.html")
    own = page(d, "da/maison-cosette/un-film/index.html")
    css = (d / "static" / "css" / "site.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)
    rules = {}
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        rules.setdefault(sel.strip(), []).append(body)
    # The route is a plain div now rather than a nav: with nothing on
    # it to click, it is not navigation. It holds only figures, so the
    # first </div> after it is its own.
    route = re.search(r'<div class="proj-route".*?</div>', folder, re.S)
    inside = route.group(0) if route else ""


    return [
        ("builds", ok),
        ("the folder is a page, with no window on the DA desk",
         "win-folder" not in page(d, "da/index.html")),
        # A PLACE TO LOOK, AND NOTHING ELSE. These asserted links, file
        # names and named placeholders — all three are gone by her ask:
        # `travail sélectionné` is somewhere a visitor arrives, scrolls
        # and enjoys. Nothing opens and nothing is labelled.
        ("the photographs inside are on the route",
         bool(route) and '<figure class="stop"' in inside),
        ("nothing on it is a link, so clicking does nothing",
         bool(route) and "<a " not in inside),
        ("and nothing carries a file's name",
         bool(route) and "<span" not in inside),
        ("a film contributes nothing, because a poster is not a photograph",
         "un-film" not in inside),
        ("EVERY photograph is a stop, not one face for the whole thing",
         inside.count('<figure class="stop"') == 3),
        ("a photograph pinned by hand carries its own width",
         '--w:37;' in inside),
        ("and an angle cannot be given at all any more",
         '--r:' not in inside),
        ("and one nobody pinned carries no style at all, so the rhythm sizes it",
         '<figure class="stop">' in inside),
        ("what a photograph shows reaches the route, which is all a"
         " screen reader has left",
         'alt="une main sur une table"' in inside),
        ("and one nobody described says nothing rather than something"
         " wrong", inside.count('alt=""') == 2),
        ("the route runs DOWN the page — a grid, not a sideways scroller",
         any("display: grid" in b for b in rules.get(".proj-route", []))
         and not any("overflow-x" in b for b in rules.get(".proj-route", []))),
        # THE HOLE THIS LEAVES, NAMED RATHER THAN HIDDEN. The route was
        # the only thing linking a child project, so with no links a
        # child that shows no photograph is built and reached from
        # nowhere — `un film.mov` here is exactly that. Nothing in the
        # real content is in that position today: the only film sits on
        # the DA desk as its own icon. If one ever is, this expectation
        # is what has to change, and what has to change with it is the
        # page — a film could play inline on the route without being a
        # link, which keeps her "only look and scroll".
        ("a child that shows no photograph is reached from nowhere,"
         " but is still built, so the work is not lost",
         "da/maison-cosette/un-film/" not in inside and own != ""),
        ("the film itself is on its own page", "<video" in own),
        ("no page has a dangling window reference",
         all(dangling(f.read_text(encoding="utf-8")) == []
             for f in (d / "public").rglob("*.html"))),
    ]


def case_a_preview_is_one_picture(d: pathlib.Path) -> list[tuple[str, bool]]:
    """A preview is one screen with one picture on it.

    It used to be "is there a picture at all", and the dialog rendered
    EVERY photograph in the folder — six <img> laid in a flex row with
    `overflow: hidden`, which shows slivers and clips the rest.

    Nothing on either desk was in that position: every photograph
    object holds exactly one, and `grocery list` holds six and carries
    `opens = "page"`. So the suite was green and the failure was one
    photograph away — SHE would have triggered it, by adding to a
    project, which is the worst way for a thing to break.

    Several photographs is a body of work rather than something to
    glance at, so it goes to its page, where they are a column. That
    also makes `opens = "page"` unnecessary for the only project that
    carries it today; the key stays, because a SINGLE photograph may
    still want its page.

    THIS REPLACED `a picture on a desk is one picture`, withdrawn on
    2026-11-13. That case forbade two photographs behind one icon,
    because the second could then be reached only by opening the
    first — true when a desk item's page was a different page, and
    false since every photograph in a folder is shown in a column on
    it. look.py carried the same rule as advice to her and advised one
    folder per photograph, which `grocery list` has never followed and
    has never needed to.
    """
    photo = (ROOT / "content" / "da" / "theodora-01" / "01.jpg").read_bytes()
    base = d / "content" / "da"
    for name, n in (("une", 1), ("deux", 2), ("six", 6)):
        q = base / name
        q.mkdir()
        (q / "index.md").write_text(FRONT.format(title=f"{name}.jpg", extra=""))
        for i in range(1, n + 1):
            (q / f"{i:02d}.jpg").write_bytes(photo)
    ok, log = build(d)
    desk = page(d, "da/index.html")

    def window_of(slug: str) -> str:
        for tag in re.findall(r'<a class="icon".*?>', desk, re.S):
            if f'data-vt="{slug}"' in tag:
                m = re.search(r'data-window="([^"]+)"', tag)
                return m.group(1) if m else ""
        return "NO SUCH ICON"

    one = window_of("da-une")
    return [
        ("builds", ok),
        ("one photograph opens in place", one.startswith("preview-")),
        ("and the dialog holds exactly that one picture",
         len(re.findall(r"<img", re.search(
             r'<dialog[^>]*id="' + one + r'".*?</dialog>', desk, re.S).group(0))) == 1),
        # TWO IS ALREADY TOO MANY. The boundary is where a rule is got
        # wrong, and "any number of pictures" and "exactly one" differ
        # first at two.
        ("two photographs go to the page instead", window_of("da-deux") == ""),
        ("and so do six", window_of("da-six") == ""),
        ("no icon names a dialog that was not written", dangling(desk) == []),
        ("and the page they go to shows every one of them",
         page(d, "da/six/index.html").count('class="proj-open"') == 6),
    ]


def case_a_photograph_can_ask_for_its_page(d: pathlib.Path) -> list[tuple[str, bool]]:
    """`opens = "page"` on a single photograph, and what it is for.

    A photograph on a desk opens IN PLACE: the picture alone, no frame
    and no title bar, which is what she asked for. Two things follow
    that nobody put together until the object audit:

      the preview carries NO way to the page — the link out was taken
      off deliberately, because arriving at a page by clicking the
      thing you just opened reads as a mistake

      the icon's own href IS the page, and the script intercepts it

    So the paragraph she writes under the +++ of a photograph is
    reachable by nothing on the site. All four photographs on the DA
    desk carry a placeholder sentence today; the day she writes a real
    one, nobody will read it.

    `opens = "page"` is the way out, and until now the panel reported
    the key and could not write it. It can now — this is the half that
    proves the key still does what the panel promises.
    """
    photo = (ROOT / "content" / "da" / "theodora-01" / "01.jpg").read_bytes()
    base = d / "content" / "da"
    for name, extra in (("muette", ""), ("bavarde", '[extra]\nopens = "page"\n'),
                        ("explicite", '[extra]\nopens = "image"\n')):
        q = base / name
        q.mkdir()
        (q / "index.md").write_text(FRONT.format(title=f"{name}.jpg", extra=extra))
        (q / "01.jpg").write_bytes(photo)
    ok, log = build(d)
    desk = page(d, "da/index.html")

    def window_of(slug: str) -> str:
        for tag in re.findall(r'<a class="icon".*?>', desk, re.S):
            if f'data-vt="{slug}"' in tag:
                m = re.search(r'data-window="([^"]+)"', tag)
                return m.group(1) if m else ""
        return "NO SUCH ICON"

    return [
        ("builds", ok),
        ("one photograph opens in place by default",
         window_of("da-muette").startswith("preview-")),
        ('and `opens = "page"` sends the same thing to its page instead',
         window_of("da-bavarde") == ""),
        # THE DEFAULT, WRITTEN OUT. The panel writes "image" rather than
        # taking the line away, so it can show the switch without
        # guessing. The templates have to treat it as the default they
        # always meant — an absent key and this must agree.
        ('`opens = "image"` means the same as saying nothing',
         window_of("da-explicite").startswith("preview-")),
        ("no icon names a dialog that was not written", dangling(desk) == []),
        # AND THE REASON THE KEY EXISTS AT ALL: her words are on the
        # page and nowhere else. If a preview ever carries them, or a
        # way to them, this check should be revisited rather than the
        # key — but today it is the only route.
        ("her words are on the page",
         "Un texte." in page(d, "da/bavarde/index.html")),
        ("and are nowhere inside the preview that replaces it",
         "Un texte." not in re.search(
             r'<dialog[^>]*id="' + window_of("da-muette") + r'".*?</dialog>',
             desk, re.S).group(0)),
    ]


def case_a_dead_click(d: pathlib.Path) -> list[tuple[str, bool]]:
    """An icon that names a window nobody rendered.

    `dangling()` has been asserted on nearly every case here since the
    folder windows went, and it never caught this — because no fixture
    held the shape that triggers it. The check was right and the
    content was missing, which is the quietest way for a suite to be
    green and wrong.

    THE SHAPE: a folder whose only image is one of OURS. _icon.html
    asked "is there an image that is not icon.*" and _preview.html
    asked "is there an image that is not icon, poster or wallpaper" —
    the second being the real question, the first borrowed from the
    face chooser, which answers something else. So the icon pointed at
    a dialog _preview.html had refused to write.

    Both arrangements are reachable without anybody doing anything
    strange:

      a film whose video is deleted keeps its poster.jpg
      a desk converted to a folder keeps its wallpaper.jpg

    And it was worse than a click that opens nothing: desk.js called
    preventDefault() before looking for the dialog, so the icon did not
    even fall through to its own page. That order is reversed now, so
    the floor under any future disagreement is "it navigates".
    """
    photo = (ROOT / "content" / "da" / "theodora-01" / "01.jpg").read_bytes()
    base = d / "content" / "da"
    for name, files in (("sans-film", ("poster.jpg",)),
                        ("mur", ("wallpaper.jpg",)),
                        ("vraie", ("01.jpg",))):
        q = base / name
        q.mkdir()
        (q / "index.md").write_text(FRONT.format(title=f"{name}.jpg", extra=""))
        for f in files:
            (q / f).write_bytes(photo)
    ok, log = build(d)
    desk = page(d, "da/index.html")

    def window_of(slug: str) -> str:
        m = re.search(r'<a class="icon[^"]*"[^>]*data-vt="' + slug + r'"[^>]*>',
                      desk, re.S)
        if not m:
            # the attributes span lines; find the tag, then read it
            for tag in re.findall(r'<a class="icon".*?>', desk, re.S):
                if f'data-vt="{slug}"' in tag:
                    m2 = re.search(r'data-window="([^"]+)"', tag)
                    return m2.group(1) if m2 else ""
            return "NO SUCH ICON"
        m2 = re.search(r'data-window="([^"]+)"', m.group(0))
        return m2.group(1) if m2 else ""

    return [
        ("builds", ok),
        ("nothing on the desk names a window that was never rendered",
         dangling(desk) == []),
        ("a film whose video is gone goes to its page, not nowhere",
         window_of("da-sans-film") == ""),
        ("and a folder left holding a wallpaper does too",
         window_of("da-mur") == ""),
        # WITHOUT THIS THE THREE ABOVE PASS BY SHOWING NOTHING AT ALL.
        # A rule that previews nothing anywhere satisfies every one of
        # them; the control is what makes them mean "only these two".
        ("while a real photograph still opens in place",
         window_of("da-vraie").startswith("preview-")),
        ("and the dialog it names is really there",
         f'id="{window_of("da-vraie")}"' in desk),
        # The script half of this — that an icon naming a window which
        # is not there NAVIGATES rather than doing nothing — is in
        # desk-check.mjs, which runs the real desk.js and clicks. A
        # regex here matched `getElementById … preventDefault` in an
        # unrelated handler and could not fail.
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
    ("a folder inside a bureau opens its own page", case_second_level_page),
    ("a folder three levels down", case_three_deep),
    ("what a file does when you click it", case_what_a_file_does),
    ("prune keeps what the site asks for", case_prune_keeps_what_the_site_asks_for),
    ("every page can say what it is", case_every_page_can_say_what_it_is),
    ("about me opens as a screen", case_about_is_a_screen),
    ("a document is shown, not downloaded", case_a_document_is_shown),
    ("a film wears its own frame", case_a_film_wears_its_own_frame),
    ("every photograph in the gallery opens", case_gallery_photographs_open),
    ("the project page is a column", case_the_project_page_is_a_column),
    ("a project wears its own first photograph", case_icon_is_the_work),
    ("a film can ask for its page", case_a_film_can_ask_for_its_page),
    ("only the opener is urgent", case_only_the_opener_is_urgent),
    ("one list of what is not her work", case_one_list_of_what_is_not_her_work),
    ("about me.txt has a face", case_about_has_a_face),
    ("a photograph has no close box", case_a_photograph_has_no_close_box),
    ("a picture fits the screen", case_a_picture_fits_the_screen),
    ("the road survives a phone", case_the_road_survives_a_phone),
    ("the phone agrees with the desk", case_the_phone_agrees_with_the_desk),
    ("a phone desk is not a file list", case_a_phone_desk_is_not_a_file_list),
    ("a phone desk can grow", case_a_phone_desk_can_grow),
    ("a stylesheet with one set of breakpoints", case_one_set_of_breakpoints),
    ("a gif she made loops", case_a_gif_she_made_loops),
    ("an animated icon survives", case_an_animated_icon_survives),
    ("every write goes through the gate", case_every_write_goes_through_the_gate),
    ("the band says what she asked for", case_the_band_says_what_she_asked_for),
    ("the form can be filled on a phone", case_the_form_can_be_filled_on_a_phone),
    ("one reader for the file types", case_one_reader_for_the_file_types),
    ("one module knows what a content file is", case_one_module_knows_what_a_content_file_is),
    ("a subfolder page is one column", case_a_subfolder_page_is_one_column),
    ("the sheet has buttons that cannot edit", case_the_sheet_has_buttons),
    ("about me.txt is read as a text file", case_about_is_read_as_a_text_file),
    ("a closed window stays closed", case_a_closed_dialog_stays_closed),
    ("a .DS_Store does not stop the preview", case_finder_droppings),
    ("a picture opens plain, a film keeps its frame", case_a_picture_opens_plain),
    ("a project inside a folder that is a page", case_film_in_a_folder),
    ("a dead click", case_a_dead_click),
    ("a photograph can ask for its page", case_a_photograph_can_ask_for_its_page),
    ("a preview is one picture", case_a_preview_is_one_picture),
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
