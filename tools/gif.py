#!/usr/bin/env python3
"""Make a looping GIF from photographs she picked.

    python3 tools/gif.py content/graphic-design/douze-regards/icon.gif \\
        content/graphic-design/douze-regards/01.jpg 02.jpg 03.jpg

WHAT IT IS FOR. A dense piece of work — a twenty-page dossier, a PDF —
has nothing to show on a desk but a grey document symbol. A few of its
pages looping say more than any icon could, and the click still opens
the document. Drop the result in as `icon.gif` and the desk animates;
nothing else has to change, because an icon she names is served whole
rather than resized.

WHY FFMPEG AND NOT PYTHON. Reading a JPEG is the hard part, not writing
a GIF, and there is no decoder in the standard library. ffmpeg is
already what kit.py draws with. It is NOT on her machine by default —
see `have_ffmpeg()`, which is what the panel asks before offering this
at all, so she is told rather than shown a failure.

TWO PASSES, WHICH IS NOT OPTIONAL. A GIF holds 256 colours. Letting
ffmpeg pick them frame by frame gives a different palette per frame and
the whole thing seethes. So: one pass to read every frame and choose
one palette for all of them, a second to write the file against it.
"""
from __future__ import annotations   # macOS ships 3.9

import argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent

# An icon is drawn about 180 wide, so this is still more than a retina
# screen asks for. It is 280 rather than the 360 the still thumbnails
# use because a GIF pays for every frame: the same four photographs
# came out at 210 KB wide and 131 KB here, for a picture nobody sees
# larger than a stamp. Frames are the bigger lever still — four is
# plenty, and the guide says so to her.
WIDTH = 280
DELAY = 0.7


class Refused(Exception):
    """Something she can fix, said in a sentence."""


def have_ffmpeg() -> bool:
    """Is the one thing this needs installed?

    The panel asks this before offering to make a gif. Her supported
    path is Homebrew, GitHub Desktop and a double-click; ffmpeg is not
    part of it, so the honest answer when it is missing is to say so
    and offer the one line that fixes it.
    """
    return shutil.which("ffmpeg") is not None


def make(out: pathlib.Path, frames: list, width: int = WIDTH,
         delay: float = DELAY) -> pathlib.Path:
    """Write `out` as a looping GIF of `frames`, in the order given."""
    if not have_ffmpeg():
        raise Refused("ffmpeg n'est pas installé — c'est lui qui fabrique"
                      " le GIF. Dans le Terminal : brew install ffmpeg")
    if len(frames) < 2:
        raise Refused("il faut au moins deux images pour que ça bouge.")
    missing = [str(f) for f in frames if not pathlib.Path(f).is_file()]
    if missing:
        raise Refused("je ne trouve pas : " + ", ".join(missing))
    if delay <= 0:
        raise Refused("une image doit rester à l'écran un instant.")

    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mybureau-gif-") as tmp:
        tmp = pathlib.Path(tmp)
        # The concat demuxer, because the image2 one wants a numbered
        # pattern and these are whatever she called them. Paths are
        # written absolute and quoted, so a space or an apostrophe in a
        # folder name does not end the argument early.
        listing = tmp / "frames.txt"
        lines = []
        for f in frames:
            p = pathlib.Path(f).resolve()
            lines.append("file '{}'".format(str(p).replace("'", r"'\''")))
            lines.append("duration {}".format(delay))
        # concat repeats the last entry's file without its duration
        # unless it is named twice; without this the final frame
        # flashes past and the loop stutters at the seam.
        last = pathlib.Path(frames[-1]).resolve()
        lines.append("file '{}'".format(str(last).replace("'", r"'\''")))
        listing.write_text("\n".join(lines) + "\n", encoding="utf-8")

        scale = "scale={}:-1:flags=lanczos".format(width)
        palette = tmp / "palette.png"

        _run(["ffmpeg", "-hide_banner", "-loglevel", "error",
              "-f", "concat", "-safe", "0", "-i", str(listing),
              "-vf", scale + ",palettegen=stats_mode=diff",
              "-y", str(palette)])

        _run(["ffmpeg", "-hide_banner", "-loglevel", "error",
              "-f", "concat", "-safe", "0", "-i", str(listing),
              "-i", str(palette),
              "-lavfi", scale + " [x]; [x][1:v] paletteuse=dither=bayer",
              "-loop", "0",            # 0 means forever
              "-y", str(out)])

    if not out.is_file() or out.stat().st_size == 0:
        raise Refused("le GIF n'a pas été écrit.")
    return out


def _run(args: list) -> None:
    done = subprocess.run(args, capture_output=True, text=True)
    if done.returncode != 0:
        raise Refused("ffmpeg a refusé : " + done.stderr.strip()[-300:])


def loops(path: pathlib.Path) -> bool:
    """Does this GIF carry the block that makes it repeat?

    The NETSCAPE2.0 application extension is the whole of what says
    "play again". A GIF written without it animates once and stops,
    which on a desk looks like a still that twitched when the page
    loaded.
    """
    return b"NETSCAPE2.0" in path.read_bytes()[:4096]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("out", help="the .gif to write")
    ap.add_argument("frames", nargs="+", help="the images, in order")
    ap.add_argument("--width", type=int, default=WIDTH)
    ap.add_argument("--delay", type=float, default=DELAY,
                    help="seconds each image stays up")
    a = ap.parse_args()
    try:
        out = make(pathlib.Path(a.out), a.frames, a.width, a.delay)
    except Refused as exc:
        print("\n  {}\n".format(exc), file=sys.stderr)
        return 1
    print("\n  {} — {} images, {:.0f} KB, {}\n".format(
        a.out, len(a.frames), out.stat().st_size / 1024,
        "en boucle" if loops(out) else "SANS BOUCLE"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
