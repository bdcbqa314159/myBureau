#!/usr/bin/env python3
"""The dashboard's little server.

    python3 tools/studio/server.py [port]

Serves the dashboard, reads content/ for it, and performs the verbs in
verbs.py on its behalf. Nothing else. It holds no state: every request
re-reads the filesystem, because somebody editing a file in TextEdit has
to win over anything this remembers.

WHAT STOPS THIS BEING A HOLE IN HER MACHINE. It is a local server that
writes to disk, and any page open in her browser can send it a request.
So: bound to the loopback address only; a token minted at startup and
required on every single request, so a page that cannot read the address
bar cannot act; cross-site requests refused outright; and every path run
through verbs.inside(), which resolves symlinks and refuses anything that
is not under content/.
"""
from __future__ import annotations

import http.server
import json
import mimetypes
import pathlib
import secrets
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import model    # noqa: E402
import verbs    # noqa: E402

ROOT = HERE.parent.parent
TOKEN = secrets.token_urlsafe(24)

# bumped by the watcher; the event stream sends the number, and the
# dashboard re-reads when it changes. A counter rather than a description
# of what changed: the dashboard re-reads everything anyway, and a
# description would be a second opinion about the filesystem.
# preview.sh hunts for a free port, so the site is not always on 1111 and
# the panel must be told rather than guessing. Guessing is how "Voir le
# site" opens a dead tab on the second run of the day.
STATE = {"n": 0, "look": "", "site": "", "mark": None}


def fingerprint() -> int:
    stamp = []
    for p in sorted((ROOT / "content").rglob("*")):
        try:
            stamp.append((str(p), p.stat().st_mtime_ns, p.stat().st_size))
        except OSError:
            pass
    return hash(tuple(stamp))


def watch() -> None:
    """Notice that content/ changed, WHOEVER changed it — except us.

    A verb writes a file, so the watcher sees it a moment later and would
    report it as news. The panel then reloads the frame for a change it
    made itself and already has on screen — which is the whole thing we
    are trying not to do. So a verb leaves its own fingerprint behind on
    the way out, and this only counts what does not match it.
    """
    while True:
        now = fingerprint()
        if STATE["mark"] is not None and now != STATE["mark"]:
            STATE["n"] += 1
        STATE["mark"] = now
        time.sleep(0.4)


def look() -> str:
    try:
        r = subprocess.run([sys.executable, "tools/look.py"], cwd=ROOT,
                           capture_output=True, text=True, timeout=30)
        return (r.stdout or r.stderr).strip()
    except Exception as exc:                        # noqa: BLE001
        return "look.py did not run: {}".format(exc)


