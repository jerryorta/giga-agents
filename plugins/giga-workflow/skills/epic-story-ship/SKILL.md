---
name: epic-story-ship
description: Take a finished epic story all the way to main and Done in one pass — `/giga-workflow:epic-evolution-audit` (sibling stories checked against what shipped), then `/giga-workflow:epic-story-complete` (commit in strict Commitizen format, push, open the PR, ticket → In Review) immediately followed by `/giga-workflow:epic-merge-pr --yes` (merge per `git.mergeMethod`, verify MERGED, repair local main, chain `/giga-workflow:post-merge-cleanup` → branch deleted, ticket → Done, wave plan reconciled), then commits and pushes to `main` any pending changes in the board's secrets repos (the board's `secretsRepo` payload repo + the shared `secrets.sharedRepo`). ONE confirmation gate at the start covers the whole run; there is no second "merge?" prompt. Use when a story is done and reviewed and the user wants it merged without stopping at the PR — "ship and merge", "complete and merge", "commit, PR and merge", "take it to Done", "ship it all the way", or `/giga-workflow:epic-story-ship` directly. Use `/giga-workflow:epic-story-complete` instead when the PR needs a human review before it merges.
---

`/giga-workflow:epic-evolution-audit` + `/giga-workflow:epic-story-complete` + `/giga-workflow:epic-merge-pr --yes` as one skill: audit the rest of the epic against what this story shipped, commit the unstaged diff, push, open the PR, transition the ticket, then merge that PR on the spot (`git.mergeMethod`) and run `/giga-workflow:post-merge-cleanup` so the story ends **merged on `main` and Done** — with the epic's sibling stories already reflecting it — in the same session, with **one** confirmation gate. The confirmations `/giga-workflow:epic-evolution-audit` and `/giga-workflow:epic-merge-pr` would otherwise ask for are skipped by design: the Step 4 gate of `/giga-workflow:epic-story-complete` already shows everything this run will do, sibling edits and merge included, so a second or third prompt would only re-ask the same question.

The three constituent skills are the procedure. **This file carries only the composition — the order, the batch points, and the amendments to their steps.** Do not re-implement anything they already do.

**Usage:**
- `/giga-workflow:epic-story-ship` — preferred. Infer the board + ticket key from the current conversation context (same resolution chain as `/giga-workflow:epic-story-complete` Step 0).
- `/giga-workflow:epic-story-ship <board> <KEY>` — explicit override.
- `/giga-workflow:epic-story-ship --yes` — skip the single gate too (the pre-flight block still prints for the record). For autonomous callers that have already gated on a validated diff.
- `/giga-workflow:epic-story-ship --type=<type>` — override the conventional-commit type (default: inferred from ticket labels).
- `/giga-workflow:epic-story-ship --build` — re-run `config.buildCommand` before committing. It runs once, before the commit; the merge follows the commit within the same run, so there is no drift window to re-build against and `/giga-workflow:epic-merge-pr --build` is never passed.
- `/giga-workflow:epic-story-ship --keep-storybook` — leave this checkout's Storybook server(s) running.
- `/giga-workflow:epic-story-ship --no-audit` — skip the evolution audit (composition step 0) for a story `/giga-workflow:epic-evolution-audit` § "When NOT to use" excludes — a pure refactor, typo fix or docs-only change. `/giga-workflow:epic-story-complete`'s own Step 2 scan then runs as usual.
- Flags compose: `/giga-workflow:epic-story-ship <board> ABC-123 --type=chore --keep-storybook`.
- **Not accepted:** `--no-push` (a run that ends at a local commit has nothing to merge — use `/giga-workflow:epic-story-complete --no-push`), `--no-cleanup`, `--dry-run`.

**Available boards:** same as `/giga-workflow:epic-next` — defined by `epic.<board>.json` files in `.claude/giga/`.

