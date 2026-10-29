---
name: epic-story-complete
description: Wrap up a finished epic story — commit the unstaged diff in strict Commitizen format, then either push + open a PR + move the Jira ticket to In Review (PR mode), push the shared epic branch + move it to Done (epic-branch mode), or fast-forward the main branch to the story, push it + move the ticket to Done (direct mode); a story's skills-repo commit (`workflow.skillsRepo`) lands on that repo's live branch and is pushed first, and a skill-only story goes to Done with no PR; record the story's outcome and its pins (one line each, pointing at the spec or rulebook rule) in its plan file, act on any epic-evolution follow-ups, and stop this checkout's Storybook servers. Use this whenever a story's implementation is done and reviewed and it needs shipping — after `/giga-workflow:epic-next` + `/giga-workflow:jira`, when the user says "wrap up the story", "commit and open the PR", "put it up for review", "finish this ticket", or invokes `/giga-workflow:epic-story-complete` directly, and as the ship step of an `/giga-workflow:epic-loop` story agent. When the user wants the PR merged in the same pass ("ship it", "ship and merge"), that is `/giga-workflow:epic-story-ship`, which runs this skill and then `/giga-workflow:epic-merge-pr --yes` behind one gate.
---

Wraps up a finished epic story: commit the unstaged changes (in the strict conventional-commit format of `commit.format`), then either **(PR mode)** push the branch, open a PR, and transition the Jira ticket to **In Review**, or **(epic-branch mode)** push the shared epic branch the commit landed on and transition the ticket to **Done**, or **(direct mode)** fast-forward `<git.mainBranch>` to the story branch, push `<git.mainBranch>`, transition the ticket to **Done** and chain `/giga-workflow:post-merge-cleanup`. The path is set by `config.mergeMode` (`"pr"` default / `"epic-branch"` / `"direct"`). When `skillsRepo` is set, the story's edits in the skills repo land first, on `<skillsRepo.branch>` (Step 5, skills leg); a **skill-only story** ends there, at **Done**, with no commit, push or PR in this repo. Either way it then stops this checkout's Storybook servers (sibling clones untouched; `--keep-storybook` opts out). Designed as the natural session-end follow-up to `/giga-workflow:epic-next` (which leaves changes unstaged after `/giga-workflow:jira` finishes its in-conversation phases).

**Usage:**
- `/giga-workflow:epic-story-complete` — preferred. Infer the board + ticket key from the current conversation context.
- `/giga-workflow:epic-story-complete <board> <KEY>` — explicit override.
- `/giga-workflow:epic-story-complete --no-push` — commit only, defer the push + PR + Jira transition.
- `/giga-workflow:epic-story-complete --type=<type>` — override the conventional-commit type (default: inferred from ticket labels).
- `/giga-workflow:epic-story-complete --build` — re-run `config.buildCommand` before committing.
- `/giga-workflow:epic-story-complete --yes` — skip the Step 4 confirmation gate (prints the pre-flight block for the record, then proceeds). For autonomous callers like an `/giga-workflow:epic-loop` story agent; only safe when the caller has already gated on a validated diff + clean cross-actor PASS.
- `/giga-workflow:epic-story-complete --keep-storybook` — leave this checkout's Storybook server(s) running (Step 11 otherwise stops them).
- Flags compose: `/giga-workflow:epic-story-complete <board> <KEY> --no-push --type=chore`.

**Available boards:** same as `/giga-workflow:epic-next` — defined by `epic.<board>.json` files in `.claude/giga/`.

## One turn, many calls

A session costs `turns × context`, and this skill runs at the point of **maximum** context — it is the
last thing a story session does, after the whole implementation is already in the transcript. Its turns
are therefore the most expensive turns in the entire session, and turn count is the only lever it has.

Measured across 67 real runs: **34.3 turns, 0.53 tool calls per turn, and 47% of turns made no tool call
at all** — each of those re-read a ~346k context to say nothing. The steps below are numbered for
**reading order, not for one-call-per-message execution.**

- Whenever the next calls do not consume each other's output, issue them in a single message.
- Whenever they are shell commands, join them with `&&` (or newlines) in **one** `Bash` call — including
  when a later command depends on an earlier one. Dependency is an argument for chaining, not for
  splitting across turns.
- Do not narrate between steps. The Step 12 report is the only prose output this skill owes the user;
  the Step 4 gate is the only place it stops. Under `--yes` nobody is reading the intermediate prose at
  all, so it is pure cost.

Explicit batch points are marked ⚡.

> **Session model:** one story per session. The conversation that ran `/giga-workflow:epic-next <board>`, planned via `/giga-workflow:jira`, implemented it, and ran the build/test gate is the same conversation that invokes this skill. The branch in play is the per-story `<git.branchPrefix><key>-<slug>` (PR and direct modes) or the shared `config.epicBranch` (epic-branch mode) that `/giga-workflow:epic-next` put you on.

> **Where this fits in the lifecycle:**
> - **PR mode:** `/giga-workflow:epic-next` (pick + branch + /giga-workflow:jira) → `/giga-workflow:epic-story-complete` (commit + push + PR + → In Review) → `/giga-workflow:epic-merge-pr` (verify state + merge by `git.mergeMethod`; a reviewer merging by hand is equivalent) → `/giga-workflow:post-merge-cleanup` (delete branch + → Done). `/giga-workflow:epic-merge-pr` chains straight into `/giga-workflow:post-merge-cleanup`, so the last two are one step in practice.
> - **Epic-branch mode:** `/giga-workflow:epic-next` (pick + checkout epic branch + /giga-workflow:jira) → `/giga-workflow:epic-story-complete` (commit onto `epicBranch` + push + → Done). The epic lands on `<git.mainBranch>` via one PR at the end (epic-level `/giga-workflow:post-merge-cleanup`).
> - **Direct mode:** `/giga-workflow:epic-next` (pick + branch + /giga-workflow:jira) → `/giga-workflow:epic-story-complete` (commit + fast-forward `<git.mainBranch>` + push + → Done) → chained `/giga-workflow:post-merge-cleanup` (delete the local branch + wave plan). No PR.
> - **Skill-only story (any mode):** `/giga-workflow:epic-next` (pick + branch + /giga-workflow:jira, edits in the skills worktree) → `/giga-workflow:epic-story-complete` (commit in the worktree + fast-forward `<skillsRepo.branch>` + push + → Done) → chained `/giga-workflow:post-merge-cleanup` on a PR or direct board. No PR.
> - **One pass (PR mode):** `/giga-workflow:epic-story-ship` runs this skill and `/giga-workflow:epic-merge-pr --yes` back to back behind this skill's Step 4 gate alone — merged on `<git.mainBranch>` + Done in one session, no merge prompt. Use it when nobody needs to review the PR before it merges.

---

## Project config

