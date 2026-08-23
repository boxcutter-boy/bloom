#!/usr/bin/env python3
"""
Bloom — zero-dependency dev server with live reload.

Serves this folder over HTTP and auto-refreshes any open browser tab the
instant you save an .html / .css / .js / .svg file. No Node, no install —
just Python 3 (already on macOS).

    python3 dev-server.py            # serves at http://localhost:5173
    python3 dev-server.py --port 8080
    python3 dev-server.py --open     # also opens the browser

Live reload works by injecting a tiny <script> into every HTML page that
listens on a Server-Sent-Events stream; a background thread watches file
mtimes and pushes a "reload" event when anything changes.
"""

import argparse
import http.server
import os
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WATCH_EXTS = {".html", ".css", ".js", ".svg", ".json"}

# Bumped whenever a watched file changes. The SSE stream compares against
# the value each client last saw and emits "reload" when it moves.
_version = 0
_version_lock = threading.Lock()

# Injected before </body> on every HTML response.
LIVE_RELOAD_SNIPPET = b"""
<script>
(function () {
  if (window.__classyLiveReload) return;
  window.__classyLiveReload = true;
  var es = new EventSource("/__livereload");
  es.addEventListener("reload", function () { location.reload(); });
  es.onerror = function () { /* server restarting; EventSource auto-retries */ };
})();
</script>
"""


def _snapshot():
    """Return a hashable signature of all watched files' mtimes+sizes."""
    sig = []
    for path in ROOT.rglob("*"):
        if path.suffix.lower() in WATCH_EXTS and ".git" not in path.parts:
            try:
                st = path.stat()
                sig.append((str(path), st.st_mtime, st.st_size))
            except OSError:
                pass
    return tuple(sorted(sig))


def _watch_loop(poll=0.4):
    global _version
    last = _snapshot()
    while True:
        time.sleep(poll)
        current = _snapshot()
        if current != last:
            last = current
            with _version_lock:
                _version += 1


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    # Quieter logs: one line per request, no noisy SSE spam.
    def log_message(self, fmt, *args):
        if "/__livereload" in (self.path or ""):
            return
        super().log_message(fmt, *args)

    def do_GET(self):
        if self.path == "/__livereload":
            return self._serve_sse()
        return self._serve_maybe_html()

    def _serve_sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        with _version_lock:
            seen = _version
        try:
            # Kick the connection alive immediately.
            self.wfile.write(b": connected\n\n")
            self.wfile.flush()
            while True:
                time.sleep(0.4)
                with _version_lock:
                    current = _version
                if current != seen:
                    seen = current
                    self.wfile.write(b"event: reload\ndata: 1\n\n")
                    self.wfile.flush()
                else:
                    # Comment line as heartbeat so proxies don't drop us.
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return  # tab closed

    def _serve_maybe_html(self):
        # Resolve the filesystem path the base handler would use.
        fs_path = self.translate_path(self.path)
        if os.path.isdir(fs_path):
            index = os.path.join(fs_path, "index.html")
            if os.path.exists(index):
                fs_path = index

        if fs_path.endswith(".html") and os.path.exists(fs_path):
            try:
                with open(fs_path, "rb") as f:
                    body = f.read()
            except OSError:
                return super().do_GET()
            if b"</body>" in body:
                body = body.replace(b"</body>", LIVE_RELOAD_SNIPPET + b"</body>", 1)
            else:
                body += LIVE_RELOAD_SNIPPET
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return

        return super().do_GET()


class ThreadingServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    parser = argparse.ArgumentParser(description="Classy dev server with live reload")
    parser.add_argument("--port", type=int, default=5173)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--open", action="store_true", help="open the browser on start")
    args = parser.parse_args()

    threading.Thread(target=_watch_loop, daemon=True).start()

    server = ThreadingServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}/"
    print(f"Classy dev server → {url}")
    print(f"Serving {ROOT}")
    print("Live reload on: .html .css .js .svg .json   (Ctrl-C to stop)")
    print("Pages:  /index.html   /mobile.html   /classy-build-log.html   /classy-component-status.html")

    if args.open:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