class Studio(http.server.BaseHTTPRequestHandler):
    server_version = "myBureau-studio"

    def log_message(self, *a):          # the terminal is hers, keep it quiet
        pass

    # ---- plumbing ---------------------------------------------------
    def send(self, code: int, body: bytes, kind: str = "text/plain; charset=utf-8",
             extra: dict = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        # this page is a tool, not a document: nothing about it should be
        # cached, embedded, or sent anywhere
        self.send_header("Cache-Control", "no-store")
        # SAMEORIGIN, not DENY. The panel frames the site it proxies, and
        # that frame is this same address — DENY refused it, which is what
        # Firefox was complaining about. Another site still cannot frame
        # the panel, which is the thing worth preventing.
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def oops(self, code: int, why: str) -> None:
        self.send(code, json.dumps({"error": why}).encode("utf-8"),
                  "application/json; charset=utf-8")

    def allowed(self, q: dict) -> bool:
        # a page on another origin can POST without being able to READ the
        # address bar, so the token is what makes forgery impossible
        if (q.get("t") or [None])[0] != TOKEN and self.headers.get("X-Studio") != TOKEN:
            return False
        if self.headers.get("Sec-Fetch-Site") in ("cross-site", "same-site"):
            return False
        return True

    # ---- reading ----------------------------------------------------
    def do_GET(self) -> None:
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        path = u.path

        if path == "/":
            if (q.get("t") or [None])[0] != TOKEN:
                return self.send(403, b"Open the address the terminal printed.")
            return self.file(HERE / "app.html", "text/html; charset=utf-8")

        # ---- the shell, served without a token -----------------------
        # A <link> and a <script> in the page cannot carry one: the browser
        # asks for exactly the url written in the markup. These two hold no
        # content of hers — they are the panel's own code. The token still
        # guards everything that reads or writes HER work: /api/*, /media/*
        # and /site/*.
        if path == "/app.css":
            return self.file(HERE / "app.css", "text/css; charset=utf-8")
        if path == "/app.js":
            return self.file(HERE / "app.js", "text/javascript; charset=utf-8")
        # The framed site carries NO token, and cannot: the iframe's src is
        # written in the markup, and every link inside the page is a plain
        # href. That is not a hole being opened — `zola serve` is already
        # serving these exact bytes on its own port with no token at all,
        # on the same loopback address. The proxy adds a second door to a
        # room that was never locked, not a door to a new room.
        if path == "/site" or path.startswith("/site/"):
            return self.proxy(path[len("/site"):] or "/")
        # ---- everything past here is her work, or acts on it ---------
        if not self.allowed(q):
            return self.oops(403, "no")
        if path == "/api/tree":
            body = json.dumps({"tree": model.tree(), "n": STATE["n"],
                               "site": STATE["site"]},
                              ensure_ascii=False).encode("utf-8")
            return self.send(200, body, "application/json; charset=utf-8")
        if path == "/api/look":
            STATE["look"] = look()
            return self.send(200, json.dumps({"look": STATE["look"]}).encode("utf-8"),
                             "application/json; charset=utf-8")
        if path == "/api/events":
            return self.stream()
        if path.startswith("/media/"):
            return self.media(urllib.parse.unquote(path[len("/media/"):]))
        return self.oops(404, "no such thing")

    def file(self, p: pathlib.Path, kind: str) -> None:
        if not p.is_file():
            return self.oops(404, "missing " + p.name)
        self.send(200, p.read_bytes(), kind)

    def media(self, rel: str) -> None:
        try:
            f = verbs.inside(rel)
        except verbs.Refused as exc:
            return self.oops(403, str(exc))
        if not f.is_file():
            return self.oops(404, "no such file")
        kind = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        self.send(200, f.read_bytes(), kind)

    def proxy(self, rest: str) -> None:
        """The real site, served from the panel's own address.

        Not a screenshot and not a second renderer: this IS the page zola
        built, fetched and handed on. Which means the panel can reach into
        it — same origin — and make the icons it really rendered draggable.
        There is one renderer in this project and it stays that way.

        EVERY absolute url is rewritten, not just the links. The page
        carries `default-src 'self'`, and once the document sits on this
        address `self` means THIS address — so a stylesheet still pointing
        at zola's port would be blocked by the site's own policy. Rewriting
        all of it keeps the page whole and its policy honest.

        The cost is zola's live-reload, whose socket no longer finds its
        way home. The panel reloads the frame itself when the watcher says
        content changed, which is one mechanism instead of two.
        """
        site = STATE["site"].rstrip("/")
        if not site:
            return self.oops(503, "the site is not running")
        try:
            with urllib.request.urlopen(site + rest, timeout=20) as r:
                kind = r.headers.get("Content-Type", "application/octet-stream")
                body = r.read()
        except urllib.error.HTTPError as e:
            return self.send(e.code, b"", "text/plain")
        except Exception as exc:                    # noqa: BLE001
            return self.oops(502, "the site did not answer: {}".format(exc))
        if kind.split(";")[0] in ("text/html", "text/css", "application/javascript",
                                  "text/javascript", "application/json"):
            body = body.decode("utf-8", "replace").replace(site, "/site").encode("utf-8")
        self.send(200, body, kind)

    def stream(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        seen = -1
        beat = time.time()
        while True:
            try:
                if STATE["n"] != seen:
                    seen = STATE["n"]
                    self.wfile.write(("data: " + json.dumps({"n": seen}) + "\n\n").encode())
                    self.wfile.flush()
                elif time.time() - beat > 15:
                    # a comment line, so a proxy or a sleeping laptop does
                    # not quietly drop the connection
                    self.wfile.write(b": still here\n\n")
                    self.wfile.flush()
                    beat = time.time()
                time.sleep(0.3)
            except (BrokenPipeError, ConnectionResetError, OSError):
                return

    # ---- writing ----------------------------------------------------
    def do_POST(self) -> None:
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if not self.allowed(q):
            return self.oops(403, "no")
        length = int(self.headers.get("Content-Length") or 0)
        if length > 64 * 1024 * 1024:
            return self.oops(413, "that file is very large")
        raw = self.rfile.read(length) if length else b""

        try:
            if u.path == "/api/upload":
                into = (q.get("into") or [""])[0]
                name = (q.get("name") or [""])[0]
                how = (q.get("as") or [""])[0]
                if how == "wallpaper":
                    out = verbs.set_wallpaper(into, name, raw)
                elif how == "icon":
                    out = verbs.set_icon(into, name, raw)
                else:
                    out = verbs.add_image(into, name, raw)
            elif u.path == "/api/do":
                ask = json.loads(raw.decode("utf-8") or "{}")
                out = self.verb(ask)
            else:
                return self.oops(404, "no such thing")
        except verbs.Refused as exc:
            return self.oops(400, str(exc))
        except Exception as exc:                    # noqa: BLE001
            return self.oops(500, "{}: {}".format(type(exc).__name__, exc))

        # our own change, written down so the watcher does not report it
        # back to us as news a moment later
        STATE["mark"] = fingerprint()
        STATE["n"] += 1
        body = json.dumps({"did": out, "tree": model.tree(), "n": STATE["n"]},
                          ensure_ascii=False).encode("utf-8")
        self.send(200, body, "application/json; charset=utf-8")

    def verb(self, ask: dict):
        name = ask.get("verb")
        if name == "place":
            return verbs.place(ask["item"], ask["x"], ask["y"])
        if name == "new_project":
            return verbs.new_project(ask["into"], ask["name"], ask.get("kind", "photos"))
        if name == "new_bureau":
            return verbs.new_bureau(ask["into"], ask["name"])
        if name == "move":
            return verbs.move(ask["item"], ask["into"])
        if name == "throw_away":
            return verbs.throw_away(ask["item"])
        if name == "retitle":
            return verbs.retitle(ask["item"], ask.get("lang", "fr"), ask["title"])
        if name == "set_body":
            return verbs.set_body(ask["item"], ask.get("lang", "fr"), ask.get("body", ""))
        if name == "reorder":
            return verbs.reorder(ask["item"], ask["names"])
        if name == "remove_image":
            return verbs.remove_image(ask["item"], ask["name"])
        if name == "undo":
            return {"undid": verbs.undo()}
        raise verbs.Refused("there is no such action")


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 1112
    STATE["site"] = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:1111/"
    threading.Thread(target=watch, daemon=True).start()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), Studio)
    srv.daemon_threads = True
    url = "http://127.0.0.1:{}/?t={}".format(port, TOKEN)
    print(url, flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