Repo-specific values come from `.claude/giga/config.json` at the repository root, under `workflow` (plus the top-level `ideas` key every plugin shares). Read it once at the start. A missing file or field takes the fallback below, never a guess.

| Field | Used for | When absent |
| --- | --- | --- |
| `plans.repo` | the plans repo holding each story's plan file and the epic's wave plan (Steps 9, 10) | stop and say the repo has no `plans.repo` in `.claude/giga/config.json` |
| `plans.script` | the script behind `board`, `section` and `stub` (Steps 2, 10) | stop and say the repo has no `plans.script` in `.claude/giga/config.json` |
| `plans.guide` | the plans guide, canonical for plan-file rules (Step 9) | skip reading it |
| `plans.autoPush` | whether the plans repo pushes itself after a commit (Step 10) | push the plans repo yourself after committing |
| `jira.mcpPrefix` | the prefix of the Jira tool ids loaded in Step 0 | stop and say the repo has no `jira.mcpPrefix` in `.claude/giga/config.json` |
| `jira.cloudId` | the Jira cloud id when the session has none (Step 1) | call `getAccessibleAtlassianResources` |
| `jira.createStatus` | the status a new follow-up story is moved to (Step 10) | `To Do` |
| `git.mainBranch` | the PR base branch, the branch direct mode fast-forwards and pushes, and the branch this skill refuses to run on | `main` |
| `git.branchPrefix` | the per-story branch prefix | `feat/` |
| `skillsRepo.path` | the skills repo's main checkout (`<repo name>` below is its last path component); the story worktree beside it is the skills leg (Steps 1, 3–5) | no skills leg: every step covers this repo alone |
| `skillsRepo.branch` | the skills repo's live branch the skills leg lands on and pushes | `main` |
| `skillsRepo.push` | the command that pushes `skillsRepo.branch`, run in the story worktree so its pre-push hook checks the tree being pushed (Step 5) | `git push origin <skillsRepo.branch>` |
| `commit.format` | the commit subject format (Step 3) | `<type>(<scope>): <KEY> <subject>` |
| `commit.hooks` | whether a commit hook validates the message | `false`: check the subject against Step 3 yourself before committing |
| `commit.refactorCommitFirst` | whether a plan file's `## Refactor (in place)` list becomes its own commit ahead of the feature (Step 5) | `true` |
| `docs.constraints` | the constraints doc holding the refactor-when-touched rule (Steps 2, 10) | state the rule without the pointer |
| `storybook.ports` | the ports `scripts/stop-storybook.sh` checks (Step 11) | the script does nothing |
| `notify` | the desktop-notification command queued in Step 11 | no desktop notification |
| `ideas.policy` (top level) | the entry threshold for new scope (Step 2) | new scope stays out of `epicEvolutionItems` and is left to the owner |
| `ideas.board` (top level) | where unadopted ideas are recorded (Step 2) | ideas stay in the report for the owner |

---

## When to use / when not to

Use after `/giga-workflow:epic-next <board>` + `/giga-workflow:jira <KEY>` complete a story and you've reviewed the unstaged diff.
Tests, lint, typecheck, and the build gate already passed during `/giga-workflow:jira` Phase 6 — this skill trusts
those results and does not re-run them by default. Pass `--build` for a final safety net.

Refuse and stop when:

- The branch is `<git.mainBranch>` or some unrelated branch. This skill expects the `/giga-workflow:epic-next` context: a `<git.branchPrefix><key>-<slug>` branch (PR and direct modes) or the `config.epicBranch` (epic-branch mode).
- The work spans multiple stories and the diff is mixed — split the changes manually first, then run this skill once per story (each on its own per-story branch).
- The PR is already open for this branch — this is a finalize-once skill; subsequent edits on the same branch are handled by `git commit` + `git push` directly (the existing PR auto-updates).

---

## Step 0 — Resolve board + ticket key, load config, load MCP tools

⚡ **This whole step is one message.** The board config path, the plans-repo path, and the MCP tool
list are all knowable before any of them returns — nothing here consumes anything else's output.

**Resolve board + key** in this order:

1. **Explicit args first.** If the args contain a board name (any `epic.<board>.json` name) and a ticket key matching `[A-Z]+-\d+`, use them verbatim.
2. **Branch fallback.** From `git rev-parse --abbrev-ref HEAD` (you are running it in Step 1 anyway — reuse that output rather than spending a turn on it here). The branch should be `<git.branchPrefix><key-lower>-<slug>`; extract the key from the first two segments after the prefix. Match the key's prefix (e.g. `ABC`) against each `epic.*.json`'s `epicKey` prefix to resolve the board.
3. **Conversation context.** If branch parsing fails, inspect the transcript for the most recent `/giga-workflow:epic-next <board>` invocation and dominant in-progress ticket key.
4. **Last resort: ask.** `AskUserQuestion` with two questions: "Which board?" and "Which ticket key?". Do not guess.

Whatever path resolved them, **echo both values prominently in the Step 4 confirmation gate** so the user can catch a wrong inference before commits/push/PR/transition fire.

**Load the board config.** Read `.claude/giga/epic.<board>.json` directly — do not `ls` the directory first to confirm it exists; a failed Read tells you the same thing in the same turn. Bind all fields as `config.field`. This skill consumes `config.commitScope` (conventional-commit scope), `config.epicKey` (PR body traceability), `config.mergeMode`, `config.epicBranch`, `config.buildCommand` (only under `--build`), and `config.epicEvolutionRules` (drives Step 2). If the file does not exist, list the available `epic.*.json` files and stop.

**Load the Atlassian MCP tools** — ONE `ToolSearch` call, not five (`<jira.mcpPrefix>` is the configured tool-id prefix):

```
select:<jira.mcpPrefix>getAccessibleAtlassianResources,<jira.mcpPrefix>getJiraIssue,<jira.mcpPrefix>getTransitionsForJiraIssue,<jira.mcpPrefix>transitionJiraIssue,<jira.mcpPrefix>addCommentToJiraIssue,<jira.mcpPrefix>createJiraIssue
```

**Parse the remaining flags** (after stripping board + key):

