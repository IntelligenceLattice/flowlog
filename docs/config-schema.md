# `flowlog.config.json` schema

Drives the viewer's lanes, phase bands, reply-pairing timings, and tooltips.
JSON, not YAML - zero extra dependency. Only `lanes` is required; everything
else is optional, and unknown `role`/`kind`/`peer` values at runtime never
error - they render generically instead (see "Unmapped values" below).

```json
{
  "lanes": [
    { "id": "HOST", "name": "Agent", "x": 22 }
  ],
  "groups": [
    { "label": "Agent · MCP host", "lanes": ["HOST", "LLM"] }
  ],
  "phases": {
    "1": "1 · Find out what the server offers"
  },
  "kind_phase": {
    "discover": 1
  },
  "pairs": {
    "tool_result": "tool_call"
  },
  "explain": {
    "tool_call": "The connector sends a tools/call request."
  }
}
```

## Fields

- **`lanes`** (required): one entry per role string your code passes as the
  first argument to `flowlog.send/recv/note/event`. `id` must match that
  role string (case-insensitive). `name` is the display label (defaults to
  `id`). `x` is an **ordering hint, not a pixel/percentage position** -
  lanes are laid out left-to-right in ascending `x` order, then evenly
  spaced; omit it and lane order follows discovery order instead.
- **`groups`**: optional visual brackets drawn above a set of lanes.
  `lanes` here is a list of lane `id`s to bracket together.
- **`phases`**: maps a phase number (as a string key) to a band title shown
  once, the first time that phase appears.
- **`kind_phase`**: maps a `kind` string to the phase number its events
  belong to. Drives which `phases` band an event's row is drawn inside.
- **`pairs`**: maps a **reply** `kind` to the **request** `kind` it answers.
  Used to compute and display round-trip timing ("took 42 ms") on the reply's
  row. Direction matters: the key is the reply, the value is the request.
- **`explain`**: maps a `kind` to a one- or two-sentence tooltip shown in the
  Code pane when that event is selected.

## Unmapped values

A role with no matching `lanes` entry gets a lane auto-created on the fly
(label = the raw role string), appended to the right. A `kind` with no
`kind_phase`/`pairs`/`explain` entry still renders - just with no phase band,
no timing, no tooltip. This is deliberate: flowlog's core has no built-in
vocabulary, and the viewer must never refuse to draw a trace just because its
config doesn't cover every `kind` yet.

## Conventions the viewer relies on

- Role `"HTTP"` renders in the thinner "wire" row style (see
  [hooks.md](hooks.md) - the httpx/requests/aiohttp helpers use this role by
  default).
- A `kind` containing `"error"` or `"fail"` (case-insensitive) renders in the
  error (red) row style.
- A `kind` containing `"log"` (case-insensitive) is hidden by the "log
  lines" toggle.

These are naming conventions, not hardcoded per-project logic - any project
can opt in by naming its `kind`s accordingly.
