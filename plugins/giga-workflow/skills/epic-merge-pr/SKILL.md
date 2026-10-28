---
name: epic-merge-pr
description: "Merge a finished story's pull request and hand off to cleanup: resolve the PR, verify it is open and conflict-free, merge it (`git.mergeMethod`), confirm the merge landed, then chain `/giga-workflow:post-merge-cleanup`. The missing link between `/giga-workflow:epic-story-complete` (which opens the PR and moves the ticket to In Review) and `/giga-workflow:post-merge-cleanup` (which deletes the branch and moves it to Done): $ARGUMENTS"
---

Merge a finished story's pull request and hand off to cleanup: resolve the PR, verify it is open and conflict-free, merge it (`git.mergeMethod`), confirm the merge landed, then chain `/giga-workflow:post-merge-cleanup`. The missing link between `/giga-workflow:epic-story-complete` (which opens the PR and moves the ticket to In Review) and `/giga-workflow:post-merge-cleanup` (which deletes the branch and moves it to Done): $ARGUMENTS

**Usage:**
- `/giga-workflow:epic-merge-pr` — preferred. Resolve the PR from the current branch.
- `/giga-workflow:epic-merge-pr <PR#>` — explicit PR number (`962` or `#962`).
- `/giga-workflow:epic-merge-pr <branch>` — explicit branch name.
- `/giga-workflow:epic-merge-pr --yes` — skip the Step 4 confirmation gate. For autonomous callers like `/giga-workflow:epic-loop`.
- `/giga-workflow:epic-merge-pr --no-cleanup` — merge only; leave `/giga-workflow:post-merge-cleanup` to the caller.
- `/giga-workflow:epic-merge-pr --build` — re-run the board's `buildCommand` against the branch before merging. Off by default (see "What this skill does not do").
- `/giga-workflow:epic-merge-pr --dry-run` — report what would happen; merge nothing.
- Flags compose: `/giga-workflow:epic-merge-pr 962 --yes --no-cleanup`.

> **Already merged it on github.com? Still run this.** The skill is idempotent — Step 3 reads
> `state == "MERGED"` and skips straight to cleanup. Reviewing and merging in the GitHub UI is a
> normal path here, not a reason to reach for `/giga-workflow:post-merge-cleanup` directly: this skill still
> deletes the branch, sweeps the Jira transitions, reconciles the wave plan, and — the part a UI
> merge always skips — repairs a local `<git.mainBranch>` that `--delete-branch` left a commit behind, which is
> the tree the next story's branch gets cut from.

> **Where this fits in the lifecycle (PR mode):**
> `/giga-workflow:epic-next` → `/giga-workflow:jira` (build + typecheck + lint + test gate) → `/giga-workflow:epic-story-complete` (commit + push + PR + → In Review) → **`/giga-workflow:epic-merge-pr`** (merge) → `/giga-workflow:post-merge-cleanup` (delete branch + → Done).
>
> `/giga-workflow:epic-story-ship` runs `/giga-workflow:epic-story-complete` and this skill (`--yes`) as one pass behind a single gate. When that run stops at its merge leg, the PR is open and the ticket is In Review — this skill, invoked with the PR number, is the resume point.

---

## Project config

Repo-specific values come from `.claude/giga/config.json` at the repository root, under `workflow`. Read it once at the start. A missing file or field takes the fallback below, never a guess.

| Field | Used for | When absent |
| --- | --- | --- |
| `git.mainBranch` | the base branch the PR merges into and the local branch Step 5c repairs | `main` |
| `git.branchPrefix` | the story branch prefix Step 1 parses the ticket key from | `feat/` |
| `git.mergeMethod` | the `gh pr merge` method flag (`squash`, `merge` or `rebase`) | `squash` |
| `git.autoMerge` | whether Step 5 may pass `--auto` | `--auto` is never passed |
| `git.hasCI` | whether checks exist to wait on | `false`: never wait on or query checks |
| `plans.repo` | the plans repo holding ticket and epic plan files (Steps 6, 6b) | skip Step 6b and say the repo has no `plans.repo` |
| `plans.script` | the script behind `ensure` and `board` (Step 6b) | skip Step 6b and say the repo has no `plans.script` |
| `epicCloseSkill` | the skill whose `Epic order` / `Plan next` block ends the report when cleanup closed the epic | omit that block |