- `--no-push` — skip push + `gh pr create` + Jira transition + final comment (direct mode: the merge into `<git.mainBranch>` too; skills leg: everything after its commit in the worktree). Commit locally and finalize later.
- `--type=<type>` — override the commit type (`feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `style`, `ci`, `build`, `revert`).
- `--build` — re-run `config.buildCommand` before committing (useful after a long pause between `/giga-workflow:jira` finishing and this skill running).
- `--yes` — skip the Step 4 gate and proceed straight to commit/push/PR/transition; the pre-flight block still prints for the record. For autonomous callers that have already gated on a clean cross-actor PASS.
- `--keep-storybook` — skip the Storybook shutdown in Step 11, leaving this checkout's server(s) up.

## Step 1 — Verify git state + read the ticket

⚡ **One `Bash` call and the MCP reads in the same message.** The git facts and the Jira facts are
independent.

```
git rev-parse --abbrev-ref HEAD && git status --short && git diff --stat
```

**Skills leg** (only when `skillsRepo.path` is set) — append to the same call. The story worktree is the one holding this repo's branch name:

```bash
sp=<skillsRepo.path> sb=<skillsRepo.branch> b=$(git rev-parse --abbrev-ref HEAD) k='<KEY>([^0-9]|$)'
wt=$(git -C "$sp" for-each-ref --format='%(worktreepath)' "refs/heads/$b")
git -C "$sp" fetch -q origin "$sb" 2>/dev/null; base=
for r in "origin/$sb" origin/HEAD; do git -C "$sp" rev-parse -q --verify "$r" >/dev/null && { base=$r; break; }; done
echo "== worktree ${wt:-none} · pushed base ${base:-none}"; [ -n "$wt" ] && git -C "$wt" status --short
echo "== on $b, not on $sb"; git -C "$sp" log --oneline "$sb..$b" 2>/dev/null
echo "== <KEY> unpushed"; git -C "$sp" log --oneline --branches -E --grep="$k" ${base:+"^$base"}
echo "== riding along"; [ -n "$base" ] && git -C "$sp" log --oneline -E --grep="$k" --invert-grep "$base..$sb"
echo "== <KEY> landed on $sb"; git -C "$sp" log -1 --format=%h -E --grep="$k" "$sb"
echo "== <KEY> commits here"; git log --oneline -E --grep="$k" origin/<git.mainBranch>..HEAD
```

Before the branch's first push there is no `origin/<skillsRepo.branch>`: the base is then `origin/HEAD` (the default branch), and with neither, every `<KEY>` commit counts as unpushed and the whole branch rides along. The skills leg is **pending** while the story worktree exists, the story branch has commits off `<skillsRepo.branch>`, or a `<KEY>` commit is unpushed. A `<KEY>` commit already on `<skillsRepo.branch>` is the story's skills SHA even when the leg is not pending (a re-run after this repo's link failed): Steps 4, 8, 9 and 12 name it. That makes three shapes:

| Shape | This repo | Skills leg | Path |
| --- | --- | --- | --- |
| story-repo only | changes | not pending | every step as without `skillsRepo` |
| mixed | changes | pending | Step 5 lands the skills leg first, then this repo's mode |
| skill-only | clean, no `<KEY>` commit | pending | Step 5 lands the skills leg only; ticket → Done, no PR |

**Refuse to proceed** if any of:

- Current branch is `<git.mainBranch>` (or `master`). Stop — this skill never runs on the base branch.
- Current branch does not match `<git.branchPrefix><key-lower>-<...>` for the resolved KEY (case-insensitive), and `config.mergeMode` is not `"epic-branch"`. Tell the user the expected branch shape and stop. Do not auto-checkout.
- `git status --short` is empty and the skills leg is not pending (or `skillsRepo` is unset). Nothing to commit. Stop.
- `git status --short` is empty, the skills leg is pending and this repo already has `<KEY>` commits (made outside this skill). Stop and surface both lists; the owner decides how they ship.
- The diff includes files from completely unrelated areas — surface the file list and ask the user to confirm rather than refusing outright. (Heuristic only; the user has final say.)

**Read the ticket.** `getJiraIssue(cloudId, KEY, fields=["summary", "status", "labels", "subtasks"], responseContentFormat="markdown")` — request `subtasks` **here**, so Step 10 already has them and never needs its own fetch. If the session does not already have a `cloudId` in context (it usually does, from `/giga-workflow:jira`; otherwise use `jira.cloudId`), call `getAccessibleAtlassianResources()` in this same message. Save `summary`, current status (warn if not "In Progress"), labels, and the subtask list.

## Step 2 — Epic evolution scan (skip if `config.epicEvolutionRules` is null)

Before composing the commit message, scan the **current conversation transcript** for evidence that this story surfaced anything that propagates beyond it:

- An architectural constraint or pivot ("we're not going to do X after all," "we need to use Y instead").
- A schema / API decision that downstream stories were going to make.
- A discovered gap — work that wasn't anticipated and needs a new story. ⚠️ A refactor to the standard within the story's reach is **never** an evolution item: it is done in this story (`docs.constraints` § Refactor When Touched). If one is still outstanding at this point, that is a stop — have the slice agent that owns the file finish its refactor before shipping. No refactor ever becomes a story or a PR of its own.
- A clarification that a sibling/discovery story was waiting on.
- **Every unfixed discrepancy that earned a story.** This covers `/giga-workflow:jira`'s "Discrepancies not fixed here" block, and every item this story's plan file records as not built (`existing` UX-review findings, deferred items, owner remarks). A `story` finding is never one: it is fixed in this story, and an unfixed one is a stop, not an evolution item. New scope is never an evolution item: it is on the Idea Board (`ideas.board`) when it meets `ideas.policy` § Entry threshold, and only the owner's adoption there leads to a story. Each needs a decision: an edit to the existing sibling whose scope it is, a new story (grouped one per area), or **No follow-up** with a one-line reason. Recommend a story only when the finding is worth tracking (a user-facing defect, a real flow gap, a release risk, an owner ask), never because a finding exists. A finding with no decision is lost once the story ships; a "No follow-up" decision is recorded, not minted.

This is a **transcript read, not a research task** — it needs no tool calls. Do not spawn an agent and do
not re-fetch what the session already knows.

For each finding, name the affected sibling or downstream stories. If you need the epic's child list and
`/giga-workflow:epic-next` did not already cache it this session, get it in the *same* message as another call:
`python3 <plans.script> board --jql 'parent = <config.epicKey>'` → JSON
`[{key,status,category,type,priority,parent,summary}]` with live status.

Hold the list as `epicEvolutionItems`. It appears in the Step 4 gate under "Epic evolution items", where the user can strike or amend entries **before** anything is created. Whatever survives the gate is **acted on automatically by Step 10** — new stories get minted `To Do` and added to the wave plan. The gate is the decision point; there is no second one afterwards.

> **Epic-description discipline:** a "description edit" item targets the CHILD ticket whose scope it is — never the parent epic. What THIS story settled is not an evolution item at all — it goes in this story's own plan file at Step 9. Do not add story-level implementation detail, acceptance criteria, or follow-up specs to the epic; it stays overall-description + wave order (one-liners) + a one-line-per-story Shipped ledger + a lock index of one-line pointers at the specs and rulebook rules that pin them. New work → a child ticket created **`To Do`, never `Backlog`** (canonical evolution rule 3, in `/giga-workflow:epic-evolution-audit`), with its one-line entry added to the wave plan in the same action.

If the scan turns up nothing, record `epicEvolutionItems = []` and continue. Don't invent items to fill the section.

> **Heavier alternative:** `/giga-workflow:epic-evolution-audit` runs a dedicated subagent for the cross-story drift check and proposes surgical Jira description edits. Run that before this skill if the story settled something architecturally significant. This step's lightweight scan is the everyday default. `/giga-workflow:epic-story-ship` runs the audit for you and feeds its findings into this step (its amendment A0).

## Step 3 — Build the commit message (strict Commitizen)

The subject follows `commit.format` and must satisfy:

- **Format:** `commit.format` (`<type>(<scope>): <KEY> <subject>` when absent).
- **Type:** lowercase, from the allowed set (`feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `style`, `ci`, `build`, `revert`).
- **Scope:** `config.commitScope` (e.g. `concierge`). Always include — never omit the parens.
- **KEY at the start of the subject** (matches repo convention).
- **Header line ≤ 100 characters** total (cz default `subject-max-length`).
- **No trailing period.** Imperative, present tense ("delete dormant load paths", not "deleted").
- **Lowercase first word of the descriptive subject** (the part after `<KEY> `). The KEY keeps its native casing.

