---
name: epic-story-complete
description: Wrap up a finished epic story — the session resolves the story, writes the strict-Commitizen commit subject, the PR body and the plan-file outcome, and confirms at one gate; then `scripts/ship.py` does the rest in one call — commit, push, open the PR and move the ticket to In Review (PR mode), push the shared epic branch and move it to Done (epic-branch mode), or fast-forward and push the main branch and move it to Done (direct mode); a story's skills-repo commit (`workflow.skillsRepo`) lands on that repo's live branch first, and a skill-only story goes to Done with no PR; it records the outcome and pins in the story's plan file and stops this checkout's Storybook. With `--merge` the same call merges the PR and cleans up to Done. Use whenever a story's implementation is done and reviewed and needs shipping — after `/giga-workflow:epic-next` + `/giga-workflow:jira`, when the user says "wrap up the story", "commit and open the PR", "put it up for review", "finish this ticket", or invokes `/giga-workflow:epic-story-complete` directly, and as the ship step of an `/giga-workflow:epic-loop` story agent (`--yes --merge`). When the user wants the PR merged in the same pass ("ship it", "ship and merge"), that is `/giga-workflow:epic-story-ship`.
---

**The judgement stays in the session; the mechanics are a script.** Everything that needs this session's memory of the story (which board and ticket, what it surfaced for its siblings, the commit subject, the PR body, the outcome and its pins) is written before the gate. After the gate nothing is left to decide, so `${CLAUDE_SKILL_DIR}/scripts/ship.py run` does every remaining step in one `Bash` call and prints a short report. Jira goes through the plans script (`transition`, `comment`, `board`), not an MCP. The script checks each stage's state before acting, so after a stop, re-running it resumes where it stopped.

**Usage:**
- `/giga-workflow:epic-story-complete` — preferred. Infer the board + ticket key from the current conversation context.
- `/giga-workflow:epic-story-complete <board> <KEY>` — explicit override.
- `/giga-workflow:epic-story-complete --no-push` — commit only, defer the push + PR + Jira transition.
- `/giga-workflow:epic-story-complete --type=<type>` — override the conventional-commit type (default: inferred from ticket labels).
- `/giga-workflow:epic-story-complete --build` — re-run `config.buildCommand` before committing.
- `/giga-workflow:epic-story-complete --merge` — PR mode: merge the PR right after it opens (`git.mergeMethod`), then clean up to Done, in the same script call. No effect on epic-branch and direct boards, which already end at Done.
- `/giga-workflow:epic-story-complete --yes` — skip the Step 4 confirmation gate (prints the pre-flight block for the record, then proceeds). For autonomous callers like an `/giga-workflow:epic-loop` story agent; only safe when the caller has already gated on a validated diff + clean cross-actor PASS.
- `/giga-workflow:epic-story-complete --keep-storybook` — leave this checkout's Storybook server(s) running.
- Flags compose: `/giga-workflow:epic-story-complete <board> <KEY> --no-push --type=chore`.

**Available boards:** same as `/giga-workflow:epic-next` — defined by `epic.<board>.json` files in `.claude/giga/`.

**One turn, many calls.** This skill runs at the session's largest context, so every turn is the most expensive turn of the story. The happy path is four messages: preflight (Step 1), the gate (Step 4), the script (Step 6), the report (Step 8). Do not narrate between steps.

> **Session model:** one story per session. The conversation that ran `/giga-workflow:epic-next <board>`, planned via `/giga-workflow:jira`, implemented it, and ran the build/test gate is the same conversation that invokes this skill. The branch in play is the per-story `<git.branchPrefix><key>-<slug>` (PR and direct modes) or the shared `config.epicBranch` (epic-branch mode).

---

## Project config

Repo-specific values come from `.claude/giga/config.json` at the repository root, under `workflow` (plus the top-level `ideas` key every plugin shares). The session reads the fields it needs for Steps 0–5; `scripts/ship.py` reads the rest itself. A missing file or field takes the fallback below, never a guess.

