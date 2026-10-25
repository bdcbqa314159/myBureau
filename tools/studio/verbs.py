#!/usr/bin/env python3
"""The only things the dashboard is allowed to do.

A closed list, not a file manager. Every verb is small, validated before
it touches anything, and recorded so it can be taken back — which is what
makes the thing safe to play with, and playing with it is the point.

    place(item, x, y)             move an icon on its desk
    add_image(item, name, data)   a photograph arrives
    reorder(item, names)          01, 02, 03 — and so the icon, which is
                                  the first one
    remove_image(item, name)      to the bin, never unlink
    undo()                        take back the last thing

TWO RULES THAT ARE NOT NEGOTIABLE, because both have bitten this project:

  Every verb touching a project touches EVERY language file it has. A
  position written to `index.md` and not `index.en.md` leaves one language
  on the old spot with nothing to say so.

  Front matter is edited SURGICALLY — the one line, by regex, leaving the
  rest of the file byte for byte. These files carry load-bearing comments
  (read content/_index.md). A parse-and-rewrite would eat them silently.
"""
from __future__ import annotations   # macOS ships 3.9

import json
import os
import pathlib
import re
import shutil
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
CONTENT = ROOT / "content"
CONFIG = ROOT / "config.toml"
STUDIO = ROOT / ".studio"
JOURNAL = STUDIO / "journal.jsonl"
TRASH = STUDIO / "trash"

IMAGE = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif"}
VIDEO = {".mp4", ".webm", ".mov", ".m4v"}
DOC = {".pdf"}
SPOKEN_FOR = {"icon", "poster", "wallpaper", "about"}

# What to say when she hands over something the site cannot show. A list
# of permitted extensions is not an answer — it does not say what to do
# with the file in her hand.
NO_USE_FOR = {
    # The site shows a PDF now — but not as a photograph, a wallpaper, an
    # icon or an affiche, which is every caller of this.
    ".pdf": "un PDF s'affiche tout seul, en grand : dépose-le sur la case"
            " du dossier, pas ici.",
    ".psd": "un .psd ne s'affiche pas. Exporte en JPEG.",
    ".ai":  "un .ai ne s'affiche pas. Exporte en JPEG ou en PNG.",
    ".tif": "un .tif ne s'affiche pas. Réexporte en JPEG.",
    ".tiff": "un .tiff ne s'affiche pas. Réexporte en JPEG.",
    ".heic": "un .heic vient de l'iPhone et ne s'affiche pas. Réexporte en JPEG.",
    ".mp3": "le site ne joue pas de son tout seul — seulement la bande d'un film.",
    ".zip": "une archive ne s'affiche pas.",
}


def unusable(ext: str, wanted: str) -> str:
    """The most useful sentence we can offer about a file we refuse."""
    if ext in NO_USE_FOR:
        return NO_USE_FOR[ext]
    return "le site ne sait pas montrer un {} ici — il attend {}.".format(
        ext.lstrip(".") or "fichier sans extension", wanted)


class Refused(Exception):
    """The verb was not allowed. The message is shown to the person."""


# ---------------------------------------------------------------------
# where things may happen
# ---------------------------------------------------------------------

def rel(p: "pathlib.Path | str") -> str:
    """A path as the journal records it: relative to the repository.

    Both sides are resolved first. On macOS /var is a symlink to
    /private/var, so a resolved path and an unresolved root do not compare
    — and the same is true of any repository reached through a symlink.
    """
    return str(pathlib.Path(p).resolve().relative_to(ROOT.resolve()))


def inside(p: "pathlib.Path | str") -> pathlib.Path:
    """Resolve a path and refuse anything outside content/.

    The dashboard is a web server that writes to disk. This is the only
    thing standing between a crafted request and the rest of the disk, so
    it resolves symlinks and compares real paths rather than trusting the
    string it was handed.
    """
    q = (ROOT / pathlib.Path(p)).resolve()
    try:
        q.relative_to(CONTENT.resolve())
    except ValueError:
        raise Refused("ce n'est pas dans le dossier du site.")
    return q


