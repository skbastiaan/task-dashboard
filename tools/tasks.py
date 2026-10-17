#!/usr/bin/env python3
"""Small, Git-backed task ledger CLI. Uses only the Python standard library."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import sys
import tempfile
from contextlib import contextmanager

from ledger_schema import STATUSES, validate

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "tasks" / "board.json"
MARKDOWN = ROOT / "tasks" / "BOARD.md"
VIEW = ROOT / "tasks" / "board-view.html"
TEMPLATE = Path(__file__).with_name("board-template.html")
LOCK = ROOT / "tasks" / ".board.lock"
TRANSITIONS = {
    "planned": {"active", "blocked", "deferred"},
    "active": {"review", "blocked", "planned"},
    "review": {"done", "active", "blocked"},
    "blocked": {"planned"},
    "deferred": {"planned"},
    "done": {"planned"},
}


class LedgerError(Exception):
    pass


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def read_board() -> dict:
    try:
        with BOARD.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise LedgerError(f"missing authoritative ledger: {BOARD}") from exc
    except json.JSONDecodeError as exc:
        raise LedgerError(f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise LedgerError("board root must be an object")
    return data


def checked_board() -> dict:
    data = read_board()
    errors = validate(data)
    if errors:
        raise LedgerError("ledger validation failed:\n- " + "\n- ".join(errors))
    return data


def task_by_id(data: dict, task_id: str) -> dict:
    for task in data["tasks"]:
        if task["id"] == task_id:
            return task
    raise LedgerError(f"unknown task: {task_id}")


def incomplete_dependencies(data: dict, task: dict) -> list[str]:
    statuses = {item["id"]: item["status"] for item in data["tasks"]}
    return [dep for dep in task["depends_on"] if statuses.get(dep) != "done"]


def display_status(data: dict, task: dict) -> str:
    if task["status"] == "planned" and not incomplete_dependencies(data, task):
        return "ready"
    return task["status"]


def require_transition(task: dict, target: str, command: str, reason: str | None) -> None:
    current = task["status"]
    if command == "start" and current != "planned":
        raise LedgerError(f"cannot start {task['id']} from {current}; only planned ready tasks may start")
    if target == current:
        return
    if target not in TRANSITIONS[current]:
        raise LedgerError(f"invalid task transition for {task['id']}: {current} -> {target}")
    if current == "done" and target == "planned" and not (reason and reason.strip()):
        raise LedgerError("reopening a done task requires --reason")


@contextmanager
def writer_lock():
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise LedgerError(f"writer lock exists; inspect and remove it explicitly if stale: {LOCK}") from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"pid": os.getpid(), "created_at": now_utc()}) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        yield
    finally:
        try:
            LOCK.unlink()
        except FileNotFoundError:
            pass


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_board(data: dict) -> None:
    data["milestone"]["updated_at"] = now_utc()
    errors = validate(data)
    if errors:
        raise LedgerError("update rejected:\n- " + "\n- ".join(errors))
    atomic_write(BOARD, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def task_line(data: dict, task: dict) -> str:
    deps = ",".join(task["depends_on"]) or "-"
    return f"{task['id']:<10} {display_status(data, task):<9} {task['kind']:<14} {task['phase']:<10} deps={deps}  {task['title']}"


def render_markdown(data: dict) -> str:
    milestone = data["milestone"]
    lines = [f"# {milestone['title']}", "", f"Updated: `{milestone['updated_at']}`", "",
             f"Baseline: {milestone['baseline_status']}", ""]
    planning = [task for task in data["tasks"] if task["kind"] in {"planning", "decision"}]
    product = [task for task in data["tasks"] if task["kind"] in {"implementation", "qualification"}]
    def counts(items: list[dict]) -> str:
        values = {status: 0 for status in (*STATUSES, "ready")}
        for item in items:
            values[display_status(data, item)] += 1
        return ", ".join(f"{key} {values[key]}" for key in ("ready", "active", "review", "blocked", "done", "planned", "deferred"))
    lines += ["## Current counts", "", f"- Planning and decisions ({len(planning)}): {counts(planning)}",
              f"- Product implementation and qualification ({len(product)}): {counts(product)}", ""]
    for phase in data["phases"]:
        lines += [f"## {phase['title']} (`{phase['id']}`)", "", phase["outcome"], "", f"Gate: {phase['gate']}", ""]
        phase_tasks = [task for task in data["tasks"] if task["phase"] == phase["id"]]
        if not phase_tasks:
            lines += ["_No tasks._", ""]
            continue
        for task in phase_tasks:
            status = display_status(data, task)
            lines.append(f"- **{task['id']}** [{status}] {task['title']} ({task['kind']}; owner: {task['owner']})")
        lines.append("")
    lines += ["## Task details", ""]
    for task in data["tasks"]:
        lines += [f"### {task['id']} — {task['title']}", "", f"Status: **{display_status(data, task)}**", "",
                  f"Role: {task['model_role']}", "", f"Scope: {', '.join(f'`{item}`' for item in task['scope']) or '—'}", "",
                  f"Tags: {', '.join(task.get('tags', [])) or '—'}", "",
                  f"Dependencies: {', '.join(f'`{item}`' for item in task['depends_on']) or '—'}", "",
                  "Acceptance:", "", *(f"- {item}" for item in task["acceptance"]), "", "Validation:", "",
                  *(f"- {item}" for item in task["validation"]), "", "Evidence:", "",
                  *(f"- {item}" for item in task["evidence"])]
        if not task["evidence"]:
            lines.append("- —")
        lines += ["", f"Review: {task['review'] or '—'}", f"Blocked reason: {task['blocked_reason'] or '—'}",
                  f"Notes: {task['notes'] or '—'}", ""]
    return "\n".join(lines).rstrip() + "\n"


def render_view(data: dict) -> str:
    try:
        template = TEMPLATE.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise LedgerError(f"missing template: {TEMPLATE}") from exc
    if template.count("__BOARD_DATA__") != 1:
        raise LedgerError("board template must contain exactly one __BOARD_DATA__ marker")
    if template.count("__CI_TOKENS__") != 1:
        raise LedgerError("board template must contain exactly one __CI_TOKENS__ marker")
    tokens = TEMPLATE.with_name("tokens.css").read_text(encoding="utf-8")
    template = template.replace("__CI_TOKENS__", tokens)
    for marker, names in {
        "__BOARD_STYLES__": ("board.css", "board-canvas.css"),
        "__BOARD_SCRIPTS__": ("board-graph.js", "board-canvas.js"),
    }.items():
        if template.count(marker) != 1:
            raise LedgerError(f"board template must contain exactly one {marker} marker")
        content = "\n".join(TEMPLATE.with_name(name).read_text(encoding="utf-8") for name in names)
        template = template.replace(marker, content)
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    return template.replace("__BOARD_DATA__", payload)


def generated(data: dict) -> dict[Path, str]:
    from page import document
    return {MARKDOWN: render_markdown(data), VIEW: document(render_view(data), data["milestone"]["title"])}


def command_render(data: dict, check: bool, inline_output: str | None) -> None:
    outputs = generated(data)
    target = Path(inline_output) if inline_output else None
    if target and not target.is_absolute():
        raise LedgerError("--inline-output must be an absolute path")
    if target:
        target = target.resolve()
        if target in {path.resolve() for path in (BOARD, MARKDOWN, VIEW, LOCK)}:
            raise LedgerError("--inline-output must not overwrite the ledger, its generated views or lock")
        outputs[target] = render_view(data)
    if check:
        stale = []
        for path, expected in outputs.items():
            try:
                actual = path.read_text(encoding="utf-8")
            except FileNotFoundError:
                actual = None
            if actual != expected:
                stale.append(str(path))
        if stale:
            raise LedgerError("generated artifacts are missing or stale:\n- " + "\n- ".join(stale))
        print("generated artifacts are current")
        return
    for path, content in outputs.items():
        atomic_write(path, content)
        print(path)


def starter(title: str, project_id: str) -> dict:
    return {
        "schema_version": 1,
        "milestone": {"id": project_id, "title": title, "updated_at": now_utc(),
                      "baseline_status": "New project; define scope and acceptance before starting."},
        "phases": [{"id": "P0", "title": "Planning", "outcome": "An agreed scope", "gate": "Scope reviewed"}],
        "tasks": [{"id": "TASK-001", "title": "Define the project scope", "phase": "P0",
                   "kind": "planning", "status": "planned", "depends_on": [],
                   "scope": ["Project brief"], "acceptance": ["Record the intended outcome and constraints."],
                   "validation": [], "model_role": "Project owner", "owner": "Unassigned",
                   "evidence": [], "review": "", "blocked_reason": "", "notes": ""}],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Operate the repository task ledger")
    parser.add_argument("--board", type=Path, default=BOARD, help="authoritative JSON ledger path")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="create a starter ledger; never overwrite an existing file")
    init.add_argument("--title", default="My project")
    init.add_argument("--id", default="my-project", dest="project_id")
    sub.add_parser("validate")
    listing = sub.add_parser("list")
    listing.add_argument("--status", choices=sorted(STATUSES | {"ready"}))
    sub.add_parser("next")
    show = sub.add_parser("show")
    show.add_argument("id")
    start = sub.add_parser("start")
    start.add_argument("id")
    setter = sub.add_parser("set")
    setter.add_argument("id")
    setter.add_argument("status", choices=sorted(STATUSES))
    setter.add_argument("--evidence", action="append", default=[])
    setter.add_argument("--validation", action="append")
    setter.add_argument("--review")
    setter.add_argument("--reason")
    setter.add_argument("--owner")
    setter.add_argument("--notes")
    render = sub.add_parser("render")
    render.add_argument("--check", action="store_true")
    render.add_argument("--inline-output")
    return parser


def main() -> int:
    global BOARD, MARKDOWN, VIEW, LOCK
    args = build_parser().parse_args()
    BOARD = args.board.expanduser().resolve()
    if BOARD.suffix.lower() != ".json":
        raise LedgerError("--board must name a .json ledger file")
    MARKDOWN, VIEW, LOCK = (BOARD.parent / name for name in ("BOARD.md", "board-view.html", ".board.lock"))
    if args.command == "init":
        with writer_lock():
            if any(path.exists() for path in (BOARD, MARKDOWN, VIEW)):
                raise LedgerError("init refuses to overwrite an existing ledger or generated view")
            data = starter(args.title, args.project_id)
            write_board(data)
            command_render(data, False, None)
        return 0
    data = checked_board()
    if args.command == "validate":
        print(f"valid: {len(data['phases'])} phases, {len(data['tasks'])} tasks")
    elif args.command == "list":
        items = data["tasks"]
        if args.status:
            items = [task for task in items if display_status(data, task) == args.status]
        for task in items:
            print(task_line(data, task))
    elif args.command == "next":
        ready = [task for task in data["tasks"] if display_status(data, task) == "ready"]
        if not ready:
            print("no ready tasks")
            return 1
        print(task_line(data, ready[0]))
    elif args.command == "show":
        task = task_by_id(data, args.id)
        shown = dict(task, derived_status=display_status(data, task),
                     incomplete_dependencies=incomplete_dependencies(data, task))
        print(json.dumps(shown, ensure_ascii=False, indent=2))
    elif args.command in {"start", "set"}:
        with writer_lock():
            data = checked_board()
            task = task_by_id(data, args.id)
            status = "active" if args.command == "start" else args.status
            current = task["status"]
            reason = args.reason if args.command == "set" else None
            require_transition(task, status, args.command, reason)
            if status in {"active", "review", "done"}:
                incomplete = incomplete_dependencies(data, task)
                if incomplete:
                    raise LedgerError(
                        f"cannot move {task['id']} to {status}; incomplete dependencies: {', '.join(incomplete)}"
                    )
            if args.command == "set":
                task["evidence"].extend(args.evidence)
                if args.review is not None:
                    task["review"] = args.review
                if args.reason is not None:
                    task["blocked_reason"] = args.reason
                if args.validation is not None:
                    task["validation"] = args.validation
                if args.owner is not None:
                    task["owner"] = args.owner
                if args.notes is not None:
                    task["notes"] = args.notes
            task["status"] = status
            if status == "planned" and current != "planned":
                detail = f": {reason.strip()}" if reason and reason.strip() else ""
                reset_note = f"Reset {current} -> planned{detail}"
                task["notes"] = f"{task['notes'].rstrip()}\n{reset_note}".strip()
                task["evidence"] = [
                    item if item.startswith("Prior attempt: ") else f"Prior attempt: {item}"
                    for item in task["evidence"]
                ]
                task["validation"] = []
                task["review"] = ""
            elif current == "review" and status == "active":
                task["validation"] = []
                task["review"] = ""
            if status != "blocked":
                task["blocked_reason"] = ""
            write_board(data)
            command_render(data, False, None)
        print(f"{task['id']} -> {status}")
    elif args.command == "render":
        with writer_lock():
            command_render(checked_board(), args.check, args.inline_output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except LedgerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
