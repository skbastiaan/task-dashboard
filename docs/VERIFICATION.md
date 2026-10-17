# Verification — 2026-10-17

The initial standalone extraction was checked on Windows with Python 3.12.14,
Node.js and the Codex in-app Chromium browser. Implementation SHA-256 identities
and the 24 focused CLI/HTTP checks are recorded in [verification.json](verification.json).
The original input identities are in [provenance.json](provenance.json).

Passed:

- Python/JavaScript syntax, schema-v1 validation, source-size limits and generated
  view freshness through `python tools/check.py`.
- Temporary external-ledger initialization (including spaces in paths), owner and
  dependency guards, evidence/review completion, reopening, stale-output repair,
  lock exclusion, export overwrite protection and malformed graph rejection.
- HTML delimiter escaping, exact license preservation, compatibility with both
  existing source-project ledger schemas and a complete embedded snapshot.
- Loopback HTTP read, changed revision, invalid-ledger 503 and recovery; arbitrary
  file routes and POST writes are rejected.
- Browser task selection in Worktree, Flowchart and Task list; map zoom from 41%
  to 51%; copied-brief success feedback; blocked-task context disclosure.
- Selected task survives reload. Empty-phase selection survives both manual reload
  and automatic five-second refresh after a temporary ledger update.
- At a 390×844 viewport, list and flow views fit without horizontal page overflow
  (document width 375 CSS pixels with the scrollbar). No browser error logs were
  reported during these checks. The viewport override was reset afterward.

Independent source review by the `dashboard_review` subagent found one empty-phase
restore issue, now corrected and browser-verified. Final review found no remaining
actionable findings. Its separate temporary diagnostics confirmed locked-render
and export rejection without changing existing bytes, plus distinct dependency
rails for IDs containing colons. All eight extraction hashes and the unchanged
license were independently verified.

Review dispatch used the inherited model/effort because the requested 5.6 Luna was
not available in the collaboration selector. Exact model/effort metadata was not
exposed; this report does not claim Luna ran.

Limits: these are static and focused local checks, not a full browser/platform
matrix or production qualification. File-protocol browser navigation was blocked
by the browser tool's URL policy, so direct `file://` interaction was not run; the
complete static document and embedded resources were checked. The sample board
is fictional. No development unit tests, LAN changes, persistent service changes
or product qualification runs were added.

GitHub-hosted CI results are attached to the commits by GitHub Actions; this local
report does not predict those outcomes.