**Type inference** (skipped if `--type=` was passed) — first hit wins:

| Ticket label / signal | Type |
|---|---|
| Label `bug` / `defect`, or summary contains `fix:` / `bug:` | `fix` |
| Label `cleanup` / `tech-debt` / `chore` / `dead-code` / `dormant` | `chore` |
| Label `docs` / `documentation` | `docs` |
| Label `refactor` / `refactoring` | `refactor` |
| Label `test` / `testing` | `test` |
| Label `perf` / `performance` | `perf` |
| Label `ci` | `ci` |
| Label `build` | `build` |
| (default) | `feat` |

**Subject text:** start from the Jira summary; lowercase the first word, strip a trailing period, convert past tense to imperative (`Deleted X` → `delete X`). If the header exceeds 100 chars, **paraphrase** to fit — keep the load-bearing nouns, drop articles/connectors. Never truncate with an ellipsis (cz rejects it).

**Body:** none by default. The Jira ticket holds the plan and AC; the commit's job is to be a discoverable index entry. Include a body only for a non-obvious decision the user explicitly raised that won't survive in Jira (rare).

**Footers:** omit the refs footer — the KEY is already in the subject, so a `references-empty` lint rule passes. Always include the co-author trailer this session is configured to use (the one in the harness's git-commit instructions).

**Skills-leg commit** (when the story worktree has changes): the same `commit.format`, type, KEY and subject. Its scope is the one plugin or top-level directory every changed path sits under (`plugins/<name>/…` → `<name>`), or `config.commitScope` when they span several. Its refactor commit, when Step 5 makes one, is `refactor(<that scope>): <KEY> bring touched files to standard`.

## Step 4 — Confirmation gate

Print the block below. **If `--yes` was passed, skip the `AskUserQuestion`** — print the block for the record (it stays as an audit trail in the transcript), then proceed straight to Step 5. The autonomous caller has already gated on a clean, zero-finding cross-actor PASS, so the human confirmation is redundant there. Otherwise ask the user to confirm with `AskUserQuestion` (yes / no / edit message).

The first three lines exist specifically so the user can catch a wrong inference from Step 0 — scan them carefully before approving. Do not run any destructive step (commit, push, PR, transition) until the user approves, unless `--yes` is set.

```
Story complete

Board:            <board>            ← inferred from <conversation | branch | explicit arg>
Ticket key:       <KEY>              ← inferred from <conversation | branch | explicit arg>
Ticket summary:   <Jira summary>
Ticket status:    <current status>  →  <In Review | Done>

Branch:           <current-branch>   (per-story branch | epic branch ✓)
Merge mode:       <pr | epic-branch | direct>
Files changed:    <N> (<insertions>+ / <deletions>->)

Proposed commit (`commit.format`, <subject-length>/100 chars):
  <subject line>

Push:             <yes | no (--no-push)>   → <git push -u origin <branch> | git push origin <epicBranch> | git push origin <git.mainBranch>, fast-forwarded to <branch>>
PR:               <will open via gh after push | n/a — epic-branch mode | n/a — direct mode | skipped (--no-push)>
Build re-run:     <yes (--build) | no>
Final comment:    will post the commit/PR link back to <KEY>
Storybook:        will stop this checkout's server(s)   (--keep-storybook → left running)

Files:
  <git status --short output>

<If the skills leg is pending:>
Skills repo:      <repo name> · <story worktree | worktree gone>
  Commit:         [<skills refactor subject> +] <skills subject> (<subject-length>/100 chars) | already committed
  Files:          <the worktree's git status --short>
  Lands:          <current-branch> → <skillsRepo.branch> (fast-forward) → push (<skillsRepo.push>) | commit only (--no-push)
  Riding along:   <each other unpushed <skillsRepo.branch> commit, one per line> | none | the whole branch (no remote base)
</If>

<If epicEvolutionItems is non-empty:>
Epic evolution items detected — these WILL BE ACTED ON in Step 10:
  - <KEY-of-affected-story> — <what to add/edit/create>   [comment | description edit]
  - (new story) — <proposed summary>   [CREATE as To Do child of <config.epicKey> + add to wave plan]
Strike or amend anything above before approving — this gate is the only decision point.
</If>
```

On a skill-only story, `Ticket status` goes to Done, and `Proposed commit`, `Push` and `PR` read `none — skill-only story`.

Responses (interactive only — `--yes` proceeds as if **yes**):

- **yes** → proceed to Step 5.
- **no** → stop. The user will fix the diff or re-invoke with different flags.
- **edit** → ask for a replacement subject via `AskUserQuestion`, validate it against the Step 3 rules, then re-show the block with the new subject. Same for striking or amending evolution items.

## Step 5 — Ship it: build, commit, push, PR

⚡ **This is ONE `Bash` call, not four.** Chaining with `&&` gives the same fail-fast behavior as
separate turns at a fraction of the cost: if the pre-commit hook fails, the chain stops there and the
push never happens.

**Under `--build`,** prefix the chain with `<config.buildCommand> &&`. A failed build stops the chain
before anything is staged — print the error and let the user fix it. Never commit a broken build.

Stage all unstaged changes for the working tree shown in Step 1 (`git add -A` is fine — the diff was
reviewed and confirmed at the gate; otherwise stage by explicit path list). **Never use `--no-verify`** —
pre-commit hooks must run. When `commit.hooks` is `false` no commit hook validates the message, so check the subject against the Step 3 rules yourself before committing.

**Refactor commit first** (only when `commit.refactorCommitFirst` is not `false`). If the story's plan file carries a `## Refactor (in place)` list (written by
`/giga-workflow:jira` once its 5a slices report), the chain opens with a separate `refactor(<config.commitScope>): <KEY> bring
touched files to standard` commit before `git add -A` stages the feature. Two commits, one push. If
the list is absent, there is one commit. **Never stage the listed paths wholesale** — the feature was built
on top of the refactor in the same files, so `git add <paths>` would commit the feature under
`refactor(...)`. Stage the refactor from the snapshot `/giga-workflow:jira` merged from each slice's:
`git apply --cached <scratchpad>/refactor.patch`, commit, then
`git add -A` for the feature. If the snapshot is missing, rebuild it per file: `git stash push -- <file>`
(parks the feature hunks) → re-apply the refactor's substitutions to the HEAD version → `git diff -- <file>
> refactor/<name>.patch` → `git checkout -- <file>` (required, or the pop refuses) → `git stash pop` → run
the SAME substitutions on the restored file so both sides carry byte-identical refactor lines and the
patch applies without conflict. A hunk that only adds, removes or rewords a comment is a refactor hunk; a
mixed hunk rides with the feature.

**Skills leg first** (when Step 1 found it pending). It opens the same call as a subshell — `( <skills leg> ) && <this mode's chain>` — so a failed link stops the call before this repo commits; on a skill-only story it is the whole call. Each link checks its own state and skips what an earlier run already did: commit in the worktree (its hooks run) → rebase the story branch onto `<skillsRepo.branch>` if that moved (it was never pushed) → fast-forward `<skillsRepo.branch>`, in the worktree that holds it or by `fetch .` when none does → push → print the story's SHA on it → remove the worktree and the landed story branch. Under `--no-push`, run the commit link only. Run the leg from a session that loads the live copy, not the story worktree, which the leg removes. With `commit.refactorCommitFirst` not `false` and a `<scratchpad>/refactor-skills.patch` snapshot from `/giga-workflow:jira`, the commit link opens with the skills repo's own refactor commit, staged from that snapshot as this repo's is (missing snapshot: rebuild it per file in the worktree, as above).