| Field | Used for | When absent |
| --- | --- | --- |
| `plans.repo` | the plans repo holding each story's plan file and the epic's wave plan (script: outcome, wave plan, commit) | stop and say the repo has no `plans.repo` in `.claude/giga/config.json` |
| `plans.script` | the script behind `board`, `section`, `ensure`, `stub`, `transition` and `comment` (Steps 1, 5; the script's Jira calls) | stop and say the repo has no `plans.script` in `.claude/giga/config.json` |
| `plans.guide` | the plans guide, canonical for plan-file rules (Step 3b) | skip reading it |
| `plans.autoPush` | whether the plans repo pushes itself after a commit (script) | the script pushes the plans repo after committing |
| `jira.mcpPrefix` | the Jira tools Step 5 loads to create a follow-up story — the only Jira call outside the plans script | Step 5 cannot mint follow-ups: report each as "not created" |
| `jira.cloudId` | the Jira cloud id for Step 5's create call | call `getAccessibleAtlassianResources` |
| `jira.createStatus` | the status a new follow-up story is moved to (Step 5) | `To Do` |
| `git.mainBranch` | the PR base branch, the branch direct mode fast-forwards and pushes, and the branch this skill refuses to run on | `main` |
| `git.branchPrefix` | the per-story branch prefix | `feat/` |
| `git.mergeMethod` | the `gh pr merge` method under `--merge` (script) | `squash` |
| `skillsRepo.path` | the skills repo's main checkout (`<repo name>` below is its last path component); the story worktree beside it is the skills leg (preflight, script) | no skills leg: every step covers this repo alone |
| `skillsRepo.branch` | the skills repo's live branch the skills leg lands on and pushes | `main` |
| `skillsRepo.push` | the command that pushes `skillsRepo.branch`, run in the story worktree so its pre-push hook checks the tree being pushed (script) | `git push origin <skillsRepo.branch>` |
| `commit.format` | the commit subject format (Step 3) | `<type>(<scope>): <KEY> <subject>` |
| `commit.hooks` | whether a commit hook validates the message | `false`: check the subject against Step 3 yourself before the gate |
| `commit.refactorCommitFirst` | whether a plan file's `## Refactor (in place)` list becomes its own commit ahead of the feature (Step 3b) | `true` |
| `docs.constraints` | the constraints doc holding the refactor-when-touched rule (Step 2) | state the rule without the pointer |
| `storybook.ports` | the ports `scripts/stop-storybook.sh` checks (script) | the script does nothing |
| `notify` | the desktop-notification command the script queues | no desktop notification |
| `epicCloseSkill` | the skill invoked when the script closes the epic (Step 8) | skip the hand-off |
| `ideas.policy` (top level) | the entry threshold for new scope (Step 2) | new scope stays out of `epicEvolutionItems` and is left to the owner |
| `ideas.board` (top level) | where unadopted ideas are recorded (Step 2) | ideas stay in the report for the owner |

---

## When to use / when not to

Use after `/giga-workflow:epic-next <board>` + `/giga-workflow:jira <KEY>` complete a story and you've reviewed the unstaged diff. Tests, lint, typecheck, and the build gate already passed during `/giga-workflow:jira` Phase 6 — this skill trusts those results and does not re-run them by default. Pass `--build` for a final safety net.

Refuse and stop when:

- The branch is `<git.mainBranch>` or some unrelated branch. This skill expects the `/giga-workflow:epic-next` context: a `<git.branchPrefix><key>-<slug>` branch (PR and direct modes) or the `config.epicBranch` (epic-branch mode). Do not auto-checkout.
- The work spans multiple stories and the diff is mixed — split the changes manually first, then run this skill once per story (each on its own per-story branch).
- The PR is already open for this branch — this is a finalize-once skill; point at `/giga-workflow:epic-merge-pr <N>`, or let later edits ride a plain `git commit` + `git push` (the open PR updates).

---

## Step 0 — Resolve board + ticket key

Resolve in this order:

1. **Explicit args first.** A board name (any `epic.<board>.json` name) and a ticket key matching `[A-Z]+-\d+` are used verbatim.
2. **Branch fallback.** The branch should be `<git.branchPrefix><key-lower>-<slug>`; extract the key from the first two segments after the prefix and match its prefix against each `epic.*.json`'s `epicKey` prefix to resolve the board.
3. **Conversation context.** The most recent `/giga-workflow:epic-next <board>` invocation and the dominant in-progress ticket key.
4. **Last resort: ask** with `AskUserQuestion` ("Which board?", "Which ticket key?"). Do not guess.

Echo both values, and how each was inferred, in the Step 4 gate. Read `.claude/giga/epic.<board>.json` (`config.*`) in the same message as Step 1 — this skill uses `config.commitScope`, `config.epicKey`, `config.mergeMode`, `config.epicBranch` and `config.epicEvolutionRules`. Strip board and key from the args; the rest are the Usage flags.

## Step 1 — Preflight: git, ticket and skills-leg facts in one call

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/ship.py preflight <board> <KEY>
```

It changes nothing and prints the board and mode, the branch check, the ticket's status, type, summary and sub-tasks (through the plans script's `board`), any PR already open, the changed files with `+/-`, `<KEY>` commits already made, the skills leg's shape (story worktree, its files, commits not yet on `<skillsRepo.branch>`, unpushed `<KEY>` commits, other commits riding along, a `<KEY>` commit already landed), and a final `Refuse:` line. **A `Refuse:` other than `none` stops the skill** — print the reason and the line it came from. Warn at the gate when the ticket is not In Progress. The diff spanning completely unrelated areas is a judgement call the script cannot make: surface the file list at the gate and let the user decide.

The skills leg makes three shapes: **story-repo only** (this repo has changes, leg not pending), **mixed** (both — the leg lands first, then this repo's mode), and **skill-only** (this repo clean, no `<KEY>` commit, leg pending — the story lands on `<skillsRepo.branch>` and goes to Done with no PR).

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
`/giga-workflow:epic-next` did not already cache it this session, get it in the *same* message as Step 1's preflight:
`python3 <plans.script> board --jql 'parent = <config.epicKey>'` → JSON
`[{key,status,category,type,priority,parent,summary}]` with live status.

Hold the list as `epicEvolutionItems`. It appears in the Step 4 gate under "Epic evolution items", where the user can strike or amend entries **before** anything is created. Whatever survives the gate is **acted on automatically by Step 5** — new stories get minted `To Do` and added to the wave plan. The gate is the decision point; there is no second one afterwards.

> **Epic-description discipline:** a "description edit" item targets the CHILD ticket whose scope it is — never the parent epic. What THIS story settled is not an evolution item at all — it goes in this story's own Outcome (Step 3b). Do not add story-level implementation detail, acceptance criteria, or follow-up specs to the epic; it stays overall-description + wave order (one-liners) + a one-line-per-story Shipped ledger + a lock index of one-line pointers at the specs and rulebook rules that pin them. New work → a child ticket created **`To Do`, never `Backlog`** (canonical evolution rule 3, in `/giga-workflow:epic-evolution-audit`), with its one-line entry added to the wave plan in the same action.

If the scan turns up nothing, record `epicEvolutionItems = []` and continue. Don't invent items to fill the section.

> **Heavier alternative:** `/giga-workflow:epic-evolution-audit` runs a dedicated subagent for the cross-story drift check and proposes surgical Jira description edits. Run that before this skill if the story settled something architecturally significant. This step's lightweight scan is the everyday default. `/giga-workflow:epic-story-ship` runs the audit for you and feeds its findings into this step (its amendment A0).

## Step 3 — Build the commit message (strict Commitizen)

The subject follows `commit.format` and must satisfy:

- **Format:** `commit.format` (`<type>(<scope>): <KEY> <subject>` when absent).
- **Type:** lowercase, from the allowed set (`feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `style`, `ci`, `build`, `revert`).
- **Scope:** `config.commitScope` (e.g. `billing`). Always include — never omit the parens.
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