> **Where this fits in the lifecycle (PR mode):**
> `/giga-workflow:epic-next` → `/giga-workflow:jira` (build + typecheck + lint + test gate) → **`/giga-workflow:epic-story-ship`** ≡ `/giga-workflow:epic-evolution-audit` (sibling drift → plan-file edits) → `/giga-workflow:epic-story-complete` (commit + push + PR + → In Review) → `/giga-workflow:epic-merge-pr --yes` (merge + verify + repair the main branch) → `/giga-workflow:post-merge-cleanup` (delete branch + → Done + wave plan). Same end state as running the three by hand; one gate instead of two, one plans-repo commit instead of two, one notification, one report.

---

## Project config

Repo-specific values come from `.claude/giga/config.json` at the repository root, under `workflow`. Read it once at the start. A missing file or field takes the fallback below, never a guess.

| Field | Used for | When absent |
| --- | --- | --- |
| `plans.script` | the script behind `stub` and `board` (composition step 5, amendment C2) | stop and say the repo has no `plans.script` in `.claude/giga/config.json` |
| `git.mainBranch` | the branch the PR merges into and local sync targets | `main` |
| `git.branchPrefix` | the story branch prefix the refusal check expects | `feat/` |
| `git.mergeMethod` | the `gh pr merge` method flag (`squash`, `merge` or `rebase`) in amendment M1 | `squash` |
| `git.autoMerge` | whether `--auto` may ever be passed | `--auto` is never passed |
| `git.hasCI` | whether checks exist to read | `false`: never wait on or query checks |
| `commit.format` | the commit subject `/giga-workflow:epic-story-complete` writes | `<type>(<scope>): <KEY> <subject>` |
| `secrets.sharedRepo` | the shared secrets repo, committed and pushed after the merge (amendment S1/S2) | the shared leg is skipped |
| `secrets.requirePrivate` | refuse to push a secrets repo whose GitHub visibility is not `PRIVATE` | `true` |
| `docs.secrets` | the secrets guide that explains the payload repo layout | omit the pointer |
| `epicCloseSkill` | the skill invoked when the epic goes Done (amendment C2) | skip the epic-close hand-off and its report block |
| `notify` | the desktop-notification command (amendment A5) | no desktop notification |

The board config's own `secretsRepo` field (path to the domain payload repo, relative to the checkout) selects the domain secrets repo; a board without it has only the shared repo.

---

## When to use / when not to

Use when the story is implemented, `/giga-workflow:jira` Phase 6's gate passed, you have reviewed the unstaged diff, and **nobody else needs to review the PR before it merges** — the normal case on a single-developer board where the PR is a historical record, not a review gate (see `/giga-workflow:epic-merge-pr` § "What this skill does not do").

Reach for `/giga-workflow:epic-story-complete` instead when the PR should sit open for review, and for `/giga-workflow:epic-merge-pr <N>` alone when the PR is already open.

Refuse and stop when:

- The branch is `<git.mainBranch>` or any branch other than the story's `<git.branchPrefix><key-lower>-<slug>` — inherited from `/giga-workflow:epic-story-complete`.
- A PR is already open for this branch — the commit-and-PR half already ran. Point at `/giga-workflow:epic-merge-pr <N>`, which is the remaining half.
- `--no-push` was passed — see Usage.

**Epic-branch boards** (`config.mergeMode === "epic-branch"`) have no per-story PR, and `/giga-workflow:epic-merge-pr` refuses them. On such a board this skill **is** `/giga-workflow:epic-story-complete`: run it unchanged (its own gate, its own report — the story reaches Done on the epic branch there) and add one line to the report saying the merge leg did not apply. Do not invoke `/giga-workflow:epic-merge-pr`.

**Direct boards** (`config.mergeMode === "direct"`) have no PR either, and `/giga-workflow:epic-merge-pr` refuses them too. There this skill also **is** `/giga-workflow:epic-story-complete`, run unchanged: its own merge fast-forwards `<git.mainBranch>` to the story and pushes it, so the story still reaches `<git.mainBranch>` and Done, and it chains `/giga-workflow:post-merge-cleanup` itself. Add one line to the report saying the merge leg did not apply. Do not invoke `/giga-workflow:epic-merge-pr`.

---

## Composition

