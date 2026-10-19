#!/usr/bin/env python3
"""Languages: what is missing, and the files to fill in.

    python3 tools/i18n.py            # what is still untranslated
    python3 tools/i18n.py --sync     # create the missing files
    python3 tools/i18n.py --prune    # delete translations of pages that are gone

ADDING A LANGUAGE is two edits in config.toml and nothing else:

    [languages.es]
    title = "myBureau"

    [languages.es.translations]
    ...copy the [translations] block and translate the right-hand side...

Then `--sync` writes a Spanish copy of every page, each one a normal
markdown file to edit. No template is touched, no code changes, no build
step is added. If adding a language ever means editing a template, the
design has failed and that is a bug worth reporting.

TWO KINDS OF TEXT, TWO PLACES
  - words the engine says (buttons, errors, "back to")  -> config.toml
  - words she writes (titles, project text)             -> content/*.md

NOTHING FALLS BACK BY ITSELF, SO --sync FILLS THE GAPS
  A word with no translation fails the build — Zola will not guess. A
  page with no translation simply is not in that language, and drops off
  that language's desktop without a word of complaint.
  So --sync writes both: every missing key into the language's table and
  every missing page into content/, each one still in the default
  language and marked TODO. The site builds and works from that moment;
  translating is then editing text in place, with --check as the list of
  what is left. Nothing is ever overwritten.
"""
from __future__ import annotations   # macOS ships 3.9; `X | Y` needs 3.10

import argparse
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config.toml"
CONTENT = ROOT / "content"

# `title = "x"` / `key = 'x'`, at the start of a line only, so a right-hand
# side containing an = sign cannot be mistaken for a second key.
KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=", re.M)
SECTION = re.compile(r"^\[([^\]]+)\]\s*$", re.M)


def sections(text: str) -> dict[str, str]:
    """TOML split into top-level tables. Not a parser — tomllib would be
    one, but this has to report the ORDER keys appear in so a translator
    can read the two blocks side by side."""
    out, name, start = {}, None, 0
    for m in SECTION.finditer(text):
        if name is not None:
            out[name] = text[start:m.start()]
        name, start = m.group(1), m.end()
    if name is not None:
        out[name] = text[start:]
    return out


def languages(text: str) -> list[str]:
    default = re.search(r'^default_language\s*=\s*"([^"]+)"', text, re.M)
    extra = re.findall(r"^\[languages\.([A-Za-z0-9_-]+)\]\s*$", text, re.M)
    return ([default.group(1)] if default else ["fr"]) + extra


def pages(lang: str, default: str) -> dict[str, pathlib.Path]:
    """Every content file in one language, keyed by its path with the
    language marker removed — so the same page in two languages collides
    on one key, which is exactly what we want to compare."""
    out = {}
    for p in CONTENT.rglob("*.md"):
        stem = p.name[:-3]                       # index / index.en / _index.fr
        base, _, marker = stem.rpartition(".")
        if base == "":                           # no marker: default language
            base, marker = stem, default
        if marker == lang:
            out[str(p.parent.relative_to(CONTENT) / base)] = p
    return out


# The three places a key is asked for. Each is a declaration, so each
# can be checked: a key nobody defined renders as the key itself —
# visible, but only to someone who reads that language.
IN_TEMPLATE = re.compile(r"""trans\(\s*key\s*=\s*['"]([A-Za-z0-9_]+)['"]""")
IN_CODE = re.compile(r"\b(?:say|no|tell)\(([^)]*)\)")   # a ternary inside counts
IN_CONFIG = re.compile(r'\bkey\s*=\s*"([A-Za-z0-9_]+)"')             # nav_extra
BROWSER = re.compile(r"browser_strings\s*=\s*\[(.*?)\]", re.S)         # the JSON blob


def used_keys() -> dict[str, list[str]]:
    """Every key the site asks for, and where it asks."""
    out: dict[str, list[str]] = {}

    def note(key: str, where: pathlib.Path | str) -> None:
        name = str(where.relative_to(ROOT)) if isinstance(where, pathlib.Path) else where
        out.setdefault(key, []).append(name)

    for f in (ROOT / "templates").rglob("*.html"):
        for k in IN_TEMPLATE.findall(f.read_text(encoding="utf-8")):
            note(k, f)
    for f in (ROOT / "src").rglob("*.ts"):
        for call in IN_CODE.findall(f.read_text(encoding="utf-8")):
            for k in re.findall(r'"([A-Za-z0-9_]+)"', call):
                note(k, f)

    body = CONFIG.read_text(encoding="utf-8")
    for k in IN_CONFIG.findall(body):
        note(k, "config.toml (nav_extra)")
    blob = BROWSER.search(body)
    if blob:
        for k in re.findall(r'"([A-Za-z0-9_]+)"', blob.group(1)):
            note(k, "config.toml (browser_strings)")
    return out


