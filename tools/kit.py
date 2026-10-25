#!/usr/bin/env python3
"""Make the test kit in kit/ — files to drag into the panel.

    python3 tools/kit.py            # make whatever is missing
    python3 tools/kit.py --force    # make all of it again
    python3 tools/kit.py --list     # say what is there, write nothing

WHY THESE ARE GENERATED AND NOT PHOTOGRAPHS. This repository is public
and the rule is that nothing a client sent is ours to publish. A kit of
real photographs would also be a kit of somebody's licence to read. So
every file here is drawn by ffmpeg or written byte by byte below, which
makes them unambiguously ours and makes the kit reproducible: delete
kit/ and this puts it back identically.

They are deliberately UGLY. A gradient is not a portfolio photograph —
it is a shape of a known size, which is the only thing being tested.

WHAT THEY ARE FOR. Each one answers a question the engine has a rule
about, and the file name says which: the opener is the first photograph,
a tall one is bounded by its height, an icon is the first picture in the
folder, a dossier is shown and not downloaded, a film needs an affiche.
The last group is files that are LYING about what they are, which the
panel has to refuse rather than pass to a build that then dies.

Nothing here reaches the site. kit/ is outside content/ and static/, so
zola never reads it and the deploy only ever uploads public/.
"""
from __future__ import annotations

import argparse
import pathlib
import shutil
import struct
import subprocess
import sys
import zlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
KIT = ROOT / "kit"

# A hue per file, so two files of the same shape are still telling apart
# on a desk. (top colour, bottom colour)
INK = {
    "dusk":    ("0x1b4965", "0xcae9ff"),
    "ochre":   ("0x8a5a22", "0xf3d8a7"),
    "moss":    ("0x2f4a33", "0xd6e5cd"),
    "rose":    ("0x7a3b4e", "0xf6d9e0"),
    "slate":   ("0x3a3a44", "0xd8d8e0"),
    "sand":    ("0x6b5a3e", "0xeee3cf"),
    "ink":     ("0x14151a", "0x8d93a1"),
    "sea":     ("0x16585c", "0xbfe3e0"),
}


def run(args: list) -> None:
    done = subprocess.run(args, capture_output=True, text=True)
    if done.returncode != 0:
        raise SystemExit("  ffmpeg failed:\n" + done.stderr.strip()[-600:])


def picture(path: pathlib.Path, w: int, h: int, hue: str, busy: bool = False) -> None:
    """One drawn image, at exactly the size asked for."""
    top, bottom = INK[hue]
    if busy:
        # a pattern with detail in it, for judging an icon over a
        # wallpaper and a thumbnail that has to stay legible when small
        src = "testsrc2=size={}x{}:rate=1".format(w, h)
    else:
        src = ("gradients=size={}x{}:c0={}:c1={}:nb_colors=2:type=linear"
               .format(w, h, top, bottom))
    path.parent.mkdir(parents=True, exist_ok=True)
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", src, "-frames:v", "1"]
    if path.suffix.lower() in (".jpg", ".jpeg"):
        args += ["-c:v", "mjpeg", "-q:v", "6"]
    run(args + ["-y", str(path)])
    # EVERY NAME IN THIS KIT CARRIES ITS SIZE, so the size has to be the
    # one the name claims. testsrc2 rounds to even dimensions, which
    # quietly turned a 2000x1125 wallpaper into 2000x1124 and left the
    # file lying about itself — in a kit whose whole job is to be a known
    # shape. Read it back rather than trust it.
    got = measure(path)
    if got != (w, h):
        raise SystemExit("  {} came out {}x{}, not {}x{} — pick even numbers"
                         " for a busy one".format(path.name, got[0], got[1], w, h))


def measure(path: pathlib.Path) -> tuple:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True)
    w, _, h = out.stdout.strip().partition(",")
    return (int(w), int(h.rstrip(","))) if w else (0, 0)


def alpha_png(path: pathlib.Path, w: int, h: int) -> None:
    """A PNG with a transparent hole in it, written here rather than by
    ffmpeg because what is being tested is the alpha channel surviving
    the resize pipeline — so it has to be certain there is one."""
    rows = []
    for y in range(h):
        row = bytearray([0])                      # filter type 0
        for x in range(w):
            far = ((x - w / 2) ** 2 + (y - h / 2) ** 2) ** 0.5
            inside = far < min(w, h) * 0.32
            row += bytes((20, 60, 90, 0) if inside
                         else (int(240 * x / w), 120, int(200 * y / h), 255))
        rows.append(bytes(row))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"".join(rows), 9))
        + chunk(b"IEND", b""))


def clip(path: pathlib.Path, seconds: int, w: int, h: int) -> None:
    """A few seconds of moving picture. Small on purpose: this is here to
    prove a film plays and gets an affiche, not to test a codec."""
    path.parent.mkdir(parents=True, exist_ok=True)
    src = "testsrc2=size={}x{}:rate=24:duration={}".format(w, h, seconds)
    if path.suffix == ".webm":
        codec = ["-c:v", "libvpx-vp9", "-b:v", "150k", "-deadline", "realtime"]
    else:
        codec = ["-c:v", "libx264", "-crf", "34", "-preset", "veryfast",
                 "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    run(["ffmpeg", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", src] + codec + ["-y", str(path)])


