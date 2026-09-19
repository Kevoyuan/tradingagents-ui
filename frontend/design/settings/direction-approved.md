# Direction approved — Settings screen

Gate file required by huashu-design before implementation starts.

## What was shown

huashu-design's three-direction gate. The visual register was already user-selected (Swiss,
from `frontend/design/variant-E.html`) and recorded, so per the skill's rule for a specified
style the three directions diverge on **information architecture**, not palette. All three
use the user's real values (NBIS, 2026-09-18, Chinese, Deep 5, DeepSeek, deepseek-v4-flash,
their analysts and their data vendors).

| Draft | Structure | File | Screenshot |
|---|---|---|---|
| 1 | Control Sheet — all five sections on one page, three columns | `1-control-sheet.html` | `1-control-sheet.png` |
| 2 | Two-Pane Index — index carries current values, one chapter open | `2-two-pane-index.html` | `2-two-pane-index.png` |
| 3 | Instrument Drawer — overlay over the live run, pinned Next-run strip | `3-drawer.html` | `3-drawer.png` |

## User's decisions, verbatim

> 3, 可以一次性看全部配置。而且我想放左边，你不是有导航栏吗，怎么不放导航栏

> 做模态抽屉就行

Read together: direction **3**, with (a) the whole configuration visible at once rather than
one chapter at a time, (b) on the **left**, and (c) as a **modal** drawer with a scrim. The
intermediate idea of docking it into the 56px nav rail was dropped by the user.

## Iterations, recorded so they are not relitigated

- `3-drawer.html` — right side, one chapter scrolled at a time. Rejected by (a).
- `3-left-panel.html` — docked into the nav rail, no scrim, all sections. Rejected by
  "做模态抽屉就行"; it also clipped the Advanced section because a docked panel has to fit
  the rail's height budget.
- `3-modal-drawer.html` — **the approved form.** Left, modal with a 38% scrim, 840px wide,
  three-column field grid, all five sections in one screen.

## Why no new three-direction gate was run for the iterations

The user had already selected a direction; each follow-up was a change to that direction,
which falls under the documented exemption for iterating on a selected direction.

## Approved form

- Left modal drawer, 840px, scrim `rgba(10,10,10,.38)`.
- Header (title + saved timestamp + close), pinned **Next run** summary strip, five sections,
  footer with unsaved count + Discard + Save preferences.
- Three-column field grid; the whole configuration fits 1050px with no scrolling.
  Verified in a real browser: `overflowPx: 0`, last row bottom 868px vs footer top 993px,
  `clipped: false`.
- Reuses the established Swiss tokens: Archivo, hairline rules, tabular numerals, paper
  white, and no colour except the credential "set" marker and the Monitor's own signal
  colours behind the scrim.

## Status

Design is locked. The implementation (Phase P6: Settings screen plus the provider, credential
and upstream API routes) is not started and follows this file.

## Open items carried into implementation

1. `1-control-sheet.html`, `2-two-pane-index.html`, `3-drawer.html` and `3-left-panel.html`
   are kept as the exploration record and must not be implemented.
2. `brand-spec.md` in the run-monitor design directory still applies: the three-rule mark is
   a placeholder, not a delivered identity.
3. The credentials panel must never render a real key value; masked plus a "set" marker only.
