#!/usr/bin/env python3
"""Draw the desktop icon set as SVG.

    python3 tools/icons.py            # write static/img/icons/
    python3 tools/icons.py --check    # validate, write nothing

Icons are code, not binaries, for the same reason the cursors are: an
SVG diff in a pull request is readable, a PNG diff is two blobs.

One silhouette per kind, tinted per colourway. The shape is what makes
the desktop read as a system; the colour is what makes it hers. When
real artwork arrives it simply replaces these — anything named icon.*
in a project folder wins.
"""
import pathlib, sys

OUT = pathlib.Path(__file__).resolve().parent.parent / "static" / "img" / "icons"

# name -> (dark, mid, light)  light falls from the top, always
COLOURS = {
    "amber":  ("#8A5A12", "#D79B2C", "#F0BC55"),
    "rust":   ("#5B1A16", "#9A3327", "#C1543E"),
    "olive":  ("#27351F", "#4A6136", "#6E8A4C"),
    "slate":  ("#1E2733", "#3C5063", "#5C7governs"),
}
COLOURS["slate"] = ("#1E2733", "#3C5063", "#5C7A93")

HEAD = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 160" width="160" height="160">'
TAIL = "</svg>"


def grad(gid, a, b, x2="0", y2="1"):
    return (f'<linearGradient id="{gid}" x1="0" y1="0" x2="{x2}" y2="{y2}">'
            f'<stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/>'
            f"</linearGradient>")


def folder(dark, mid, light):
    return f"""{HEAD}
<defs>{grad("b", light, mid)}{grad("f", mid, dark)}</defs>
<path d="M10 46a9 9 0 0 1 9-9h38a9 9 0 0 1 6.4 2.6L74 50h67a9 9 0 0 1 9 9v62a9 9 0 0 1-9 9H19a9 9 0 0 1-9-9z" fill="url(#b)"/>
<path d="M10 64h140v57a9 9 0 0 1-9 9H19a9 9 0 0 1-9-9z" fill="url(#f)"/>
<path d="M10 64h140v3H10z" fill="{light}" opacity=".55"/>
{TAIL}"""


def doc(dark, mid, light):
    return f"""{HEAD}
<defs>{grad("p", "#FFFFFF", "#E4E0D8")}</defs>
<path d="M30 16h62l38 38v86a8 8 0 0 1-8 8H30a8 8 0 0 1-8-8V24a8 8 0 0 1 8-8z" fill="url(#p)"/>
<path d="M92 16l38 38H100a8 8 0 0 1-8-8z" fill="{mid}" opacity=".35"/>
<g fill="{dark}" opacity=".34">
<rect x="40" y="74" width="74" height="5" rx="2.5"/>
<rect x="40" y="90" width="74" height="5" rx="2.5"/>
<rect x="40" y="106" width="48" height="5" rx="2.5"/>
</g>
{TAIL}"""


def photo(dark, mid, light):
    return f"""{HEAD}
<defs>{grad("s", light, mid)}</defs>
<rect x="22" y="20" width="116" height="124" rx="4" fill="#FBFAF7"/>
<rect x="31" y="29" width="98" height="78" fill="url(#s)"/>
<path d="M31 107l27-30 21 24 14-15 36 21H31z" fill="{dark}" opacity=".45"/>
<circle cx="106" cy="48" r="10" fill="#FFFFFF" opacity=".75"/>
{TAIL}"""


def movie(dark, mid, light):
    holes = "".join(
        f'<rect x="{x}" y="{y}" width="11" height="12" rx="2.5" fill="#FBFAF7" opacity=".9"/>'
        for x in (18, 131) for y in (36, 58, 80, 102)
    )
    return f"""{HEAD}
<defs>{grad("m", mid, dark)}</defs>
<rect x="10" y="26" width="140" height="108" rx="8" fill="{dark}"/>
<rect x="36" y="36" width="88" height="88" rx="3" fill="url(#m)"/>
<path d="M70 62l30 18-30 18z" fill="#FBFAF7" opacity=".92"/>
{holes}
{TAIL}"""