def pdf(path: pathlib.Path, title: str, pages: list) -> None:
    """A real PDF, with a correct xref table and selectable text.

    Written here rather than printed by macOS so the bytes are ours and
    the same on every machine. Helvetica is one of the fourteen fonts a
    reader is required to have, so nothing is embedded.
    """
    objs: list[bytes] = []

    def add(body: bytes) -> int:
        objs.append(body)
        return len(objs)

    font = add(b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica"
               b"/Encoding/WinAnsiEncoding>>")
    kids, contents = [], []
    for n, lines in enumerate(pages, start=1):
        out = ["BT /F1 30 Tf 60 760 Td ({}) Tj ET".format(_esc(title)),
               "BT /F1 15 Tf 60 720 Td (page {} sur {}) Tj ET".format(n, len(pages))]
        y = 660
        for line in lines:
            out.append("BT /F1 13 Tf 60 {} Td ({}) Tj ET".format(y, _esc(line)))
            y -= 24
        # a rule along the top, so the page edge is visible in a frame
        out.append("0.55 0.62 0.70 rg 60 788 475 3 re f")
        stream = "\n".join(out).encode("latin-1")
        contents.append(add(b"<</Length " + str(len(stream)).encode()
                            + b">>stream\n" + stream + b"\nendstream"))
    pages_obj = len(objs) + len(pages) + 1
    for c in contents:
        kids.append(add(
            ("<</Type/Page/Parent {} 0 R/MediaBox[0 0 595 842]"
             "/Resources<</Font<</F1 {} 0 R>>>>/Contents {} 0 R>>")
            .format(pages_obj, font, c).encode()))
    pages_ref = add(("<</Type/Pages/Kids[" + " ".join(
        "{} 0 R".format(k) for k in kids) + "]/Count {}>>".format(len(kids))).encode())
    assert pages_ref == pages_obj, (pages_ref, pages_obj)
    root = add(("<</Type/Catalog/Pages {} 0 R>>".format(pages_ref)).encode())

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += str(i).encode() + b" 0 obj\n" + body + b"\nendobj\n"
    start = len(out)
    out += b"xref\n0 " + str(len(objs) + 1).encode() + b"\n0000000000 65535 f \n"
    for off in offsets:
        out += ("%010d 00000 n \n" % off).encode()
    out += (b"trailer\n<</Size " + str(len(objs) + 1).encode()
            + b"/Root " + str(root).encode() + b" 0 R>>\nstartxref\n"
            + str(start).encode() + b"\n%%EOF\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(out))


# Typography folded down to ASCII. A PDF string here is latin-1, and an
# em-dash is not in it — policing every sentence above would be one typo
# away from a crash, so it happens in one place instead.
PLAIN = {0x2014: "-", 0x2013: "-", 0x2019: "'", 0x2018: "'",
         0x201c: '"', 0x201d: '"', 0x2026: "...", 0x00a0: " "}


def _esc(s: str) -> str:
    """Parentheses and backslashes end a PDF string early."""
    s = s.translate(PLAIN)
    return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


# ---------------------------------------------------------------------
# what the kit holds
# ---------------------------------------------------------------------
def build(force: bool) -> None:
    def want(rel: str) -> "pathlib.Path | None":
        p = KIT / rel
        if p.exists() and not force:
            return None
        return p

    # ---- photographs, for a project or the gallery -------------------
    # The shapes are the point: the first one opens a project page at
    # full width, the rest fall into pairs, and CSS bounds a tall one by
    # its height rather than cropping it.
    shapes = [
        ("photos/01-landscape-1800x1200.jpg", 1800, 1200, "dusk", False),
        ("photos/02-portrait-1200x1800.jpg", 1200, 1800, "ochre", False),
        ("photos/03-square-1400x1400.jpg", 1400, 1400, "moss", False),
        ("photos/04-panorama-2400x800.jpg", 2400, 800, "rose", False),
        ("photos/05-very-tall-900x2400.jpg", 900, 2400, "slate", False),
        ("photos/06-small-400x300.jpg", 400, 300, "sand", False),
        ("photos/07-busy-1600x1000.jpg", 1600, 1000, "ink", True),
        # capitals, because the engine lower-cases an extension and there
        # is a check for it — hers will come off a camera like this
        ("photos/08-SHOUTING-1500x1000.JPG", 1500, 1000, "sea", False),
    ]
    for rel, w, h, hue, busy in shapes:
        p = want(rel)
        if p:
            picture(p, w, h, hue, busy)

    p = want("photos/09-transparent-1200x1200.png")
    if p:
        alpha_png(p, 1200, 1200)

    # ---- a wallpaper, which is the biggest surface on the site -------
    # 1920x1080: a busy source rounds to even numbers, and a kit file
    # whose name disagrees with its pixels is worse than no kit file
    p = want("wallpapers/wallpaper-busy-1920x1080.jpg")
    if p:
        picture(p, 1920, 1080, "ink", True)
    p = want("wallpapers/wallpaper-calm-2000x1125.jpg")
    if p:
        picture(p, 2000, 1125, "sea", False)

    # ---- about me.txt: a portrait above the words --------------------
    p = want("about/portrait-tall-1000x1400.jpg")
    if p:
        picture(p, 1000, 1400, "rose", False)
    p = want("about/portrait-wide-1600x1000.jpg")
    if p:
        picture(p, 1600, 1000, "moss", False)

    # ---- dossiers: shown in the page, never offered as a download ----
    p = want("documents/brochure-4-pages.pdf")
    if p:
        pdf(p, "Brochure", [
            ["A dossier is shown inside its own page.",
             "Nothing on the site links to this file,",
             "so nothing offers to download it.",
             "",
             "Scroll: there are four pages."],
            ["Page two exists so the frame has",
             "something to scroll.",
             "",
             "The icon on the desk is the first",
             "photograph in this folder, if there",
             "is one — otherwise a drawn document."],
            ["Page three.",
             "",
             "A project holding a video is a film,",
             "and a film never shows a dossier.",
             "The panel refuses both in one folder."],
            ["Page four, the last.",
             "",
             "Drop a cover photograph beside this",
             "file and it becomes the icon, while",
             "this stays what the click opens."],
        ])
    p = want("documents/one-pager.pdf")
    if p:
        pdf(p, "One pager", [
            ["A single page, for a project whose",
             "whole story is one sheet.",
             "",
             "Try it with and without a cover",
             "photograph in the same folder."],
        ])

    # ---- films -------------------------------------------------------
    p = want("films/clip-3s.mp4")
    if p:
        clip(p, 3, 640, 360)
    p = want("films/clip-2s.webm")
    if p:
        clip(p, 2, 480, 270)
    p = want("films/affiche-1600x900.jpg")
    if p:
        picture(p, 1600, 900, "dusk", False)

    # ---- files that are lying about what they are -------------------
    # Every one of these used to be accepted and then kill the build on
    # get_image_metadata. The panel has to refuse them, in French, and
    # say what the file really is.
    liars = KIT / "wrong"
    liars.mkdir(parents=True, exist_ok=True)
    if force or not (liars / "actually-a-pdf.jpg").exists():
        shutil.copyfile(KIT / "documents/one-pager.pdf",
                        liars / "actually-a-pdf.jpg")
    if force or not (liars / "actually-a-photograph.mov").exists():
        shutil.copyfile(KIT / "photos/06-small-400x300.jpg",
                        liars / "actually-a-photograph.mov")
    if force or not (liars / "actually-a-photograph.pdf").exists():
        shutil.copyfile(KIT / "photos/06-small-400x300.jpg",
                        liars / "actually-a-photograph.pdf")
    p = liars / "actually-an-iphone-photo.jpg"
    if force or not p.exists():
        # the first bytes of a .heic: an ISO base-media box whose brand
        # says heic. Enough for the panel to recognise and refuse it,
        # which is the whole of what is being tested.
        p.write_bytes(b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00"
                      b"mif1heic" + b"\x00" * 64)
    p = liars / "empty.jpg"
    if force or not p.exists():
        p.write_bytes(b"")
    # a PNG wearing a .jpg name is NOT a liar worth refusing: zola reads
    # it and builds it, so the panel lets it through on purpose
    if force or not (liars / "a-png-named-jpg.jpg").exists():
        shutil.copyfile(KIT / "photos/09-transparent-1200x1200.png",
                        liars / "a-png-named-jpg.jpg")


def report() -> int:
    if not KIT.is_dir():
        print("\n  no kit yet — run: python3 tools/kit.py\n")
        return 1
    total = 0
    print()
    for d in sorted(p for p in KIT.iterdir() if p.is_dir()):
        print("  {}/".format(d.name))
        for f in sorted(d.iterdir()):
            if f.is_file():
                total += f.stat().st_size
                print("    {:>8}  {}".format(_size(f.stat().st_size), f.name))
    print("\n  {} files, {}\n".format(
        sum(1 for _ in KIT.rglob("*") if _.is_file()), _size(total)))
    return 0


def _size(n: int) -> str:
    return "{:.0f} KB".format(n / 1024) if n < 1e6 else "{:.1f} MB".format(n / 1e6)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="make all of it again")
    ap.add_argument("--list", action="store_true", help="say what is there")
    args = ap.parse_args()
    if args.list:
        return report()
    if not shutil.which("ffmpeg"):
        print("\n  this needs ffmpeg:  brew install ffmpeg\n", file=sys.stderr)
        return 1
    build(args.force)
    return report()


if __name__ == "__main__":
    raise SystemExit(main())