**Skills-leg commit** (when the story worktree has changes): the same `commit.format`, type, KEY and subject. Its scope is the one plugin or top-level directory every changed path sits under (`plugins/<name>/…` → `<name>`), or `config.commitScope` when they span several. Its refactor commit, when the script makes one, is `refactor(<that scope>): <KEY> bring touched files to standard`.

## Step 3b — Write the rest of the handoff

Compose these from what the session already holds; they cost no tool call.

- **PR body** (PR mode):

  ```markdown
  ## Summary
  <1–3 bullets distilled from the Jira summary + key implementation notes from the /giga-workflow:jira plan>

  ## Jira
  - <KEY>: <Jira summary>
  - Epic: <config.epicKey>

  ## Test plan
  <the test plan /giga-workflow:jira Phase 7 produced, verbatim>

  🤖 Generated with [Claude Code](https://claude.com/claude-code)
  ```

  If the test plan is missing (`/giga-workflow:jira` was skipped or aborted), ask the user for one before the gate.
- **Outcome** — 2–5 sentences: what actually shipped, and what it did NOT do where that was a deliberate call. The script writes it to the story's own plan file under `## Outcome — shipped (<PR #N | sha>)`, never to Jira and never to the epic. A verdict story (REJECTED, DROP, KEEP) records the verdict and the reasoning that closed the fork.
- **Pins** — one line each: `<the claim> — pinned by <spec file> | <lib>/AGENTS.md § <section> | a comment at <file>`. A lock is pinned in the code or the rulebook, never narrated: a spec that fails when it is broken, a one-sentence rule in the library's `AGENTS.md`, or a two-line comment at the site. A claim that cannot be pinned in one of those is a preference — drop it. No reasoning, no measurement; not a changelog. Empty when nothing was pinned. A lock a *sibling* must act on is an `epicEvolutionItems` entry, not a pin.
- **Shipped line** — what the story did, past tense, ≤10 words. The script writes `- <KEY> — <it> *(Wave <N>; PR #<N> | <sha>)*` to the epic's `## Shipped` once the story reaches Done.
- **Refactor snapshot** — when the plan file carries a `## Refactor (in place)` list and `commit.refactorCommitFirst` is not `false`, the absolute path of the `<scratchpad>/refactor.patch` `/giga-workflow:jira` merged from its slices (and `refactor-skills.patch` for the skills leg). The script commits it first as `refactor(<config.commitScope>): <KEY> bring touched files to standard`. If the snapshot is missing, rebuild it per file before the gate: `git stash push -- <file>` (parks the feature hunks) → re-apply the refactor's substitutions to the HEAD version → `git diff -- <file> > refactor/<name>.patch` → `git checkout -- <file>` (required, or the pop refuses) → `git stash pop` → run the SAME substitutions on the restored file so both sides carry byte-identical refactor lines. A hunk that only adds, removes or rewords a comment is a refactor hunk; a mixed hunk rides with the feature. Never stage the listed paths wholesale: the feature was built on top of the refactor in the same files.