def window(dark, mid, light):
    """The System message dialog, as an icon. Her proto puts one on the
    desktop for contact — a window you can pick up."""
    return f"""{HEAD}
<rect x="14" y="34" width="132" height="92" rx="2" fill="#C0C0C0" stroke="#000" stroke-width="2"/>
<path d="M17 37h126v4H17z" fill="#F2F2F2"/>
<rect x="20" y="40" width="120" height="18" fill="#000082"/>
<rect x="124" y="43" width="12" height="12" fill="#C0C0C0" stroke="#000" stroke-width="1.5"/>
<path d="M127 46l6 6M133 46l-6 6" stroke="#000" stroke-width="1.5"/>
<g fill="#6E6E6E">
<rect x="26" y="68" width="52" height="5" rx="1"/>
<rect x="26" y="82" width="68" height="5" rx="1"/>
</g>
<g fill="#C0C0C0" stroke="#000" stroke-width="1.5">
<rect x="36" y="100" width="38" height="16" rx="1"/>
<rect x="86" y="100" width="38" height="16" rx="1"/>
</g>
{TAIL}"""


SHAPES = {"folder": folder, "doc": doc, "photo": photo, "movie": movie, "window": window}
# one colourway each is enough for a demo; folders get the full set
PLAN = [("folder", c) for c in COLOURS] + [
    ("doc", "slate"), ("photo", "rust"), ("movie", "slate"), ("window", "slate"),
]


def build(write=True):
    made = []
    for shape, colour in PLAN:
        svg = SHAPES[shape](*COLOURS[colour])
        assert svg.count("<svg") == 1 and svg.rstrip().endswith("</svg>")
        name = f"{shape}.svg" if (shape, colour) == PLAN[0] or shape != "folder" else f"{shape}-{colour}.svg"
        if shape == "folder" and colour == "amber":
            name = "folder.svg"
        if write:
            OUT.mkdir(parents=True, exist_ok=True)
            (OUT / name).write_text(svg)
        made.append(name)
    return made




# ---------------------------------------------------------------------
# Backdrops
#
# A wallpaper as SVG rather than a photograph: a duotone wash, real film
# grain from feTurbulence, and a vignette. About 1 KB each instead of
# 380 KB, crisp at any size, and the grain is computed rather than
# compressed — so it never bands.
#
# These are scaffolding. When her photographs arrive they replace the
# `wallpaper` path in a section's front matter and none of this runs.
# ---------------------------------------------------------------------

WALLS = {
    "home":       ("#8A4A2E", "#C77A4A", "#3A2018"),
    "da":         ("#2A1410", "#7A2E22", "#140A08"),
    "graphic":    ("#6E6A63", "#A6A096", "#2E2C28"),
    "pellicules": ("#141211", "#2A2622", "#060505"),
}


def backdrop(deep, lift, edge, grain=".42", freq="0.82"):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" \
preserveAspectRatio="xMidYMid slice" width="1600" height="900">
<defs>
<linearGradient id="w" x1="0.1" y1="0" x2="0.9" y2="1">
<stop offset="0" stop-color="{lift}"/><stop offset=".55" stop-color="{deep}"/>
<stop offset="1" stop-color="{edge}"/></linearGradient>
<radialGradient id="v" cx=".5" cy=".42" r=".78">
<stop offset=".45" stop-color="#000" stop-opacity="0"/>
<stop offset="1" stop-color="#000" stop-opacity=".46"/></radialGradient>
<filter id="g" x="0" y="0" width="100%" height="100%">
<feTurbulence type="fractalNoise" baseFrequency="{freq}" numOctaves="4" stitchTiles="stitch"/>
<feColorMatrix type="saturate" values="0"/>
<feComponentTransfer><feFuncA type="linear" slope="{grain}"/></feComponentTransfer>
</filter>
</defs>
<rect width="1600" height="900" fill="url(#w)"/>
<rect width="1600" height="900" filter="url(#g)" opacity=".55"/>
<rect width="1600" height="900" fill="url(#v)"/>
</svg>"""


def build_walls(write=True):
    made = []
    for name, cols in WALLS.items():
        svg = backdrop(*cols)
        assert svg.count("<svg") == 1 and svg.rstrip().endswith("</svg>")
        if write:
            OUT.parent.mkdir(parents=True, exist_ok=True)
            (OUT.parent / f"wall-{name}.svg").write_text(svg)
        made.append(f"wall-{name}.svg")
    return made


if __name__ == "__main__":
    write = "--check" not in sys.argv
    names = build(write) + build_walls(write)
    print("  " + "\n  ".join(sorted(set(names))))
