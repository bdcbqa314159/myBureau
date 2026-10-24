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
    verbs.ROOT = tmp
    verbs.CONTENT = tmp / "content"
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

    shutil.rmtree(tmp, ignore_errors=True)

    serve()
    print()
    if failed:
        print("  {} FAILED\n".format(failed))
        return 1
    print("  the dashboard keeps its hands where they belong\n")
    return 0




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

        try:
            post("/api/do", {"verb": "rm", "item": "content"})
            check("an unknown verb is refused", False)
        except urllib.error.HTTPError as e:
            check("an unknown verb is refused", e.code == 400)

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
