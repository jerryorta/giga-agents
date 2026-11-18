# Step 4.5 — Verify the existing baseConfig isn't in flight — detail

Otherwise:

1. Fetch the existing config's epic status:
   ```
   python3 <plans.script> board --jql 'key = <baseConfig.epicKey>'
   ```
   → one-row JSON with the epic's `summary` + **live** `status`.
2. Inspect the row's `status` (or `category`):
   - **Done** → safe to overwrite. Note in the Step 9 confirmation block: "Replacing config for completed epic `<baseConfig.epicKey>` (Done)."
   - **Not Done** (Backlog / To Do / In Progress / In Review / etc.) → **ask the user before continuing.**

3. If the existing epic is not Done, ask via `AskUserQuestion` (or plain prompt if not loaded):

   ```
   The existing config at .claude/giga/epic.<boardName>.json points at
   <baseConfig.epicKey> (<baseConfig.name>) — currently <status> in Jira (NOT Done).

   Repointing it strips the /giga-workflow:epic-next <boardName> and /giga-workflow:epic-story-complete <boardName>
   shortcuts that anyone working on <baseConfig.epicKey> depends on.

   Options:
     [A] Repoint this board at <argEpicKey> — one board per domain.
         <baseConfig.epicKey> keeps its stories and plan file, and gets its
         <boardName> shortcut back when the board is repointed at it.
     [B] Add a second board, for a parallel track you approve, at:
         .claude/giga/epic.<boardName>-<argEpicKey-lowercase>.json
         (board name becomes "<boardName>-<argEpicKey-lowercase>", invoked as
         /giga-workflow:epic-next <boardName>-<argEpicKey-lowercase>)
         Both epics keep working shortcuts.

   Default: [A]. A second board for one domain forks its conventions, and they drift.
   ```

4. Record the user's choice as `configFileMode`:
   - `"overwrite"` → Step 12 writes to `epic.<boardName>.json` (replaces the existing config).
   - `"alternate"` → Step 12 writes to `epic.<boardName>-<argEpicKey-lowercase>.json` (new file alongside the existing one). The effective board name for the rest of the skill becomes `<boardName>-<argEpicKey-lowercase>` (used in summary output, completion message defaults, etc.).

5. If `configFileMode === "alternate"`, **do not** carry `app`, `libraries`, `routingFiles`, `conventions` forward from the existing baseConfig blindly — those describe the workspace and stay valid, but the user should confirm in Step 9. (For a same-domain alternate epic they're typically still right; record them as "carried forward (same workspace)" in the Step 9 disclosure.)
