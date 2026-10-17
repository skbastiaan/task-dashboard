"""Standalone HTML wrapper shared by snapshots and the local server."""

from html import escape


def document(view: str, title: str, *, live: str = "") -> str:
    return (
        '<!doctype html>\n<html lang="en" data-ci="signal-inspector">\n<head>\n'
        '<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<title>{escape(title)} · Task Dashboard</title>\n'
        '<style>body{margin:0;background:var(--ci-bg);color:var(--ci-text);font-family:var(--ci-font)}'
        '.live-state{margin:0;padding:8px;font-size:12px;background:var(--ci-panel)}</style>\n'
        '</head>\n<body>\n' + view + live + '\n</body>\n</html>\n'
    )