Invoke each constituent with the `Skill` tool at the point named below and follow its steps, applying the amendments in § Amendments. Where an amendment and the constituent's text differ, **the amendment wins**. Everything else — the Commitizen rules, the type inference table, the ADF comment shape, the evolution-item mechanics, the audit's dimensions and subagent contract, the merge-state table, the branch-deletion and wave-plan mechanics — is theirs, unchanged.

This skill inherits `/giga-workflow:epic-story-complete`'s turn-cost model: it runs at the point of maximum context, so the steps below are **reading order, not one-call-per-message**. Explicit batch points are marked ⚡. Before the gate, the audit costs its discovery reads plus one foreground subagent (its Step 6 model choice stands — do not downgrade it; a wrong sibling edit is the expensive failure). The happy path after the gate is **six messages** (ship → transition + merge → Done + comment + plan edits → plans commit + Storybook + notify + next-story gather → next story's effort → report), plus one if GitHub is still computing mergeability on the first read.

0. **`/giga-workflow:epic-evolution-audit <board> <KEY>`** — Steps 0 → 6 (resolve, candidate discovery, the audit subagent), then stop: its Step 7 gate and Step 8 apply are replaced by amendments E1–E3. Skip this step when `--no-audit` was passed or `config.epicEvolutionRules` is `null` (the audit's own opt-out); an empty candidate set ends it with nothing to carry. ⚡ Issue its Step 0–4 reads in the same message as `/giga-workflow:epic-story-complete` Step 0–1's — both resolve the same board and key.
1. **`/giga-workflow:epic-story-complete <board> <KEY> [--yes] [--type=…] [--build] [--keep-storybook]`** — Steps 0 → 4 unchanged except the evolution scan (amendment A0) and the gate block (amendment A1). **The gate is the only stop in this skill.** `--yes` passes straight through. ⚡ The secrets-repo read (amendment S1) rides in Step 1's `Bash` call.
2. **`/giga-workflow:epic-story-complete` Step 5** — the one-call ship (build if `--build`, commit, push, `gh pr create`). Prints the short SHA and the PR URL; bind the PR number as `N`. Any failure here stops the run **before the merge leg begins** — nothing has merged, and the constituent's own failure handling applies verbatim.
3. ⚡ **One message:** `/giga-workflow:epic-story-complete` Step 6 (→ In Review) + Step 7 (sub-tasks → Done, if any) + **`/giga-workflow:epic-merge-pr N --yes`** Steps 0 → 5c collapsed into the guarded chain in amendment M1. The MCP transitions and the merge chain are independent, so they share the message. If the chain reports a non-proceeding state, apply `/giga-workflow:epic-merge-pr` Step 3's table (amendment M2) and re-issue the chain — that is the one extra message.
4. ⚡ **One message:** `/giga-workflow:epic-merge-pr` Step 6 → **`/giga-workflow:post-merge-cleanup N`** Jira leg (→ Done, amendment C2) + `/giga-workflow:epic-story-complete` Step 8 comment (amendment A3) + Step 10(a) `createJiraIssue` calls for any surviving evolution items + the plan-file edits of `/giga-workflow:epic-story-complete` Step 9, `/giga-workflow:post-merge-cleanup`'s wave-plan step (amendment C3) and the audit's approved sibling edits (amendment E2). Edits that need a freshly minted key (a new story's wave-plan line) wait for that key; everything else lands here.
5. ⚡ **One `Bash` call:** `<plans.script> stub` for each minted key (if any) `&&` the **single** plans-repo commit (amendment A4) `&&` `${CLAUDE_SKILL_DIR}/../epic-story-complete/scripts/stop-storybook.sh` (unless `--keep-storybook`) `&&` the `<notify>` call (amendment A5; skipped when `notify` is absent). `TaskStop` any Storybook `Monitor` first, as `/giga-workflow:epic-story-complete` Step 11 says. `/giga-workflow:post-merge-cleanup`'s `.claude/plans/` sweep and branch-deletion checks fold into this call too (amendment C1), and so does the next-story lookup (amendment M4). The secrets-repo commit + push (amendment S2) closes the call, joined with `;` so a secrets failure never blocks the rest.
6. **Report** — § Final report. No constituent's report prints; this one replaces all three (amendments E1, A6, M3).

---

## Amendments

### To `/giga-workflow:epic-evolution-audit`

**E1 — no gate of its own.** Its Step 7 digest and `yes / pick / no` prompt do not run; the digest's content moves into the `Story ship` gate (amendment A1), where each stale sibling is listed with its one-line drift summary. Approving the gate approves every listed edit; the user strikes a sibling there to decline its edit — the `pick` path, folded into the gate's `edit` response. `--yes` applies every edit, as the audit's own `yes` would. Its Step 9 report does not print either; the outcome is § Final report's `Audit:` line.

**E2 — apply edits after the gate, inside composition step 4.** Its Step 8 find-and-replace on each approved sibling's local plan file runs in the plan-file-edit message, and rides amendment A4's single plans-repo commit. Its atomicity rule holds: a "Replacing" block not found verbatim skips that sibling and becomes a line in the report — never a partial write.

**E3 — new-story recommendations become evolution items.** They seed `/giga-workflow:epic-story-complete`'s `epicEvolutionItems` as `(a) New story` entries (amendment A0), so Step 10(a) mints them after the gate rather than leaving them as the audit's "user action" suggestions. On a `type: bug` ticket the board's bug rule still suppresses minting — the audit returns verdicts and sibling edits only.

### To `/giga-workflow:epic-story-complete`

**A0 — Step 2 takes the audit's findings.** When composition step 0 ran, Step 2 does not repeat the cross-story scan: `epicEvolutionItems` = the audit's new-story recommendations (amendment E3) plus the audit's stale-sibling edits as `description edit` items, each marked `(audit)`. Anything this session surfaced that the audit did not cover — a discovered gap outside the sibling set — is still added by Step 2's own rules. With `--no-audit`, Step 2 runs unchanged.

**A1 — Step 4 gate block.** Head it `Story ship` and replace the `Ticket status`, `Push`, `PR` lines and add `Audit`, `Merge` + `Cleanup` so the block states the whole run — it is the only place the user approves the sibling edits and the merge:

```
Audit:            <N> siblings of <config.epicKey> audited — <X> stale · <Y> clean · <Z> new-story
                  | skipped (--no-audit) | skipped (epicEvolutionRules: null) | failed — <reason>
Ticket status:    <current status>  →  In Review  →  Done

Push:             yes   → git push -u origin <branch>
PR:               will open via gh after push
Merge:            <git.mergeMethod> + delete branch, immediately after the PR opens — no second gate
Cleanup:          /giga-workflow:post-merge-cleanup → <KEY> → Done · wave plan reconciled · local <git.mainBranch> synced
Secrets:          <domain repo> — <N> pending: <paths> → commit + push to <git.mainBranch> | clean | skipped — <reason>
                  <secrets.sharedRepo> — <N> pending: <paths> → commit + push to <git.mainBranch> | clean | skipped — <reason>
```

The stale siblings and new-story recommendations print under the block's existing epic-evolution items, marked `(audit)`, each with its one-line drift summary; the full proposed-vs-replacing text is available on `edit`. Everything else in the block — the inference provenance lines, the proposed commit, `Build re-run`, `Final comment`, `Storybook`, `Files` — stays as the constituent prints it. The `yes` / `no` / `edit` responses and the `--yes` behaviour are unchanged. Anything the user strikes or amends here is the final say for the whole run, sibling edits and merge included.

**A2 — Step 6 (→ In Review) stays.** The ticket is Done a minute later, but the review state is the transition the Done transition is known to be reachable from, and it costs nothing — it shares a message with the merge chain. Do not skip it and do not try In Progress → Done directly.

**A3 — Step 8 comment: post it after the merge, headed `Merged`.** Same ADF shape with two changes — the heading text is `Merged`, and the `Commit:` paragraph names the **merge commit on `<git.mainBranch>`** (the `sha` from the merge chain's verification read), not the branch commit: `Commit: <merge-sha> on <git.mainBranch> (epic <config.epicKey>).` The PR paragraph is unchanged. Posting it before the merge would record a state the ticket left seconds later.

**A4 — Step 10(d): one plans-repo commit for the whole run.** It also carries `/giga-workflow:post-merge-cleanup`'s wave-plan edit (amendment C3) and the audit's sibling edits (amendment E2). Subject: `docs(<board>): <KEY> shipped` when there are no follow-ups, `docs(<board>): <KEY> shipped + follow-ups <NEW-KEYS>` when there are; append ` · audit <SIBLING-KEYS>` when sibling edits landed. The push rules in that step are unchanged — commit only; the repo pushes itself.

**A5 — Step 11 notification body:** `'<KEY> · story shipped — PR #<N> merged + Done'`. Same `<KEY> · <task>` format, same handoff file, same one-ping rule.

**A6 — Step 12 does not print.** This skill's § Final report replaces it.

### To `/giga-workflow:epic-merge-pr`

**M1 — Steps 0 → 5c are one guarded `Bash` chain.** Step 0 (resolve) is already done — `N` came out of `gh pr create`; Step 1's board guard was settled at composition (an epic-branch board never reaches here); Step 4's gate is `--yes`; `--build` is never passed (see Usage). What remains is read state → merge if the state permits → verify → sync local `<git.mainBranch>`, and the state read guards the merge so the happy path is a single call:

```bash
s=$(gh pr view <N> --json mergeStateStatus --jq .mergeStateStatus) && case "$s" in
  CLEAN|UNSTABLE|HAS_HOOKS)
    gh pr merge <N> --<git.mergeMethod> --delete-branch \
    && gh pr view <N> --json state,mergedAt,mergeCommit --jq '{state,mergedAt,sha:.mergeCommit.oid}' \
    && git checkout -q <git.mainBranch> && git fetch -q origin && git pull -q --ff-only \
    && git rev-list --left-right --count <git.mainBranch>...origin/<git.mainBranch> ;;
  *) echo "mergeStateStatus=$s — not merged" ; false ;;
esac
```

Print the `/giga-workflow:epic-merge-pr` Step 4 pre-flight block in the same message, as its audit trail. The verification read's `state`/`mergedAt`/`sha` are Step 5b's ground truth — require `MERGED` with a non-null `mergedAt`; the final `rev-list` line is Step 5c's `0	0`. A non-zero *left* count is the constituent's stop-and-report case. Its `⚠️` on `statusCheckRollup` / `gh pr checks` holds, as does its `--auto` rule (`git.autoMerge`: never `--auto` unless true; this chain merges immediately and does not use it). With `git.hasCI` false no checks are queried or awaited.

**M2 — a non-proceeding state.** The chain prints `mergeStateStatus=<s> — not merged` and exits non-zero; apply Step 3's table to `<s>` and re-issue the chain **once**:

- `UNKNOWN` is the **expected** first read here — the PR is seconds old and GitHub computes mergeability lazily. Re-issue the chain on the next message; do not `sleep`, the next message is already later than any wait you would script.
- `BEHIND` → `gh pr update-branch <N>` first, then re-issue.
- `DIRTY` / `BLOCKED` / `CLOSED`, or a second non-proceeding read → **stop** (see § Failure handling). Do not run cleanup.

**M3 — Step 7 does not print.** § Final report replaces it.

**M4 — Step 6b rides in composition step 5.** Its gather command (To Do keys + wave-plan section) runs in the same `Bash` call, after the plans commit, so the shipped story is already out of its wave. Pick the next story from that output, then read its `effort:` with one more `grep` — the one extra message this adds. Its `Next` / `Effort` lines end § Final report.

### To `/giga-workflow:post-merge-cleanup`

**C1 — branch + tree.** `gh pr merge --delete-branch` already deleted the local and remote branch and left the checkout on a synced `<git.mainBranch>` with a clean tree (Step 5 committed everything). Its stash / checkout / pull preamble has nothing to do; its local-delete reports *not found locally* and its remote check *already removed* — those are the expected outcomes, not failures. `git remote prune origin` and the `.claude/plans/` sweep still run, inside the § Composition step 5 `Bash` call.

**C2 — Jira leg without re-reads.** The ticket's status is In Review (Step 6 just set it) and its sub-tasks are Done (Step 7 just closed them, or there were none) — do not re-fetch either. Transition `<KEY>` → Done (match by name), and re-transition only a sub-task Step 7 reported as a straggler. Its *Close the epic when its last story is Done* check still runs: the open-children `board` query rides in composition step 5's `Bash` call (after the Done transition has landed), and a `[]` result transitions the epic → Done in the report message. In that same message, invoke the skill named in `epicCloseSkill` as `<epicCloseSkill> closed <EPIC-KEY>`; its block ends § Final report. Without `epicCloseSkill` this hand-off is skipped.

**C3 — wave plan: the cleanup's edit, without its commit.** `/giga-workflow:post-merge-cleanup`'s wave-plan step runs as written. It removes the story's `### Wave N` entry (and the wave heading if that empties it) and writes the story's one `## Shipped` line; `/giga-workflow:epic-story-complete` Step 9 writes none on a PR board. Stamp the line with this run's PR number `N`, with no `gh pr list` lookup. Its own plans-repo commit is dropped: the edit rides in amendment A4's single commit.

### Secrets repos

The board's secrets repos are the domain payload repo, named by the board config's `secretsRepo` (a path relative to the checkout, resolved as a sibling; layout in `docs.secrets`), plus the shared repo `secrets.sharedRepo`. A board without `secretsRepo` has only the shared repo; with neither, the secrets leg is skipped entirely and the gate's `Secrets:` lines read `skipped — no secrets repo configured`.

**S1 — read before the gate.** For each repo, resolve the real path (`cd -P`, since the sibling may be a symlink). Then `git fetch -q`, and read its branch, `git status --porcelain` and `git rev-list --left-right --count HEAD...@{u}`. **Print paths only — never `git diff` or a file's contents; they are secrets.** The gate's `Secrets:` lines (amendment A1) list every pending path, whether or not this story made it. The user strikes a path or a whole repo there, and that is the final say. A repo is `skipped — <reason>` at the gate if it is missing, not on `<git.mainBranch>`, or ahead/behind/diverged from `origin/<git.mainBranch>`.

**S2 — commit + push after the merge.** This runs as the last group in composition step 5, for each repo with approved paths:

```bash
( cd "<repo>" \
  && [ "$(git rev-parse --abbrev-ref HEAD)" = <git.mainBranch> ] \
  && [ "$(gh repo view --json visibility -q .visibility)" = PRIVATE ] \
  && git pull -q --ff-only \
  && git add -- <approved paths> \
  && git commit -q -m "chore: <KEY> commit pending secrets" -m "<co-author trailer>" \
  && git push -q origin <git.mainBranch> \
  && echo "<repo>: pushed $(git rev-parse --short HEAD)" ) || echo "<repo>: NOT pushed"
```

Stage the approved paths by name, never `git add -A`. A struck path stays uncommitted. Never force-push. Never push a repo whose GitHub visibility is not `PRIVATE` (the check runs when `secrets.requirePrivate` is true or absent; when it is false, drop that line from the chain). A clean repo prints `clean` and runs nothing.

**S3 — no secrets repo pushes when leg 2 stops.** If the merge did not land, composition step 5 does not run, and the secrets stay uncommitted with the rest. Report them as pending.

---

## Failure handling

The run is two legs after the audit, and the seam between them is a safe place to stop.

- **The audit fails** (its subagent returns malformed output twice, or discovery errors out) — nothing has been written. Report it on the gate's `Audit:` line as `failed — <reason>` and let the gate decide: `yes` ships without sibling edits (Step 2's own scan then runs, as with `--no-audit`), `no` stops so the audit can be re-run. With `--yes`, ship and carry the failure into § Final report. A single sibling's edit failing to apply after the gate is amendment E2's skip, not a run failure.
- **Leg 1 fails** (build, pre-commit hook, push, `gh pr create`) — `/giga-workflow:epic-story-complete` Step 5's handling applies verbatim. Nothing merged; the PR either does not exist or is open on an un-transitioned ticket. Fix and re-run this skill (or `/giga-workflow:epic-merge-pr <N>` if the PR did open).
- **Leg 2 stops** (`DIRTY`, `BLOCKED`, `CLOSED`, a persistent non-proceeding state, or a verification read that is not `MERGED`) — the story is exactly where `/giga-workflow:epic-story-complete` alone leaves it: committed, pushed, PR open, ticket In Review. Report that state and the merge blocker; the user resumes with `/giga-workflow:epic-merge-pr <N>` once it is cleared. Do **not** run cleanup — deleting a branch whose PR did not merge loses the work.
- **After the merge** (a Done transition, the comment, a plan-file edit, a minted follow-up, a secrets-repo push, Storybook) — the constituents' shared rule: nothing rolls the merge back; report the failure as an explicit line and continue.
- **`gh` 403 on any call** — an auth problem, not a PR problem. Report it verbatim and stop.

---

## Final report

The skill's only prose output. Print it once, then stop.

```
✓ Story <KEY> shipped — merged on <git.mainBranch> + Done
Commit:    <branch-sha> — <subject>
Merged:    PR #<N> → <merge-sha> on <git.mainBranch> (<git.mergeMethod>) — <PR URL>
Branch:    <branch> deleted (local + remote) · local <git.mainBranch> synced ✓
Ticket:    <KEY> → In Review → Done
Sub-tasks: <N> → Done | none
Comment:   posted ✓ | skipped
Outcome:   <board>/<KEY>.md § Outcome ✓ (<N> pin(s)) | nothing pinned
Wave plan: <config.epicKey> — <KEY> Wave <N> → Shipped ✓
Epic:      <EPIC-KEY> → Done (last story shipped) | <N> children still open
Audit:     <K> sibling edit(s) applied — <SIBLING-KEYS> | <Z> skipped (<why>) | none stale | skipped (--no-audit | opt-out) | failed — <reason>
Plans:     committed (auto-sync pushes it)
Secrets:   <domain repo> <sha> pushed | clean | NOT pushed — <reason> · <secrets.sharedRepo> <same>
Storybook: <the script's own output lines>

<If epicEvolutionItems was non-empty — the same block /giga-workflow:epic-story-complete Step 12 prints>

Next:      <NEXT-KEY> — <summary> (<config.groupLabel> <N>) → /giga-workflow:epic-next <board>
Effort:    <effort> — run `/effort <effort>` before /giga-workflow:epic-next
```

`Next` / `Effort` follow `/giga-workflow:epic-merge-pr` Step 7's rules: no `Effort` line without an `effort:` key, and `Next: none — <config.completionMessage>` when no story is To Do. When the epic went Done, the `<epicCloseSkill> closed` block (`Epic order` / `Plan next … → /giga-workflow:epic-plan <NEXT-KEY>`) follows verbatim, last.

---

## Notes

- **PR-mode boards only, by design.** `/giga-workflow:epic-merge-pr` refuses epic-branch and direct boards; on those this skill degrades to `/giga-workflow:epic-story-complete`, which already takes the story to Done on the epic branch, or onto `<git.mainBranch>` on a direct board.
- **`/giga-workflow:epic-loop`'s story agent runs the same chain** (`/giga-workflow:epic-story-complete --yes` → `/giga-workflow:epic-merge-pr --yes`); its autonomy contract owns that wording. This skill is the interactive equivalent — one gate for a human, then the same end state.
- **Canonical notification behavior** (per-repo handoff file queued by `<notify>`, keyed by the session's git toplevel so sessions in sibling clones never take each other's message; `<KEY> · <task>` body, title + subtitle auto-stamped by the global Stop hook) is shared with `/giga-workflow:epic-story-complete`, `/giga-workflow:epic-next`, and `/notify`. If you change the format, update all of them together.
