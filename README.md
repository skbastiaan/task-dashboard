# Task Dashboard

A reusable, Git-backed task dashboard with a Python CLI and no runtime dependencies.
Open a snapshot offline, or run a local server that refreshes as your ledger changes.

- **Worktree:** zoomable dependency map with pan, fit, minimap and task details.
- **Flowchart:** selected-task connections, or a whole category or phase list.
- **Task list:** browse phases, owners, tags, acceptance, evidence and review.
- **Task lifecycle:** dependency checks, named ownership, writer locking and
  evidence-gated completion.
- **Portable briefs:** copy a selected task's context into your preferred tool.

Worktree separates numbered stage buttons from a category filter dropdown. Stage
and category selections combine, so a category can be shown within one stage or
across all stages. Stage buttons wrap into rows, occupy at most
20% of the viewport height, and then scroll vertically. Filtered graphs keep direct
external dependencies as smaller cards showing the task name and category.
Filtered graphs place selected tasks in the upper half and external dependencies
in the lower half, separated by a horizontal line. Selecting
a reference card opens its details without leaving the filter.

The browser is read-only. Selection and camera position are remembered locally;
they do not change task status. The JSON ledger remains the source of truth.

## Try it

Requires Python **3.11 or later**. No pip packages, Node server or database needed.
Node.js is used only by the development syntax checker.

```sh
git clone https://github.com/skbastiaan/task-dashboard.git
cd task-dashboard
python tools/tasks.py validate
python tools/serve_board.py
```

Open [localhost:8792](http://127.0.0.1:8792/). Stop with Ctrl+C. The server binds
only to loopback and serves the board and its revision, with no file browser or
write API. Use `--port 9000` to choose a different port.

On Windows, use `py -3` instead of `python` if needed. On macOS/Linux, use `python3`
when that is your Python 3 command.

The included seven-task board is **fictional sample data**. Its completed and
reviewed states are examples, not evidence of actual work.

For an offline snapshot, open `tasks/board-view.html` in a browser. All styles,
scripts and data are embedded. Regenerate after changing the ledger:

```sh
python tools/tasks.py render
python tools/tasks.py render --check
```

## Reuse in another project

Authorized users can use GitHub's **Use this template** to create their own repository, or keep
this checkout as a shared tool and point it at a ledger in another project.

Initialize a fresh ledger in a new directory:

```sh
python tools/tasks.py --board ../my-project/tasks/board.json init --title "My project" --id my-project
python tools/serve_board.py --board ../my-project/tasks/board.json
```

Initialization refuses to overwrite an existing ledger or generated views. Edit
the new JSON to define your phases, tasks, dependencies and acceptance criteria.
Use a unique milestone ID for each project. See [the ledger format](docs/LEDGER.md).

Existing schema-v1 ledgers can be opened directly with `--board`. Paths supplied
on the command line resolve from your current directory. Generated `BOARD.md` and
`board-view.html` sit beside that ledger, so use one ledger per directory. The
read-only server does not generate or modify those files.

There are no fixed project names, task prefixes or workstation paths. Browser
state is scoped by page path and milestone ID. Append `?view=worktree`,
`?view=flow` or `?view=list` to choose the initial view.

## Update task status

The following commands operate on a newly initialized ledger:

```sh
python tools/tasks.py --board ../my-project/tasks/board.json next
python tools/tasks.py --board ../my-project/tasks/board.json show TASK-001
python tools/tasks.py --board ../my-project/tasks/board.json set TASK-001 planned --owner "Your name"
python tools/tasks.py --board ../my-project/tasks/board.json start TASK-001
python tools/tasks.py --board ../my-project/tasks/board.json set TASK-001 review --evidence "Project brief written"
python tools/tasks.py --board ../my-project/tasks/board.json set TASK-001 done --validation "passed: scope reviewed against requirements" --review "Reviewed by a second contributor"
```

Record the actual evidence and review for your work. `done` requires evidence,
review and at least one `passed:` validation result. A task with incomplete
dependencies cannot start or finish. `ready` is derived from a planned task's
dependencies; it is not a stored status. See [transitions and locks](docs/LEDGER.md).

## Development

Edit the files in `tools/`, then regenerate and check:

```sh
python tools/tasks.py render
python tools/check.py
git diff --check
```

The checker validates Python/JavaScript syntax, the sample ledger, source sizes
and deterministic generated views. It does not prove browser behavior or task
completion. The GitHub workflow runs these static checks on Windows and Linux.

`tools/tasks.py render --inline-output /absolute/path/fragment.html` also writes
an HTML fragment for an embedding host. Normal snapshots are complete HTML files.

## Ownership

Publicly visible with the owner's authorization; the proprietary
[LICENSE.md](LICENSE.md) is retained unchanged. Public visibility does not grant
an open-source license. This extraction was requested for reuse across the owner's
projects. [Provenance](docs/provenance.json) records the original dashboard input
hashes. Original product code, task data and history are absent.