---

## What this skill does not do

**It does not re-run build, lint, or tests, and it does not wait on CI.** That is deliberate, not an
oversight (CI is described by `git.hasCI`; when it is true, the PR's `mergeStateStatus` already reflects
required checks and Step 3's table handles it):

- The gate already ran. `/giga-workflow:jira` Phase 6 runs `nx run <project>:build`, `:typecheck`, `:lint`, and
  `:test` for every affected project plus the app build, and blocks on any failure — **before**
  `/giga-workflow:epic-story-complete`
  commits and pushes. `/giga-workflow:epic-story-complete` itself trusts those results by design.
- With `git.hasCI` false there is no CI to wait on: GitHub and Jira carry historical tracking, not
  development gates.
- There is no drift window worth closing. In the sequential story loop each branch is cut from a
  freshly-pulled `<git.mainBranch>` immediately after the previous story merged, so the tree the gate ran against
  and the tree that lands are the same tree.

`--build` exists for the one case the above does not cover: a long pause between `/giga-workflow:jira` finishing and
this skill running, where `<git.mainBranch>` may have moved underneath the branch. Use it deliberately; do not
wire it on by default.

⚠️ **Never query `statusCheckRollup`, and never run `gh pr checks`.** The local `gh` token can return
`Resource not accessible by personal access token` for both, so a naive check reads as a hard failure
on a perfectly mergeable PR.

---

## Step 0 — Resolve the PR

Resolve in this order and stop at the first hit:

1. **Explicit PR number** — `$ARGUMENTS` contains a purely numeric token (strip a leading `#`). Use it.
2. **Explicit branch name** — a non-numeric, non-flag token. Look the PR up:
   ```bash
   gh pr list --head <branch> --state all --json number,state --jq '.[0]'
   ```
3. **Current branch** — the normal path straight out of `/giga-workflow:epic-story-complete`:
   ```bash
   gh pr list --head "$(git branch --show-current)" --state open --json number --jq '.[0].number'
   ```
4. **Conversation context** — the PR number `/giga-workflow:epic-story-complete` just reported.

If nothing resolves, run Step 1's direct-mode guard on the branch searched (a direct-mode board never has a PR), then report which branch was searched and stop. Do not guess a PR number.

## Step 1 — Board guard

Derive the ticket key from the PR's `headRefName` (`<git.branchPrefix><key-lower>-<slug>` → uppercase the key) and
match its prefix against each `epic.*.json`'s `epicKey` prefix to resolve the board. Read that config.

**If `config.mergeMode === "epic-branch"`, stop.** Those boards have no per-story PR — stories are
committed straight onto `config.epicBranch` and taken to Done by `/giga-workflow:epic-story-complete`, and the epic
lands via a single PR at the end. Report that, and when the whole epic is Done, surface the
epic-landing block for the user to run (don't run it):

```
gh pr create --base <git.mainBranch> --head <config.epicBranch> --title "<epic key> <epic name>"
# after it merges:
/giga-workflow:post-merge-cleanup <config.epicBranch>
```

**If `config.mergeMode === "direct"`, stop.** Stories on those boards merge at `/giga-workflow:epic-story-complete`, which fast-forwards `<git.mainBranch>` to the story branch and pushes it, so there is no PR to merge. If the current branch is an unmerged story branch with commits, point at `/giga-workflow:epic-story-complete`.

A board that cannot be resolved is not fatal — continue without `config`; only `--build` needs it.

## Step 2 — Read the PR's state

```bash
gh pr view <N> --json number,title,url,state,isDraft,mergeable,mergeStateStatus,headRefName,baseRefName
```

Bind `state`, `isDraft`, `mergeable`, `mergeStateStatus`, `headRefName`.

## Step 3 — Gate on state

| Condition | Action |
|---|---|
| `state == "MERGED"` | Already merged. Skip to Step 6 (cleanup) — this skill is idempotent. |
| `state == "CLOSED"` | Stop. The PR was closed without merging; report and let the user decide. |
| `isDraft == true` | Stop. Report that the PR is still a draft. |
| `mergeStateStatus` ∈ `CLEAN`, `UNSTABLE`, `HAS_HOOKS` | Proceed to Step 4. |
| `mergeStateStatus == "BEHIND"` | `gh pr update-branch <N>`, re-read Step 2 **once**, then re-evaluate. If it does not reach a proceeding state, stop. |
| `mergeStateStatus == "DIRTY"` | **Stop and escalate.** A real merge conflict. Never auto-resolve one — report the conflicting branch and let a human drive. |
| `mergeStateStatus == "BLOCKED"` | Stop. Report the block (usually a review requirement); do not attempt `--admin`. |
| anything else / `mergeable == "UNKNOWN"` | GitHub is still computing mergeability. Wait ~5s, re-read once, then treat the result on its merits. |

## Step 4 — Confirmation gate

Print this block regardless of `--yes` — it is the audit trail:

```
Merge pre-flight
  PR:        #<N> — <title>
  Branch:    <headRefName> → <baseRefName>
  Ticket:    <KEY>  (board: <board>)
  State:     <state> / <mergeStateStatus>
  Build:     re-run | skipped (gate ran in /giga-workflow:jira Phase 6)
  Method:    <git.mergeMethod> + delete branch
  Cleanup:   /giga-workflow:post-merge-cleanup | skipped (--no-cleanup)
```

- **Interactive** — confirm with `AskUserQuestion` (merge / cancel). Do not merge before approval.
- **`--yes`** — proceed straight to Step 5. Intended for `/giga-workflow:epic-loop`, which has already gated on a
  story agent's completed gate + a shipped PR.
- **`--dry-run`** — stop here and report.

## Step 4b — Optional build (`--build` only)

Run `config.buildCommand` from the repo root, on the PR's head branch. Any non-zero exit stops the
skill before the merge — report the failing output and leave the PR open.

## Step 5 — Merge

```bash
gh pr merge <N> --<git.mergeMethod> --delete-branch
```

With `squash`, `<git.mainBranch>` holds one commit per story, matching the existing history.

**Do not pass `--auto` unless `git.autoMerge` is true.** Auto-merge queues a PR behind required status
checks; with no CI (`git.hasCI` false) there is nothing to wait on, and the call errors on repos where
auto-merge is not enabled. A direct merge is both correct and observable then.

If the merge command fails, do not retry blindly — re-read Step 2 and report the current
`mergeStateStatus`, which is what actually changed.

## Step 5b — Verify it landed

The exit code is not the ground truth; the PR's state is:

```bash
gh pr view <N> --json state,mergedAt,mergeCommit --jq '{state,mergedAt,sha:.mergeCommit.oid}'
```

Require `state == "MERGED"` with a non-null `mergedAt`. Anything else — report it and **do not run
cleanup**; deleting a branch whose PR did not merge loses the work.

## Step 5c — Sync the local default branch

`gh pr merge --delete-branch` switches back to `<git.mainBranch>` and tries to update it, but it can fail with
only a **warning** — `! warning: not possible to fast-forward to: "<git.mainBranch>"` — leaving the local
checkout behind the merge it just made. The remote is correct and `gh pr view` reports `MERGED`, so
nothing looks wrong; the working tree is simply a commit stale. The
checkout can still hold the pre-merge files afterwards.

That matters here because the next story branch is cut from **local** `<git.mainBranch>`. Verify and repair:

```bash
git fetch origin
git rev-list --left-right --count <git.mainBranch>...origin/<git.mainBranch>   # want "0	0"
git pull --ff-only                                     # if behind
```

A non-zero *left* count (local ahead of origin) is not a stale checkout — stop and report it, since
something committed to `<git.mainBranch>` directly.

## Step 6 — Chain cleanup

Unless `--no-cleanup`, invoke `/giga-workflow:post-merge-cleanup <N>`. It owns the rest and already handles all of
it: deleting the local + remote branch, transitioning `<KEY>` → Done (plus its sub-tasks), moving the
story out of its epic's `### Wave N` section into `## Shipped` in
`<plans.repo>/<board>/<EPIC-KEY>.md`, and deleting any matching `.claude/plans/` file.

Do not duplicate any of that here.

## Step 6b — Look up the next story and its effort

Runs after cleanup, so the merged story is Done and out of its wave. Skip it when `config` is
unresolved (Step 1) or when invoked by `/giga-workflow:epic-loop` — the orchestrator picks the next story itself.

This is `/giga-workflow:epic-next` Steps 5 → 7, read-only, and the pick is yours, not a regex's. One call gathers
the To Do keys and the epic's wave-plan section:

```bash
epic=$(python3 <plans.script> ensure <config.epicKey>)
python3 <plans.script> board --jql '<config.jql>' | python3 -c "import json,sys;print('To Do:',' '.join(i['key'] for i in json.load(sys.stdin)))"
awk 'tolower($0) ~ /^## wave plan/ {f=1; next} /^## /{f=0} f' "$epic"
```

Take the first story **entry** in wave order whose key is To Do. Wave plans are hand-written and vary by
board — `- KEY — …` lines, `- KEY: …`, numbered prose with keys mid-sentence — and a note above the
first wave can name a later story in passing, so a first-key-in-the-section regex picks wrong. With no wave-plan section, read the ordered list the way
Step 5 of `/giga-workflow:epic-next` does; a `config.storyOrdering === "jql"` board takes the first To Do key.

Then read its effort fresh — the owner edits the plan-file front matter by hand:

```bash
grep -m1 '^effort:' "$(python3 <plans.script> ensure <NEXT-KEY>)"
```

The owner sets `/effort` from this line before starting the next story, so it is what the report ends on.

## Step 7 — Report

```
Merged PR #<N> — <title>
  Commit:   <sha> on <baseRefName>
  Ticket:   <KEY> → Done            (or: held — skills repo unpushed; or: cleanup skipped)
  Branch:   <headRefName> deleted   (local + remote)
  Wave:     <KEY> moved to Shipped in <EPIC-KEY>
  Next:     <NEXT-KEY> — <summary> (<config.groupLabel> <N>) → /giga-workflow:epic-next <board>
  Effort:   <effort> — run `/effort <effort>` before /giga-workflow:epic-next
```

`Next` / `Effort` come from Step 6b. Omit `Effort` when the plan file has no `effort:` key; when no
story is To Do, print `Next: none — <config.completionMessage>` and no `Effort` line; omit both when
Step 6b was skipped. When cleanup closed the epic, end the report with its `Epic order` / `Plan next` block
from `<epicCloseSkill> closed`, verbatim. `Plan next` is the epic this board should `/giga-workflow:epic-plan` next.

When invoked by `/giga-workflow:epic-loop`, the surrounding story agent folds this into its JSON report — do not
write a desktop notification here. The caller owns the notification handoff.

## Error handling

- **No PR found** — report the branch searched and stop. Never merge a PR you inferred loosely.
- **`DIRTY` / conflict** — stop and escalate. This is one of `/giga-workflow:epic-loop`'s hard-stop triggers.
- **Merge succeeded but `state != MERGED`** — treat as failure, skip cleanup, report both signals.
- **`gh` 403 on any call** — an auth problem, not a PR problem. Report it verbatim and stop; the loop
  treats it as a run-level escalation rather than a story failure.