```bash
( sp=<skillsRepo.path> sb=<skillsRepo.branch> b=<current-branch> wt=<story worktree; empty when gone> r=<skills refactor snapshot; empty when none>
  live=$(git -C "$sp" for-each-ref --format='%(worktreepath)' "refs/heads/$sb")
  has() { git -C "$sp" rev-parse -q --verify "refs/heads/$b" >/dev/null; }
  if [ -n "$wt" ] && [ -n "$(git -C "$wt" status --porcelain)" ]; then
    if [ -n "$r" ] && ! git -C "$wt" log --format=%s "$sb..HEAD" | grep -q '^refactor('; then
      git -C "$wt" apply --cached "$r" && git -C "$wt" commit -q -m "<skills refactor subject>" -m "<co-author trailer>" || exit 1
    fi
    git -C "$wt" add -A && git -C "$wt" commit -q -m "<skills subject>" -m "<co-author trailer>" || exit 1
  fi
  if has && ! git -C "$sp" merge-base --is-ancestor "$b" "$sb"; then
    git -C "$sp" merge-base --is-ancestor "$sb" "$b" || git -C "${wt:?no story worktree}" rebase -q "$sb" \
      || { git -C "$wt" rebase --abort; echo "rebase conflict — not landed"; exit 1; }
    if [ -n "$live" ]; then git -C "$live" merge -q --ff-only "$b"; else git -C "$sp" fetch -q . "$b:$sb"; fi || exit 1
  fi
  (cd "${wt:-${live:-$sp}}" && <skillsRepo.push>) && git -C "$sp" log -1 --format=%h -E --grep='<KEY>([^0-9]|$)' "$sb" | grep . || exit 1
  { [ -z "$wt" ] || git -C "$sp" worktree remove "$wt"; } \
    && { ! has || { git -C "$sp" merge-base --is-ancestor "$b" "$sb" && git -C "$sp" branch -D "$b"; }; } )
```

The printed SHA is the skills SHA Steps 8, 9 and 12 use. The story branch is deleted only once it is an ancestor of `<skillsRepo.branch>`, whichever branch the main checkout holds. On a skill-only story this is the whole of Step 5: this repo has nothing to commit, push or open.

**PR mode** (`config.mergeMode` absent or `"pr"`) — the whole ship in one call:

```bash
git add -A && git commit -m "$(cat <<'EOF'
<subject>

<co-author trailer>
EOF
)" && git rev-parse --short HEAD && git push -u origin <current-branch> && gh pr create \
  --title "<commit subject>" --base <git.mainBranch> --head <current-branch> --body "$(cat <<'EOF'
## Summary
<1–3 bullets distilled from the Jira summary + key implementation notes from the /giga-workflow:jira plan>

## Jira
- <KEY>: <Jira summary>
- Epic: <config.epicKey>

## Test plan
<the test plan /giga-workflow:jira Phase 7 produced, verbatim>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

The chain prints the short SHA and the PR URL — both are needed in Steps 8 and 13. Compose the PR body
*before* issuing the call; it comes from context you already hold, so it costs no extra turn. If the test
plan is somehow missing (i.e. `/giga-workflow:jira` was skipped or aborted mid-flight), ask the user for one before
opening the PR.

**Epic-branch mode** (`config.mergeMode === "epic-branch"`) — the commit lands in the main checkout directly on `config.epicBranch` (that's where `/giga-workflow:epic-next` put you). There is no per-story branch and nothing to merge — just commit and publish:

```bash
git add -A && git commit -m "$(cat <<'EOF'
<subject>

<co-author trailer>
EOF
)" && git rev-parse --short HEAD && git push origin <config.epicBranch>
```

**Direct mode** (`config.mergeMode === "direct"`) — the story lands on `<git.mainBranch>` with no PR. Commit on the story branch, bring it up to date with `origin/<git.mainBranch>`, fast-forward `<git.mainBranch>` to it and push, in one call:

```bash
git add -A && git commit -m "$(cat <<'EOF'
<subject>

<co-author trailer>
EOF
)" && git fetch origin <git.mainBranch> \
  && { git merge-base --is-ancestor origin/<git.mainBranch> HEAD \
       || git rebase origin/<git.mainBranch> \
       || { git rebase --abort; echo "rebase conflict — not merged"; false; }; } \
  && git checkout <git.mainBranch> && git merge --ff-only <current-branch> \
  && git push origin <git.mainBranch> && git rev-parse --short HEAD
