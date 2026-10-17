# Ledger format and lifecycle

A ledger is a UTF-8 JSON object with `schema_version: 1`, one `milestone`, a
`phases` array and a `tasks` array. The included `tasks/board.json` is a complete
fictional example; `init` creates a smaller, planned-only starter.

## Fields

| Object | Fields |
| --- | --- |
| Milestone | `id`, `title`, `updated_at`, `baseline_status`: nonempty strings; timestamp includes a UTC offset |
| Phase | `id`, `title`, `outcome`, `gate`: nonempty strings |
| Task identity | `id`, `title`, `phase`, `kind`, `status`, `model_role`, `owner`: nonempty strings |
| Task lists | `depends_on`, `scope`, `acceptance`, `validation`, `evidence`: arrays of nonempty strings; may be empty |
| Task text | `review`, `blocked_reason`, `notes`: strings; may be empty |
| Optional task tags | `tags`: a nonempty array of unique labels, case-insensitive; no required title prefix |

Kinds are `planning`, `decision`, `implementation`, `qualification`. Phase IDs and
task IDs must be unique within their respective arrays. Dependencies reference
task IDs in the same ledger and cannot repeat, reference the task itself or form
a cycle. Cross-phase dependencies are supported.

An active task needs a named owner other than `Unassigned` and a nonempty scope.
Blocked tasks require a reason. Active, review and done tasks require all
dependencies to be done. Empty boards and empty phases are valid.

The CLI writes UTC timestamps. Existing timestamps with other offsets are valid.
The source ledger is independent of browser local storage.

## Transitions

| Current | Allowed next states |
| --- | --- |
| planned | active, blocked, deferred |
| active | review, blocked, planned |
| review | done, active, blocked |
| blocked | planned |
| deferred | planned |
| done | planned, with an explicit `--reason` |

Same-state `set` commands can update metadata. `start` requires a planned task
with completed dependencies. `list --status ready` and `next` use derived
readiness. No ready task makes `next` exit with code 1; invalid input exits with 2.

Every return to planned clears validation and review, marks retained evidence as
prior-attempt history and appends a reset note. Review to active clears the old
review and validation. Leaving blocked clears its reason.

Completion needs evidence, nonempty review text and a `passed:` validation entry.
Every validation entry must start with `passed:`, `not run:` or `waived:`;
`pending:`, `expected:` and `failed:` prevent completion. Qualification tasks
also reject `not run:`. These checks require recorded evidence, not proof that
the statements are true; an independent reviewer remains necessary.

Repeated `--evidence` flags append. Repeated `--validation` flags replace the
validation list when supplied. `--owner`, `--review`, `--notes` and `--reason`
replace their fields.

## Writing and recovery

`init`, `start`, `set` and `render` (including `--check`) acquire `.board.lock`
beside the ledger. A second writer
fails instead of overwriting another update. Do not delete a lock until its
recorded process has been checked and the writer is known to have stopped.

Each file is replaced atomically. JSON and its two generated views are not one
filesystem transaction: if view generation fails after a ledger write, the JSON
remains authoritative. Fix the rendering problem, run `render`, then
`render --check`. A malformed ledger causes the local server to return 503 and
an already-open board to show refresh unavailable; it does not reset task state.

When editing the JSON directly, coordinate with other writers, then run
`validate` and `render`. Maintain one ledger per directory because the generated
filenames and lock are shared by that directory. Commit the ledger and both
generated views together in the project that owns them.

Snapshot HTML contains the complete ledger, including evidence and notes. Handle
it with the same access controls as its source. This template does not configure
GitHub Pages or upload board contents to another service.
