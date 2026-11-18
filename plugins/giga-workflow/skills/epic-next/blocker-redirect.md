# Step 7.5 — Blocker redirect — detail

**Redirect**. Do not build the blocked story; the blocker's
work comes first:

1. Resolve the blocker's board. A blocker that is an epic is its own target; a story's target is its `parent`.
   Find the `epic.*.json` whose `epicKey` is that target.
2. Report, and stop:
   ```
   <KEY> is blocked by <BLOCKER> (<status>) — <summary>
   Redirect: /giga-workflow:epic-next <target-board>
   ```
   If no config points at the target, say so. The fix is `/giga-workflow:epic-config` to repoint that prefix's board (one board
   per domain, never a second config), then `/giga-workflow:epic-plan <target>` if its children do not exist yet.

For the default pick, check whether a later, unblocked To Do story exists in the order before redirecting. If one
does, offer the choice (redirect, or take that story) instead of silently skipping ahead. Wave order stays the owner's.
