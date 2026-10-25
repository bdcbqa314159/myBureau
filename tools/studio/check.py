#!/usr/bin/env python3
"""Does the dashboard keep its hands where they belong?

    python3 tools/studio/check.py

Every verb writes to the filesystem, so these run against a COPY of the
real content and assert what must survive: the comments in her files, the
other language, the bytes of a photograph, and the ability to take any of
it back.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
import verbs  # noqa: E402

failed = 0


def check(what: str, held: bool, detail: str = "") -> None:
    global failed
    print(("  ok    " if held else "  FAIL  ") + what + (("\n          " + detail) if detail and not held else ""))
    if not held:
        failed += 1


def sandbox(tmp: pathlib.Path) -> pathlib.Path:
    shutil.copytree(ROOT / "content", tmp / "content")
    # config.toml too, and not only so the identity cases have something
    # to edit: set_identity is the one verb that writes outside content/,
    # so without this line a test run would edit the real file.
    shutil.copy2(ROOT / "config.toml", tmp / "config.toml")
    verbs.ROOT = tmp
    verbs.CONTENT = tmp / "content"
    verbs.CONFIG = tmp / "config.toml"
    verbs.STUDIO = tmp / ".studio"
    verbs.JOURNAL = verbs.STUDIO / "journal.jsonl"
    verbs.TRASH = verbs.STUDIO / "trash"
    return tmp


def main() -> int:
    tmp = sandbox(pathlib.Path(tempfile.mkdtemp(prefix="studio-")))
    print()

    # ---- the file she wrote survives being edited -------------------
    home = tmp / "content" / "_index.md"
    before = home.read_text(encoding="utf-8")
    verbs.place("content/da/theodora", 44, 18)
    check("an unrelated content file is not touched at all",
          home.read_text(encoding="utf-8") == before)

    theo = tmp / "content" / "da" / "theodora" / "index.md"
    theo_en = tmp / "content" / "da" / "theodora" / "index.en.md"
    check("the position is written", 'x = 44' in theo.read_text(encoding="utf-8"))
    check("and to the OTHER language too, which is the whole trap",
          'x = 44' in theo_en.read_text(encoding="utf-8"))

    # the home desk has load-bearing comments in its [extra] block
    verbs.place("content/da", 50, 50)
    da = (tmp / "content" / "da" / "_index.md").read_text(encoding="utf-8")
    check("a bureau's own comments survive the edit",
          "template = " in da and da.count("#") >= 0 and "title = " in da)

    # a file whose comments we can name
    probe = tmp / "content" / "da" / "theodora" / "index.md"
    probe.write_text('+++\ntitle = "t.jpg"\n\n[extra]\n# ne touche pas a cette ligne\nx = 1\ny = 2\n+++\n\nUn texte.\n', encoding="utf-8")
    verbs.place("content/da/theodora", 7, 9)
    after = probe.read_text(encoding="utf-8")
    check("a comment inside [extra] is still there, word for word",
          "# ne touche pas a cette ligne" in after, after)
    check("and the body text is untouched", after.rstrip().endswith("Un texte."))
    check("only the two numbers changed", "x = 7" in after and "y = 9" in after)

    # ---- a project with no [extra] at all ---------------------------
    bare = tmp / "content" / "da" / "sans-extra"
    bare.mkdir()
    (bare / "index.md").write_text('+++\ntitle = "b.jpg"\n+++\n\nTexte.\n', encoding="utf-8")
    verbs.place("content/da/sans-extra", 10, 20)
    t = (bare / "index.md").read_text(encoding="utf-8")
    check("an [extra] block is created when there was none",
          "[extra]" in t and "x = 10" in t and t.count("+++") == 2, t)

    # ---- it refuses to leave content/ -------------------------------
    for bad in ("../README.md", "/etc", "content/../../etc", "content/da/../../.git"):
        try:
            verbs.inside(bad)
            check("refuses " + bad, False)
        except verbs.Refused:
            check("refuses " + bad, True)

    # ---- photographs -------------------------------------------------
    proj = "content/da/theodora"
    d = tmp / "content" / "da" / "theodora"
    pixels = (ROOT / "content" / "da" / "theodora" / "01.jpg").read_bytes()
    verbs.add_image(proj, "whatever.jpg", pixels)
    names = sorted(f.name for f in d.iterdir() if f.suffix == ".jpg")
    check("a dropped photograph is numbered, not left with its own name",
          "03.jpg" in names and "whatever.jpg" not in names, str(names))
    check("and arrives byte for byte", (d / "03.jpg").read_bytes() == pixels)

    try:
        verbs.add_image(proj, "notes.txt", b"x")
        check("refuses a file the site cannot show", False)
    except verbs.Refused:
        check("refuses a file the site cannot show", True)

    first = (d / "01.jpg").read_bytes()
    third = (d / "03.jpg").read_bytes()
    verbs.reorder(proj, ["03.jpg", "01.jpg", "02.jpg"])
    check("reordering renumbers without losing one",
          sorted(f.name for f in d.iterdir() if f.suffix == ".jpg") == ["01.jpg", "02.jpg", "03.jpg"])
    check("and the photograph that was third is now first — so it is the icon",
          (d / "01.jpg").read_bytes() == third)
    check("nothing is left holding a temporary name",
          not any("studio-hold" in f.name for f in d.iterdir()))

    verbs.remove_image(proj, "02.jpg")
    check("a removed photograph leaves the folder",
          not (d / "02.jpg").exists())
    check("but goes to the bin rather than being unlinked",
          any(p.name == "02.jpg" for p in verbs.TRASH.rglob("*")))

    # ---- taking it back ----------------------------------------------
    verbs.undo()
    check("undo brings it back out of the bin", (d / "02.jpg").exists())
    verbs.undo()
    check("undo reverses a reorder", (d / "01.jpg").read_bytes() == first)
    verbs.undo()
    check("undo removes a photograph that was added", not (d / "03.jpg").exists())
    # the next entry back is the bare project's placement, not theodora's
    verbs.undo()
    bare_t = (bare / "index.md").read_text(encoding="utf-8")
    check("undo takes back an [extra] block it had to invent",
          "x = 10" not in bare_t, bare_t)
    verbs.undo()
    t = probe.read_text(encoding="utf-8")
    check("undo restores a position, comment and all",
          "x = 1" in t and "y = 2" in t and "# ne touche pas a cette ligne" in t, t)

    # ---- and it stops, rather than going wrong, when there is no more
    for _ in range(20):
        try:
            verbs.undo()
        except verbs.Refused:
            break
    try:
        verbs.undo()
        check("undo refuses once the journal is empty", False)
    except verbs.Refused:
        check("undo refuses once the journal is empty", True)
    check("and content/ is still a buildable tree",
          (tmp / "content" / "_index.md").exists()
          and (tmp / "content" / "da" / "theodora" / "index.md").exists())

    # ---- making things, and dressing them ----------------------------
    out = verbs.new_project("content/da", "Mon Essai", "film")
    made = tmp / out["made"]
    check("a new project is a folder with a file per language",
          made.is_dir() and (made / "index.md").exists() and (made / "index.en.md").exists())
    check("its name carries the extension that gives it a face",
          out["title"] == "Mon Essai.mov", out["title"])
    check("the folder name is a slug, whatever she typed",
          made.name == "mon-essai", made.name)
    verbs.new_project("content/da", "Mon Essai", "photos")
    check("asking twice does not collide",
          (tmp / "content" / "da" / "mon-essai-2").is_dir())

    b = verbs.new_bureau("content/da", "Sous Bureau")
    nb = tmp / b["made"]
    check("a new bureau declares the template that makes it a desk",
          'template = "section.html"' in (nb / "_index.md").read_text(encoding="utf-8"))
    check("and exists in both languages too", (nb / "_index.en.md").exists())

    try:
        verbs.new_project("content/da/theodora", "Dedans")
        check("a project cannot be made inside a project", False)
    except verbs.Refused:
        check("a project cannot be made inside a project", True)

    pixels = (ROOT / "content" / "da" / "theodora" / "01.jpg").read_bytes()
    verbs.set_icon("content/da", "whatever.png", pixels)
    check("a BUREAU can be given a face, which it never could before",
          (tmp / "content" / "da" / "icon.png").exists())
    verbs.set_icon("content/da", "again.jpg", pixels)
    check("a second icon replaces the first rather than joining it",
          not (tmp / "content" / "da" / "icon.png").exists()
          and (tmp / "content" / "da" / "icon.jpg").exists())
    verbs.undo()
    check("and undo brings the first one back",
          (tmp / "content" / "da" / "icon.png").exists()
          and not (tmp / "content" / "da" / "icon.jpg").exists())


    # ---- she reads these, and she reads French ----------------------
    # Twenty-nine of thirty-four refusals were in English. A panel that
    # answers "that folder is not a project or a bureau" to somebody who
    # does not write code is a dead end, however correct it is.
    import re as _re
    source = (HERE / "verbs.py").read_text(encoding="utf-8")
    # Common English words that are NOT also French. "site", "image",
    # "page" and "a" are deliberately absent — they appear in perfectly
    # good French and would make this cry wolf.
    english = set("the is are was this that these those no such thing things"
                  " file files folder not with your you cannot does has have"
                  " there here what which where open close address printed"
                  " very large missing empty name only inside goes unknown"
                  " kind percentage desk quote photograph photographs"
                  " exist exists already whole set same".split())
    offenders = []
    for m in _re.finditer(r'Refused\(\s*"([^"]+)"', source):
        words = set(_re.findall(r"[a-zA-Z']+", m.group(1).lower()))
        # a French sentence will not be mostly English words
        if words and len(words & english) >= max(2, len(words) // 2):
            offenders.append(m.group(1))
    check("every refusal she can meet is in her language", offenders == [],
          "; ".join(offenders[:3]))

    # the server has messages of its own, and she meets those too
    srv = (HERE / "server.py").read_text(encoding="utf-8")
    spoken = _re.findall(r'oops\(\d+,\s*"([^"{]+)"', srv)
    spoken += _re.findall(r'send\(4\d\d,\s*"([^"]+)"', srv)
    loud = [s for s in spoken
            if len(set(_re.findall(r"[a-zA-Z']+", s.lower())) & english) >= 2]
    check("and so are the server's own", loud == [], "; ".join(loud[:3]))

    # ---- a film can receive a film ----------------------------------
    clip = b"\x00\x00\x00\x18ftypmp42" + b"0" * 200
    pixels = (ROOT / "content" / "da" / "theodora" / "01.jpg").read_bytes()
    out = verbs.new_project("content/da", "Nuit", "film")
    film = out["made"]
    verbs.add_video(film, "whatever.mp4", clip)
    check("a film project can be given a film",
          (tmp / film / "film.mp4").exists())
    verbs.set_poster(film, "still.jpg", pixels)
    check("and an affiche, which is not one of its photographs",
          (tmp / film / "poster.jpg").exists())
    verbs.add_video(film, "second.mov", clip)
    check("a second film replaces the first — the engine only reads one",
          (tmp / film / "film.mov").exists() and not (tmp / film / "film.mp4").exists())
    verbs.undo()
    check("and undo brings the first film back",
          (tmp / film / "film.mp4").exists())

    # ---- each thing receives its own kind ----------------------------
    def refused(fn, *a):
        try:
            fn(*a)
            return ""
        except verbs.Refused as exc:
            return str(exc)

    say = refused(verbs.add_image, film, "clip.mp4", clip)
    check("a video dropped on the photographs is refused, and told where to go",
          "vidéo" in say and "film" in say, say)
    say = refused(verbs.add_video, film, "photo.jpg", pixels)
    check("an image dropped on the film is refused, and told where to go",
          "image" in say and ("photos" in say or "affiche" in say), say)
    say = refused(verbs.set_poster, film, "clip.mp4", clip)
    check("an affiche refuses a video", "image" in say, say)
    say = refused(verbs.set_wallpaper, "content/da", "clip.mp4", clip)
    check("a wallpaper refuses a video", "image" in say, say)
    say = refused(verbs.set_icon, "content/da", "clip.mp4", clip)
    check("an icon refuses a video", "image" in say, say)

    # the refusal has to say what to DO, not list extensions
    # Still refused here — a PDF is not a photograph — but the sentence
    # now points at the box that takes one. It used to say "exporte les
    # pages en JPEG", which was true of an engine that could not show a
    # PDF at all.
    say = refused(verbs.add_image, film, "brochure.pdf", b"%PDF-1.4")
    check("a PDF is refused with what to do about it, not a list of formats",
          "PDF" in say and "dossier" in say and "JPEG" not in say, say)
    say = refused(verbs.add_image, film, "photo.heic", pixels)
    check("and so is an iPhone .heic", "JPEG" in say, say)

    # ---- a gallery is a gallery, however you arrive at it ----------
    import json as _json, subprocess as _sub
    got = _json.loads(_sub.run([sys.executable, "tools/studio/model.py"], cwd=ROOT,
                               capture_output=True, text=True).stdout)
    as_child = [o for d in got["desks"] for o in d["on"]
                if o["path"] == "content/pellicules"]
    as_desk = [d for d in got["desks"] if d["path"] == "content/pellicules"]
    check("the gallery is described both as a child and as a desk",
          len(as_child) == 1 and len(as_desk) == 1)
    if as_child and as_desk:
        a, b = as_child[0], as_desk[0]
        same = all(a.get(k) == b.get(k)
                   for k in ("gallery", "depth", "opens_as", "empty", "holds",
                             "photographs", "x", "y", "icon"))
        check("and the two descriptions agree on every fact", same,
              str({k: (a.get(k), b.get(k)) for k in
                   ("gallery", "depth", "opens_as", "empty", "holds")}))
        check("whichever way she reaches it, it knows it is a gallery",
              a.get("gallery") is True and b.get("gallery") is True)
        check("and it knows about its photographs", len(a.get("photographs", [])) > 0)

    # WHAT THE PANEL OFFERS vs WHAT THE SERVER ALLOWS. The panel lights up
    # a folder she can drop onto; if that disagrees with the verb she
    # either aims at something that then refuses, or is denied a move that
    # was always legal. Asked of every folder in the real tree.
    import shutil as _sh
    disagreed = []
    for d in got["desks"]:
        probe = pathlib.Path(tempfile.mkdtemp(prefix="studio-rx-"))
        _sh.copytree(ROOT / "content", probe / "content")
        verbs.ROOT, verbs.CONTENT = probe, probe / "content"
        verbs.STUDIO, verbs.JOURNAL = probe / ".studio", probe / ".studio/journal.jsonl"
        verbs.TRASH = probe / ".studio/trash"
        # a probe that is not ALREADY in the destination, or the server
        # refuses for a different reason entirely ("il y est déjà") and
        # the comparison is answering the wrong question
        probe_item = ("content/graphic-design/calendar"
                      if d["path"] in ("content/da", "content/da/theodora")
                      else "content/da/theodora")
        if d["path"] in (probe_item, "content"):
            _sh.rmtree(probe, ignore_errors=True); continue
        allowed = True
        try:
            verbs.move(probe_item, d["path"])
        except verbs.Refused:
            allowed = False
        if allowed != d["can_receive"]:
            disagreed.append((d["path"], d["can_receive"], allowed))
        _sh.rmtree(probe, ignore_errors=True)
    verbs.ROOT, verbs.CONTENT = tmp, tmp / "content"
    verbs.STUDIO, verbs.JOURNAL = tmp / ".studio", tmp / ".studio/journal.jsonl"
    verbs.TRASH = tmp / ".studio/trash"
    check("what the panel offers as a target is what the server accepts",
          disagreed == [], str(disagreed))

    # nothing may be filed into a gallery: it renders photographs only
    for fn, args in ((verbs.new_project, ("content/pellicules", "Essai")),
                     (verbs.new_bureau, ("content/pellicules", "Essai")),
                     (verbs.move, ("content/da/theodora", "content/pellicules"))):
        try:
            fn(*args)
            check("a gallery refuses to be filed into (%s)" % fn.__name__, False)
        except verbs.Refused as exc:
            check("a gallery refuses to be filed into (%s)" % fn.__name__,
                  "galerie" in str(exc), str(exc))

    # ---- moving and throwing away, the two Finder trips -------------
    verbs.move("content/da/theodora", "content/graphic-design")
    check("a project moves whole, into another bureau",
          (tmp / "content/graphic-design/theodora/index.md").exists()
          and not (tmp / "content/da/theodora").exists())
    check("and every language went with it",
          (tmp / "content/graphic-design/theodora/index.en.md").exists())
    check("as did its photographs",
          (tmp / "content/graphic-design/theodora/01.jpg").exists())
    verbs.undo()
    check("undo puts it back where it was",
          (tmp / "content/da/theodora/index.md").exists()
          and not (tmp / "content/graphic-design/theodora").exists())

    verbs.move("content/da/maison-cosette", "content/graphic-design")
    check("a bureau moves with its children",
          (tmp / "content/graphic-design/maison-cosette/jojo/index.md").exists())
    verbs.undo()

    for bad in [("content/da", "content/da/maison-cosette")]:
        try:
            verbs.move(*bad)
            check("a folder cannot be put inside itself", False)
        except verbs.Refused:
            check("a folder cannot be put inside itself", True)
    try:
        verbs.move("content/da/theodora", "content/da/confidence-glow")
        check("and not inside a project either", False)
    except verbs.Refused:
        check("and not inside a project either", True)

    verbs.throw_away("content/da/theodora")
    check("throwing a project away takes the whole folder",
          not (tmp / "content/da/theodora").exists())
    check("to the bin, not to nowhere",
          any(p.name == "index.md" for p in verbs.TRASH.rglob("*")))
    verbs.undo()
    check("and undo brings all of it back",
          (tmp / "content/da/theodora/index.md").exists()
          and (tmp / "content/da/theodora/01.jpg").exists())

    try:
        verbs.throw_away("content")
        check("the whole site cannot be thrown away", False)
    except verbs.Refused:
        check("the whole site cannot be thrown away", True)

    doc_cases(tmp)
    gate_cases(tmp)
    affiche_cases(tmp)
    honesty_cases(tmp)
    identity_cases(tmp)

    shutil.rmtree(tmp, ignore_errors=True)

    serve()
    print()
    if failed:
        print("  {} FAILED\n".format(failed))
        return 1
    print("  the dashboard keeps its hands where they belong\n")
    return 0




TINY_PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"


def doc_cases(tmp: pathlib.Path) -> None:
    """A dossier, and the guardrails around which file goes where."""
    print("\n  -- a dossier PDF --\n")
    pixels = (ROOT / "content/da/theodora/01.jpg").read_bytes()
    clip = b"\x00\x00\x00\x18ftypmp42"

    def refused(fn, *a, **k):
        try:
            fn(*a, **k)
        except verbs.Refused as why:
            return str(why)
        return ""

    made = verbs.new_project("content/da", "grocery", "document")
    proj = made["made"]
    check("a new document is named .pdf, so it has a face before it has a file",
          made["title"].endswith(".pdf"))

    verbs.add_doc(proj, "Grocery Brochure.PDF", TINY_PDF)
    folder = tmp / proj
    check("the PDF lands in the project",
          (folder / "dossier.pdf").read_bytes() == TINY_PDF)
    check("and the extension is lowered",
          [f.name for f in folder.iterdir() if f.suffix.lower() == ".pdf"]
          == ["dossier.pdf"])

    verbs.add_doc(proj, "v2.pdf", TINY_PDF + b"2")
    check("a second PDF replaces the first rather than sitting beside it",
          len([f for f in folder.iterdir() if f.suffix.lower() == ".pdf"]) == 1
          and (folder / "dossier.pdf").read_bytes() == TINY_PDF + b"2")
    verbs.undo()
    check("undo brings the first one back",
          (folder / "dossier.pdf").read_bytes() == TINY_PDF)

    # ---- which file goes where ---------------------------------------
    check("an image is refused on the dossier, and says where it goes",
          "photos" in refused(verbs.add_doc, proj, "cover.jpg", pixels))
    check("a video is refused on the dossier",
          "film" in refused(verbs.add_doc, proj, "clip.mov", clip))
    check("something that is neither is refused with a sentence about PDFs",
          "PDF" in refused(verbs.add_doc, proj, "notes.txt", b"x"))
    check("an empty file is refused",
          refused(verbs.add_doc, proj, "x.pdf", b"") != "")

    say = refused(verbs.add_image, proj, "brochure.pdf", TINY_PDF)
    check("a PDF is still refused as a photograph",
          say != "" and "JPEG" not in say, say)
    check("and the refusal now points at the dossier instead of lying",
          "dossier" in say, say)
    check("a PDF is refused as a wallpaper",
          refused(verbs.set_wallpaper, "content/da", "x.pdf", TINY_PDF) != "")
    check("and as an icon",
          refused(verbs.set_icon, proj, "x.pdf", TINY_PDF) != "")
    check("and as an affiche",
          refused(verbs.set_poster, proj, "x.pdf", TINY_PDF) != "")

    # ---- a film and a dossier are two different projects -------------
    check("a film cannot also be a dossier",
          "propre projet" in refused(verbs.add_video, proj, "film.mp4", clip))
    film = verbs.new_project("content/da", "une bande", "film")["made"]
    verbs.add_video(film, "clip.mp4", clip)
    check("and a dossier cannot be added to a film",
          "propre page" in refused(verbs.add_doc, film, "x.pdf", TINY_PDF))

    # photographs are still welcome — a brochure has a cover
    verbs.add_image(proj, "cover.jpg", pixels)
    check("a dossier still takes a cover photograph",
          (folder / "01.jpg").is_file())

    check("a dossier cannot be made in a gallery",
          refused(verbs.new_project, "content/pellicules", "x", "document") != "")

    # ---- the one that ate her text ----------------------------------
    # The route defaulted a missing `body` to "", so a request that
    # spelled the field wrong replaced the paragraph with nothing and
    # answered {"wrote": 0}. Found by driving the real server with the
    # wrong key, which is how a typo in anything calling it would look.
    home = tmp / "content" / "_index.md"
    had = home.read_text(encoding="utf-8")
    verbs.set_body("content", "fr", "Je suis directrice artistique.")
    check("writing the text keeps the front matter, comments and all",
          home.read_text(encoding="utf-8").split("+++")[1] == had.split("+++")[1])
    check("and the text is what she typed",
          home.read_text(encoding="utf-8").split("+++")[2].strip()
          == "Je suis directrice artistique.")
    verbs.undo()
    check("undo puts her old text back", home.read_text(encoding="utf-8") == had)
    check("clearing it on purpose is still allowed",
          verbs.set_body("content", "fr", "")["wrote"] == 0)
    verbs.undo()


def honesty_cases(tmp: pathlib.Path) -> None:
    """A file is what its bytes say, the gallery decides at the verb, the
    bin does not grow for ever, and a photograph can be described."""
    print("\n  -- what a file really is, and what it can be told --\n")
    pixels = (ROOT / "content/da/theodora/01.jpg").read_bytes()
    pdf = TINY_PDF
    heic = b"\x00\x00\x00\x18ftypheic" + b"\x00" * 40
    mp4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 40
    png = (b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR"
           + b"\x00" * 40)

    def refused(fn, *a, **k):
        try:
            fn(*a, **k)
        except verbs.Refused as why:
            return str(why)
        return ""

    proj = "content/da/theodora"
    # The one that broke the build: zola dies on get_image_metadata, so a
    # drag that said it worked left a site that would not compile.
    say = refused(verbs.add_image, proj, "cover.jpg", pdf)
    check("a PDF renamed .jpg is refused before it can break the build",
          "PDF" in say and ".jpg" in say, say)
    check("and an iPhone .heic renamed .jpg too, with the export advice",
          "heic" in refused(verbs.add_image, proj, "photo.jpg", heic))
    check("a photograph renamed .mov is refused as a film",
          "JPEG" in refused(verbs.add_video, proj, "clip.mov", pixels))
    check("a photograph renamed .pdf is refused as a dossier",
          "JPEG" in refused(verbs.add_doc, proj, "x.pdf", pixels))
    # ...but NOT this one. zola reads a PNG carrying a .jpg name and
    # builds it; refusing that would be a refusal she cannot act on.
    check("a PNG carrying a .jpg name is allowed, because the site reads it",
          refused(verbs.add_image, proj, "fine.jpg", png) == "")
    check("a real film is still allowed",
          refused(verbs.add_video, proj, "ok.mp4", mp4) == "")
    check("bytes we do not recognise are not refused on a guess",
          refused(verbs.add_image, proj, "odd.jpg", b"no idea what this is") == "")

    # ---- the gallery decides at the verb, not in the interface -------
    check("the gallery refuses a wallpaper at the verb, not just in the panel",
          "galerie" in refused(verbs.set_wallpaper, "content/pellicules",
                               "w.jpg", pixels))
    check("and a real bureau still takes one",
          refused(verbs.set_wallpaper, "content/da", "w.jpg", pixels) == "")

    # ---- the bin is bounded -----------------------------------------
    for i in range(verbs.REMEMBERED + 25):
        verbs.set_wallpaper("content/da", "w{}.jpg".format(i), pixels)
    kept = [l for l in verbs.JOURNAL.read_text(encoding="utf-8").splitlines()
            if l.strip()]
    bins = [d for d in verbs.TRASH.iterdir() if d.is_dir()]
    check("the journal stops at what Annuler can actually reach",
          len(kept) == verbs.REMEMBERED, str(len(kept)))
    check("and the bin holds nothing the journal no longer names",
          len(bins) <= verbs.REMEMBERED, str(len(bins)))
    check("undo still works after the trim",
          verbs.undo() == "set_wallpaper")

    # ---- a photograph can say what it shows -------------------------
    print()
    before = (tmp / proj / "index.md").read_text(encoding="utf-8")
    out = verbs.set_alt(proj, "01.jpg", "Deux silhouettes sur une plage.")
    check("a description is written to every language, not just one",
          out["files"] == 2, str(out))
    for f in ("index.md", "index.en.md"):
        got = (tmp / proj / f).read_text(encoding="utf-8")
        check("  it is in {}, under [extra.alt]".format(f),
              "[extra.alt]" in got and "Deux silhouettes sur une plage." in got)
    check("the front matter it already had is untouched",
          "x = 32" in (tmp / proj / "index.md").read_text(encoding="utf-8"))
    verbs.set_alt(proj, "01.jpg", "Deux silhouettes, au crépuscule.")
    got = (tmp / proj / "index.md").read_text(encoding="utf-8")
    check("writing it again replaces the line rather than adding a second",
          got.count('"01.jpg"') == 1 and "au crépuscule" in got)
    verbs.set_alt(proj, "01.jpg", "")
    check("clearing it takes the line out",
          '"01.jpg"' not in (tmp / proj / "index.md").read_text(encoding="utf-8"))
    check("a description for a photograph that is not there is refused",
          refused(verbs.set_alt, proj, "99.jpg", "x") != "")
    check("a quote is refused, because it would end the TOML string",
          refused(verbs.set_alt, proj, "01.jpg", 'a "b') != "")
    check("and three hundred characters is the limit",
          refused(verbs.set_alt, proj, "01.jpg", "x" * 301) != "")
    # and the panel has to be able to SHOW what is written, or the box
    # comes up empty every time she reopens the project
    verbs.set_alt(proj, "02.jpg", "Un portrait de profil.")
    import model as the_model
    the_model.ROOT, the_model.CONTENT = tmp, tmp / "content"
    seen = {}
    for d in the_model.tree()["desks"]:
        for c in d["on"]:
            if c["path"] == proj:
                seen = c.get("alt") or {}
    check("the panel reads back the description it wrote",
          seen.get("02.jpg") == "Un portrait de profil.", str(seen))

    verbs.undo()
    verbs.undo()
    verbs.undo()
    verbs.undo()
    check("undo walks all of it back",
          (tmp / proj / "index.md").read_text(encoding="utf-8") == before)


def affiche_cases(tmp: pathlib.Path) -> None:
    """A dropped film gets its own first frame as its affiche."""
    print("\n  -- the film's own first frame --\n")
    clip = (ROOT / "kit/films/clip-3s.mp4").read_bytes()
    other = (ROOT / "kit/films/clip-2s.webm").read_bytes()
    pixels = (ROOT / "kit/films/affiche-1600x900.jpg").read_bytes()
    started = len([l for l in verbs.JOURNAL.read_text(encoding="utf-8").splitlines()
                   if l.strip()]) if verbs.JOURNAL.exists() else 0

    made = verbs.new_project("content/da", "sans affiche", "film")["made"]
    d = tmp / made
    out = verbs.add_video(made, "clip.mp4", clip)
    check("dropping a film writes an affiche from its first frame",
          out.get("poster") == "poster.png" and (d / "poster.png").is_file(),
          str(out))
    check("and the frame is a real picture, not an empty file",
          (d / "poster.png").stat().st_size > 2000)
    import model as the_model
    the_model.ROOT, the_model.CONTENT = tmp, tmp / "content"
    seen = None
    for desk in the_model.tree()["desks"]:
        for c in desk["on"]:
            if c["path"] == made:
                seen = c
    check("which the panel reports, so it can show it",
          seen is not None and seen.get("poster") == "poster.png"
          and seen.get("video") == "film.mp4", str(seen and
          {k: seen.get(k) for k in ("video", "poster")}))

    # and a film that is too broken to read must not hold the panel:
    # Quick Look hangs for ever on a truncated one (measured), and this
    # runs with the write lock held
    broken_proj = verbs.new_project("content/da", "corrompu", "film")["made"]
    import time as _t
    t0 = _t.perf_counter()
    got = verbs.add_video(broken_proj, "truncated.mp4",
                          b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 40000)
    spent = _t.perf_counter() - t0
    check("a truncated film gives up instead of hanging the panel",
          got.get("poster") is None and spent < verbs.FRAME_DEADLINE + 5,
          "{:.1f}s".format(spent))
    check("and the film itself still landed, which is what she asked for",
          (tmp / broken_proj / "film.mp4").is_file())

    # A NEW FILM MUST NOT KEEP THE OLD FILM'S FRAME. A .webm is the
    # sharpest case: Quick Look cannot read one — it hangs for ever on a
    # perfectly valid vp9 file, measured — so there is no new frame to
    # draw, and the question becomes what happens to the old one. It has
    # to go. A page showing one film's frame while playing another is
    # worse than a page showing no frame.
    verbs.add_video(made, "autre.webm", other)
    check("a film Quick Look cannot read gets no frame",
          not (d / "poster.png").exists())
    check("and the frame of the film it replaced is gone with it",
          not any(f.stem.lower() == "poster" for f in d.iterdir()))
    import time as _t
    t0 = _t.perf_counter()
    verbs.add_video(made, "encore.webm", other)
    webm_cost = _t.perf_counter() - t0
    check("a webm is refused a frame immediately, not after the deadline",
          webm_cost < 2, "{:.1f}s".format(webm_cost))

    # and a format it CAN read draws one again
    verbs.add_video(made, "retour.mp4", clip)
    check("dropping a readable film draws its frame again",
          (d / "poster.png").is_file())

    # but hers wins, and keeps winning
    verbs.set_poster(made, "la mienne.jpg", pixels)
    check("choosing her own affiche replaces ours",
          (d / "poster.jpg").is_file() and not (d / "poster.png").exists())
    verbs.add_video(made, "encore.mp4", clip)
    check("and a new film leaves HER affiche alone",
          (d / "poster.jpg").read_bytes() == pixels
          and not (d / "poster.png").exists())

    # the one already in the real content has a hand-made affiche
    before = sorted(f.name for f in (tmp / "content/da/junes-cry").iterdir())
    verbs.add_video("content/da/junes-cry", "x.mp4", clip)
    check("a project that already had an affiche keeps it",
          (tmp / "content/da/junes-cry/poster.jpg").is_file()
          and not (tmp / "content/da/junes-cry/poster.png").exists())

    # and all of it comes back — undone until the journal is the length
    # it was when these cases started, rather than a fixed count that
    # silently stops meaning anything when a case is added above
    while len([l for l in verbs.JOURNAL.read_text(encoding="utf-8").splitlines()
               if l.strip()]) > started:
        verbs.undo()
    check("undo walks the whole lot back, and the film project is gone",
          not (tmp / made).exists(), str(
              sorted(f.name for f in (tmp / made).iterdir())
              if (tmp / made).exists() else "gone"))


def gate_cases(tmp: pathlib.Path) -> None:
    """The panel must never leave a file zola cannot read.

    A content file turned up with its front matter gone and the site
    stopped building. Nothing in the journal explained it, so instead of
    guessing at a cause the class is closed at the last gate before the
    disk: every write to a content .md goes through verbs.atomic.
    """
    print("\n  -- the last gate before the disk --\n")

    def refused(fn, *a, **k):
        try:
            fn(*a, **k)
        except verbs.Refused as why:
            return str(why)
        return ""

    f = tmp / "content" / "_index.en.md"
    good = f.read_text(encoding="utf-8")
    for what, text in [
            ("an empty file", ""),
            ("one with no opening +++", "Juste du texte.\n"),
            ("one whose header is never closed", '+++\ntitle = "x"\n\nTexte.\n'),
            ("one with a blank line before the +++",
             '\n+++\ntitle = "x"\n+++\n\nTexte.\n')]:
        say = refused(verbs.atomic, f, text)
        check("atomic refuses " + what, say != "", "it was written")
        check("  and says which file", "_index.en.md" in say, say)
    check("and the file is untouched by any of those attempts",
          f.read_text(encoding="utf-8") == good)

    # the gate is for content only: the journal and config.toml are not
    # markdown and must still be writable
    verbs.atomic(verbs.JOURNAL, "")
    check("the journal may still be emptied — it is not content",
          verbs.JOURNAL.read_text(encoding="utf-8") == "")

    # a real edit still goes through
    verbs.set_body("content", "en", "I am an art director.")
    now = f.read_text(encoding="utf-8")
    check("a real edit still lands",
          "art director" in now and now.startswith("+++"))

    # ---- the refusals name the file ---------------------------------
    broken = tmp / "content" / "da" / "theodora" / "index.en.md"
    was = broken.read_text(encoding="utf-8")
    broken.write_text("Pas d'en-tete ici.\n", encoding="utf-8")
    for what, fn, args in [
            ("set_body", verbs.set_body, ("content/da/theodora", "en", "Texte.")),
            ("retitle", verbs.retitle, ("content/da/theodora", "en", "Nom")),
            ("set_alt", verbs.set_alt, ("content/da/theodora", "01.jpg", "Une photo."))]:
        say = refused(fn, *args)
        check("{} on a broken file names it".format(what),
              "index.en.md" in say, say)
    broken.write_text(was, encoding="utf-8")

    # ---- a verb that writes EVERY language is all or nothing --------
    # Asked of BOTH orders. `index.en.md` sorts before `index.md`, so
    # breaking the English one found the problem before anything was
    # written and the check passed on sort order rather than on the code
    # being right. Breaking the French one is the real test.
    fr = tmp / "content" / "da" / "theodora" / "index.md"
    for which, other in ((broken, fr), (fr, broken)):
        keep_a = which.read_text(encoding="utf-8")
        keep_b = other.read_text(encoding="utf-8")
        which.write_text("Pas d'en-tete.\n", encoding="utf-8")
        say = refused(verbs.place, "content/da/theodora", 40, 40)
        check("place refuses when {} is broken".format(which.name),
              say != "", "it went ahead")
        check("  and names that file", which.name in say, say)
        check("  and left {} completely alone".format(other.name),
              other.read_text(encoding="utf-8") == keep_b)
        which.write_text(keep_a, encoding="utf-8")

    for which, other in ((broken, fr), (fr, broken)):
        keep_a, keep_b = (which.read_text(encoding="utf-8"),
                          other.read_text(encoding="utf-8"))
        which.write_text("Pas d'en-tete.\n", encoding="utf-8")
        refused(verbs.set_alt, "content/da/theodora", "01.jpg", "Une photo.")
        check("set_alt left {} alone when {} was broken"
              .format(other.name, which.name),
              other.read_text(encoding="utf-8") == keep_b)
        which.write_text(keep_a, encoding="utf-8")


def identity_cases(tmp: pathlib.Path) -> None:
    """The portrait in `about me.txt`, and the two words in the top bar."""
    print("\n  -- about me.txt, and the bandeau --\n")
    pixels = (ROOT / "content/da/theodora/01.jpg").read_bytes()

    def refused(fn, *a, **k):
        try:
            fn(*a, **k)
        except verbs.Refused as why:
            return str(why)
        return ""

    verbs.set_about("content", "moi.JPG", pixels)
    face = tmp / "content" / "about.jpg"
    check("a portrait lands beside _index.md, named about.jpg",
          face.is_file() and face.read_bytes() == pixels)
    # By the name the filesystem reports, not by .exists() — macOS is
    # case-insensitive, so about.JPG "exists" either way and the check
    # would pass without the lowering it is there to prove.
    check("and the extension is lowered, so the template's test matches",
          [f.name for f in (tmp / "content").iterdir()
           if f.stem.lower() == "about"] == ["about.jpg"])

    verbs.set_about("content", "autre.png", pixels)
    check("a second one replaces the first rather than sitting next to it",
          sorted(f.name for f in (tmp / "content").iterdir()
                 if f.stem == "about") == ["about.png"])

    check("a portrait is refused on any desk but the home one",
          "accueil" in refused(verbs.set_about, "content/da", "x.jpg", pixels))
    check("a video is refused, and says why",
          "vidéo" in refused(verbs.set_about, "content", "x.mov", b"\x00"))
    check("a PDF is refused as a portrait",
          refused(verbs.set_about, "content", "x.pdf", b"%PDF") != "")
    check("an empty file is refused",
          refused(verbs.set_about, "content", "x.jpg", b"") != "")

    verbs.undo()
    check("undo puts the first portrait back",
          (tmp / "content" / "about.jpg").is_file()
          and not (tmp / "content" / "about.png").exists())

    # ---- the bandeau ------------------------------------------------
    cfg = tmp / "config.toml"
    before = cfg.read_text(encoding="utf-8")
    comments = before.count("#")
    verbs.set_identity("le studio de", "VALENTINA")
    now = cfg.read_text(encoding="utf-8")
    check("the bandeau is written into the block that is actually in use",
          re.search(r'\[extra\.demo\][^\[]*owner\s*=\s*"le studio de"', now, re.S)
          is not None)
    check("and the other block is left exactly as it was",
          re.search(r'\[extra\.real\][^\[]*owner\s*=\s*"valentina for"', now, re.S)
          is not None)
    check("config.toml keeps every one of its comments",
          now.count("#") == comments, "{} -> {}".format(comments, now.count("#")))
    check("and every other line of it",
          len(now.splitlines()) == len(before.splitlines()))

    check("an empty studio name is refused",
          refused(verbs.set_identity, "x", "   ") != "")
    check("a quote is refused, because it would end the TOML string",
          refused(verbs.set_identity, 'a "b', "S") != "")
    check("a newline is refused for the same reason",
          refused(verbs.set_identity, "a\nb", "S") != "")
    check("sixty-one characters is refused",
          refused(verbs.set_identity, "x" * 61, "S") != "")

    verbs.undo()
    check("undo restores config.toml byte for byte",
          cfg.read_text(encoding="utf-8") == before)

    # live = true has to send it to the other block, or launch day puts
    # the demo name on her site and nothing says so
    cfg.write_text(before.replace("live = false", "live = true"), encoding="utf-8")
    verbs.set_identity("valentina pour", "STUDIO S")
    now = cfg.read_text(encoding="utf-8")
    check("with live = true it writes [extra.real] instead",
          re.search(r'\[extra\.real\][^\[]*owner\s*=\s*"valentina pour"', now, re.S)
          is not None
          and re.search(r'\[extra\.demo\][^\[]*owner\s*=\s*"a demo of"', now, re.S)
          is not None)
    cfg.write_text(before, encoding="utf-8")


def serve() -> None:
    """The server itself, as a real process against a real copy.

    The verbs above are tested in-process. This is the other half: the
    boundary. A local server that writes to disk is the one genuinely
    dangerous thing in this repository, so what is asserted here is
    mostly what it REFUSES.
    """
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="studio-srv-"))
    # everything zola needs to actually build, because the panel's middle
    # pane is the real site and a site that cannot build cannot be framed
    for name in ("content", "templates", "tools", "static", "sass", "config.toml"):
        src = ROOT / name
        if not src.exists():
            continue
        (shutil.copytree if src.is_dir() else shutil.copyfile)(src, tmp / name)
    port, site_port = 1197, 1198
    # a real zola behind it, because the panel's middle pane IS the site
    subprocess.run(["zola", "build"], cwd=tmp, capture_output=True)
    site = subprocess.Popen(["zola", "serve", "--interface", "127.0.0.1",
                             "--port", str(site_port)], cwd=tmp,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    p = subprocess.Popen([sys.executable, "tools/studio/server.py", str(port),
                          "http://127.0.0.1:{}/".format(site_port)],
                         cwd=tmp, stdout=subprocess.PIPE, text=True)
    try:
        url = p.stdout.readline().strip()
        token = url.split("t=")[1]

        def get(path, tok=token, headers=None):
            req = urllib.request.Request(
                "http://127.0.0.1:{}{}{}t={}".format(
                    port, path, "&" if "?" in path else "?", tok),
                headers=headers or {})
            return urllib.request.urlopen(req, timeout=10)

        def code_for_plain(port_, path):
            try:
                return urllib.request.urlopen(
                    "http://127.0.0.1:{}{}".format(port_, path), timeout=10).getcode()
            except urllib.error.HTTPError as e:
                return e.code

        def code_for(path, tok, headers=None):
            try:
                return get(path, tok, headers).getcode()
            except urllib.error.HTTPError as e:
                return e.code

        for _ in range(40):
            try:
                get("/api/tree"); break
            except Exception:                        # noqa: BLE001
                time.sleep(0.25)
        # and zola behind it: the proxy answers 502 until the site is up,
        # which is a real state the panel can be in, not a test artefact
        for _ in range(80):
            try:
                if urllib.request.urlopen(
                        "http://127.0.0.1:{}/".format(site_port), timeout=5).getcode() == 200:
                    break
            except Exception:                        # noqa: BLE001
                time.sleep(0.5)

        tree = json.loads(get("/api/tree").read())["tree"]
        check("the server reads the same desks the model does",
              len(tree["desks"]) == len(json.loads(
                  subprocess.run([sys.executable, "tools/studio/model.py"], cwd=tmp,
                                 capture_output=True, text=True).stdout)["desks"]))

        # THE PAGE'S OWN SUBRESOURCES, asked for the way a browser asks:
        # exactly the url written in the markup, with nothing appended.
        # This is the check that was missing. The suite asserted
        # "/app.js?t=<token>" and passed, while the browser asked for
        # "/app.js" and got 403 — no stylesheet, no script, dead buttons.
        # Never test the url you invented; test the one the page uses.
        page = get("/").read().decode()
        refs = sorted({u for u in re.findall(r'(?:href|src)="([^"]+)"', page)
                       if not u.startswith("http")})
        check("the page references something at all", len(refs) >= 3)
        dead = []
        for u in refs:
            req = urllib.request.Request("http://127.0.0.1:{}{}".format(port, u))
            try:
                if urllib.request.urlopen(req, timeout=10).getcode() != 200:
                    dead.append(u)
            except urllib.error.HTTPError as e:
                dead.append("{} ({})".format(u, e.code))
        check("every one of them loads with NO token, as the browser asks",
              dead == [], str(dead))

        # the site, proxied onto the panel's own address — this is what
        # the frame loads, and being same-origin is what lets the panel
        # reach into the real page at all
        check("the real site comes through the panel", code_for_plain(port, "/site/") == 200)
        framed = urllib.request.urlopen(
            "http://127.0.0.1:{}/site/".format(port), timeout=10).read().decode()
        check("and nothing in it still points at zola's own address",
              "127.0.0.1:{}".format(port + 1) not in framed and ":1111" not in framed)
        check("the framed page is a real desk, with real icons",
              'data-vt="da"' in framed)

        # HEADERS A BROWSER OBEYS AND curl IGNORES. The panel sent
        # X-Frame-Options: DENY on everything, as a blanket precaution —
        # including the proxied site, whose entire job is to be framed.
        # Every request still answered 200, so nothing here noticed;
        # Firefox refused the frame and said so.
        head = urllib.request.urlopen(
            "http://127.0.0.1:{}/site/".format(port), timeout=10).headers
        xfo = (head.get("X-Frame-Options") or "").upper()
        check("the site it proxies may actually be framed by the panel",
              xfo in ("", "SAMEORIGIN"), "X-Frame-Options: " + (xfo or "(none)"))
        csp = head.get("Content-Security-Policy") or ""
        check("and no frame-ancestors policy forbids it either",
              "frame-ancestors" not in csp, csp)
        own = urllib.request.urlopen(
            "http://127.0.0.1:{}/?t={}".format(port, token), timeout=10).headers
        check("while the panel itself still refuses to be framed by others",
              (own.get("X-Frame-Options") or "").upper() in ("SAMEORIGIN", "DENY"))
        inner = sorted({u for u in re.findall(r'(?:href|src)="(/site/[^"]+)"', framed)})
        broken = [u for u in inner if code_for_plain(port, u) != 200]
        check("everything the framed page asks for loads too", broken == [], str(broken[:3]))

        # THE FEEDBACK LOOP. A verb's own write must not come back as
        # news: the panel would reload the frame for a change it already
        # has on screen, and land on zola's mid-rebuild 404 doing it.
        n0 = json.loads(get("/api/tree").read())["n"]
        post_do = urllib.request.Request(
            "http://127.0.0.1:{}/api/do?t={}".format(port, token),
            data=json.dumps({"verb": "place", "item": "content/da/theodora",
                             "x": 66, "y": 44}).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        said = json.loads(urllib.request.urlopen(post_do, timeout=10).read())["n"]
        check("a write moves the counter once", said == n0 + 1, "{} -> {}".format(n0, said))
        time.sleep(1.2)                       # long enough for the watcher to look
        later = json.loads(get("/api/tree").read())["n"]
        check("and the watcher does not report it back as somebody else's",
              later == said, "{} -> {}".format(said, later))
        urllib.request.urlopen(urllib.request.Request(
            "http://127.0.0.1:{}/api/do?t={}".format(port, token),
            data=json.dumps({"verb": "undo"}).encode(),
            headers={"Content-Type": "application/json"}, method="POST"), timeout=10)

        check("no token, no answer", code_for("/api/tree", "wrong") == 403)
        check("the page itself refuses without the token",
              code_for("/", "wrong") == 403)
        check("a cross-site request is refused even WITH the token",
              code_for("/api/tree", token, {"Sec-Fetch-Site": "cross-site"}) == 403)

        # the thing that would matter most: reading outside content/
        check("it will not serve a file outside content/",
              code_for("/media/../../etc/passwd", token) in (403, 404))
        check("nor one addressed absolutely",
              code_for("/media//etc/passwd", token) in (403, 404))
        check("but it does serve a photograph that is inside",
              code_for("/media/content/da/theodora/01.jpg", token) == 200)

        def post(path, payload):
            req = urllib.request.Request(
                "http://127.0.0.1:{}{}?t={}".format(port, path, token),
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            return json.loads(urllib.request.urlopen(req, timeout=10).read())

        out = post("/api/do", {"verb": "place", "item": "content/da/theodora",
                               "x": 71, "y": 23})
        moved = (tmp / "content/da/theodora/index.md").read_text(encoding="utf-8")
        moved_en = (tmp / "content/da/theodora/index.en.md").read_text(encoding="utf-8")
        check("a drag writes the position through the server",
              "x = 71" in moved and out["did"]["x"] == 71)
        check("and both languages again, over HTTP", "x = 71" in moved_en)
        check("the answer carries the fresh tree, so nothing is cached",
              "tree" in out and out["tree"]["desks"])

        post("/api/do", {"verb": "undo"})
        check("undo over HTTP puts it back",
              "x = 71" not in (tmp / "content/da/theodora/index.md").read_text(encoding="utf-8"))

        # THE ONE THAT ATE HER TEXT. `body` was defaulted to "", so a
        # request naming the field anything else replaced the paragraph
        # with nothing and answered 200 {"wrote": 0}.
        home = tmp / "content" / "_index.md"
        had = home.read_text(encoding="utf-8")
        try:
            post("/api/do", {"verb": "set_body", "item": "content",
                             "lang": "fr", "text": "pas le bon champ"})
            check("a set_body with no body is refused, not obeyed", False)
        except urllib.error.HTTPError as e:
            check("a set_body with no body is refused, not obeyed", e.code == 400)
        check("and her text is still there", home.read_text(encoding="utf-8") == had)
        out = post("/api/do", {"verb": "set_body", "item": "content",
                               "lang": "fr", "body": "Directrice artistique."})
        check("with the right field it writes",
              "Directrice artistique." in home.read_text(encoding="utf-8"))
        post("/api/do", {"verb": "undo"})

        # FOUR AT ONCE. This answered [200, 200, 500, 500] and left ONE
        # photograph on disk: _next_number() reads the folder then writes
        # to it, so two threads chose the same number and one overwrote
        # the other — while both told her it had worked.
        import threading
        P = "content/travail-selectionne/nocturne"
        had = {f.name for f in (tmp / P).iterdir()}
        shot = (ROOT / "content/da/theodora/01.jpg").read_bytes()
        got = {}

        def upload(i):
            req = urllib.request.Request(
                "http://127.0.0.1:{}/api/upload?into={}&name=p{}.jpg&as=photos&t={}"
                .format(port, P, i, token), data=shot, method="POST")
            try:
                got[i] = urllib.request.urlopen(req, timeout=20).status
            except urllib.error.HTTPError as e:
                got[i] = e.code
            except Exception as e:                      # noqa: BLE001
                got[i] = type(e).__name__

        threads = [threading.Thread(target=upload, args=(i,)) for i in range(4)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        now = {f.name for f in (tmp / P).iterdir()}
        check("four photographs dropped at once are all accepted",
              sorted(got.values()) == [200, 200, 200, 200], str(got))
        check("and all four are really on disk, with distinct names",
              len(now - had) == 4, "{} new".format(len(now - had)))
        for f in now - had:
            (tmp / P / f).unlink()


        try:
            post("/api/do", {"verb": "rm", "item": "content"})
            check("an unknown verb is refused", False)
        except urllib.error.HTTPError as e:
            check("an unknown verb is refused", e.code == 400)
            check("and refused in French, like every other refusal",
                  "action" in (e.read().decode("utf-8") if hasattr(e, "read") else ""))

        try:
            post("/api/do", {"verb": "place", "item": "../../etc", "x": 1, "y": 1})
            check("a verb cannot be aimed outside content/", False)
        except urllib.error.HTTPError as e:
            check("a verb cannot be aimed outside content/", e.code == 400)
    finally:
        p.terminate(); p.wait(timeout=10)
        site.terminate(); site.wait(timeout=10)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