def a_project(p: "pathlib.Path | str") -> pathlib.Path:
    d = inside(p)
    if not d.is_dir():
        raise Refused("il n'y a pas de dossier à cet endroit.")
    if not any(d.glob("index*.md")) and not any(d.glob("_index*.md")):
        raise Refused("ce dossier n'est ni un projet ni un bureau.")
    return d


def language_files(d: pathlib.Path) -> list:
    stem = "_index" if (d / "_index.md").exists() else "index"
    return sorted(d.glob(stem + "*.md"))


# ---------------------------------------------------------------------
# writing, carefully
# ---------------------------------------------------------------------

def atomic(p: pathlib.Path, text: str) -> None:
    """Write via a temp file in the same directory, then rename.

    `zola serve` is watching this directory. A plain write is visible
    half-finished, and zola will occasionally read it and flash an error
    at her for something she did not do.
    """
    tmp = p.with_name(p.name + ".studio-tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, p)


def nudge(folder: pathlib.Path) -> None:
    """Make `zola serve` notice something it otherwise will not.

    It watches by modification time, and a MOVED file keeps the time it
    always had — so renaming a directory changes nothing it can see. Left
    alone it serves the old url happily and never renders the new one,
    which looks exactly like the panel having done nothing.

    Rewriting each content file with its own bytes is enough: identical
    content, a new timestamp, one rebuild. Tried before it was written —
    the move alone showed nothing, the nudge brought the new url up and
    turned the old one into a 404.
    """
    for f in sorted(folder.rglob("*index*.md")):
        try:
            atomic(f, f.read_text(encoding="utf-8"))
        except OSError:
            pass


def set_key(text: str, name: str, value) -> str:
    """Set one key in the front matter, leaving every other byte alone.

    Three cases, in order: the key is already there; there is an [extra]
    block to put it in; there is neither and one has to be made. Only the
    front matter is ever touched — the split on `+++` is what keeps an
    `x = ` in the body text from being rewritten.
    """
    parts = text.split("+++")
    if len(parts) < 3:
        raise Refused("ce fichier n'a pas d'en-tête entre les +++.")
    fm = parts[1]
    line = "{} = {}".format(name, value if isinstance(value, int)
                            else '"{}"'.format(value))
    pattern = re.compile(r'^\s*' + re.escape(name) + r'\s*=.*$', re.M)
    if pattern.search(fm):
        fm = pattern.sub(line, fm, count=1)
    elif re.search(r'^\[extra\]\s*$', fm, re.M):
        fm = re.sub(r'^(\[extra\]\s*)$', r'\1\n' + line, fm, count=1, flags=re.M)
    else:
        fm = fm.rstrip("\n") + "\n\n[extra]\n" + line + "\n"
    parts[1] = fm
    return "+++".join(parts)


# ---------------------------------------------------------------------
# taking it back
# ---------------------------------------------------------------------

def record(verb: str, texts: list, moves: list) -> None:
    """One line per action, holding enough to reverse it.

    The .md files are under a kilobyte, so the whole previous text is
    kept rather than a diff — reversing is then "put it back", with
    nothing to get subtly wrong.
    """
    STUDIO.mkdir(exist_ok=True)
    entry = {"at": time.time(), "verb": verb, "texts": texts, "moves": moves}
    with JOURNAL.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def undo() -> str:
    if not JOURNAL.exists():
        raise Refused("il n'y a rien à annuler.")
    lines = JOURNAL.read_text(encoding="utf-8").splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        raise Refused("il n'y a rien à annuler.")
    entry = json.loads(lines[-1])
    for t in entry["texts"]:
        atomic(ROOT / t["path"], t["before"])

    # THROUGH A HOLDING NAME, every one of them, before anything lands.
    # A reorder is a permutation — 01 became 02 while 02 became 03 — and
    # undoing that with plain renames overwrites a photograph halfway
    # round the cycle. The forward verb stages for the same reason.
    staged = []
    for i, m in enumerate(entry["moves"]):
        src = ROOT / m["to"]
        if not src.exists():
            continue
        if not m["from"]:
            # it did not exist before this verb, so taking the verb back
            # means taking it away — to the bin, like everything else here
            TRASH.mkdir(parents=True, exist_ok=True)
            bin_ = TRASH / str(int(time.time() * 1000))
            bin_.mkdir(exist_ok=True)
            shutil.move(str(src), str(bin_ / src.name))
            continue
        hold = src.with_name(src.name + ".studio-undo-{}".format(i))
        os.replace(src, hold)
        staged.append((hold, ROOT / m["from"]))
    for hold, dst in staged:
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.replace(hold, dst)
        if dst.is_dir():
            nudge(dst)          # undoing a move has the same blind spot
        elif dst.parent.is_dir():
            nudge(dst.parent)
    JOURNAL.write_text("\n".join(lines[:-1]) + ("\n" if lines[:-1] else ""),
                       encoding="utf-8")
    return entry["verb"]


# ---------------------------------------------------------------------
# the verbs
# ---------------------------------------------------------------------

def place(item: str, x: int, y: int) -> dict:
    d = a_project(item)
    x, y = int(x), int(y)
    if not (0 <= x <= 100 and 0 <= y <= 100):
        raise Refused("une position est un pourcentage du bureau, de 0 à 100.")
    texts = []
    for f in language_files(d):
        before = f.read_text(encoding="utf-8")
        after = set_key(set_key(before, "x", x), "y", y)
        if after != before:
            texts.append({"path": rel(f), "before": before})
            atomic(f, after)
    if texts:
        record("place", texts, [])
    return {"x": x, "y": y, "files": len(texts)}


def retitle(item: str, lang: str, title: str) -> dict:
    """The name under the icon, in one language.

    One language at a time on purpose — unlike a position, a title is not
    the same in French and English, and writing both from one box is how a
    site ends up with English text under a French heading.
    """
    d = a_project(item)
    title = title.strip()
    if not title:
        raise Refused("il faut un nom.")
    if '"' in title:
        raise Refused('un nom ne peut pas contenir de guillemet droit.')
    stem = "_index" if (d / "_index.md").exists() else "index"
    f = d / ("{}.md".format(stem) if lang in ("", "fr", None)
             else "{}.{}.md".format(stem, lang))
    if not f.exists():
        raise Refused("il n'y a pas encore de version {} pour celui-ci.".format(lang))
    before = f.read_text(encoding="utf-8")
    after = set_key(before, "title", title)
    if after != before:
        atomic(f, after)
        record("retitle", [{"path": rel(f), "before": before}], [])
    return {"title": title, "lang": lang}


def set_body(item: str, lang: str, body: str) -> dict:
    """The paragraph under the front matter, in one language.

    Only the part after the closing fence is replaced; the front matter is
    handed back untouched, comments and all.
    """
    d = a_project(item)
    stem = "_index" if (d / "_index.md").exists() else "index"
    f = d / ("{}.md".format(stem) if lang in ("", "fr", None)
             else "{}.{}.md".format(stem, lang))
    if not f.exists():
        raise Refused("il n'y a pas encore de version {} pour celui-ci.".format(lang))
    before = f.read_text(encoding="utf-8")
    parts = before.split("+++")
    if len(parts) < 3:
        raise Refused("ce fichier n'a pas d'en-tête entre les +++.")
    after = "+++".join(parts[:2]) + "+++\n\n" + body.strip() + "\n"
    if after != before:
        atomic(f, after)
        record("set_body", [{"path": rel(f), "before": before}], [])
    return {"wrote": len(body)}


def _next_number(d: pathlib.Path) -> int:
    taken = []
    for f in d.iterdir():
        if f.is_file() and f.suffix.lower() in IMAGE and f.stem.isdigit():
            taken.append(int(f.stem))
    return (max(taken) + 1) if taken else 1


def add_image(item: str, name: str, data: bytes) -> dict:
    d = a_project(item)
    ext = pathlib.Path(name).suffix.lower()
    if ext in VIDEO:
        raise Refused("c'est une vidéo — dépose-la sur « le film », pas sur les photos.")
    if ext not in IMAGE:
        raise Refused(unusable(ext, "une image"))
    if not data:
        raise Refused("ce fichier est vide.")
    dest = d / "{:02d}{}".format(_next_number(d), ext)
    tmp = dest.with_name(dest.name + ".studio-tmp")
    tmp.write_bytes(data)
    os.replace(tmp, dest)
    record("add_image", [], [{"from": "", "to": rel(dest)}])
    return {"named": dest.name}


# What a new thing is called before she renames it, and what the engine
# will draw for it. The extension is not decoration: it is how a project
# with no photograph yet gets a face at all — see _icon.html.
NEW_KINDS = {
    "photos":  {"suffix": ".jpg", "what": "des photos"},
    "film":    {"suffix": ".mov", "what": "un film"},
    "document": {"suffix": ".pdf", "what": "un dossier PDF"},
    "page":    {"suffix": "",     "what": "une page"},
}


def _free_folder(parent: pathlib.Path, wanted: str) -> pathlib.Path:
    """A folder name nobody is using, derived from what she typed."""
    base = re.sub(r"[^a-z0-9]+", "-", wanted.lower().strip()).strip("-") or "nouveau"
    name, n = base, 2
    while (parent / name).exists():
        name = "{}-{}".format(base, n)
        n += 1
    return parent / name


def _languages_of(parent: pathlib.Path, stem: str) -> list:
    """Make the new thing in exactly the languages its neighbours have.

    A project born in French only, on a site that is also in English, is a
    half-translated site by construction — and nothing would say so until
    somebody switched language and found the French.
    """
    out = set()
    for f in parent.rglob(stem + "*.md"):
        bits = f.name[len(stem):-3].strip(".")
        out.add(bits or "")
    if not out:
        out = {""}
    return sorted(out)


def is_gallery(d: pathlib.Path) -> bool:
    for f in d.glob("_index*.md"):
        if 'template = "gallery.html"' in f.read_text(encoding="utf-8", errors="replace"):
            return True
    return False


def new_project(into: str, name: str, kind: str = "photos") -> dict:
    """A new project in a bureau: a folder, and one file per language."""
    d = inside(into)
    if not any(d.glob("_index*.md")):
        raise Refused("un projet se range dans un bureau.")
    # A gallery renders its own photographs and nothing else: a project
    # put inside one would be built and never shown anywhere.
    if is_gallery(d):
        raise Refused("une galerie ne montre que ses photos — un projet rangé"
                      " là ne s'afficherait nulle part.")
    if kind not in NEW_KINDS:
        raise Refused("je ne connais pas ce genre de projet.")
    name = name.strip()
    if not name or '"' in name:
        raise Refused("donne-lui un nom, sans guillemets.")
    folder = _free_folder(d, name)
    folder.mkdir()
    title = name + NEW_KINDS[kind]["suffix"]
    moves = []
    for lang in _languages_of(d, "_index"):
        f = folder / ("index.md" if not lang else "index.{}.md".format(lang))
        f.write_text('+++\ntitle = "{}"\n+++\n\n\n'.format(title), encoding="utf-8")
        moves.append({"from": "", "to": rel(f)})
    moves.append({"from": "", "to": rel(folder)})
    record("new_project", [], moves)
    return {"made": rel(folder), "title": title}


def new_bureau(into: str, name: str) -> dict:
    """A new bureau inside another one."""
    d = inside(into)
    if not any(d.glob("_index*.md")):
        raise Refused("un dossier se range dans un bureau.")
    if is_gallery(d):
        raise Refused("une galerie ne montre que ses photos — un dossier rangé"
                      " là ne s'afficherait nulle part.")
    name = name.strip()
    if not name or '"' in name:
        raise Refused("donne-lui un nom, sans guillemets.")
    folder = _free_folder(d, name)
    folder.mkdir()
    moves = []
    for lang in _languages_of(d, "_index"):
        f = folder / ("_index.md" if not lang else "_index.{}.md".format(lang))
        f.write_text('+++\ntitle = "{}"\ntemplate = "section.html"\n+++\n\n\n'.format(name),
                     encoding="utf-8")
        moves.append({"from": "", "to": rel(f)})
    moves.append({"from": "", "to": rel(folder)})
    record("new_bureau", [], moves)
    return {"made": rel(folder)}


def move(item: str, into: str) -> dict:
    """Put a thing in a different bureau.

    The folder moves whole, so every language file, every photograph and
    anything inside it travels together — which is the point. Doing this
    in the Finder means knowing that index.md and index.en.md are the same
    object, and that a bureau carries its children.

    Its url changes with it, because the url is where it sits. Anything
    anyone had bookmarked to the old one stops working, and nothing here
    can prevent that — the panel says so before it does it.
    """
    src = a_project(item)
    dst = inside(into)
    if not any(dst.glob("_index*.md")):
        raise Refused("ça se range dans un bureau.")
    if is_gallery(dst):
        raise Refused("une galerie ne montre que ses photos — ce que tu déposes"
                      " là ne s'afficherait nulle part.")
    if src == dst:
        raise Refused("il y est déjà.")
    if dst == src.parent:
        raise Refused("il y est déjà.")
    # a folder cannot be put inside itself, nor inside anything it contains
    try:
        dst.relative_to(src)
        raise Refused("un dossier ne peut pas être rangé dans lui-même.")
    except ValueError:
        pass
    dest = _free_folder(dst, src.name)
    os.replace(src, dest)
    record("move", [], [{"from": rel(src), "to": rel(dest)}])
    nudge(dest)                 # or zola keeps serving it where it was
    return {"moved": rel(dest)}


def throw_away(item: str) -> dict:
    """To the bin, whole, and nothing is unlinked.

    `Annuler` brings it back where it was, so this is a thing she can do
    without being sure — which is the only way a delete button belongs in
    a tool for somebody who is not a programmer.
    """
    d = a_project(item)
    if d == CONTENT.resolve():
        raise Refused("c'est le site entier.")
    TRASH.mkdir(parents=True, exist_ok=True)
    bin_ = TRASH / str(int(time.time() * 1000))
    bin_.mkdir(exist_ok=True)
    dest = bin_ / d.name
    parent = d.parent
    shutil.move(str(d), str(dest))
    record("throw_away", [], [{"from": rel(d), "to": rel(dest)}])
    # nothing inside it is left to nudge, so nudge the bureau it left
    nudge(parent)
    return {"binned": d.name}


def add_video(item: str, name: str, data: bytes) -> dict:
    """The film itself.

    A project holding a video IS a film, whatever its name says — that is
    the engine's rule, and it means dropping a video here changes what
    the thing does. One video: the engine takes the first it finds, so a
    second would sit there doing nothing. The one already present goes to
    the bin, which `Annuler` undoes.
    """
    d = a_project(item)
    ext = pathlib.Path(name).suffix.lower()
    if ext in IMAGE:
        raise Refused("c'est une image — dépose-la sur les photos, ou sur l'affiche.")
    if ext not in VIDEO:
        raise Refused(unusable(ext, "une vidéo (mp4, mov, webm, m4v)"))
    if not data:
        raise Refused("ce fichier est vide.")
    # the other half of the rule in add_doc: a film's icon opens the film
    # window, which never shows a dossier
    if any(f.suffix.lower() in DOC for f in d.iterdir() if f.is_file()):
        raise Refused("ce projet est un dossier PDF. Un film a besoin de son"
                      " propre projet.")
    moves = []
    for old in sorted(d.iterdir()):
        if old.is_file() and old.suffix.lower() in VIDEO:
            TRASH.mkdir(parents=True, exist_ok=True)
            bin_ = TRASH / str(int(time.time() * 1000))
            bin_.mkdir(exist_ok=True)
            shutil.move(str(old), str(bin_ / old.name))
            moves.append({"from": rel(old), "to": rel(bin_ / old.name)})
    dest = d / ("film" + ext)
    tmp = dest.with_name(dest.name + ".studio-tmp")
    tmp.write_bytes(data)
    os.replace(tmp, dest)
    moves.append({"from": "", "to": rel(dest)})
    record("add_video", [], moves)
    return {"video": dest.name}


def add_doc(item: str, name: str, data: bytes) -> dict:
    """The dossier itself — a PDF, shown in the project's own page.

    One per project: the engine shows the first one it finds, so a second
    would sit in the folder doing nothing. The one already there goes to
    the bin, which `Annuler` brings back.

    ponytail: the bin-then-write below is the sixth copy of the same ten
    lines (add_video, set_poster, set_icon, set_about, set_wallpaper). The
    lever is one `_replace(d, predicate, dest, data)` helper, worth
    pulling the day a seventh wants it — not on a branch about PDFs.
    """
    d = a_project(item)
    ext = pathlib.Path(name).suffix.lower()
    if ext in IMAGE:
        raise Refused("c'est une image — dépose-la sur les photos.")
    if ext in VIDEO:
        raise Refused("c'est une vidéo — dépose-la sur le film.")
    if ext not in DOC:
        raise Refused(unusable(ext, "un PDF"))
    if not data:
        raise Refused("ce fichier est vide.")
    # A project holding a video IS a film, and its icon opens the film
    # window — which never shows a dossier. The PDF would be built,
    # copied, and reachable from nowhere.
    if any(f.suffix.lower() in VIDEO for f in d.iterdir() if f.is_file()):
        raise Refused("ce projet est un film. Un dossier PDF a besoin de sa"
                      " propre page — fais-en un projet à part.")
    moves = []
    for old in sorted(d.iterdir()):
        if old.is_file() and old.suffix.lower() in DOC:
            TRASH.mkdir(parents=True, exist_ok=True)
            bin_ = TRASH / str(int(time.time() * 1000))
            bin_.mkdir(exist_ok=True)
            shutil.move(str(old), str(bin_ / old.name))
            moves.append({"from": rel(old), "to": rel(bin_ / old.name)})
    dest = d / ("dossier" + ext)
    tmp = dest.with_name(dest.name + ".studio-tmp")
    tmp.write_bytes(data)
    os.replace(tmp, dest)
    moves.append({"from": "", "to": rel(dest)})
    record("add_doc", [], moves)
    return {"doc": dest.name}


def set_poster(item: str, name: str, data: bytes) -> dict:
    """The still shown before a film is played.

    `poster.<ext>` beside it, which the engine reads and which is never
    counted among the project's photographs — so this does not quietly
    add a picture to the page.
    """
    d = a_project(item)
    ext = pathlib.Path(name).suffix.lower()
    if ext in VIDEO:
        raise Refused("une affiche est une image, pas une vidéo.")
    if ext not in IMAGE:
        raise Refused(unusable(ext, "une image"))
    if not data:
        raise Refused("ce fichier est vide.")
    moves = []
    for old in sorted(d.iterdir()):
        if old.is_file() and old.stem.lower() == "poster":
            TRASH.mkdir(parents=True, exist_ok=True)
            bin_ = TRASH / str(int(time.time() * 1000))
            bin_.mkdir(exist_ok=True)
            shutil.move(str(old), str(bin_ / old.name))
            moves.append({"from": rel(old), "to": rel(bin_ / old.name)})
    dest = d / ("poster" + ext)
    tmp = dest.with_name(dest.name + ".studio-tmp")
    tmp.write_bytes(data)
    os.replace(tmp, dest)
    moves.append({"from": "", "to": rel(dest)})
    record("set_poster", [], moves)
    return {"poster": dest.name}


def set_icon(item: str, name: str, data: bytes) -> dict:
    """What this thing LOOKS like on the desk.

    Written as `icon.<ext>` beside its content file, which is the
    engine's own rule and the only one that works for a bureau — a
    bureau has no photographs to take a face from, so until now its
    appearance could not be changed from the panel at all.

    A picture called icon is never shown among a project's photographs,
    so this does not quietly add one to the page.
    """
    d = a_project(item)
    ext = pathlib.Path(name).suffix.lower()
    if ext in VIDEO:
        raise Refused("une icône est une image fixe, pas une vidéo.")
    if ext not in IMAGE and ext != ".svg":
        raise Refused(unusable(ext, "une image"))
    if not data:
        raise Refused("ce fichier est vide.")
    moves = []
    for old in sorted(d.iterdir()):
        if old.is_file() and old.stem.lower() == "icon":
            TRASH.mkdir(parents=True, exist_ok=True)
            bin_ = TRASH / str(int(time.time() * 1000))
            bin_.mkdir(exist_ok=True)
            shutil.move(str(old), str(bin_ / old.name))
            moves.append({"from": rel(old), "to": rel(bin_ / old.name)})
    dest = d / ("icon" + ext)
    tmp = dest.with_name(dest.name + ".studio-tmp")
    tmp.write_bytes(data)
    os.replace(tmp, dest)
    moves.append({"from": "", "to": rel(dest)})
    record("set_icon", [], moves)
    return {"icon": dest.name}


def set_identity(owner: str, studio: str) -> dict:
    """The two words in the top bar. The only verb that leaves content/.

    They are not content — they are the site's identity, and they live in
    `config.toml` under `[extra.demo]` and `[extra.real]`, one of which is
    chosen by `live`. Written to WHICHEVER ONE IS IN USE, because writing
    to the other would be a change she cannot see, and the next person to
    flip `live` inherits it without knowing.

    Surgical, inside that block only, for the usual reason: config.toml is
    four hundred lines of comments explaining itself.
    """
    owner, studio = owner.strip(), studio.strip()
    if not studio:
        raise Refused("le nom du studio ne peut pas être vide.")
    if len(owner) > 60 or len(studio) > 60:
        raise Refused("c'est trop long pour le bandeau — 60 caractères au plus.")
    if "\n" in owner or "\n" in studio or '"' in owner or '"' in studio:
        raise Refused("pas de guillemets ni de retour à la ligne ici.")
    text = CONFIG.read_text(encoding="utf-8")
    which = "real" if re.search(r'^\s*live\s*=\s*true', text, re.M) else "demo"
    block = re.search(r'^\[extra\.' + which + r'\]\s*$(.*?)(?=^\[|\Z)',
                      text, re.M | re.S)
    if block is None:
        raise Refused("config.toml n'a pas de bloc [extra.{}].".format(which))
    body = block.group(1)
    fixed = body
    for key, value in (("owner", owner), ("studio", studio)):
        line = re.compile(r'^(\s*' + key + r'\s*=\s*)".*"', re.M)
        if not line.search(fixed):
            raise Refused("config.toml n'a pas de ligne {} ici.".format(key))
        fixed = line.sub(lambda m: m.group(1) + '"' + value + '"', fixed, count=1)
    whole = text[:block.start(1)] + fixed + text[block.end(1):]
    record("set_identity", [{"path": rel(CONFIG), "before": text}], [])
    atomic(CONFIG, whole)
    return {"owner": owner, "studio": studio, "block": which}


def set_about(item: str, name: str, data: bytes) -> dict:
    """The portrait in `about me.txt`.

    `about.<ext>` beside the home desk's `_index.md`. Only there: the
    about window is built on the home page and nowhere else, so offering
    it on another bureau would be offering something that is never shown.
    """
    d = inside(item)
    if d.resolve() != CONTENT.resolve():
        raise Refused("la présentation est sur la page d'accueil.")
    ext = pathlib.Path(name).suffix.lower()
    if ext in VIDEO:
        raise Refused("une présentation montre une image fixe, pas une vidéo.")
    if ext not in IMAGE:
        raise Refused(unusable(ext, "une image"))
    if not data:
        raise Refused("ce fichier est vide.")
    moves = []
    for old in sorted(d.iterdir()):
        if old.is_file() and old.stem.lower() == "about":
            TRASH.mkdir(parents=True, exist_ok=True)
            bin_ = TRASH / str(int(time.time() * 1000))
            bin_.mkdir(exist_ok=True)
            shutil.move(str(old), str(bin_ / old.name))
            moves.append({"from": rel(old), "to": rel(bin_ / old.name)})
    dest = d / ("about" + ext)
    tmp = dest.with_name(dest.name + ".studio-tmp")
    tmp.write_bytes(data)
    os.replace(tmp, dest)
    moves.append({"from": "", "to": rel(dest)})
    record("set_about", [], moves)
    return {"about": dest.name}


def set_wallpaper(item: str, name: str, data: bytes) -> dict:
    """The photograph behind a bureau.

    Dropped in as `wallpaper.<ext>` beside the `_index.md`, which is the
    convention the engine already reads — one file serving every
    language, and a sub-bureau inheriting it unless it has its own. Any
    wallpaper already there goes to the bin first, so two of them cannot
    sit in one folder arguing about which is the ground.
    """
    d = inside(item)
    if not any(d.glob("_index*.md")):
        raise Refused("seul un bureau a un fond d'écran.")
    ext = pathlib.Path(name).suffix.lower()
    if ext in VIDEO:
        raise Refused("un fond d'écran est une image fixe, pas une vidéo.")
    if ext not in IMAGE:
        raise Refused(unusable(ext, "une image"))
    if not data:
        raise Refused("ce fichier est vide.")
    moves = []
    for old in sorted(d.iterdir()):
        if old.is_file() and old.stem.lower() == "wallpaper":
            TRASH.mkdir(parents=True, exist_ok=True)
            bin_ = TRASH / str(int(time.time() * 1000))
            bin_.mkdir(exist_ok=True)
            shutil.move(str(old), str(bin_ / old.name))
            moves.append({"from": rel(old), "to": rel(bin_ / old.name)})
    dest = d / ("wallpaper" + ext)
    tmp = dest.with_name(dest.name + ".studio-tmp")
    tmp.write_bytes(data)
    os.replace(tmp, dest)
    moves.append({"from": "", "to": rel(dest)})
    record("set_wallpaper", [], moves)
    return {"wallpaper": dest.name}


def reorder(item: str, names: list) -> dict:
    """Renumber the photographs into the order given.

    Two phases, through a temporary name each: renaming 02 to 01 while 01
    still exists would lose one, and the order the browser sends is
    exactly the order that collides.
    """
    d = a_project(item)
    have = [f.name for f in sorted(d.iterdir())
            if f.is_file() and f.suffix.lower() in IMAGE
            and f.stem.lower() not in SPOKEN_FOR]
    if sorted(names) != sorted(have):
        raise Refused("ce ne sont pas les mêmes photos.")
    moves = []
    staged = []
    for i, n in enumerate(names, start=1):
        src = d / n
        hold = d / ("studio-hold-{}{}".format(i, src.suffix.lower()))
        os.replace(src, hold)
        staged.append((hold, "{:02d}{}".format(i, src.suffix.lower()), n))
    for hold, final, was in staged:
        os.replace(hold, d / final)
        if final != was:
            moves.append({"from": rel(d / was), "to": rel(d / final)})
    if moves:
        record("reorder", [], moves)
    return {"order": [s[1] for s in staged]}


def remove_image(item: str, name: str) -> dict:
    d = a_project(item)
    f = inside(pathlib.Path(item) / name)
    if not f.is_file():
        raise Refused("cette photo n'existe pas.")
    TRASH.mkdir(parents=True, exist_ok=True)
    bin_ = TRASH / str(int(time.time() * 1000))
    bin_.mkdir()
    dest = bin_ / f.name
    shutil.move(str(f), str(dest))
    record("remove_image", [], [{"from": rel(f), "to": rel(dest)}])
    return {"binned": f.name}
