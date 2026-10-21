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

## Stage and category separation

Numbered stage controls and category tags are now separate. Worktree buttons
contain stages only; category dropdowns filter both graph views. Stage and category
filters intersect. Legacy tag-only and stage-only saved selections remain supported.

Passed: eight sample stage/category combinations, correct membership and boundary
edges, immutable input, legacy scope decoding, tools/check.py, HTTP assets and
embedded-script syntax. Local source verification covered 296 combinations.
Browser visual verification remains not run under the previously recorded block.

## Divided dependency lanes

Filtered canvases now have equal upper/lower halves, with selected tasks above
and compact external dependencies below a labeled horizontal divider. The overview
also shows the divider. Unfiltered all-task layout remains unsplit. Camera layout
version was advanced to discard stale positions after geometry changes.

Passed: eight sample scope layouts and 40 links; midpoint divider, node bounds,
correct membership halves, attached ports and no edges crossing another card.
Equivalent private-local diagnostics covered 296 scopes and 4424 links.
Static checks pass; desktop/mobile visual checks remain not run.

## Canvas-owned dragging

Pointer capture belongs only to the viewport, including drags originating on
cards or labels. Native dragging and text selection are prevented in the canvas.
Stationary primary clicks select a task; dragging, cancellation and multi-pointer
gestures do not select one. Keyboard button activation remains native.

Passed: external mocked-handler diagnostic for card/background pan deltas,
stationary clicks, pointer cancellation, multi-pointer suppression, keyboard
passthrough and dragstart prevention in both copies. This is source-event logic
evidence, not browser verification. Static checks pass. Actual browser dragging
and touch interaction remain not run under the recorded URL policy block.
