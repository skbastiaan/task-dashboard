#!/usr/bin/env python3
"""Static source, ledger and generated-output checks; no runtime test suite."""

import ast
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import tasks


def main():
    root = Path(__file__).resolve().parents[1]
    sources = sorted((root / "tools").iterdir())
    for path in sources:
        if path.suffix not in {".py", ".js", ".html", ".css"}:
            continue
        content = path.read_text(encoding="utf-8")
        if len(content.splitlines()) > 500:
            raise SystemExit(f"source exceeds 500 physical lines: {path.name}")
        if path.suffix == ".py":
            ast.parse(content, filename=str(path))
    data = tasks.checked_board()
    tasks.command_render(data, True, None)
    node = shutil.which("node")
    if not node:
        raise SystemExit("Node.js is required for development JavaScript syntax checks")
    view = tasks.render_view(data)
    scripts = re.findall(r"<script>(.*?)</script>", view, flags=re.S)
    if not scripts:
        raise SystemExit("rendered board has no executable script")
    with tempfile.TemporaryDirectory(prefix="task-dashboard-syntax-") as folder:
        for index, script in enumerate(scripts):
            path = Path(folder) / f"script-{index}.js"
            path.write_text(script, encoding="utf-8")
            subprocess.run([node, "--check", str(path)], check=True)
    print(f"passed: Python/JavaScript syntax, source sizes, {len(data['tasks'])}-task ledger, generated views")


if __name__ == "__main__":
    main()
