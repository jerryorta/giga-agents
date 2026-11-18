# Cross-epic blockers (`blocked_by`) — detail

When the epic depends on another board's epic, its plan file carries a `### Wave 0 — Blocked by <KEY> (redirect)`
section, and `blocked_by: [<KEY>]` in the epic's front matter when the whole epic waits.

- **Every policy keeps Wave 0 verbatim** as the first wave. It is not a child of this epic, so it never enters the
  Step 7/8 analysis.
- When only some stories wait (Wave 0 names them), write `blocked_by: [<KEY>]` into each of those stories' front
  matter in the same pass. Newly minted stories get it at creation.

`/giga-workflow:epic-next` Step 7.5 and `/giga-workflow:epic-loop` 2a read these to redirect blocked work to the blocker's board.
