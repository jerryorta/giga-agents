---
name: epic-story-ship
description: Take a finished epic story all the way to main and Done in one pass — `/giga-workflow:epic-evolution-audit` (sibling stories checked against what shipped), then `/giga-workflow:epic-story-complete --merge`, whose one script call commits in strict Commitizen format, pushes, opens the PR, moves the ticket to In Review, merges per `git.mergeMethod`, verifies MERGED, syncs local main, moves the ticket to Done, reconciles the wave plan, and commits and pushes any approved pending changes in the board's secrets repos (the board's `secretsRepo` payload repo + the shared `secrets.sharedRepo`). ONE confirmation gate at the start covers the whole run; there is no second "merge?" prompt. Use when a story is done and reviewed and the user wants it merged without stopping at the PR — "ship and merge", "complete and merge", "commit, PR and merge", "take it to Done", "ship it all the way", or `/giga-workflow:epic-story-ship` directly. Use `/giga-workflow:epic-story-complete` instead when the PR needs a human review before it merges.
---

`/giga-workflow:epic-evolution-audit` + `/giga-workflow:epic-story-complete --merge` behind one gate: audit the rest of the epic against what this story shipped, then commit, push, open the PR and merge it on the spot so the story ends **merged on `main` and Done**, with the epic's siblings already reflecting it. Everything after the gate is one call to `/giga-workflow:epic-story-complete`'s `scripts/ship.py`; the session's part is the audit, the gate, the sibling edits and the report.

The two constituent skills are the procedure. **This file carries only the composition and the amendments to their steps.** Do not re-implement anything they already do.

**Usage:**
- `/giga-workflow:epic-story-ship` — preferred. Infer the board + ticket key from the current conversation context (same resolution chain as `/giga-workflow:epic-story-complete` Step 0).
- `/giga-workflow:epic-story-ship <board> <KEY>` — explicit override.
- `/giga-workflow:epic-story-ship --yes` — skip the single gate too (the pre-flight block still prints for the record). For autonomous callers that have already gated on a validated diff.
- `/giga-workflow:epic-story-ship --type=<type>` — override the conventional-commit type (default: inferred from ticket labels).
- `/giga-workflow:epic-story-ship --build` — re-run `config.buildCommand` before committing.
- `/giga-workflow:epic-story-ship --keep-storybook` — leave this checkout's Storybook server(s) running.
- `/giga-workflow:epic-story-ship --no-audit` — skip the evolution audit for a story `/giga-workflow:epic-evolution-audit` § "When NOT to use" excludes — a pure refactor, typo fix or docs-only change. `/giga-workflow:epic-story-complete`'s own Step 2 scan then runs as usual.
- **Not accepted:** `--no-push` (a run that ends at a local commit has nothing to merge — use `/giga-workflow:epic-story-complete --no-push`), `--no-cleanup`, `--dry-run`.

**Available boards:** same as `/giga-workflow:epic-next` — defined by `epic.<board>.json` files in `.claude/giga/`.

---

## Project config

Repo-specific values come from `.claude/giga/config.json` at the repository root, under `workflow`. Read it once at the start. A missing file or field takes the fallback below, never a guess. `/giga-workflow:epic-story-complete`'s table covers every field its steps and script read.

| Field | Used for | When absent |
| --- | --- | --- |
| `git.mainBranch` | the branch the PR merges into, and the branch each secrets repo must be on | `main` |
| `git.mergeMethod` | the `gh pr merge` method the script uses | `squash` |
| `secrets.sharedRepo` | the shared secrets repo, committed and pushed after the merge (S1/S2) | the shared leg is skipped |
| `secrets.requirePrivate` | refuse to push a secrets repo whose GitHub visibility is not `PRIVATE` | `true` |
| `docs.secrets` | the secrets guide that explains the payload repo layout | omit the pointer |
| `epicCloseSkill` | the skill invoked when the epic goes Done | skip the epic-close hand-off |

The board config's own `secretsRepo` field (path to the domain payload repo, relative to the checkout) selects the domain secrets repo; a board without it has only the shared repo.

---

## When to use / when not to

Use when the story is implemented, `/giga-workflow:jira` Phase 6's gate passed, you have reviewed the unstaged diff, and **nobody else needs to review the PR before it merges** — the normal case on a single-developer board where the PR is a record of completion, not a review gate.