## Step 4 — Confirmation gate

Print the block below. **If `--yes` was passed, skip the `AskUserQuestion`** — print the block for the record, then proceed. Otherwise ask the user to confirm with `AskUserQuestion` (yes / no / edit message). The first three lines exist so the user can catch a wrong inference from Step 0. Nothing is committed, pushed, opened or transitioned before the user approves, unless `--yes` is set.

```
Story complete

Board:            <board>            ← inferred from <conversation | branch | explicit arg>
Ticket key:       <KEY>              ← inferred from <conversation | branch | explicit arg>
Ticket summary:   <Jira summary>
Ticket status:    <current status>  →  <In Review | Done | In Review → Done (--merge)>

Branch:           <current-branch>   (per-story branch | epic branch ✓)
Merge mode:       <pr | epic-branch | direct>
Files changed:    <N> (<insertions>+ / <deletions>->)

Proposed commit (`commit.format`, <subject-length>/100 chars):
  [<refactor subject> +] <subject line>

Push:             <yes | no (--no-push)>   → <origin <branch> | origin <epicBranch> | <git.mainBranch>, fast-forwarded>
PR:               <will open via gh | n/a — epic-branch mode | n/a — direct mode | skipped (--no-push)>
Merge:            <git.mergeMethod> + delete branch, right after the PR opens   ← only under --merge
Build re-run:     <yes (--build) | no>
Final comment:    will post the commit/PR link back to <KEY>
Storybook:        will stop this checkout's server(s)   (--keep-storybook → left running)

Files:
  <the preflight's file list>

<If the skills leg is pending:>
Skills repo:      <repo name> · <story worktree | worktree gone>
  Commit:         [<skills refactor subject> +] <skills subject> (<subject-length>/100 chars) | already committed
  Files:          <the worktree's files from the preflight>
  Lands:          <current-branch> → <skillsRepo.branch> (fast-forward) → push (<skillsRepo.push>) | commit only (--no-push)
  Riding along:   <each other unpushed <skillsRepo.branch> commit> | none | the whole branch (no remote base)
</If>

<If epicEvolutionItems is non-empty:>
Epic evolution items detected — these WILL BE ACTED ON in Step 5:
  - <KEY-of-affected-story> — <what to add/edit/create>   [comment | description edit]
  - (new story) — <proposed summary>   [CREATE as To Do child of <config.epicKey> + add to wave plan]
Strike or amend anything above before approving — this gate is the only decision point.
</If>
```

