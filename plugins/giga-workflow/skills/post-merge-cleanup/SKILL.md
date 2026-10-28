---
name: post-merge-cleanup
description: "Clean up after a PR merge or a direct-mode merge: delete the merged branch (local, and remote when it was pushed) and transition the Jira ticket to Done: $ARGUMENTS"
---

Clean up after a PR merge or a direct-mode merge: delete the merged branch (local, and remote when it was pushed) and transition the Jira ticket to Done: $ARGUMENTS

> **Three modes:** (1) **PR-mode boards** — run per story on the merged `<git.branchPrefix><key>-<slug>` branch (deletes it + transitions the story → Done). (2) **Epic-branch-mode boards** (`mergeMode:"epic-branch"`) — stories were already taken to Done by `/giga-workflow:epic-story-complete`, so here you run this **once per epic** on the merged epic branch (e.g. `/giga-workflow:post-merge-cleanup <git.branchPrefix>abc-123-short-slug`) to delete the epic branch + transition the **epic** ticket → Done. (3) **Direct-mode boards** (`mergeMode:"direct"`) — run per story, chained by `/giga-workflow:epic-story-complete` right after it fast-forwards `<git.mainBranch>` to the story branch and pushes it. The story branch was never pushed and the ticket is usually already Done, so this deletes the local branch, reconciles the wave plan and closes the epic when it was the last story. The branch-name key parse picks up whichever key the branch encodes (story or epic).

> ⚠️ **On a PR-mode board, prefer `/giga-workflow:epic-merge-pr <N>` over calling this skill directly — including when you reviewed and merged the PR on github.com.** `/giga-workflow:epic-merge-pr` is idempotent: it reads an already-`MERGED` PR and skips straight to chaining this skill, so it is never the wrong call. What it adds on top is the part a manual merge silently skips — it verifies the PR genuinely reached `MERGED` before anything is deleted, and it repairs a local `<git.mainBranch>` left a commit stale when `gh pr merge --delete-branch` fails with only a warning. That stale `<git.mainBranch>` is what the next story's branch gets cut from, so the repair is not cosmetic. Run this skill standalone only on an **epic-branch-mode** epic branch, which `/giga-workflow:epic-merge-pr` refuses by design. This note applies to PR-mode boards only: a direct-mode board has no PR, and its stories reach this skill through `/giga-workflow:epic-story-complete`.

## Project config

Repo-specific values come from `.claude/giga/config.json` at the repository root, under `workflow`. Read it once at the start. A missing file or field takes the fallback below, never a guess.

| Field | Used for | When absent |
| --- | --- | --- |
| `git.mainBranch` | the branch checked out and pulled before the branch is deleted | `main` |
| `git.branchPrefix` | the story branch prefix the ticket key is parsed from | `feat/` |
| `jira.cloudId` | the Atlassian cloud id passed to every Jira call | look it up with `getAccessibleAtlassianResources` |
| `jira.mcpPrefix` | the prefix of the Atlassian MCP tool names | stop the Jira legs and tell the user to mark the ticket Done manually |
| `plans.repo` | the plans repo holding ticket and epic plan files (wave-plan reconcile, epic close) | skip the wave-plan and epic-close sections |
| `plans.script` | the script behind `section` and `board` | skip the wave-plan and epic-close sections |
| `plans.autoPush` | whether the plans repo pushes its own commits | `false`: push the commit after committing |
| `epicCloseSkill` | the skill invoked once the epic is Done | skip the hand-off and the epic-review line |

---

## Determine the branch to clean up

1. **If `$ARGUMENTS` is provided**, determine if it is a PR number or a branch name:
   - **PR number** (purely numeric, e.g., `57` or `#57` — strip the `#` if present): Look up the branch name from the PR:
     ```
     gh pr view <number> --json headRefName --jq '.headRefName'
     ```
     Use the returned value as the branch name to delete.
   - **Branch name** (not purely numeric): Use it directly as the branch name to delete.

2. **If `$ARGUMENTS` is empty**, detect the current branch:
   ```
   git branch --show-current
   ```
   - If already on `<git.mainBranch>`, inform the user: "Already on <git.mainBranch>. Provide a PR number or branch name as an argument (e.g., `/giga-workflow:post-merge-cleanup 57` or `/giga-workflow:post-merge-cleanup feat/my-branch`)." and stop.
   - Otherwise, use the current branch as the branch to delete.

Save the branch name for later steps.

## Handle current branch safely

1. **Check the current branch and working tree status:**
   ```
   git branch --show-current
   git status --porcelain
   ```
   Save the current branch name as `<original-branch>`. If `git status --porcelain` produces any output, there are uncommitted changes — set a `needs-stash` flag.

2. **If there are uncommitted changes** (`needs-stash` is true):
   ```
   git stash push -m "post-merge-cleanup: auto-stash"
   ```

3. **If the current branch IS the branch to be cleaned up:**
   - Switch to the main branch:
     ```
     git checkout <git.mainBranch>
     ```
   - Pull latest:
     ```
     git pull
     ```
   - Note: after cleanup, the user will remain on `<git.mainBranch>` (since their branch was deleted). If changes were stashed, they will be unstashed on `<git.mainBranch>`.

