#!/usr/bin/env python3
"""Fetch stand-in photographs, and be able to delete every one of them.

    python3 tools/placeholders.py            # fetch what is missing
    python3 tools/placeholders.py --force    # refetch everything
    python3 tools/placeholders.py --check    # report, write nothing
    python3 tools/placeholders.py --purge    # delete every file listed here

Real photographs, because procedural noise cannot answer the questions
that matter: does white text survive a bright sky, does a masonry of real
aspect ratios hold, do the folder icons read over a busy wallpaper.

From Lorem Picsum, which serves Unsplash photography. Seeded, so the same
seed returns the same photograph on every machine and every build — a
layout change is then the only variable when judging a layout change.

NONE OF THIS SHIPS. It is scaffolding for a site that carries no client's
name while `live = false`. Every path is listed in PLAN, so --purge
removes the lot in one command with nothing left behind to wonder about.
"""
import argparse
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PICSUM = "https://picsum.photos/seed/{seed}/{w}/{h}"

# (path relative to the repo, seed, width, height)
PLAN: list[tuple[str, str, int, int]] = [
    # ---- wallpapers: the largest surface, and the one that decides
    #      whether white text and the icons survive a real photograph ----
    # no wallpaper for pellicules: body.gallery is a deliberate dark room,
    # so one declared there would be fetched, shipped and never rendered
    ("static/img/wall-home.jpg",       "bureau-home",   2000, 1125),
    ("content/da/wallpaper.jpg",                "bureau-da",      2000, 1125),
    ("content/graphic-design/wallpaper.jpg",    "bureau-gd",      2000, 1125),
    ("content/travail-selectionne/wallpaper.jpg", "bureau-atelier", 2000, 1125),
]

# ---- pellicules: varied proportions, because that is what makes a
#      masonry hard. Portraits, landscapes and squares together. ----
_GALLERY = [
    ("argentique-01", 1200, 1800), ("argentique-02", 1600, 1067),
    ("argentique-03", 1400, 1400), ("argentique-04", 1100, 1650),
    ("argentique-05", 1800, 1200), ("argentique-06", 1200, 1600),
    ("argentique-07", 1500, 1000), ("argentique-08", 1300, 1733),
    ("argentique-09", 1400, 1050), ("argentique-10", 1200, 1200),
    ("argentique-11", 1000, 1500), ("argentique-12", 1700, 1133),
]
for _i, (_seed, _w, _h) in enumerate(_GALLERY, start=1):
    PLAN.append((f"content/pellicules/{_i:02d}.jpg", _seed, _w, _h))

# ---- project pages ----
_PROJECTS = [
    "graphic-design/grocery-list", "graphic-design/calendar",
    "graphic-design/douze-regards", "graphic-design/atelier-mirabelle/terrasses",
    "graphic-design/atelier-mirabelle/facades", "graphic-design/logofolio/marks",
    "graphic-design/logofolio/wordmarks", "da/theodora",
    "da/confidence-glow", "da/maison-cosette/jojo",
    "da/maison-cosette/lookbook",
    "travail-selectionne/nocturne", "travail-selectionne/vitrine-hiver",
    "travail-selectionne/papier-calque",
]
# A seed draws whatever it draws. Where the draw did not suit the page
# it sits on, the seed is chosen by hand here instead.
RESEEDED = {
    "content/graphic-design/atelier-mirabelle/terrasses/01.jpg": "terrasses-01",
    # the first draw carried an airline's livery on a tail fin
    "content/travail-selectionne/nocturne/01.jpg": "nocturne-01",
    # first draw: a sportswear logo on a shoe, over a rooftop drop.
    # second: an identifiable face, which no other placeholder here has.
    "content/travail-selectionne/vitrine-hiver/01.jpg": "vitrine-03",
}

for _p in _PROJECTS:
    _name = _p.replace("/", "-")
    for _n in (1, 2):
        _rel = f"content/{_p}/{_n:02d}.jpg"
        PLAN.append((_rel, RESEEDED.get(_rel, f"{_name}-{_n}"), 1800, 1200))


def fetch(path: pathlib.Path, url: str) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as r:
        data = r.read()
    if len(data) < 1024:
        raise RuntimeError(f"suspiciously small response for {url}")
    path.write_bytes(data)
    return len(data)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true", help="refetch what is already there")
    ap.add_argument("--check", action="store_true", help="report, write nothing")
    ap.add_argument("--purge", action="store_true", help="delete every file listed")
    args = ap.parse_args()

    if args.purge:
        gone = 0
        for rel, _seed, _w, _h in PLAN:
            p = ROOT / rel
            if p.exists():
                p.unlink()
                gone += 1
        print(f"  deleted {gone} placeholder(s); {len(PLAN) - gone} were already absent")
        return 0

    if args.check:
        here = [rel for rel, *_ in PLAN if (ROOT / rel).exists()]
        total = sum((ROOT / rel).stat().st_size for rel in here)
        print(f"  {len(here)}/{len(PLAN)} present, {total / 1e6:.1f} MB")
        for rel, *_ in PLAN:
            if not (ROOT / rel).exists():
                print(f"    missing: {rel}")
        return 0

    got = skipped = 0
    total = 0
    for rel, seed, w, h in PLAN:
        p = ROOT / rel
        if p.exists() and not args.force:
            skipped += 1
            total += p.stat().st_size
            continue
        try:
            total += fetch(p, PICSUM.format(seed=seed, w=w, h=h))
            got += 1
        except Exception as exc:                       # noqa: BLE001
            print(f"    FAILED {rel}: {exc}", file=sys.stderr)
            return 1
    print(f"  fetched {got}, kept {skipped}, {total / 1e6:.1f} MB total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