On a skill-only story, `Ticket status` goes to Done, and `Proposed commit`, `Push` and `PR` read `none — skill-only story`.

- **yes** → Step 5. **no** → stop. **edit** → ask for a replacement subject, validate it against Step 3, re-show the block. Same for striking or amending evolution items.

## Step 5 — Act on the epic evolution items (skip when `epicEvolutionItems` is empty)

These edits land in the plans repo uncommitted; the script's single plans-repo commit carries them with the outcome. A failed item never stops the ship — report it as `NOT created: <item> — <reason>; run /giga-workflow:create-jira <board> <config.epicKey> to file it`.

- **(a) New story** — only genuinely new product work, never a refactor (`docs.constraints` § Refactor When Touched). Born split, as `/giga-workflow:create-jira` does: load `<jira.mcpPrefix>createJiraIssue` (one `ToolSearch`), create it with `parent=<config.epicKey>` and a summary under 80 characters, `Write` its scope, evidence and acceptance to `<plans.repo>/<board>/<NEW-KEY>.md` (front matter `jira/project/board/type/epic/summary`), then in one `Bash` call `python3 <plans.script> transition <NEW-KEY> "<jira.createStatus>"` (`To Do` when absent — a project may create it in `Backlog`, which hides it from `/giga-workflow:epic-next`) `&& python3 <plans.script> stub <NEW-KEY>`. Batch several new stories' create calls in one message and their transitions in one call. Add each to the wave plan: `python3 <plans.script> section <config.epicKey> Wave`, `Read` only that range, append `- <NEW-KEY> — <summary> · <Type>` to the wave it belongs to (a new `### Wave <N> — <theme>` when none fits). Pass the new keys as `followUps`.
- **(b) Existing sibling** — a comment goes through `printf '%s' '<markdown>' | python3 <plans.script> comment <SIBLING>`; a description edit goes to that sibling's own `<plans.repo>/<board>/<SIBLING>.md`, never to Jira's description.

## Step 6 — Ship: one script call

Stop any `Monitor` this session armed on a Storybook log first (`TaskStop`), unless `--keep-storybook` — otherwise its `tail -f` outlives the server. Then write the handoff to the scratchpad and run the script, in one message:

```json
{
  "board": "<board>", "key": "<KEY>",
  "until": "review | merged",
  "noPush": false, "build": false, "keepStorybook": false,
  "commit": { "subject": "<subject>", "trailer": "<the co-author trailer this session uses>",
              "refactorSubject": "<refactor subject> | null", "refactorPatch": "<abs path> | null" },
  "skills": { "subject": "<skills subject>", "refactorSubject": null, "refactorPatch": null },
  "prBody": "<Step 3b PR body>",
  "outcome": { "text": "<Step 3b outcome>", "pins": ["<pin>"] },
  "shipped": "<Step 3b shipped line>",
  "followUps": ["<NEW-KEY>"], "auditKeys": [],
  "secrets": [],
  "notify": true, "nextStory": true
}
```

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/ship.py run <scratchpad>/ship-<KEY>.json
```

`until` is `merged` under `--merge`, else `review`; epic-branch and direct boards ignore it. `skills` is `null` when the leg is not pending. Under an `/giga-workflow:epic-loop` story agent set `notify` and `nextStory` to `false`: the orchestrator owns the notification and picks the next story. Run the skills leg from a session that loads the live copy of the skills repo, not the story worktree, which the leg removes.

What the script does, in order, each stage skipped when its state says it already ran: `--build` → the skills leg (commit in the story worktree, rebase onto `<skillsRepo.branch>` if it moved, fast-forward it, push with `skillsRepo.push`, remove the worktree and the landed branch) → the refactor commit, then the feature commit (hooks run; never `--no-verify`) → land by mode (PR: push, open the PR or reuse an open one, ticket → In Review, sub-tasks → Done; epic-branch: push the epic branch, ticket → Done; direct: rebase onto `origin/<git.mainBranch>` if needed, fast-forward, push, ticket → Done) → under `--merge`, wait out `UNKNOWN`, update a `BEHIND` branch once, merge `CLEAN`/`UNSTABLE`/`HAS_HOOKS` with `--<git.mergeMethod> --delete-branch`, verify `MERGED`, sync local `<git.mainBranch>`, ticket → Done → the Jira comment → the plan file's `## Outcome` → on reaching Done: the wave-plan entry out, the `## Shipped` line in, the epic → Done when no child is open, matching `.claude/plans/` files removed → one plans-repo commit → approved secrets paths (from `/giga-workflow:epic-story-ship`) → stop Storybook → the notification → the next story and its `effort:`.

