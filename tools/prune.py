#!/usr/bin/env python3
"""Drop what the built site carries but never asks for.

    python3 tools/prune.py            # delete them
    python3 tools/prune.py --check    # say what would go, delete nothing

Zola copies every photograph that sits next to a content file into the
output, and once more into each translated output — byte for byte. The
templates never serve those: they serve what `resize_image` made. So a
deployed site carries the originals twice over and nobody ever requests
them.

On the demo that is 19.5 MB of 35.3 MB. It stops being a curiosity the
day the placeholders become real camera files: sixty photographs at 8 MB
is some 300 MB, doubled, against a GitHub Pages soft limit of 1 GB.

THIS RUNS IN CI, between `zola build` and the upload. It never runs on
her machine — `preview.sh` does not call it, and it only ever touches
`public/`, which is generated and git-ignored. Nothing in `content/` is
read, let alone removed; the originals stay in the repository, which is
where they belong.

The safety is not the matcher, it is the check after it: every url the
built pages ask for must still exist when this is done, or it exits
non-zero and the artifact is never uploaded.
"""
from __future__ import annotations   # macOS ships 3.9

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "public"

# Only ever media. Never html, css, js, fonts, robots.txt — those are the
# site itself, and a matcher that misses one of those breaks the page
# rather than wasting a few kilobytes.
MEDIA = {".pdf",
         ".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif",
         ".mp4", ".webm", ".mov", ".m4v"}


def asked_for(out: pathlib.Path) -> set[str]:
    """Every url the built pages and the stylesheet reference.

    A url is recorded WITHOUT its query or fragment, because what is on
    disk has neither. The document frame asks for

        .../da/grocery/dossier.pdf#toolbar=0&navpanes=0

    and with the fragment left on, `wanted()` matched nothing, the PDF was
    pruned, and the deployed page framed a 404. The check below that is
    meant to refuse exactly that missed it too: `.pdf#toolbar=0...` is not
    a media suffix, so it skipped the url instead of failing on it. One
    strip here, and both of them are right.
    """
    urls: set[str] = set()

    def note(u: str) -> None:
        u = u.split("#")[0].split("?")[0]
        if u:
            urls.add(u)

    for p in list(out.rglob("*.html")) + list(out.rglob("*.css")):
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r'(?:src|href)="([^"]+)"', text):
            note(m.group(1))
        for m in re.finditer(r'url\(\s*[\'"]?([^)\'"]+)', text):
            note(m.group(1))
        # srcset is a comma-separated list, each with a width descriptor
        for m in re.finditer(r'srcset="([^"]+)"', text):
            for part in m.group(1).split(","):
                note(part.strip().split(" ")[0])
    return urls


def wanted(rel: str, urls: set[str]) -> bool:
    """Is this file asked for?

    Matched by SUFFIX against the whole relative path, which sidesteps
    base_url entirely — the same build serves /myBureau/da/x.jpg today and
    /da/x.jpg from her own domain later, and a matcher that parsed the
    prefix would quietly stop matching on the day that changes.

    The whole path, never the bare file name: `da/theodora/01.jpg` and
    `en/da/theodora/01.jpg` are different files and have to be judged
    separately, or the English copy is kept because the French one is used.
    """
    return any(u.endswith("/" + rel) or u == rel for u in urls)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="report, delete nothing")
    args = ap.parse_args()

    if not OUT.is_dir() or not any(OUT.rglob("*.html")):
        print("  no built site in public/ — run `zola build` first", file=sys.stderr)
        return 1

    # Nothing built by the image pipeline is ever a candidate. Those are
    # the files the pages actually load, and a matcher that went wrong on
    # them would delete the visible site rather than waste a few MB. By
    # construction the only things that can go are SOURCE originals that
    # Zola copied in beside the content.
    urls = asked_for(OUT)
    keep, drop, generated = [], [], 0
    for p in sorted(OUT.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in MEDIA:
            continue
        rel = str(p.relative_to(OUT))
        if rel.split("/")[0] == "processed_images":
            generated += 1
            continue
        (keep if wanted(rel, urls) else drop).append(p)

    freed = sum(p.stat().st_size for p in drop)
    total = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())

    if args.check:
        print(f"\n  {generated} generated file(s) never considered")
        print(f"  {len(drop)} file(s) shipped but never requested, {freed / 1e6:.1f} MB "
              f"of {total / 1e6:.1f} MB")
        for p in sorted(drop, key=lambda x: -x.stat().st_size)[:10]:
            print(f"    {p.stat().st_size / 1e6:6.2f} MB  {p.relative_to(OUT)}")
        if len(drop) > 10:
            print(f"    … and {len(drop) - 10} more")
        print()
        return 0

    for p in drop:
        p.unlink()
    # directories that held nothing else
    for d in sorted((d for d in OUT.rglob("*") if d.is_dir()),
                    key=lambda x: -len(x.parts)):
        if not any(d.iterdir()):
            d.rmdir()

    # ---- the part that matters ------------------------------------
    # A matcher that is too eager deletes a photograph the site shows,
    # and the page still builds, still deploys, and is simply broken. So
    # every media url the pages ask for is resolved against the tree we
    # are about to hand over, and anything that cannot be found stops the
    # run — the artifact is never uploaded.
    #
    # Resolved by suffix, like `wanted`, so this keeps working the day the
    # site moves off a github.io subpath onto her own domain.
    on_disk = {str(p.relative_to(OUT)) for p in OUT.rglob("*") if p.is_file()}
    missing = []
    for u in sorted(urls):
        tail = u                      # already stripped — see asked_for
        if pathlib.PurePosixPath(tail).suffix.lower() not in MEDIA:
            continue
        if not any(tail.endswith("/" + d) or tail == d for d in on_disk):
            missing.append(tail)
    if missing:
        print(f"  REFUSED: {len(missing)} url(s) the site asks for are not there",
              file=sys.stderr)
        for m in missing[:10]:
            print(f"    {m}", file=sys.stderr)
        return 1

    after = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"  pruned {len(drop)} unrequested file(s), {freed / 1e6:.1f} MB; "
          f"{after / 1e6:.1f} MB left, {len(keep)} media file(s) kept, "
          f"{generated} generated file(s) never considered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
