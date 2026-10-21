# Category filter verification — 2026-10-21

Added Flowchart category/phase selection and Worktree category/phase buttons.
Buttons wrap and are bounded by 20vh with vertical scrolling. Projections retain
only direct boundary links; external cards show a name and category.

- Passed: tools/check.py (syntax, schema, generated artifacts, source size).
- Passed: focused external graph diagnostic over all six sample scopes and 27
  routed links; finite paths and attached ports, direct-only boundary references,
  unchanged authoritative input, and a synthetic five-task chain boundary.
- Passed: local HTTP response includes current controls and styles; embedded
  scripts pass Node syntax checks.
- Passed: independent source review after correcting original-task status lookup,
  preserving hidden-view camera state and ordering late host-state restoration.
- Passed: Gitleaks working-tree scan with the existing narrow checksum allowlist.
- Not run: desktop/mobile browser interaction and screenshot verification. The
  browser tool rejected URL access under its security policy; no bypass attempted.
- No development unit tests or product runtime qualification were added or run.

The browser remains a read-only view. The fictional sample ledger is unchanged.