```

The rebase is safe because the story branch was never pushed. The chain prints the short SHA of the story's last commit on `<git.mainBranch>`, which Steps 8, 9 and 12 use. Direct mode never pushes the story branch and never force-pushes. It ignores `git.mergeMethod` and always fast-forwards: a squash would fold the refactor commit into the feature commit.

Failure handling:

- **Pre-commit hook fails** → report it, leave the changes staged, do **not** retry with `--no-verify`, do **not** amend. The chain already stopped before the push. In a mixed story the skills leg ran first and has already landed and pushed: keep the SHA it printed for Steps 8, 9 and 12 (a re-run finds it again in Step 1).
- **`--no-push`** → run the `git add && git commit && git rev-parse` portion only. With the skills leg pending, run its commit link only and leave this repo uncommitted, so the re-run lands the skills leg before it commits this repo. Then stop: print "Commit ready locally. Run `git push …` + `gh pr create` manually when ready (or re-run without `--no-push`)." and exit cleanly. **Leave the Storybook servers running and skip the Step 11 notification** — the story isn't finished on this path, just committed locally. Direct mode: commit only — no fetch, rebase, merge or push.
- **Push rejected, PR mode** → stop and surface it. Do **not** force-push. Per-story branches are short-lived; a name collision means a deeper coordination issue the user must investigate.
- **Push rejected, epic-branch mode** → someone advanced the epic branch. `git pull --rebase origin <config.epicBranch>` then push; on conflict, stop and surface it. Never force-push. The commit is safe locally.
- **Rebase conflict, direct mode** → the chain already ran `git rebase --abort`. Stop and surface the conflict; the commit is safe on the story branch and `<git.mainBranch>` is untouched.
- **Fast-forward refused, direct mode** → local `<git.mainBranch>` carries commits `origin/<git.mainBranch>` lacks. Stop and surface `git log origin/<git.mainBranch>..<git.mainBranch>`; `<git.mainBranch>` is unchanged and the commit is safe on the story branch.
- **Push rejected as non-fast-forward, direct mode** → `origin/<git.mainBranch>` moved after the fetch. Local `<git.mainBranch>` now holds only the story's commits on top of the old tip, so run `git checkout <current-branch> && git branch -f <git.mainBranch> origin/<git.mainBranch>` and re-run the chain from `git fetch`.
- **Push refused by branch protection, direct mode** (a ruleset the account cannot bypass) → stop. Local `<git.mainBranch>` is ahead of `origin/<git.mainBranch>`. Tell the user to push it themselves, or to switch the board to `"pr"` with `/giga-workflow:epic-config <board>`. Never force-push.
- **`gh pr create` fails** (missing auth, etc.) → surface the error. The commit + push already succeeded; the user can retry the PR creation manually.
- **Skills-repo hook fails** → as a pre-commit hook failure: the changes stay in the story worktree, nothing landed and this repo is uncommitted. Never `--no-verify`; fix in the worktree and re-run.
- **Rebase conflict, skills leg** → the chain already ran `rebase --abort`. Stop and surface the conflict; the commit is safe on the story branch, and `<skillsRepo.branch>` and this repo are untouched.
- **Fast-forward refused, skills leg** → the checkout holding `<skillsRepo.branch>` has uncommitted edits in files the story changes. Stop and surface its `git status --short`; never stash or discard them. Once the owner commits or moves them, a re-run lands the story (the commit link skips).
- **Push rejected, skills leg** → `origin/<skillsRepo.branch>` has commits the local branch lacks. Stop; never force-push. The story is on the local live branch; once the owner brings `origin/<skillsRepo.branch>` into it, a re-run pushes, cleans up and carries on with this repo.

## Step 6 — Transition the ticket

Read the transitions and match by **name** — never guess an id, they differ per project.

```
getTransitionsForJiraIssue(cloudId, KEY)
transitionJiraIssue(cloudId, KEY, transition={id: <matched-id>})
```

- **PR mode** → match **In Review** (case-insensitive; common variants "In Review", "Code Review", "Ready for Review" — prefer the exact "In Review"). If no review state is reachable, surface the available transitions and let the user pick; if the workflow has no review state at all, leave the ticket In Progress, note it in the final report, and still post the Step 8 comment so the linkage is captured.
- **Epic-branch mode** → match **Done**. The story is integrated into `config.epicBranch` and verified; there is no per-story PR to wait on, which mirrors how an epic-branch story is closed by hand. If no Done transition is reachable, surface the options and let the user pick.
- **Direct mode** → match **Done**, as in epic-branch mode: the story is already on `<git.mainBranch>`. If no Done transition is reachable, surface the options and let the user pick.
- **Skill-only story** (any mode) → match **Done**, as in direct mode: the story is on `<skillsRepo.branch>` and pushed.

## Step 7 — Close the story's sub-tasks

You already have the subtask list from Step 1 — do **not** re-fetch the issue. **No sub-tasks → skip this step entirely** (the common case for leaf stories).

A decomposed story's sub-tasks are implementation slices; their deliverable is code that is now committed, so they reach **Done** when the story's implementation is wrapped. ⚡ Process every sub-task **not already Done** in parallel in a single message — read each one's transitions, then transition it to Done (match by name).

If a sub-task can't reach Done directly (workflow gap), surface it and continue — **never fail the story wrap-up over a sub-task transition**; `/giga-workflow:post-merge-cleanup` sweeps any stragglers.

## Step 8 — Comment the linkage onto the ticket

⚡ **Issue this in the same message as Step 6's transition** — they're independent once the PR URL is in
hand — and in the same message as Step 7's sub-task transitions where there are any.

Post a short ADF comment so the work is discoverable without scanning git history. PR mode links Jira → PR; epic-branch mode has no PR, so head it "Committed on epic branch" and drop the PR-link paragraph. Direct mode has no PR either: head it "Merged to `<git.mainBranch>`", drop the PR-link paragraph, and give the SHA on `<git.mainBranch>` (`Commit: <short-sha> on <git.mainBranch> (epic <config.epicKey>).`). When the skills leg landed, add a paragraph `Skills: <skills-sha> on <skillsRepo.branch> (<repo name>).` A skill-only story heads the comment `Landed on <skillsRepo.branch>` and keeps only that paragraph.

```json
{ "version": 1, "type": "doc", "content": [
  { "type": "heading", "attrs": { "level": 3 }, "content": [{ "type": "text", "text": "In Review" }] },
  { "type": "paragraph", "content": [
    { "type": "text", "text": "PR: " },
    { "type": "text", "text": "<PR URL>", "marks": [{ "type": "link", "attrs": { "href": "<PR URL>" } }] }
  ]},
  { "type": "paragraph", "content": [
    { "type": "text", "text": "Commit: " },
    { "type": "text", "text": "<short-sha>", "marks": [{ "type": "code" }] },
    { "type": "text", "text": " on branch " },
    { "type": "text", "text": "<current-branch>", "marks": [{ "type": "code" }] },
    { "type": "text", "text": " (epic " },
    { "type": "text", "text": "<config.epicKey>", "marks": [{ "type": "code" }] },
    { "type": "text", "text": ")." }
  ]}
]}
```

If the comment fails to post, report the error but do not roll back the commit/push/PR/transition — the comment is non-blocking.

## Step 9 — Record the outcome in the story's OWN plan file

**This is the step that keeps the parent epic slim.** A story's plan file (`<plans.repo>/<board>/<KEY>.md`) is authored *before* the work and stops at Acceptance, so without this step a shipped story's outcome has no durable home and gets written into the parent epic instead — one paragraph per story, forever. That is how an epic reaches tens of KB and stops being readable.

Append to the local plan file (never to Jira's description — see the plans guide (`plans.guide`) §4):

```markdown
## Outcome — shipped (PR #<N>)

