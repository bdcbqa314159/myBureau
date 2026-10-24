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
import urllib.parse

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
STATE = {"n": 0, "look": "", "site": ""}


def watch() -> None:
    """Notice that content/ changed, whoever changed it."""
    last = None
    while True:
        stamp = []
        for p in sorted((ROOT / "content").rglob("*")):
            try:
                stamp.append((str(p), p.stat().st_mtime_ns, p.stat().st_size))
            except OSError:
                pass
        now = hash(tuple(stamp))
        if last is not None and now != last:
            STATE["n"] += 1
        last = now
        time.sleep(0.6)


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
        self.send_header("X-Frame-Options", "DENY")
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
        # asks for exactly the url written in the markup. These hold no
        # content — the panel's own code, the site's stylesheet, and the
        # drawn icons and pointers that are public on the live site anyway.
        # The token still guards everything that reads or writes HER work:
        # /api/* and /media/*.
        if path == "/app.css":
            return self.file(HERE / "app.css", "text/css; charset=utf-8")
        if path == "/app.js":
            return self.file(HERE / "app.js", "text/javascript; charset=utf-8")
        if path == "/site.css":
            # the dashboard wears the bevels of the thing it edits
            return self.file(ROOT / "static" / "css" / "site.css",
                             "text/css; charset=utf-8")
        if path.startswith("/img/"):
            # site.css asks for ../img/cursors/… relative to itself, so the
            # dashboard gets the real pointers and the real drawn icons
            f = (ROOT / "static" / "img" / path[len("/img/"):]).resolve()
            try:
                f.relative_to((ROOT / "static" / "img").resolve())
            except ValueError:
                return self.oops(403, "no")
            return self.file(f, mimetypes.guess_type(f.name)[0] or "image/png")

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

        STATE["n"] += 1
        body = json.dumps({"did": out, "tree": model.tree(), "n": STATE["n"]},
                          ensure_ascii=False).encode("utf-8")
        self.send(200, body, "application/json; charset=utf-8")

    def verb(self, ask: dict):
        name = ask.get("verb")
        if name == "place":
            return verbs.place(ask["item"], ask["x"], ask["y"])
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
