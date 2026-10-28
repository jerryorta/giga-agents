---
name: clean-exit
description: Shut a session down cleanly right before `/exit` — stop this session's background Bash tasks, Monitors, subagents and workflows, delete its cron jobs, stop every detached dev server / Storybook running from this checkout (this session's and any an earlier session left behind), remove its clean harness worktrees, close the browser tabs it opened, and print what was stopped and what was deliberately left running. Use when the user says "clean exit", "shut everything down", "wrap up the session", "stop all servers and agents", "tear down before I exit", or invokes `/giga-workflow:clean-exit`. Flags — `--keep-servers` leaves every OS process alone; `--dry-run` reports without stopping anything.
---

# Clean exit

The last thing a session runs before `/exit`. It tears down this session's harness work and every detached server running from this checkout, and leaves everything else alone — servers in the user's own terminal, sibling clones, IDE processes, and any work not yet committed or pushed.

**Usage:** `/giga-workflow:clean-exit` · `/giga-workflow:clean-exit --keep-servers` · `/giga-workflow:clean-exit --dry-run` (flags compose)

**Two sources of truth, never one.** The harness owns background tasks, Monitors, subagents, workflows and crons — only *your transcript* and the tool listings know their ids. The OS owns detached servers (`cmd > log 2>&1 &` is reparented to launchd and outlives the session) — only `scripts/scan.sh` finds them. Skipping either leaves something running.

This runs at maximum context, so every turn is expensive: issue independent calls in **one message** wherever the steps below allow it.

## Step 1 — Inventory (one message)

Load the deferred tools you need in one `ToolSearch` (`select:TaskStop,CronList,CronDelete,ExitWorktree`), then in a single message:

- `Bash`: `${CLAUDE_SKILL_DIR}/scripts/scan.sh` — process groups rooted in this checkout (and its worktrees), each labelled `detached` / `terminal`, plus every linked worktree with its dirty-file and unpushed-commit counts.
- `ListAgents` — subagents and teammates this session spawned.
- `CronList` — scheduled jobs.

Then list from your own transcript every id you started that has **no completion notification yet**: `run_in_background` Bash tasks, `Monitor` tasks, background `Agent`s, `Workflow` runs; and every browser tab or page you opened (`tabs_create_mcp`, chrome-devtools `new_page`, a `playwright-cli` session).

Nothing found anywhere → say so in one line and stop.

## Step 2 — Harness-managed work (one message)

- **`TaskStop` every still-running id from Step 1** — Monitors first in the batch, so a `tail -f` watcher is not left reporting on a server you are about to stop. A task already finished returns an error; ignore it.
- **Subagents / teammates** still running → `TaskStop` by id. Their uncommitted edits stay on disk; Step 4 reports them.
- **Crons** → `CronDelete` each job this session created. A job you did not create (durable, another session's) is listed in the report, never deleted. Cloud routines (`/schedule`, `RemoteTrigger`) are not session state — leave them.

## Step 3 — Servers and other OS processes

Pass every `detached` pgid to one call: `${CLAUDE_SKILL_DIR}/scripts/stop-groups.sh <pgid> …`. It signals the whole group (the `npm run` supervisor, `nx` and the node server go down together, so nothing orphaned keeps the port), SIGKILLs after 10 s, and re-checks each group's cwd immediately before signalling — a recycled pgid or a sibling clone's group is skipped, not killed.

| Label from `scan.sh` | Action |
| --- | --- |
| `detached` — no tty: launched in the background by this session or an earlier one | **stop** |
| `terminal` — a member holds a tty: running in the user's own terminal | leave, report it (the user stops it there) |

- Stop every `detached` group, including long-lived ones an earlier session left behind (an app server up for a day is exactly the case). Invoking `/giga-workflow:clean-exit` is the user's explicit instruction to stop them, which is what CLAUDE.md's "never kill a dev server the user is relying on" asks for.
- Processes outside this checkout (sibling clones, other repos) never appear in the scan and are never touched.
- Claude Code's own children (MCP servers, harness shells), IDE-owned trees and the Nx daemon are excluded by the scanner — they are not yours to stop and they end or restart on their own.
- `--keep-servers` → skip this step entirely.

## Step 4 — Worktrees

From the scan's WORKTREES block:

- **`CURRENT` is a linked worktree** (the session entered one with `EnterWorktree`) → `ExitWorktree` first: `remove` when `dirty:0 unpushed-commits:0`, otherwise `keep`.
- **`harness` worktree** (under `.claude/worktrees/`) with `dirty:0 unpushed-commits:0` → `git worktree remove <path>`, then `git branch -d <branch>` (lower-case `-d`: git refuses an unmerged branch, and that refusal is the correct outcome — report it).
- **`dirty` > 0 or `unpushed-commits` > 0 or `LOCKED`** → **keep**, report the path and counts. Removing it destroys work that exists nowhere else; never `--force`, never `-D`.
- **`external` worktree** (anywhere else) → the user's; report only.
- `prunable:` lines → `git worktree prune`.

## Step 5 — Browser

Close only the tabs / pages this session opened (`tabs_close_mcp`, chrome-devtools `close_page`, `playwright-cli close`). Never a tab the user had open. Skip the step when no browser tool was used this session.

## Never

Commit, push, stash, `git clean`, delete log files, a build-cache reset, `kill` by name pattern (`pkill -f`, `pgrep -f storybook` — sibling clones run identical commands), or touch anything outside this checkout. A clean exit stops processes; it never resolves or discards work.

## `--dry-run`

Run Step 1, then print the Step 6 report with every action phrased as *would stop / would remove*. Change nothing.

## Step 6 — Report

The skill's only prose output. Print once, then stop.

```
Clean exit — <repo path>
Stopped:   <n> background task(s) · <n> monitor(s) · <n> agent(s) · <n> cron(s)
Servers:   stopped pgid <g> :<ports> <cmd>            (one line each; "none" if none)
Worktrees: removed <path> · kept <path> (dirty:<n> unpushed:<n>)
Browser:   closed <n> tab(s)
Left running:
  pgid <g> terminal :<ports> <cmd> — your terminal; stop it there   ("none" if none)
✓ Ready to /exit
```

Replace the last line with `⚠ Review the kept items above before /exit` when a worktree was kept for uncommitted or unpushed work.