def report(text: str) -> int:
    langs = languages(text)
    default, others = langs[0], langs[1:]
    tables = sections(text)
    base_keys = list(dict.fromkeys(KEY.findall(tables.get("translations", ""))))

    # A key asked for but never defined is a bug, not a translation gap.
    used = used_keys()
    undefined = {k: v for k, v in used.items() if k not in base_keys}

    unused = sorted(k for k in base_keys if k not in used)

    print(f"\n  default language: {default}")
    if unused:
        print("\n  DEFINED BUT NEVER ASKED FOR — delete them, or they are typos"
              " for a key that is:")
        for k in unused:
            print(f"    {k}")
    if undefined:
        print("\n  USED BUT NOT DEFINED — these render as the key itself:")
        for k, where in sorted(undefined.items()):
            print(f"    {k}   ({', '.join(sorted(set(where)))})")
        print("    Add them to [translations] in config.toml.")
    if not others:
        print("  no other language configured — see the top of this file\n")
        return 0

    gaps = 0
    for lang in others:
        table = tables.get(f"languages.{lang}.translations", "")
        have = set(KEY.findall(table))
        missing = [k for k in base_keys if k not in have]
        extra = sorted(have - set(base_keys))
        todo = [k for k in base_keys if k in have and TODO.search(line_of(table, k) or "")]

        base_pages = pages(default, default)
        theirs = pages(lang, default)
        no_page = sorted(set(base_pages) - set(theirs))
        orphan = sorted(set(theirs) - set(base_pages))

        print(f"\n  [{lang}]")
        done = len(base_keys) - len(missing) - len(todo)
        print(f"    words  {done}/{len(base_keys)} translated")
        for k in missing:
            print(f"             MISSING — the build will fail: {k}")
        for k in todo:
            print(f"             still in {default}: {k}")
        for k in extra:
            print(f"             not a real key (typo?): {k}")
        print(f"    pages  {len(theirs)}/{len(base_pages)} exist")
        for k in no_page:
            print(f"             absent from the {lang} site: {k}")
        for k in orphan:
            print(f"             no longer in {default} (--prune): {k}")

        gaps += len(missing) + len(extra) + len(todo) + len(no_page) + len(orphan)

    if gaps:
        print(f"\n  {gaps} gap(s). --sync creates the missing pages;"
              f" missing words are edited in config.toml.\n")
    else:
        print("\n  nothing missing.\n")

    # Untranslated is a stage of work. Undefined is a mistake — only that
    # fails, so this is safe to run in CI while a translation is half done.
    return 1 if undefined else 0


TODO = re.compile(r"#\s*TODO")


def line_of(table: str, key: str) -> "str | None":
    m = re.search(rf"^{re.escape(key)}\s*=.*$", table, re.M)
    return m.group(0) if m else None


def fill_table(text: str, lang: str, default: str) -> str:
    """Copy whatever keys the language has not got, still in the default
    language and marked TODO so --check can list them. Existing lines are
    never touched — a translation already made is not up for revision."""
    tables = sections(text)
    base = tables.get("translations", "")
    head = f"[languages.{lang}.translations]"
    if head[1:-1] not in tables:
        print(f"    no {head} in config.toml — add it (see the top of this file)")
        return text

    have = set(KEY.findall(tables[head[1:-1]]))
    added = []
    for k in dict.fromkeys(KEY.findall(base)):
        if k in have:
            continue
        line = line_of(base, k)
        if line is None:
            continue
        added.append(f"{line.rstrip()}   # TODO translate")
        print(f"    {lang}: added {k}")
    if not added:
        return text

    block = tables[head[1:-1]].rstrip("\n")
    return text.replace(head + block, head + block + "\n" + "\n".join(added), 1)


def sync(text: str) -> int:
    langs = languages(text)
    default, others = langs[0], langs[1:]
    if not others:
        print("\n  no other language configured — nothing to create\n")
        return 0

    text_now = text
    for lang in others:
        text_now = fill_table(text_now, lang, default)
    if text_now != text:
        CONFIG.write_text(text_now, encoding="utf-8")

    made = 0
    for lang in others:
        base_pages = pages(default, default)
        theirs = pages(lang, default)
        for key in sorted(set(base_pages) - set(theirs)):
            src = base_pages[key]
            dst = src.with_name(f"{src.stem}.{lang}.md")
            if dst.exists():                      # never overwrite a translation
                continue
            shutil.copyfile(src, dst)
            print(f"    created {dst.relative_to(ROOT)}")
            made += 1

    print(f"\n  created {made} file(s), in the default language, ready to translate.")
    print("  Photographs are not copied — a page in any language shows the same ones.\n")
    return 0


def prune(text: str) -> int:
    langs = languages(text)
    default, others = langs[0], langs[1:]
    gone = 0
    for lang in others:
        base_pages = pages(default, default)
        for key in sorted(set(pages(lang, default)) - set(base_pages)):
            p = pages(lang, default)[key]
            p.unlink()
            print(f"    deleted {p.relative_to(ROOT)}")
            gone += 1
    print(f"\n  deleted {gone} translation(s) whose {default} page no longer exists.\n")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sync", action="store_true", help="create the missing pages")
    ap.add_argument("--prune", action="store_true",
                    help="delete translations whose original is gone")
    ap.add_argument("--check", action="store_true", help="report (the default)")
    args = ap.parse_args()

    text = CONFIG.read_text(encoding="utf-8")
    if args.sync:
        return sync(text)
    if args.prune:
        return prune(text)
    return report(text)


if __name__ == "__main__":
    raise SystemExit(main())
