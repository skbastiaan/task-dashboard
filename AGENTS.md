# Task Dashboard

Read README.md and docs/LEDGER.md before editing. The browser is a read-only
projection; JSON is authoritative. Browser selection, zoom and copied task briefs
never start work or change task state.

- Preserve LICENSE.md and source attribution in docs/provenance.json. The owner
  authorized public visibility on 2026-10-17 after credential scanning; this does
  not change the proprietary license. Do not add secrets or private project data.
- Keep the runtime dependency-free: Python 3.11+ standard library and browser APIs.
- Keep generic sample data visibly fictional. Never copy another project's private
  ledger, evidence, credentials or host configuration into the template.
- Use tools/tasks.py for task lifecycle changes. Serialize writers with its lock.
- Edit tools/board-template.html, board CSS/JS and tokens.css, then regenerate.
  tasks/BOARD.md and tasks/board-view.html are generated views.
- Keep each handwritten source file below 500 physical lines. Keep validation,
  ledger IO/lifecycle, rendering and graph/camera boundaries clear.
- Do not add development unit tests. Use syntax, schema, generation checks and
  independent review; use focused external probes for uncertain behavior.
- Run python tools/check.py and git diff --check before delivery. Browser changes
  need focused desktop/mobile interaction verification.
- Keep changes local unless publication is requested. Publish only clean commits.