4. **If the current branch is NOT the branch to be cleaned up** (i.e., the user is on a different working branch):
   - Switch to the main branch:
     ```
     git checkout <git.mainBranch>
     ```
   - Pull latest:
     ```
     git pull
     ```
   - Note: after cleanup, the skill will return to `<original-branch>` and restore any stashed changes.

## Delete the feature branch

1. **Delete the local branch** (if it exists):
   ```
   git branch -D <branch-name>
   ```
   - If the branch doesn't exist locally, that's fine — report it was not found locally.
   - Defensive (only if someone used native `isolation: worktree` agents): if `<branch-name>` is still checked out in a `git worktree`, run `git worktree remove <dir>` then `git worktree prune` before deleting it.

2. **Check if the remote branch exists, then delete it:**
   ```
   git ls-remote --heads origin <branch-name>
   ```
   - If the output is empty, the remote branch was already removed (e.g., via GitHub PR merge) or, on a direct-mode board, never existed (the story branch is never pushed) — skip deletion and report it was already removed.
   - If the output is non-empty, delete it:
     ```
     git push origin --delete <branch-name>
     ```

3. **Prune stale remote refs:**
   ```
   git remote prune origin
   ```

## Transition Jira Ticket to Done

1. **Extract the ticket key** from the branch name. Branch names follow the pattern `<git.branchPrefix><KEY>-description` or `fix/<KEY>-description` (e.g., `<git.branchPrefix>ABC-123-short-slug` → `ABC-123`). Parse the key as the segment between the first `/` and the second `-`-separated word that is not uppercase (i.e., match the pattern `[A-Z]+-\d+`). Keys may be lowercase in the branch (`abc-123`) — uppercase them for the Jira API. For an epic-branch-mode **epic branch** (e.g. `<git.branchPrefix>abc-123-short-slug`) the same parse yields the **epic** key (`ABC-123`), so this transitions the **epic** → Done.

2. **If a ticket key is found**, load the required Atlassian MCP tools using the ToolSearch tool:
   - `select:<jira.mcpPrefix>getAccessibleAtlassianResources`
   - `select:<jira.mcpPrefix>getJiraIssue`
   - `select:<jira.mcpPrefix>getTransitionsForJiraIssue`
   - `select:<jira.mcpPrefix>transitionJiraIssue`

3. **Get the Atlassian Cloud ID:** use `jira.cloudId`; when absent, look it up:
   ```
   <jira.mcpPrefix>getAccessibleAtlassianResources()
   ```

4. **Check the ticket's current status:**
   ```
   <jira.mcpPrefix>getJiraIssue(cloudId, issueIdOrKey, fields=["status"])
   ```
   - If already "Done", skip the transition.

5. **Get available transitions and transition to Done:**
   ```
   <jira.mcpPrefix>getTransitionsForJiraIssue(cloudId, issueIdOrKey)
   ```
   - Find the transition with `name: "Done"` and use its `id`.
   ```
   <jira.mcpPrefix>transitionJiraIssue(cloudId, issueIdOrKey, transition={id: "<transition-id>"})
   ```

5b. **Close the ticket's sub-tasks → Done.** A decomposed story's sub-tasks reach Done with the story; this sweeps any still open (typically already closed by `/giga-workflow:epic-story-complete`). For an epic-branch-mode **epic** key this is a no-op — epics have no sub-tasks.
   ```
   <jira.mcpPrefix>getJiraIssue(cloudId, issueIdOrKey, fields=["subtasks"])
   ```
   For each sub-task **not already "Done"**, read its transitions and transition it to **Done** (match by name, never guess the id). On any error, note it and continue — do not fail cleanup over a sub-task.

6. **If no ticket key was found** in the branch name, skip this step silently.
7. **If any Atlassian MCP call fails or returns an error** (at any step — cloud ID lookup, issue fetch, transitions fetch, or transition), do not retry. Instead, inform the user:
   > "Could not transition `<KEY>` automatically (Atlassian returned an error). Please mark it Done manually in Jira."
   Then continue with the rest of the cleanup without failing.

## Move the story out of its epic's wave plan

The wave plan lists what is **left**. A merged story that stays in it is drift, and nothing else reconciles it — so retire the entry here, at the one moment the story is genuinely finished.

Skip silently if no ticket key was found.