Reach for `/giga-workflow:epic-story-complete` instead when the PR should sit open for review, and for `/giga-workflow:epic-merge-pr <N>` alone when the PR is already open. Refuse and stop on everything `/giga-workflow:epic-story-complete` refuses (its preflight's `Refuse:` line), including an open PR — point at `/giga-workflow:epic-merge-pr <N>`.

**Epic-branch and direct boards and skill-only stories** have no PR to merge. There this skill **is** `/giga-workflow:epic-story-complete`, fed by the audit (A0) and the secrets read (S1): the script already takes the story to Done. Add one line to the report saying the merge leg did not apply.

---

## Composition

0. **`/giga-workflow:epic-evolution-audit <board> <KEY>`** — Steps 0 → 6 (resolve, candidate discovery, the audit subagent), then stop: its Step 7 gate and Step 8 apply are replaced by E1–E3. Skip it with `--no-audit` or when `config.epicEvolutionRules` is `null`. ⚡ Issue its Step 0–4 reads in the same message as `/giga-workflow:epic-story-complete` Steps 0–1.
1. **`/giga-workflow:epic-story-complete <board> <KEY> --merge [--yes] [--type=…] [--build] [--keep-storybook]`** — Steps 0 → 4, with A0 (evolution scan), A1 (gate block) and S1 (secrets read). **The gate is the only stop in this skill.**
2. **After the gate, one message:** the audit's approved sibling edits (E2) and `/giga-workflow:epic-story-complete` Step 5's evolution items.
3. **`/giga-workflow:epic-story-complete` Step 6** with `"until": "merged"`, `"auditKeys"` and `"secrets"` filled (S2). One `Bash` call.
4. **Report** — `/giga-workflow:epic-story-complete` Step 8, plus the `Audit:` line (E1).

---

## Amendments

### To `/giga-workflow:epic-evolution-audit`

**E1 — no gate of its own.** Its Step 7 digest and `yes / pick / no` prompt do not run; the digest's content moves into the `Story ship` gate (A1), each stale sibling listed with its one-line drift summary. Approving the gate approves every listed edit; the user strikes a sibling there to decline its edit. `--yes` applies every edit. Its Step 9 report does not print; the outcome is an `Audit:` line under the script's report: `Audit: <K> sibling edit(s) applied — <SIBLING-KEYS> | <Z> skipped (<why>) | none stale | skipped (--no-audit | opt-out) | failed — <reason>`.

**E2 — apply edits after the gate.** Its Step 8 find-and-replace on each approved sibling's local plan file runs in composition step 2, uncommitted: the script's single plans-repo commit carries it, with ` · audit <SIBLING-KEYS>` in its subject through `auditKeys`. Its atomicity rule holds: a "Replacing" block not found verbatim skips that sibling and becomes a line in the report — never a partial write.

**E3 — new-story recommendations become evolution items.** They seed `epicEvolutionItems` as `(a) New story` entries (A0), minted in `/giga-workflow:epic-story-complete` Step 5. On a `type: bug` ticket the board's bug rule still suppresses minting.

### To `/giga-workflow:epic-story-complete`

**A0 — Step 2 takes the audit's findings.** When composition step 0 ran, Step 2 does not repeat the cross-story scan: `epicEvolutionItems` = the audit's new-story recommendations (E3) plus its stale-sibling edits as `description edit` items, each marked `(audit)`. Anything this session surfaced that the audit did not cover is still added by Step 2's own rules. With `--no-audit`, Step 2 runs unchanged.

**A1 — Step 4 gate block.** Head it `Story ship` and add these lines so the block states the whole run — it is the only place the user approves the sibling edits, the merge and the secrets:

```
Audit:            <N> siblings of <config.epicKey> audited — <X> stale · <Y> clean · <Z> new-story
                  | skipped (--no-audit) | skipped (epicEvolutionRules: null) | failed — <reason>
Ticket status:    <current status>  →  In Review  →  Done
Merge:            <git.mergeMethod> + delete branch, immediately after the PR opens — no second gate
Cleanup:          <KEY> → Done · wave plan reconciled · local <git.mainBranch> synced
Secrets:          <domain repo> — <N> pending: <paths> → commit + push to <git.mainBranch> | clean | skipped — <reason>
                  <secrets.sharedRepo> — <same>
```

The stale siblings and new-story recommendations print under the block's epic-evolution items, marked `(audit)`; the full proposed-vs-replacing text is available on `edit`. Anything the user strikes or amends here is the final say for the whole run.

### Secrets repos

**S1 — read before the gate.** Run Step 1's preflight as `ship.py preflight <board> <KEY> --secrets`. For each secrets repo it resolves the real path (the sibling may be a symlink), fetches, and prints only **paths** — never a diff or a file's contents; they are secrets — or `skipped — <reason>` when the repo is missing, not on `<git.mainBranch>`, or ahead/behind/diverged. The gate's `Secrets:` lines list every pending path, whether or not this story made it; the user strikes a path or a whole repo there.

**S2 — commit + push after the merge.** Pass the approved paths as `"secrets": [{"repo": "<path>", "paths": ["…"]}]`. The script commits them by name (never `git add -A`) as `chore: <KEY> commit pending secrets`, pulls fast-forward first, pushes to `<git.mainBranch>`, never force-pushes, and refuses a repo whose GitHub visibility is not `PRIVATE` unless `secrets.requirePrivate` is `false`. A struck path stays uncommitted. A secrets failure prints `NOT pushed — <reason>` and never blocks the rest.

**S3 — no secrets push when the merge stops.** The script runs the secrets stage only after the story reaches Done; report the secrets as pending otherwise.

---

## Failure handling

`/giga-workflow:epic-story-complete` Step 7 applies. Two additions:

- **The audit fails** (its subagent returns malformed output twice, or discovery errors out) — nothing has been written. Report it on the gate's `Audit:` line as `failed — <reason>`: `yes` ships without sibling edits (Step 2's own scan then runs), `no` stops so the audit can be re-run. With `--yes`, ship and carry the failure into the report.
- **The merge stops** — the story is committed, pushed, PR open, ticket In Review; the sibling edits sit uncommitted in the plans repo, and the outcome is not written yet. Once the blocker is cleared, re-run the same `ship.py run <handoff>` command: it skips what landed, merges, and writes the outcome, the wave plan and the one plans commit. (Re-running this skill would refuse on the open PR.) Never delete a branch whose PR did not merge.
