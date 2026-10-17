#!/usr/bin/env python3
"""Serve one task ledger, read-only, on loopback. Python standard library only."""

import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlsplit

from page import document
import tasks


def current_view(ledger: Path) -> tuple[str, str, str]:
    data = json.loads(ledger.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise tasks.LedgerError("board root must be an object")
    errors = tasks.validate(data)
    if errors:
        raise tasks.LedgerError("; ".join(errors))
    view = tasks.render_view(data)
    return view, hashlib.sha256(view.encode("utf-8")).hexdigest(), data["milestone"]["title"]


def live_script(revision: str) -> str:
    return '''
<p class="live-state" id="live-state" role="status">Live local ledger · refreshes every 5 seconds</p>
<script>
const revision = ''' + json.dumps(revision) + ''';
let checking = false;
setInterval(async () => {
  if (checking) return;
  checking = true;
  try {
    const response = await fetch('/revision', {cache:'no-store', signal:AbortSignal.timeout(4000)});
    if (!response.ok) throw new Error('Refresh unavailable');
    if ((await response.text()) !== revision) location.reload();
    document.getElementById('live-state').textContent = 'Live local ledger · refreshes every 5 seconds';
  } catch {
    document.getElementById('live-state').textContent = 'Refresh unavailable · showing the last loaded snapshot';
  } finally { checking = false; }
}, 5000);
</script>'''


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlsplit(self.path)
        if url.path not in ("/", "/roadmap", "/revision"):
            self.send_error(404)
            return
        try:
            view, revision, title = current_view(self.server.ledger)
            payload = revision if url.path == "/revision" else document(view, title, live=live_script(revision))
        except (OSError, ValueError, tasks.LedgerError):
            self.send_error(503, "Task ledger is temporarily unavailable or invalid")
            return
        content = payload.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8" if url.path == "/revision" else "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board", type=Path, default=tasks.BOARD, help="authoritative JSON ledger path")
    parser.add_argument("--port", type=int, default=8792)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    ledger = args.board.expanduser().resolve()
    try:
        current_view(ledger)
    except (OSError, ValueError, tasks.LedgerError) as exc:
        parser.error(str(exc))
    ThreadingHTTPServer.allow_reuse_address = False
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError as exc:
        parser.error(f"cannot listen on 127.0.0.1:{args.port}: {exc}; choose another --port")
    server.ledger = ledger
    print(f"Task Dashboard: http://127.0.0.1:{args.port}/", flush=True)
    print(f"Read-only ledger: {ledger}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