1. **Find the epic.** `grep -m1 '^epic:' <plans.repo>/<board>/<KEY>.md` (board = the lowercased key prefix, e.g. `ABC-78` → `abc`) gives `epic: <EPIC-KEY>` without reading the story. No such file, or no `epic:` line → skip.
2. **Locate the two sections** in one call, without reading the epic whole:
   ```bash
   S=<plans.script>
   python3 $S section <EPIC-KEY> Wave; python3 $S section <EPIC-KEY> Shipped --range
   ```
   The first prints the wave plan and its line range on stderr; exit 1 means no `Wave` heading, so skip this
   whole section. The second prints `<path> <start> <end>` for `## Shipped`, or exits 1 if the epic has none.
   `Read` only those ranges (`offset`/`limit`): the whole wave range, and just the last ~5 lines of `## Shipped`,
   which is enough to anchor the append. Then edit `<plans.repo>/<board>/<EPIC-KEY>.md`:
   - **Remove** the story's one-line entry from its `### Wave N` section. If that leaves the wave empty, remove the wave heading too.
   - **Append** to the `## Shipped` section (create it if absent), rewriting the line to say what the story *did* rather than what was wrong, and stamping the PR: `- <KEY> — <what shipped, past tense> *(was Wave <N>; PR #<N>)*`. Get the PR number from `gh pr list --state merged --head <branch-name> --json number --jq '.[0].number'` if it is not already known. With no PR (a direct-mode board), stamp the story's last commit on `<git.mainBranch>` instead, `git log -1 --format=%h -E --grep='<KEY>([^0-9]|$)' origin/<git.mainBranch>`: `*(was Wave <N>; <short-sha>)*`.
3. **Commit the plans repo:**
   ```bash
   cd <plans.repo> && git add <board>/<EPIC-KEY>.md && \
   git commit -m "docs(<board>): <KEY> shipped"   # + the session's co-author trailer
   ```
   When `plans.autoPush` is true the repo pushes its own commits, so commit only, never `git push`, and
   ⚠️ never report the commit as unpushed or tell the user to push it. When `plans.autoPush` is false or
   absent, push the commit after committing.

If the epic file has no wave section at all (step 2's first command exits 1), skip — that epic uses a different shape and has nothing to reconcile.

## Close the epic when its last story is Done

An epic whose children are all Done is finished, and nothing else closes it. Run this after the story's own Done
transition, so the live status already counts it.

Skip steps 1–3 silently if no ticket key was found or the plan file named no `epic:`. If the key is itself an
epic-branch-mode **epic**, the Jira leg above already took it to Done, so go straight to step 4.

1. **Count the open children** (live status, one call):
   ```bash
   python3 <plans.script> board --jql 'parent = <EPIC-KEY> AND statusCategory != Done'
   ```
2. **`[]` → transition `<EPIC-KEY>` → Done** — read its transitions and match `Done` by name, never guess the id;
   skip if it is already Done. Any other result leaves the epic as it is.
3. **Do not ask.** A scheduled follow-up action that is not a ticket (a switch to flip after launch) does not keep an
   epic open; open work that matters is a child ticket. On an MCP error, report it and continue.
4. **Hand off to the epic order.** This step runs when the epic is Done: transitioned in step 2, found already Done
   with `[]` open children, or closed as an epic-branch epic. Invoke `<epicCloseSkill> closed <EPIC-KEY>` (Skill tool)
   from this clone, or skip steps 4 and 5 when `epicCloseSkill` is absent. Its `Epic order` / `Plan next` block ends the summary. It runs unattended and asks nothing.
5. **Name the epic review.** Under that block, print `Review: /giga-workflow:epic-review <EPIC-KEY> — before /giga-workflow:epic-plan <NEXT-KEY>`.
   Do not run it here; it drives the app and the owner decides its ideas.

## Clean up plan files

1. **Check for plan files associated with the branch** in `.claude/plans/`:
   ```
   ls .claude/plans/
   ```
2. **Read each plan file** and check if it references the Jira ticket key or the branch name.
3. **If a matching plan file is found**, delete it — the work is complete and merged.
4. **If no plan files exist or none match**, skip silently.

## Return to working branch

1. **If `<original-branch>` is different from `<git.mainBranch>`** (i.e., the user was on a different working branch):
   ```
   git checkout <original-branch>
   ```

## Restore stashed changes

1. **If `needs-stash` was true**, pop the stash to restore uncommitted changes:
   ```
   git stash pop
   ```
   - If the pop fails (e.g., merge conflict), report the warning: "Stashed changes could not be auto-applied. Run `git stash pop` manually to resolve."

## Summary

Output a summary:

```
Post-merge cleanup complete:
- Current branch: <current-branch> (unchanged) or "switched to <git.mainBranch>"
- Deleted local branch: <branch-name> (or "not found locally")
- Deleted remote branch: <branch-name> (or "already removed")
- Jira <KEY>: transitioned to Done (or "no ticket found" or "already Done")
- Sub-tasks: <N> → Done (or "none")
- Wave plan: <EPIC-KEY> — <KEY> moved from Wave <N> to Shipped (or "no wave plan" / "skipped")
- Epic: <EPIC-KEY> → Done, last story shipped (or "<N> children still open" / "already Done" / "skipped")
- Plan file: deleted <filename> (or "no matching plan found")

<When the epic is Done — the <epicCloseSkill> closed block, verbatim:>
Epic order: <EPIC-KEY> removed from the <board> lane
Plan next:  <NEXT-KEY> — <summary> (<status>) → /giga-workflow:epic-plan <NEXT-KEY>
Review:     /giga-workflow:epic-review <EPIC-KEY> — before /giga-workflow:epic-plan <NEXT-KEY>
```
