# The viewer

`flowlog run`/`flowlog view` open a browser tab with three panes:

- **Flow** (left, widest by default): the sequence diagram. Lanes come from
  your config; arrows are request (solid) or reply (dashed); phase bands and
  per-`kind` tooltips come from config too. Click any arrow.
- **Code** (middle): the source snippet from the code location that logged
  the selected event, plus its tooltip if your config has one for that
  `kind`. Needs the viewer server running (not available when loading a
  saved `.jsonl` offline, since there's no filesystem to read from in that
  mode).
- **Packet** (right): the selected event's metadata (from/to, timing) and
  its full JSON payload, pretty-printed with a copy button.

## Resizing

Drag the thin divider between any two panes. Minimum widths: flow 320px,
code 200px, packet 180px - no pane can be dragged to zero. Your chosen
widths are remembered in the browser's `localStorage` (per-origin, so per
deployment of the viewer) and restored next time you open it. **Reset
layout** in the header clears that and goes back to the defaults.

Below 1000px viewport width, panes stack vertically instead (touch/narrow
screens) and dragging resizes height instead of width.

## Toggles

- **HTTP wire**: show/hide rows where the role or peer is `"HTTP"` (see
  [hooks.md](hooks.md)).
- **log lines**: show/hide rows whose `kind` contains `"log"`.
- **follow**: auto-scroll to the newest event as the trace grows.

## Loading a saved trace

**Load trace…** in the header reads a `.jsonl` file from disk and replays it
- no viewer server needed for this path, so the page also works opened
directly from a file (`file://`), just without the Code pane's source
snippets (those need `/code` from a running server) or live SSE updates.
