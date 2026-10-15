#!/usr/bin/env python3
"""Draw the cursor PNGs from ASCII art.

    python3 tools/cursors.py          # regenerate static/img/cursors/
    python3 tools/cursors.py --show   # preview in the terminal
    python3 tools/cursors.py --check  # verify the art, write nothing

The art lives here as text on purpose: a PNG diff in a pull request tells
you nothing, an ASCII diff shows exactly which pixels moved.

    #  black outline      *  white fill      .  transparent

Every hand has four fingers and a thumb. Count them before committing.
Hotspots live in the CURSORS block of static/css/site.css and are in
pixels of the 16x16 art — if you move a visual anchor, move the hotspot.
"""
import zlib, struct, sys, pathlib

SIZE = 16
OUT = pathlib.Path(__file__).resolve().parent.parent / "static" / "img" / "cursors"

ART = {
"arrow": [
 "#...............",
 "##..............",
 "#*#.............",
 "#**#............",
 "#***#...........",
 "#****#..........",
 "#*****#.........",
 "#******#........",
 "#*******#.......",
 "#********#......",
 "#*********#.....",
 "#*****#####.....",
 "#**#**#.........",
 "#*#.#**#........",
 "##..#**#........",
 "....####........",
],
"point": [
 "...##...........",
 "..#**#..........",
 "..#**#..........",
 "..#**#..........",
 "..#**#..........",
 "..#**##**#**#...",
 "..#**##**#**#**#",
 "..#**#*********#",
 ".##************#",
 "#**#***********#",
 "#**#***********#",
 "#**************#",
 ".#************#.",
 ".#***********#..",
 "..#*********#...",
 "..##########....",
],
"open": [
 "......#**#......",
 "...#**#**#**#...",
 "...#**#**#**#...",
 "...#**#**#**#**#",
 "...#**#**#**#**#",
 "...#**#**#**#**#",
 "#**#***********#",
 "#**************#",
 "#**************#",
 ".#************#.",
 ".#************#.",
 "..#**********#..",
 "..#**********#..",
 "...#********#...",
 "...#********#...",
 "....########....",
],
"grab": [
 "................",
 "...##.##.##.##..",
 "..#**#**#**#**#.",
 ".#************#.",
 "#**************#",
 "#**************#",
 "#**#############",
 "#**#***********#",
 "#**#***********#",
 "#**#############",
 "#**************#",
 ".#************#.",
 ".#***********#..",
 "..#*********#...",
 "...#*******#....",
 "....#######.....",
],
"no": [
 "................",
 "....########....",
 "...###****###...",
 "..###*******##..",
 ".#####*******##.",
 ".##*###******##.",
 ".#***###******#.",
 ".#****###*****#.",
 ".#*****###****#.",
 ".#******###***#.",
 ".##******###*##.",
 ".##*******#####.",
 "..##*******###..",
 "...###****###...",
 "....########....",
 "................",
],
}
PIXEL = {"#": (0, 0, 0, 255), "*": (255, 255, 255, 255)}


def check():
    for name, art in ART.items():
        assert len(art) == SIZE, f"{name}: {len(art)} rows, want {SIZE}"
        for i, row in enumerate(art):
            assert len(row) == SIZE, f"{name} row {i}: {len(row)} wide, want {SIZE}"
            bad = set(row) - set("#*.")
            assert not bad, f"{name} row {i}: unknown {bad}"
    # a hand is four fingers and a thumb: five fills side by side somewhere
    for name in ("open", "grab", "point"):   # the no-entry sign is not a hand
        widest = max(len([g for g in r.replace("#", " ").split() if g]) for r in ART[name])
        assert widest >= 5, f"{name}: only {widest} digits, a hand has five"
    return True


def show():
    block = {"#": "█", "*": "░", ".": "·"}
    for name, art in ART.items():
        print(f"\n  {name}")
        for row in art:
            print("   " + "".join(block[c] for c in row))


def png(path, art, scale):
    side = SIZE * scale
    raw = b"".join(
        b"\x00" + b"".join(
            bytes(PIXEL.get(art[y // scale][x // scale], (0, 0, 0, 0)))
            for x in range(side))
        for y in range(side))

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", side, side, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b""))


if __name__ == "__main__":
    check()
    if "--check" in sys.argv:
        print("art ok")
    elif "--show" in sys.argv:
        show()
    else:
        OUT.mkdir(parents=True, exist_ok=True)
        for name, art in ART.items():
            png(OUT / f"{name}.png", art, 1)
            png(OUT / f"{name}@2x.png", art, 2)
            print(f"  {name}.png 16x16   {name}@2x.png 32x32")