<2–5 sentences: what actually shipped, and what it did NOT do where that was a deliberate call.>

### Pinned        ← omit the whole subsection when the story pinned nothing

- <the claim, one line> — pinned by `<spec file>` | `<lib>/AGENTS.md` § <section> | a comment at `<file>`
```

Rules:

- **A lock is pinned in the code or the rulebook, never narrated here.** Something a future story would get wrong is recorded as, in order of preference: a spec that fails when it is broken; a rule in the library's `AGENTS.md` (one sentence, the invariant and its reason); a two-line comment at the site. This subsection is ONE line per pin — the claim and where it is pinned. No reasoning, no measurement, no ⚠️ narrative: if the reason matters it is in the spec's name or the rulebook sentence. A claim that cannot be pinned in any of those three places is a preference, not a lock — drop it. Not a changelog of the diff; git has that.
- **Write it even in epic-branch and direct modes** (no PR — head the section `## Outcome — shipped (<short-sha>)`).
- **A skills leg is named in the heading:** `## Outcome — shipped (PR #<N> · <repo name> <skills-sha>)`; a skill-only story: `## Outcome — shipped (<repo name> <skills-sha>)`. An `## Outcome` the plan file already has (a re-run, or a skills leg finished after the PR merged) gets the skills SHA added to its heading, never a second section.
- **Verdict stories still get one.** A story that shipped nothing but a decision (REJECTED, DROP, KEEP) has the most valuable outcome of all — record the verdict and the reasoning that closed the fork.
- If the story surfaced a lock a *sibling* must act on, that is an `epicEvolutionItems` entry (Step 2) targeting the sibling — this section is the durable record, not the propagation mechanism.

Then, and only then, touch the parent epic. Write its `## Shipped` line here **only in epic-branch mode**, which has no per-story cleanup: one line, `- <KEY> — <what shipped, past tense, ≤10 words> *(Wave <N>; <short-sha>)*` (a skill-only story: `<repo name> <skills-sha>`), dropping `Wave <N>; ` when the epic has no wave plan. In PR and direct modes, do not write it: the `/giga-workflow:post-merge-cleanup` that the merge chains (`/giga-workflow:epic-merge-pr` in PR mode, Step 10.5 in direct mode and for a skill-only story) writes it in the same format once the story is on `<git.mainBranch>`. If a pin is genuinely cross-cutting, it earns **one line** in the epic's lock index: the claim and where it is pinned, with this story as owner. Never a paragraph, here or in the story file.

⚡ This edit and the Step 10 wave-plan edit both land in the plans repo. Make **both** edits, then commit
them together in Step 10's single `Bash` call. Do not commit the plans repo twice.

## Step 10 — Act on the epic evolution items ((a)–(c) only when `epicEvolutionItems` is non-empty; (d) always runs)

Run this for every item that survived the Step 4 gate. **This step is the work, not a printed suggestion.** A finding the user approved but nobody executed is exactly the drift the epic-evolution rules exist to prevent, and in a single-developer automated workflow there is no second pair of hands to catch it later.

**(a) New story.** Only for genuinely new product work — never a refactor (`docs.constraints` § Refactor When Touched: refactors are done in the story in progress, no exceptions). Born-split, same as `/giga-workflow:create-jira`:

1. `createJiraIssue(cloudId, projectKey, issueTypeName=<Bug|Task|Story>, parent=<config.epicKey>, summary=<concise, <80 chars>)` → read the `key`.
2. `Write` the content to `<plans.repo>/<board>/<KEY>.md` (front matter `jira/project/board/type/epic/summary` + body). Put the scope, the evidence and the acceptance there — **never** in the epic description.
3. **Transition to `<jira.createStatus>`** (`To Do` when absent) — read the transitions and match by NAME; never guess the id. ⚠️ A project may create an issue in **`Backlog`**, so skipping this leaves the story invisible to `/giga-workflow:epic-next`'s JQL — the single most common way a filed follow-up is silently lost.
4. `python3 <plans.script> stub <KEY>`.
5. **Add it to the wave plan** — see (c) — in the same pass.

Create it in the ticket-ready status (`jira.createStatus`) unconditionally. Do **not** weigh whether it is "ready"; canonical evolution rule 3 removed that judgment call, because every story in this workflow gets worked and a `Backlog` tier only hides them. Use `Backlog` solely when the user explicitly asked to park that item at the gate.

⚡ Steps 1 and 4 are per-story shell/MCP calls with no cross-item dependency — for multiple new stories,
batch the `createJiraIssue` calls in one message, then batch the `stub` invocations into one `Bash` call
(`… stub KEY-1 && … stub KEY-2`).

**(b) Existing sibling needing a comment or a description edit.** Post via `addCommentToJiraIssue`, or edit that story's **own** `<plans.repo>/<board>/<KEY>.md` — never `editJiraIssue(fields={description})`, which only holds a stub.

**(c) Wave plan — update it, do not propose it.** Print just the wave plan with `python3 <plans.script> section <config.epicKey> Wave` (its line range goes to stderr), `Read` only that range of the epic file (`offset`/`limit`), then edit `<plans.repo>/<board>/<config.epicKey>.md`: append each new story to the wave it belongs to as a one-liner `- <KEY> — <summary> · <Type>`, opening a new `### Wave <N> — <theme>` if the work fits no existing wave. Keep the entry to ONE line; scope belongs in the child ticket. If a rule the story settled needs recording, add at most one bullet under the wave-rationale section — never per-story detail.

**(d) Commit the plans repo** — one call, covering Step 9's outcome edit *and* every edit above. Commit; whether you also push depends on `plans.autoPush` (see the note under the code block):

```bash
cd <plans.repo> && git add <board>/ && git commit -m "$(cat <<'EOF'
docs(<board>): <KEY> outcome + follow-ups

<co-author trailer>
EOF
)"
```

> **Pushing the plans repo.** With `plans.autoPush` true the plans repo commits and pushes itself (a turn-end hook plus a periodic timer), so your commit reaches its remote within minutes: do not push it, and do not report it as unpushed. If you need the real state, measure it with `git -C <plans.repo> rev-list --left-right --count HEAD...@{u}`. With `plans.autoPush` false or absent, push it yourself after the commit.

If any Jira call fails, report it and continue — a failed follow-up must not roll back the shipped story, but it MUST be surfaced as an explicit "not created" line rather than dropped silently.

## Step 10.5 — Direct mode and skill-only stories: chain `/giga-workflow:post-merge-cleanup`