## Step 7 — When the script stops

It exits 1 with `STOPPED at <stage>: <reason>` and a `State:` line saying what has and has not landed; every stage before it stands. Fix the cause and re-run the same command — it resumes. The rules it already follows are yours too: never `--no-verify`, never `--amend`, never force-push.

- **commit / refactor commit** — the hook output is in the reason; fix, re-run.
- **push rejected (PR mode), skills push rejected** — a deeper coordination issue: surface it to the user, do not force anything.
- **rebase conflict, fast-forward refused, branch protection (direct mode or skills leg)** — `<git.mainBranch>` / `<skillsRepo.branch>` is untouched or the reason names what to do; surface it.
- **merge** (`DIRTY`, `BLOCKED`, `CLOSED`, never mergeable) — the story is committed, pushed, PR open, ticket In Review; no outcome, wave-plan or cleanup step ran. Report the blocker; once it is cleared, re-run the same `ship.py run` command (re-invoking this skill would refuse on the open PR).
- **pr** — `gh pr create` failed after the push; surface it, re-run once `gh` works.

Failures after the story landed (a transition, the comment, the outcome, the wave plan, the plans commit, a secrets push, Storybook) never stop the run: they print as `!` lines or as the row's own text. Relay them.

## Step 8 — Final report

Print the script's output verbatim from its `✓`/`✗` line through its last `!` line, minus the `RESULT` JSON. Then, when `RESULT.epicClosed` is true and `epicCloseSkill` is set, invoke `<epicCloseSkill> closed <RESULT.epic>` (Skill tool) and print its `Epic order` / `Plan next` block, then `Review: /giga-workflow:epic-review <RESULT.epic> — before /giga-workflow:epic-plan <NEXT-KEY>`. Under PR mode without `--merge`, end with:

```
Next:
  • Review the PR (github.com or `gh pr view <N>`).
  • Then run /giga-workflow:epic-merge-pr <N> — merges it (`git.mergeMethod`), deletes the branch, and chains
    /giga-workflow:post-merge-cleanup to transition <KEY> → Done.
```

On an epic-branch board add: when the whole epic is complete, open ONE PR (`<config.epicBranch>` → `<git.mainBranch>`); after it merges run `/giga-workflow:post-merge-cleanup <config.epicBranch>`.

---

## Notes

- **PR mode:** without `--merge` this skill ends at In Review, and `/giga-workflow:epic-merge-pr` takes the reviewed PR to Done. `/giga-workflow:epic-story-ship` is this skill with `--merge`, the evolution audit and the secrets repos behind one gate. **Epic-branch mode:** this skill takes the story to **Done** on the epic branch; `/giga-workflow:post-merge-cleanup` runs once per epic on the final `epicBranch → <git.mainBranch>` PR. **Direct mode:** this skill takes the story onto `<git.mainBranch>` and to **Done** and cleans up itself. **Skill-only story:** onto `<skillsRepo.branch>` and to **Done**, no PR.
- The notification body is `<KEY> · <task>` — the Jira key, never the board, repo name or path; the notify tooling stamps those. The format is shared with `/giga-workflow:epic-next`; change them together.
- Once the commit has landed, nothing downstream rolls it back — report the failure and continue.