In direct mode when Step 5 pushed `<git.mainBranch>`, and for a skill-only story on a PR or direct board when Step 5 pushed `<skillsRepo.branch>` (never under `--no-push`; never on an epic-branch board, whose current branch is the shared epic branch). Right after Step 10's plans-repo commit, invoke `/giga-workflow:post-merge-cleanup <current-branch>` with the `Skill` tool, the way `/giga-workflow:epic-merge-pr` chains it. It deletes the local story branch (the remote one never existed), finds the ticket already Done, moves the story out of its wave into `## Shipped` stamped with the SHA, and closes the epic when this was its last story. Fold its summary into the Step 12 report rather than printing it. A cleanup failure never rolls the merge back: report it as a line and continue.

## Step 11 — Stop Storybook and queue the notification

⚡ **One `Bash` call for both.** Neither depends on the other, and the notification is a single `<notify>` call
that must never cost a turn of its own.

1. **Stop the Monitor task first** with `TaskStop`, if this session armed one on a Storybook log — otherwise the `tail -f` outlives the server it was watching. This is the only part that isn't shell.
2. Then, in one call (skip the script under `--keep-storybook`; skip `<notify>` under `--no-push`, and when `notify` is absent):

```bash
${CLAUDE_SKILL_DIR}/scripts/stop-storybook.sh
<notify> '<KEY> · story complete — PR #<N> ready for review'
```

The script discovers Storybook processes on the ports in `storybook.ports` (it does nothing when none are configured) plus `nx storybook` / `npm run storybook` supervisors, **filters every candidate on its cwd**, and stops only those inside this working copy. It prints what it stopped, what it skipped and why, and anything still listening. Read its output into the Step 12 report — a surviving port held by another clone is the *correct* outcome, not a failed kill. Failures here are non-blocking: the commit / push / PR / transition already landed.

The story is wrapped, so the Storybook server(s) it was verified against are dead weight. Worse than idle: one survives into the *next* story's session holding port 4400, where a server still serving the previous branch's tree renders a story that looks fine and proves nothing.

**Notification body format is `<KEY> · <task>`** — lead with the Jira key (it already encodes the board, so do NOT add the board name), and do NOT include the repo name or path; the notify tooling stamps those from the session's working directory. Epic-branch mode: `'<KEY> · story complete — committed on epic branch + Done'`. Direct mode: `'<KEY> · story complete — merged to <git.mainBranch> + Done'`. Skill-only story: `'<KEY> · story complete — landed on <skillsRepo.branch> + Done'`. Ignore write failures.

> The notification format is shared across `/giga-workflow:epic-story-complete`, `/giga-workflow:epic-next` and `/notify`. If you change it, update all of them together.

---

## Step 12 — Final report

This is the skill's only prose output. Print it once, then stop.

```
✓ Story <KEY> <ready for review | committed on the epic branch | merged to <git.mainBranch> | landed on <skillsRepo.branch>>
Commit:   <short-sha> — <subject>               <omitted on a skill-only story>
Branch:   <current-branch> (pushed ✓)          <PR mode>
Pushed:   <config.epicBranch> ✓                 <epic-branch mode>
Pushed:   <git.mainBranch> ✓ (fast-forward)     <direct mode>
Skills:   <skills-sha> on <skillsRepo.branch> (pushed ✓) — <repo name>   <skills leg>
PR:       #<N> — <PR URL>                       <PR mode>
Ticket:   <KEY> → <In Review | Done>
Cleanup:  <branch> deleted (local) · wave plan → Shipped · epic <→ Done | N children open>   <direct mode, skill-only>
Comment:  posted ✓ | skipped
Outcome:  <board>/<KEY>.md § Outcome ✓ (<N> pin(s)) | nothing pinned
Storybook: <the script's own output lines>

<If epicEvolutionItems was non-empty:>
Epic evolution — done (Step 10):
  Created:   <NEW-KEY> · <Type> · To Do · <summary>
  Updated:   <KEY> — comment posted | description edited
  Wave plan: <config.epicKey> — added <N> to "<wave title>" (plans repo committed; pushed per `plans.autoPush`)
  <if any failed:> NOT created: <item> — <reason>; run /giga-workflow:create-jira <board> <config.epicKey> to file it
</If>

Next:
  <PR mode:>
  • Review the PR (github.com or `gh pr view <N>`).
  • Then run /giga-workflow:epic-merge-pr <N> — merges it (`git.mergeMethod`), deletes the branch, and chains
    /giga-workflow:post-merge-cleanup to transition <KEY> → Done. Already merged it in the GitHub UI?
    Run it anyway; it reads MERGED and skips to cleanup.
  <Epic-branch mode:>
  • Story is committed on <config.epicBranch> + Done — nothing to merge per story.
  • When the whole epic is complete, open ONE PR (<config.epicBranch> → <git.mainBranch>); after it merges run /giga-workflow:post-merge-cleanup <config.epicBranch>.
  <Direct mode:>
  • Story is merged on <git.mainBranch> + Done — no PR to review or merge.
  <Skill-only story, any mode:>
  • Story is on <skillsRepo.branch> (pushed) + Done — nothing to review or merge.
  <every mode:>
  • To start the next story in the epic: /giga-workflow:epic-next <board>
```

When the chained cleanup closed the epic (direct mode), its `<epicCloseSkill> closed` block (`Epic order` / `Plan next`) and `Review` line end the report, verbatim.

---

## Notes

- **PR mode:** this skill is the **per-story** wrap-up to In Review; the merge and the wrap-up to Done are `/giga-workflow:epic-merge-pr`, which chains `/giga-workflow:post-merge-cleanup` itself — so point the user at `/giga-workflow:epic-merge-pr`, not at the cleanup skill directly, and do so however they reviewed (it is idempotent on a PR already merged in the GitHub UI). `/giga-workflow:epic-story-ship` is this skill + `/giga-workflow:epic-merge-pr --yes` as one pass; its amendments to these steps live in its own SKILL.md, not here. **Epic-branch mode:** this skill takes the story all the way to **Done**; `/giga-workflow:epic-merge-pr` refuses these boards, and `/giga-workflow:post-merge-cleanup` runs once per epic on the final `epicBranch → <git.mainBranch>` PR. **Direct mode:** this skill takes the story onto `<git.mainBranch>` and to **Done**, then chains `/giga-workflow:post-merge-cleanup` itself (Step 10.5); `/giga-workflow:epic-merge-pr` refuses these boards, and `/giga-workflow:epic-story-ship` runs this skill unchanged on them. **Skill-only story** (any mode): this skill takes it onto `<skillsRepo.branch>` and to **Done** with no PR, and on a PR or direct board chains `/giga-workflow:post-merge-cleanup` itself (Step 10.5).
- Commit-message format is intentionally aligned with `commit-commands:commit` and the existing repo history so `git log --oneline` stays scannable.
- Every failure mode is handled at the step that can hit it (Step 5 for build/hook/rebase/push/PR, Step 6 for transitions, Step 8 for the comment, Step 10.5 for the direct-mode cleanup, Step 11 for Storybook). The rule they share: once the commit has landed, nothing downstream rolls it back — report the failure and continue.
