---
name: jira
description: "Work on a Jira ticket: read ticket details, create a feature branch, plan the implementation, update the ticket with technical details, and start coding: $ARGUMENTS"
---

Work on a Jira ticket: read ticket details, create a feature branch, plan the implementation, update the ticket with technical details, and start coding: $ARGUMENTS

## Project config

Repo-specific values come from `.claude/giga/config.json` at the repository root, under `workflow` (plus the top-level `ideas` and `ux` keys every plugin shares). Read it once at the start. A missing file or field takes the fallback below, never a guess.

| Field | Used for | When absent |
| --- | --- | --- |
| `plans.repo` | the plans repo that holds ticket content and board navigation | stop and say the repo has no `plans.repo` in `.claude/giga/config.json` |
| `plans.script` | the script behind `ensure` and `board` (Phases 1, 2.75) | stop and say the repo has no `plans.script` in `.claude/giga/config.json` |
| `plans.guide` | the plans guide, canonical for those commands | skip reading it |
| `jira.cloudId` | the Jira cloud id for every MCP call (Phase 1) | resolve it with `<jira.mcpPrefix>getAccessibleAtlassianResources` |
| `jira.mcpPrefix` | the tracker MCP tool-name prefix | stop and say the repo has no `jira.mcpPrefix` in `.claude/giga/config.json` |
| `git.mainBranch` | the base branch the story is not switched to | `main` |
| `skillsRepo.path` | the skills repo's main checkout; a plan that edits files there gets a story worktree beside it (Phases 3, 5s, 6, 7) | no skills leg: every file the story edits is in this repo |
| `skillsRepo.branch` | the skills repo's live branch the story worktree is cut from (5s) | `main` |
| `skillsRepo.check` | the skills repo's own check command, run in the story worktree (Phase 6) | the skills repo's commit and push hooks are its only gate |
| `docs.constraints` | the standards doc plan-time refactoring is measured against | skip that standards read |
| `docs.agentsMd` | the `AGENTS.md` locations to consider (Phase 3), with `<app>` / `<domain>` to fill in | the nearest `AGENTS.md` above each file the ticket touches |
| `docs.testingStrategy` | where the roster of projects declaring `typecheck` lives | skip the pointer |
| `docs.commands` | the commands doc that deliberately omits dev-server launch details | skip the pointer |
| `checks.gate` | the combined build / typecheck / lint / test run (Phase 6) | run `build`, `typecheck`, `lint` and `test` per affected project with `checks.single`; with both absent, ask the user for the check commands |
| `checks.single` | one target on one project (`<project>`, `<target>`), for slice checks and red-gate re-runs (Phases 5, 6) | run `checks.gate` instead; with both absent, ask the user for the check commands |
| `checks.affected` | the broad-change variant of the gate | use `checks.gate` only |
| `checks.antiPatterns` | the anti-pattern checker run on touched files | skip that check and say so |
| `planning.backendGlobs` | path globs that mark a backend slice (Phases 3b, 5a) | treat a plan as having no backend slice |
| `planning.frontendGlobs` | path globs that mark frontend slices (Phases 3b, 5a) | treat every non-backend slice as frontend |
| `planning.designLibrary` | the shared design library to reuse from: its component `prefix` and `path` (Phase 3) | look for reusable components in the domain's own libraries only |
| `commit.refactorCommitFirst` | whether refactor work lands as its own commit ahead of the feature (Phase 5r) | skip the refactor snapshot and the `## Refactor (in place)` list; still refactor in place |
| `ideas.policy` (top level) | the Idea Board entry threshold and match check | no idea is written to a board: each stays a plans-file note and goes in the report for the owner |
| `ideas.board` (top level) | where qualifying ideas are written | a qualifying idea goes in the story's plan file under `## Ideas for the Idea Board` and in the report for the owner |
| `ux.brandVoice.guides` (top level) | the voice guide handed to the UX agents | pass "none yet" |
| `ux.devServerSkill` (top level) | the skill that owns the dev-server launch command and port per app | read `devServers`; if neither exists, ask the user for the serve command and port |
| `devServers` | the per-app serve command and port for the test plan | as `ux.devServerSkill` above |

---

## Prerequisites

Ticket **content** (description / implementation plan / acceptance criteria) lives in the **plans repo** (`plans.repo`) as `<prefix>/<KEY>.md` (prefix = lowercased key prefix, e.g. `abc/ABC-123.md`), **not** in Jira — the Atlassian MCP returns a ~5.5k-char fat envelope per issue and ignores field-narrowing. Jira keeps **status** (transitions, assignees, comments). Read descriptions + board-nav from the plans repo via `python3 <plans.script>` (it self-authenticates); use the MCP only for the cloud ID, a scoped metadata/comment read, transitions, and comments. Canonical guide: the plans guide (`plans.guide`).

This skill still makes MCP calls, so load the required MCP tools with **one** ToolSearch call — the
`select:` query takes a comma-separated list, and eight separate calls are eight round trips for the
same result:

```
select:<jira.mcpPrefix>getAccessibleAtlassianResources,<jira.mcpPrefix>getJiraIssue,<jira.mcpPrefix>addCommentToJiraIssue,<jira.mcpPrefix>getTransitionsForJiraIssue,<jira.mcpPrefix>transitionJiraIssue
```

Add the Stitch trio to that same call **only when the ticket actually carries a Stitch reference**
(Phase 2.5 tells you): `mcp__stitch__get_project,mcp__stitch__list_screens,mcp__stitch__get_screen`.

## Subagent budget

A subagent's bill is **its turn count × its context size × its model rate** — it is not a flat fee,
and it does not shrink because the task was small. Measured across epic sessions,
subagents are 44% of all tokens and Opus subagents alone are 67% of the subagent total. Three rules
follow, and every phase below applies them:

1. **Settle a question in the main context when a shell command can settle it.** An agent spawned to
   confirm something `git log` already proves costs millions of tokens to say "yes".
2. **Default to one agent.** Fan out only against a stated threshold, and say the count and the
   reason out loud before spawning.
3. **Pin the model to the work.** `sonnet` for mechanical or bounded work (wiring, scaffolding,
   running a target, reviewing a named diff); inherit Opus only where a wrong judgment call is
   expensive — the re-validation audit (Phase 2.75) and design-bearing implementation slices.

Never spend an agent on reformatting context you already hold.

## One turn, many calls

The same `turns × context` arithmetic governs your *own* context, and it is the larger of the two
bills in practice. Measured on a real run of this chain: **491 tool calls across 491 turns** — a mean
of exactly 1.00, so no independent pair was ever batched, and each call re-read a ~474k context to
run a two-line shell command.

The phases below are numbered for reading order, **not** for one-call-per-message execution:

- Calls that do not consume each other's output go in **one message**, however many there are.
- Shell steps that run in sequence go in **one `Bash` call**, joined with `&&` or newlines. Three
  numbered code blocks in a row are one call unless a decision sits between them.
- Never probe before acting when the action reports the same thing — no `ls` before `Read`, no
  `git branch --show-current` in its own turn when the next git call can print it.
- Batch every `Read` whose path you already know into the message that needs the first one.

Explicit batch points are marked ⚡.

## Phase 1: Read the Jira Ticket

1. **Parse the ticket ID and flags** from `$ARGUMENTS`. If no ticket ID is present, ask the user for a ticket ID and stop. Recognized flags:
   - `--no-revalidate` — skip Phase 2.75 entirely. Use only for tickets you know are fresh.

2. **Get the Atlassian Cloud ID.** Use `jira.cloudId` as `cloudId` for all subsequent Jira calls. If it is absent:

   ```
   <jira.mcpPrefix>getAccessibleAtlassianResources()
   ```

   and use the `id` field from the response.

3. **Read the ticket.** The **description / plan / acceptance criteria** live in the plans repo, not Jira. Print the local file path (migrating on-miss) and read it:

   ⚡ The plan-file path and the sub-task board query (step 6 below) are independent — resolve both in
   one `Bash` call, then `Read` the plan file:

   ```
   python3 <plans.script> ensure <KEY>
   python3 <plans.script> board --jql 'parent = <KEY> ORDER BY created ASC'
   ```

   Then `Read` the path the first line printed. If sub-tasks came back, ⚡ `Read` every sub-task plan
   file in **one** message (their paths come from a single `ensure` call per key, batched the same way).

   For the status metadata + comments the local file does not carry, make a **scoped** MCP read — description dropped (it comes from the file above), no `expand="renderedFields"`:

   ```
   <jira.mcpPrefix>getJiraIssue(cloudId, issueIdOrKey, fields=["summary","status","assignee","reporter","priority","issuetype","comment","created","updated","labels","components"])
   ```

4. **Display a summary** to the user:

   ```
   Jira Ticket: <KEY> — <summary>
   Type: <issuetype> | Status: <status> | Priority: <priority>
   Assignee: <assignee> | Reporter: <reporter>

   Description:
   <description text>

   Comments: <count>
   <list comments if any>
   ```

5. **Save the ticket details** (key, summary, description, current status) for later phases.

6. **Fetch the ticket's sub-tasks.** A decomposed story carries its implementation detail in its sub-tasks, not its own description — so they MUST be pulled in. Enumerate them via the board script (live status, not the MCP):

   ```
   python3 <plans.script> board --jql 'parent = <KEY> ORDER BY created ASC'
   ```

   Returns JSON `[{key,status,category,type,priority,parent,summary}]` — the sub-task keys + summaries + live status, but **not** their descriptions (content lives in the plans repo, one file per key).

   - **If sub-tasks are returned:** for each sub-task, read its description from its own local file — `plan=$(python3 <plans.script> ensure <SUBTASK-KEY>)` then `Read $plan` — and treat **each sub-task's description as a required slice of this story's implementation** (the build checklist — not optional). Add them to the Phase 1 summary as `Sub-tasks: <count>` followed by each `<KEY> — <summary> [<status>]`, and carry every sub-task description into planning (Phase 3).
   - **If none are returned:** this is a leaf ticket — continue normally (no-op).

## Phase 2: Use Current Branch

1. **Check the current branch:**

   ```
   git branch --show-current
   ```

   Use whatever branch is currently checked out — do NOT create a new branch or switch to `<git.mainBranch>`.

2. **Transition to "In Progress"** unconditionally:
   - Get available transitions:
     ```
     <jira.mcpPrefix>getTransitionsForJiraIssue(cloudId, issueIdOrKey)
     ```
   - Find the transition with `name: "In Progress"` and use its `id`
   - Execute the transition:
     ```
     <jira.mcpPrefix>transitionJiraIssue(cloudId, issueIdOrKey, transition={id: "<transition-id>"})
     ```
   - If the ticket is already "In Progress", skip the transition call.

3. **Report** the current branch name and status change to the user.

## Phase 2.5: Fetch Design Comps

Before planning, extract any design references from the ticket and load the comp content so it informs the implementation plan.

### Detect design references

Scan the ticket description and comments for:

- **Stitch links** — any mention of a Stitch project/screen ID or URL (a Stitch URL, `stitch project`, a `projectId` / `screenId`)
- **Figma links** — any `figma.com/file/...` or `figma.com/design/...` URL

### Fetch Stitch comps (if found)

Only when the Stitch MCP tools are available in the session; otherwise report the reference to the user and continue.

1. Load the project overview:
   ```
   mcp__stitch__get_project(projectId)
   ```
2. List all screens:
   ```
   mcp__stitch__list_screens(projectId)
   ```
3. For each screen referenced in the ticket (or all screens if the ticket says "all"), fetch the full screen spec:
   ```
   mcp__stitch__get_screen(projectId, screenId)
   ```
4. **Summarize the comps** — layout, component names used, color tokens, spacing, typography, interactive states. Keep this summary concise; it will be passed into the planning context.

### Fetch Figma comps (if found)

Use `WebFetch` to retrieve the Figma embed URL or use the Figma share URL directly if it is publicly accessible. Capture the design description, component names, and any annotated specs visible from the URL. If the link requires auth (returns a login page), report to the user:

> "Figma link found but requires authentication — please paste the relevant comp screenshot or description."

Then wait for the user to supply it before proceeding.

### No design reference

If the ticket contains no Stitch or Figma reference, skip this phase and proceed to Phase 2.75.

---

## Phase 2.75: Pre-implementation Re-validation

> The ticket description was written at a point in time. By the time it is picked up, sibling stories may have shipped that moved files, renamed symbols, or made the proposed work already-done or obsolete. This phase grounds every code anchor in the description against the current repo state BEFORE planning. If anything has drifted, the description is replaced with revised instructions; if intent is unclear, the human is asked.
>
> **Audit focus, in priority order:**
> 1. **Every explicit file path mentioned in the description** — exists? moved? deleted? renamed?
> 2. **Every line-number reference** (`file.ts:N` patterns) — does line N still match the description's claim, or has the content shifted up/down (or vanished)?
> 3. Secondary anchors — function / class / type / slice / facade / route / Firestore path / callable names mentioned alongside the above.
>
> Files + line numbers are the primary drift surfaces. Secondary anchors are confirmatory signals.

### 2.75a — Skip conditions

Skip this phase entirely if either of:
- `--no-revalidate` was passed in `$ARGUMENTS`
- The ticket description contains no file-path references AND no line-number references AND no symbol mentions (pure-prose / pure-acceptance-criteria ticket — nothing to ground)

Otherwise run **2.75a2 next — do NOT spawn the subagent yet.**

### 2.75a2 — Deterministic drift gate (no subagent)

**Drift is caused by commits.** If nothing has landed in the anchored paths since the description was
written, the description cannot have drifted, and an Opus agent that spends millions of tokens
rediscovering that is pure waste. Settle the question here, in your own context, with three shell
calls.

1. **Collect the anchors.** From the description you already hold, list every `libs/…`, `apps/…`,
   `docs/…` or `scripts/…` path and every `file:N` reference. Call the path set `ANCHORS`.

2. **Date the description.** The plan file is version-controlled, so its last write *is* the moment
   the description was authored:
   ```
   PF=<plans.repo>/<prefix>/<KEY>.md
   N=$(git -C <plans.repo> rev-list --count HEAD -- "$PF")
   DESC_TS=$(git -C <plans.repo> log -1 --format=%cI -- "$PF")
   ```

   ⚠️ **`N <= 1` means the timestamp is worthless.** Phase 1's `ensure` migrates a missing file, so a
   single-commit history dates the *migration*, not the authoring — the description may have been
   written in Jira months earlier. Treat `N <= 1` as INCONCLUSIVE and go straight to 2.75b. Same if
   the one commit that produced `DESC_TS` changed only the front matter rather than the body.

3. **Test existence, then movement.** ⚡ Steps 2 and 3 are one `Bash` call — nothing between them
   needs your judgment:
   ```
   PF=<plans.repo>/<prefix>/<KEY>.md
   N=$(git -C <plans.repo> rev-list --count HEAD -- "$PF")
   DESC_TS=$(git -C <plans.repo> log -1 --format=%cI -- "$PF")
   echo "N=$N DESC_TS=$DESC_TS"
   for p in $ANCHORS; do [ -e "$p" ] || echo "MISSING $p"; done
   [ "$N" -gt 1 ] && git log --oneline --since="$DESC_TS" -- $ANCHORS
   ```
   The entire gate is one round trip.

Read the gate:

| Result | Action |
|---|---|
| No `MISSING` **and** zero commits since `DESC_TS` | **ALIGNED.** Print `✓ Anchors ground clean — no commit has touched them since the description was written (<DESC_TS>).` **Skip 2.75b** and continue to Phase 3. |
| Any `MISSING`, or ≥1 commit since `DESC_TS` | Drift is *possible*. Run 2.75b, passing the `MISSING` list and the `git log --oneline` output as pre-computed evidence. |
| `N <= 1`, `DESC_TS` empty, or anchors unresolvable | Inconclusive. Run 2.75b with no pre-computed evidence. |

The pass condition holds the anchored tree byte-identical to what the description's author saw. Every
drift class this phase names — moved, renamed, reshaped, removed, already-done, now-obsolete —
requires a commit to occur, so zero commits rules out all of them. This is a sound skip, not a
weakened audit; do not extend it to a "probably fine" judgment call when the gate does not pass.

The gate's two error directions are not symmetric. A `DESC_TS` that is **too early** shows extra
commits, fails the gate and runs the agent — it costs tokens and nothing else. A `DESC_TS` that is
**too late** hides real commits and skips an audit that was needed. So whenever the timestamp's
provenance is in any doubt, resolve it toward the earlier value and let the agent run.

### 2.75b — Spawn re-validation subagent (only when 2.75a2 did not pass)

Use the `Agent` tool with `subagent_type: general-purpose` and **`model: opus`**. Intent inference under drift is the most error-prone part of this skill (a dry run produced a hallucinated drift finding under default model selection); the cost of an Opus run is justified by the cost of a wrong revised description landing in Jira. One foreground agent — the audit needs the full ticket in context.

Fill the `## Pre-computed evidence` block from 2.75a2 before sending the prompt. It is what keeps this
agent short: without it, the agent re-derives the commit history and the file inventory one tool call
at a time, and turns are the cost multiplier.

Prompt template:

```
You are the pre-implementation re-validation agent for a Jira ticket about to be coded.

Your job: read the ticket description, ground every code anchor in the current repo
state, and decide whether the description is still actionable AS-IS.

If it is, return ALIGNED.

If it is not, infer the ORIGINAL INTENT of each drifted instruction (what was the
author trying to achieve?), then write a REVISED description that achieves the same
intent against the current code. Be conservative — when intent is ambiguous, flag it
as an open question rather than guess.

## Ticket

Key: <KEY>
Summary: <summary>
Description (current, from Jira):
<full description markdown>

## Pre-computed evidence

The orchestrator already ran the deterministic gate. Start from these results — do NOT re-derive
them, and do NOT survey the wider repo:

Description last written: <DESC_TS>
Anchored paths that no longer exist:
<MISSING list, or "none">
Commits touching the anchored paths since the description was written:
<git log --oneline output, or "none">

Confine your investigation to the anchors named in the description and the commits listed above. If
that evidence is marked "none" for both, the only drift classes still open are semantic ones
(reshaped-in-place, already-done) inside the listed commits — check those and stop.

## Audit dimensions (priority order)

PRIMARY — these are the must-audit anchors:

1. **Every explicit file path** mentioned in the description (every `libs/...`,
   `apps/...`, or relative path mention). For each:
   - Does the file exist at that path TODAY? (Read / Bash `ls`)
   - If not, has it been moved or renamed? (Bash `git log --diff-filter=R --follow`,
     `git log --diff-filter=D`, or grep the new tree for a matching basename)
   - Was it deleted with no replacement?

2. **Every line-number reference** of the form `file:N` or `file.ts:N` in the
   description. For each:
   - Read that exact line in the current file.
   - Does its content still match what the description claims is there?
   - If not, grep the file for the description's claimed content — has it shifted to
     a different line, or has it vanished entirely?
   - Distinguish line-number-drift (same content, different line) from
     structural-drift (content gone or changed).

SECONDARY — these are confirmatory signals, audited in service of the primary anchors:

3. Function / class / type / interface / slice / facade / selector / route /
   Firestore path / callable names mentioned alongside primary anchors. Confirm
   each still exists and matches the description's claimed shape (signature,
   members, location).

4. Acceptance-criteria items that reference any of the above.

## What to look for

For each anchor in the primary set, classify drift as one of:
- **Renamed** — same conceptual thing, new name; description should refer to the new name
- **Moved** — same content, different path; description's path should update
- **Removed-and-replaced** — original is gone; a sibling story shipped the replacement
- **Removed entirely** — gone with no replacement; description's premise is broken
- **Reshaped** — still there but signature/fields/types differ from the description
- **Already done** — the work the description proposes is already in the code
- **Line-shifted** — same content, different line number; trivial fix to the description
- **Now-obsolete** — a sibling story made the proposed work irrelevant

## Output

Return exactly one of two structured blocks:

REVALIDATION_RESULT_START
Verdict: ALIGNED
(no further content)
REVALIDATION_RESULT_END

OR

REVALIDATION_RESULT_START
Verdict: DRIFTED

Drift findings:
  - <anchor (path or path:line)> — <drift class from above> — <one-line impact on the description>
    Source quote: "<verbatim substring from the description that introduced this anchor>"
  - ...

Intent inference (per drifted section of the description):
  - § <section name> — Original intent: <one sentence>. Confidence: high | medium | low.
  - ...

Open questions (only if any intent confidence is medium or low):
  - <question for the human, framed so a single sentence resolves it>
  - ...

Revised description (full markdown, ready to replace verbatim):

<the entire new description>

REVALIDATION_RESULT_END

## Rules of conduct

- Never invent code anchors. If you cannot verify something, surface it as an open
  question rather than guessing.
- **Source-quote requirement.** Every drift finding MUST carry a `Source quote:`
  sub-line containing a verbatim substring of the description (the text that
  introduced the anchor — file path, line reference, symbol name, etc.). If you
  cannot quote the anchor from the description verbatim, DROP THE FINDING —
  do not list it. This rule exists to suppress hallucinated drift findings.
- **Only list DRIFTED anchors in the drift findings block.** Aligned anchors stay
  silent — do NOT include them with an "Aligned" label or a "no drift on this
  anchor" note. The drift findings block exists exclusively to enumerate items
  the revised description will change.
- Preserve the description's existing structure (Summary / Files / Plan / AC / etc.) —
  revise the contents, not the skeleton.
- Preserve every acceptance-criteria checkbox. If an AC item is now obsolete, mark
  it ~struck-through~ with a one-line note rather than deleting it. The human
  decides whether to remove obsolete AC.
- Cite each drift finding with file_path:line_number (current state, not what the
  description claimed).
- If you find that the proposed work is already done, that IS drift — say so
  explicitly in findings and have the revised description either reduce scope to the
  remaining work or recommend closing the ticket.
- Line-shifted-only drift (content found, just at a different line) is real drift —
  fix the line numbers in the revised description.
```

### 2.75c — Parse + present

Parse the subagent output between `REVALIDATION_RESULT_START` / `REVALIDATION_RESULT_END`.

- **ALIGNED** → print one line ("✓ Description is current — no revision needed.") and continue to Phase 3.
- **DRIFTED** →
  1. Print the drift findings + intent inference.
  2. If any open questions exist, ask the user via `AskUserQuestion`. Cannot revise until they are answered. After answers come back, re-spawn the subagent with the answers folded into the prompt (under a new `## Human-resolved questions` section) so it can produce a final revised description.
  3. Otherwise, gate via `AskUserQuestion`: *"Replace ticket description with revised version? (yes / preview / no)"*
     - `preview` → print the full proposed new description, then re-ask
     - `yes` → proceed to 2.75d
     - `no` → continue to Phase 3 with the ORIGINAL description (the audit becomes informational only; the human implicitly accepts that the plan will be against the as-written description)

### 2.75d — Replace description + breadcrumb

The description lives in the plans repo — replace it **there**, not in Jira (never `editJiraIssue(fields={description})`; Jira's description is only a stub). `Edit` the local plan file you read in Phase 1 (`$plan`, i.e. `<plans.repo>/<prefix>/<KEY>.md`): replace its **body** (everything below the front matter) with the revised description verbatim, preserving the `jira/project/board/type/epic/summary` front-matter block. You already read this file in Phase 1, so you have its current body to match against.

Then post a one-line breadcrumb comment so future readers know the description was re-validated (not modified by a human):

> *Pre-implementation re-validation (`/giga-workflow:jira`, <today's date>) — description revised against current code state. Original preserved in the plans-repo git history.*

Use `<jira.mcpPrefix>addCommentToJiraIssue` with a minimal ADF document containing just that one paragraph.

Refresh the saved ticket details from Phase 1 (Step 5) with the revised description so Phase 3 plans against the up-to-date version.

### 2.75e — Autonomous-run behavior

When invoked from an `/giga-workflow:epic-loop` story agent (i.e. no human is sitting at the keyboard):

- If the subagent returns **ALIGNED**, proceed normally.
- If the subagent returns **DRIFTED**, **STOP the run** and surface the findings to the user. Drift means the autonomous run cannot trust the description; a human must confirm the revised version (or modify it) before implementation continues. Never auto-revise + auto-continue.

---

## Phase 2.8: UX Frame (`giga-ux:ux-design` — Before)

A story that changes what a user sees gets its structure — placement in the app, entry points, labels, flow, states — framed before it is planned, so the plan builds the piece **in the app**, not in isolation. The method is the `giga-ux:ux-design` skill's Before stage. Phases 2.8 and 6.5 run only when the `giga-ux:ux-design` skill is available in the session; without it, say so and skip both.

**Skip** when the story has no user-facing surface: backend-only, docs-only, a pure rename or refactor with no UI change, emit-only telemetry. Say which and move on.

**Size it like the change:**

| Story | Run |
| --- | --- |
| One component, no new route or nav entry | Inline, in your own context: `giga-ux:ux-design` Frame steps 1, 5, 6 and 7 — no agent |
| A page, a flow, a new route or nav entry, or a dashboard / hub change | **One** `giga-ux:ux-architect` agent (`model: sonnet`) |

Hand `giga-ux:ux-architect` the plan-file path, the Phase 2.5 comp summary, any spec or `designReferences` the board config names, and the app's voice guide path (`ux.brandVoice.guides` in `.claude/giga/config.json`, or "none yet"); it reads the code itself. It returns the **UX brief** and **Decisions for the owner**, at most three per story.

- The brief is a planning requirement in Phase 3, beside the acceptance criteria — its entry points, states, vocabulary and words are slices of this story, not follow-ups.
- The brief's **Ideas** go to the Idea Board (`ideas.board`) only when they meet the idea policy (`ideas.policy`) § Entry threshold and nothing matches them (§ Check for a match first); a match is recorded as "covered by <key or id>", and the rest are plans-file notes. An idea that qualifies but cannot be written (no `ideas.board`, or no `ArtifactData` in this context) goes in the story's plan file under `## Ideas for the Idea Board`, where `/giga-workflow:epic-review` posts it; a note that fails the threshold never goes under that heading. Never into the plan.
- **Interactive:** put the Decisions for the owner to the user at the plan gate (`ExitPlanMode`), in plain terms. A recommended cut is a decision like any other, and the story is built as written unless the user agrees to it.
- **Autonomous** (`/giga-workflow:epic-next` under `/giga-workflow:epic-loop`): build the brief as framed, record each decision for the owner in the story's plans file under `## UX decisions for the owner` with the default taken, append it to the epic's plan file under `## UX decisions for the owner` (one list per epic, story key on each line) so none is defaulted unseen, and list them in the final report. The default for a recommended cut is always to build the story as written. STOP only when a decision blocks an acceptance criterion — the same rule as 2.75e.

---

## Phase 3: Plan the Implementation

1. **Discover relevant AGENTS.md files** before entering plan mode. Based on the ticket scope, identify which apps and libraries will be touched (inferred from the ticket description, domain keywords, or obvious feature area). These files define component conventions, CSS variable contracts, available reusable components, state patterns, and review checklists, and **all of it must inform the plan**.

   Read the AGENTS.md of **every library the ticket will actually modify** — that set is not optional. Candidate locations: the `docs.agentsMd` paths, with `<app>` and `<domain>` filled in for this ticket (any that do not exist are skipped).

   ⚡ Once you have decided which of these the ticket touches, `Read` them **all in one message** —
   they are independent files and reading them one per turn pays the whole context over again for
   each one.

   The list is a checklist of places to *consider*, not a set to read wholesale. Skip any path the ticket does not touch: these files stay in context for the remainder of the session and are re-read on every subsequent turn, so a shared-library AGENTS.md pulled in "just in case" is paid for again at every later turn of the story.

2. **Enter plan mode** using the `EnterPlanMode` tool. This will trigger codebase exploration and plan creation per the system's plan mode workflow.

2b. **Read the code in context, and plan its refactor — in place.** For every file the ticket will touch, read it and note where it falls short of the current standard (`docs.constraints`, the library's `AGENTS.md`, `<checks.antiPatterns> <file>`). Bringing those files into the standard is part of the story, done in this story by the implementation agent that owns each file, as the first step of its slice (Phase 5r) — not an optional extra, not something to route around, and NEVER a follow-up story or PR (§ Refactor When Touched — no exceptions, repo-wide). A file discovered below standard later in the story — while building or verifying — joins the story the same way, before the feature is tested. The plan assigns every file — refactor-only or feature — to exactly one slice, and lists each slice's refactor files with the standard each is brought to. The code and its specs, not a notes file, are how a feature's current behavior is learned.

3. **During plan mode**, use the ticket description, comments, **every sub-task description from Phase 1** (each sub-task is a required slice of this story — the plan must cover all of them), acceptance criteria, **design comp summary from Phase 2.5**, **UX brief from Phase 2.8**, and **AGENTS.md context** as requirements. Explore the codebase to understand:
   - Which files need to be created or modified
   - Existing shared design-library components (`planning.designLibrary`: the `<prefix>`-prefixed components under its `<path>`) or the domain's own design-library components that can be reused
   - Existing patterns and conventions to follow (from AGENTS.md files)
   - Dependencies and related code
   - Testing approach

3b. **Split by layer, backend first.** If the plan spans the backend (`planning.backendGlobs` —
   functions, rules, indexes, seed) AND the frontend (`planning.frontendGlobs`; store / ui / app) and clears the 5a split
   threshold, the plan says so and proposes splitting the ticket into a backend story and frontend
   story(ies), backend first (`/giga-workflow:epic-plan` Step 7.5 is the rule). The user decides at the plan gate; if
   they keep one story, 5a runs the backend slice first.

3c. **Skills-repo files** (only when `skillsRepo.path` is set). A file the story changes in the skills
   repo — a skill, agent or hook — is listed under its own `Skills repo (<repo name>)` heading, by its
   path in that repo, and assigned to a slice like any other file. Phase 5 edits it in a story
   worktree (5s).

4. **Write the plan** to the plan file as directed by plan mode.

5. **Present the plan** to the user for approval via `ExitPlanMode`.

## Phase 4: Update Jira Ticket

After the user approves the plan (i.e., after exiting plan mode):

1. **Post the implementation plan as a comment** on the Jira ticket using `<jira.mcpPrefix>addCommentToJiraIssue`. The comment body must be in Atlassian Document Format (ADF).

   Build the ADF document with this structure:

   ```json
   {
     "version": 1,
     "type": "doc",
     "content": [
       {
         "type": "heading",
         "attrs": { "level": 2 },
         "content": [{ "type": "text", "text": "Implementation Plan" }]
       },
       {
         "type": "heading",
         "attrs": { "level": 3 },
         "content": [{ "type": "text", "text": "Context" }]
       },
       {
         "type": "paragraph",
         "content": [
           { "type": "text", "text": "<1-2 sentence summary of the problem and approach>" }
         ]
       },
       {
         "type": "heading",
         "attrs": { "level": 3 },
         "content": [{ "type": "text", "text": "Changes" }]
       },
       {
         "type": "bulletList",
         "content": [
           {
             "type": "listItem",
             "content": [
               {
                 "type": "paragraph",
                 "content": [
                   { "type": "text", "text": "<file-path>", "marks": [{ "type": "code" }] },
                   { "type": "text", "text": " — <what changes>" }
                 ]
               }
             ]
           }
         ]
       },
       {
         "type": "heading",
         "attrs": { "level": 3 },
         "content": [{ "type": "text", "text": "Branch" }]
       },
       {
         "type": "paragraph",
         "content": [{ "type": "text", "text": "<branch-name>", "marks": [{ "type": "code" }] }]
       }
     ]
   }
   ```

   Call:

   ```
   <jira.mcpPrefix>addCommentToJiraIssue(cloudId, issueIdOrKey, commentBody=<ADF document above>)
   ```

   Populate the ADF with the actual plan content:
   - **Context**: A concise summary of the problem and the chosen approach
   - **Changes**: One bullet per file being created or modified, with the file path in code format and a short description of the change
   - **Branch**: The current git branch name

2. **Report** to the user:

   ```
   Jira ticket <KEY> updated:
   - Comment added with Implementation Plan
   - Branch: <branch-name>

   Ready to start coding.
   ```

## Phase 5: Start Coding

> **Never commit.** Do not run `git add` or `git commit`, here or in the skills-repo worktree (5s). Leave all changes unstaged for the user to review and commit manually.

Implement according to the approved plan using a **team of parallel agents**. Divide work into as many agents as makes sense for the scope, then run a mandatory review gate before proceeding to Phase 6.

**Build the story as written.** Implementation proposes nothing. A defect noticed while building, outside this story, is one Idea Board entry (`ideas.board`) with `source: "build"` only when it meets the idea policy (`ideas.policy`) § Entry threshold and nothing matches it (§ Check for a match first; otherwise a plans-file note), never a slice, a branch or a ticket. One that qualifies but cannot be written goes under `## Ideas for the Idea Board` in the story's plan file (Phase 2.8). Tell every 5a agent to report only a defect that breaks or visibly mars a task, never an idea, and to act on none of it.

### 5s: Skills-repo worktree — only when the plan edits the skills repo

Skills-repo files are edited in a story worktree, never in `<skillsRepo.path>` or in the checkout that
holds `<skillsRepo.branch>`: that branch is live, and every repo that loads the skills runs it. ⚡ Create
it once, before 5a, in one `Bash` call — it takes this repo's branch name, and a rerun reuses it:

```bash
wt=<skillsRepo.path>-<key-lower> b=$(git branch --show-current)
[ -d "$wt" ] || git -C <skillsRepo.path> worktree add "$wt" -b "$b" <skillsRepo.branch> \
  || git -C <skillsRepo.path> worktree add "$wt" "$b"
git -C "$wt" status --short --branch
```

Each 5a agent that owns a skills-repo file gets the worktree path with its slice and edits there. Its 5r
snapshot is kept apart, `git -C <worktree> diff -- <refactor files> > <scratchpad>/refactor-skills-<slice>.patch`;
the orchestrator concatenates those into `<scratchpad>/refactor-skills.patch`, checks it with
`git -C <worktree> apply --check --cached`, and lists those files under the skills repo's name in
`## Refactor (in place)`, so the skills repo lands its own refactor commit ahead of the feature.

### 5r: Refactor inside each slice — no separate pass

There is no refactor team ahead of the feature agents. Each 5a agent owns its slice's files outright —
refactor and feature — and works them in two steps: (1) **Refactor first**: bring the slice's listed
refactor files to the standard the plan names, changing behavior only where the standard requires it;
gate them with `<checks.antiPatterns> <files>` plus the project's `lint` / `typecheck` /
`test`. (2) **Snapshot, then build**: before the first feature edit, save the slice's refactor diff —
`git diff -- <refactor files> > <scratchpad>/refactor-<slice>.patch`, appending
`git diff --no-index /dev/null <file>` for each file the refactor created — then implement the feature
on top.

Slices never share a file, so each agent's per-file diff holds its own refactor and nothing else; that
disjointness is what lets slices run in parallel instead of waiting on a refactor pass. A file two
slices would both need is assigned to one of them; the other codes against it once it lands. The
orchestrator edits no slice's files.

A project the plan refactors but the feature does not touch gets its own refactor-only slice (usually
`model: sonnet`), run alongside the others.

**Orchestrator rule:** do not read the refactored files. When every 5a agent has reported, concatenate
the slice snapshots into `<scratchpad>/refactor.patch` and confirm the index still equals HEAD and the
refactor applies cleanly on top of it — `git diff --cached --quiet && git apply --check --cached
<scratchpad>/refactor.patch` (a reverse check against the working tree fails once feature edits land on
the same lines, even when the patch is fine). Then append the refactor file list to the story's plan
file under a `## Refactor (in place)` heading (one path per line, grouped by project) —
`/giga-workflow:epic-story-complete` reads both to land the refactor commit ahead of the feature commit (`commit.refactorCommitFirst`).

### 5a: Implementation agents — one by default

Use the `Agent` tool (subagent_type: `general-purpose`). **Spawn ONE agent unless the plan clears the
split threshold below.** Under `/giga-workflow:epic-loop`, slices that own disjoint files fan out regardless of the threshold: `${CLAUDE_SKILL_DIR}/../epic-loop/autonomy-contract.md` §6.7. Each extra agent is a full agentic loop with its own context and its own
re-exploration of the repo; three agents on a four-file story cost roughly three times one agent and
coordinate worse.

**Split threshold** — fan out only when the approved plan touches **≥2 Nx projects AND ≥8 files**.
Below that, one agent. State the count and the reason in one line before spawning, e.g.
`3 agents — plan spans feature-store / feature-ui / the app, 21 files`.

**Model per agent** — do not let every slice inherit Opus:
- **`model: sonnet`** for mechanical slices — barrel/index exports, route + app-config wiring, spec
  scaffolding, a component that follows an existing sibling verbatim, mass renames.
- **inherit (Opus)** for design-bearing slices — new store slices, new component architecture,
  anything where the plan left a judgment call open.

When the threshold is cleared, split along natural boundaries (typically: backend — functions, rules,
indexes, seed and the models / API contract they define (`planning.backendGlobs`); store —
state/services/guards; UI — components/templates/styles (store and UI under `planning.frontendGlobs`);
wiring — routes, app config, index exports in the app).

**Backend first.** When the plan spans the backend and the frontend, the backend slice runs first,
alone; the frontend slices start once it reports, in parallel with each other, coding against the
landed contract. A plan with no backend slice starts every slice at once. Shared contract files
(models, API types) belong to the backend slice when there is one, else to the first slice.

Each agent receives:
- The full approved plan
- Its specific slice of files to create/modify
- All relevant context (existing patterns, imports, conventions from CLAUDE.md)
- Its slice's refactor file list and the standard for each (5r)
- For skills-repo files, the story worktree path (5s), the only place it edits them

Each agent must:
- Refactor its slice's listed files and save its refactor snapshot before any feature edit (5r)
- Follow all project conventions from CLAUDE.md
- Write unit tests alongside the code
- Run the `lint` and `test` targets with `<checks.single>` and fix any failures before reporting done
- Run `<checks.antiPatterns> <every file you touched>` — a `blocker` hit is a standards violation to fix, not to exempt (the commit hook will refuse it anyway)
- Scope those targets to its own slice's projects — never `run-many` across the workspace

> **Orchestrator rule:** Do not read implementation files yourself to prepare these prompts.
> Pass the plan text and the specific file list from the plan directly to each agent.
> Agents do their own codebase exploration — loading files into the main context here
> defeats the purpose of delegation.

### 5b: Mandatory Review Gate (runs after 5a) — sized to the diff

**Measure the diff before sizing the gate.** One call, in your own context:

```
git diff --stat
```

| Diff | Reviewers |
|---|---|
| ≤5 files, one project | **One** agent (`model: sonnet`) covering AC **and** tests in a single pass |
| Larger, or spanning projects | The AC + Unit Test split below, `model: sonnet` each |
| Ticket carries a Stitch reference | Add the Design reviewer (`model: sonnet`) in either case |

**Hand every reviewer the change set.** Put the `git diff --stat` output and the changed-file list in
the prompt and tell it to read `git diff -- <file>` for detail. A reviewer left to discover what
changed spends most of its turns on that discovery, and turns are the cost multiplier.

Spawn them in parallel — single message, multiple Agent tool calls.

⚠️ **Spawn them as `general-purpose`, not `feature-dev:code-reviewer`.** That agent type has no `Bash`
tool — it cannot grep at scale, cannot run the test target below, and on a large diff it falls back to
hand-reading every file. Measured on a 47-file story: 45 minutes, and it declined to assert the gate
criterion because it could not run the gate. A reviewer that cannot execute anything is not cheaper,
it is slower and weaker.

1. **AC Review agent** (`general-purpose`, `model: sonnet`)
   - Load the ticket description and acceptance criteria
   - Check every AC item: does the code satisfy it? Is any AC missing?
   - Report: `✓ AC met` / `✗ AC not met — <what's missing>`

2. **Unit Test agent** (`general-purpose`, `model: sonnet`)
   - Verify tests cover: component creation, key behaviors, edge cases, guard logic
   - Run the `test` target with `<checks.single>` for the affected projects only and confirm all pass
   - Flag any missing coverage for critical paths

3. **Design Review agent** (`general-purpose`, `model: sonnet`) — *only if a Stitch design reference is in the ticket*
   - Compare component HTML/SCSS against the Stitch board referenced in the ticket (via `mcp__stitch__get_screen` if available, or screenshot)
   - Check: layout matches, typography matches, spacing/color tokens match, interactive states match
   - Report: `✓ Design matches` / `✗ Mismatch — <what differs>`

Sizing the gate is about **how many contexts pay for the same reading**, never about how hard the
reviewers look. The blocking rules below are unchanged at every size.

#### This gate blocks — it is not a parallel track

**Do not proceed to 5c, Phase 6, or any commit/merge step until every agent spawned here has
reported.** A review that arrives after the merge gated nothing: it spent the tokens, produced its
finding too late to act on, and left a record implying the work was reviewed when it was not.

- A reviewer that cannot report is a **stop**, not a pass. Report `NEEDS_HUMAN` (unattended) or ask
  the user (interactive). Never merge around it and call the outcome reviewed.
- **Do not pressure a reviewer into a partial verdict.** Your deadline is not its principal's
  authorization to shorten an independent review, and a verdict extracted under pressure is worth
  less than the one you were waiting for.
- If a reviewer is slow because it lacks tools, fix the spawn and re-run it — do not route around it.

### 5c: Fix review findings

If any failures were reported in 5b, spawn a new round of fix agents (`general-purpose`). Pass each
agent the review findings relevant to its slice plus the original plan. Each fix agent must re-run
the `lint` and `test` targets with `<checks.single>` and confirm clean before reporting done.

**Never spawn more fix agents than 5a spawned build agents** — a fix round is strictly smaller than
the round that produced it. Reuse 5a's split and its per-slice models; where the findings land in one
slice, that is one agent, whatever 5a's count was.

If 5b reported no failures, skip this step.

### 5d: Document deviations from the ticket

After fixes are applied, compare the final implementation against the original ticket AC and specs. If **anything was intentionally built differently** — due to architectural constraints, a better approach discovered during development, a spec ambiguity resolved a certain way, or a scope reduction — post a comment on the Jira ticket documenting it.

Use `<jira.mcpPrefix>addCommentToJiraIssue` with an ADF comment structured as:

```
## Implementation Notes

### Deviations from Spec
- **<AC item or spec section>** — Originally specified as X. Implemented as Y instead.
  *Reason:* <brief architectural/technical rationale>

### Decisions Made
- <Any ambiguity in the ticket that was resolved during development, and how>
```

**When to post this comment:**
- A guard, component, or route was structured differently than the ticket described
- A specified behavior was simplified, deferred, or replaced with a stub
- An AC item was partially implemented (note what's covered and what isn't)
- An architectural pattern was chosen that differs from any example in the ticket

**When to skip it:**
- The implementation matches the ticket exactly with no notable deviations

This comment becomes the authoritative record of why the code diverged from the spec, visible to future developers and the PM without needing to trace git history.

## Phase 6: Build, Type-check, Lint, Test (no PR)

Do **not** create a PR per ticket. Instead:

1. ⚡ **Run the whole gate in one call.** Nx already parallelises across projects and targets, so a
   per-project loop buys nothing and costs one full-context turn per line. For the affected projects
   plus the app:
   ```
   <checks.gate>   # <projects> = <proj-a>,<proj-b>,<app>
   ```
   Nx skips a target a project does not declare, so listing all four is safe for a test-only library.

   ⚠️ **Read the summary line, not the exit code.** When *no* named project declares *any* named
   target — a typo in the `-p` list, say — Nx prints "No tasks were run" and **still exits 0**. A
   green exit is therefore not evidence the gate ran. Confirm the closing
   `Successfully ran targets build, typecheck, lint, test for N projects` line names every target you
   asked for and a plausible `N`.
   Use `<checks.affected>` instead when the change is broad enough that
   naming the projects is guesswork — but prefer the explicit `-p` list, which does not drag in
   unrelated projects a global input marked affected.

   Each target still matters for its own reason, and none may be dropped:
   - **build** catches type errors and module-resolution issues lint and unit tests miss. **Always
     include the app** — a ticket touching only libraries can still break the app build via
     barrel/type drift.
   - **typecheck** reads `.spec.ts` type errors, which are invisible to both `lint` and `test`. The
     roster of projects declaring it is in `docs.testingStrategy` § Type-checking a
     `.spec.ts`. The pre-commit hook runs it again at commit time, so a red result here is a
     blocked commit later.
   - **lint** and **test** as usual.

   Only when the combined run goes red do you re-run a single `<checks.single>` to
   isolate it — one call to get the answer, not fifteen to ask the question.

   **Skills-repo worktree (5s).** Run `<skillsRepo.check>` inside it in the same call, joined with `;`
   so a red gate still shows its result: `(cd <skillsRepo.path>-<key-lower> && <skillsRepo.check>)`. It
   blocks like the gate. With `skillsRepo.check` absent, say that the skills repo's commit and push
   hooks are its only gate.

2. **Fix any failures before proceeding.** Build failures in particular block the PR when the epic ships — do not defer them. If a build failure is pre-existing (not introduced by this ticket), verify by stashing the diff and rebuilding on the base commit; report to the user and continue only if it reproduces clean.
3. Report results to the user.
4. The PR is created once for the entire epic branch when all tickets are complete.

## Phase 6.5: UX Review (`giga-ux:ux-design` — After)

Runs after the Phase 6 gate is green, on every story Phase 2.8 did not skip. It needs the compiled, running app, which is why it cannot fold into the 5b gate.

- **Inline story** (one component): check the brief's states render and the label matches its siblings, in your own context — no agent.
- **Otherwise:** **one** `giga-ux:ux-reviewer` agent (`model: sonnet`). Hand it the UX brief, the app and port from the `ux.devServerSkill` skill's table (or `devServers`), the routes touched, and the app's voice guide path (`ux.brandVoice` in `.claude/giga/config.json`, or "none yet"). When the dev server is already running, tell the reviewer so, and not to start another.

**It blocks like 5b, and it may veto** (`giga-ux:ux-design` § Authority). Outcome `Owed` → render the named screens (seed the state, open the route, switch the theme or width) and re-dispatch `giga-ux:ux-reviewer` on them; this is not a revision round, and a screen still owed stops the story like a second failing review. Outcome `Revise` → **one** fix round with 5c's rules (never more agents than 5a spawned), on the reviewer's `story` findings only, then re-run Phase 6 and re-dispatch `giga-ux:ux-reviewer` on the failed steps only. The fix round never deletes, removes, rebuilds or refactors anything the story did not build. `existing` findings, rewordings of `existing` strings and `Remove` verdicts are recommendations: interactive, list them for the user; autonomous, record them in the story's plans file, and on the Idea Board only when they meet the § Entry threshold and nothing matches them (§ Check for a match first; a match is "covered by <key or id>" in the plans file), batched into one polish `fix` per section or page (`cut` for a `Remove`); an entry that qualifies but cannot be written goes under `## Ideas for the Idea Board` in the story's plan file. A second failing review, or Outcome `Stop for the owner`, stops the story: interactive, put the reviewer's decision to the user; autonomous, return `NEEDS_HUMAN` with it as a `decisions[]` entry. There is no third round.

A severity-1 `story` finding is fixed in place, without a re-review, and never blocks Ship. Every `story` finding, severity 1 to 4, is fixed in this story: never an Idea Board entry, never a follow-up story. One whose fix needs a genuinely new feature beyond the story's goal and acceptance stops the story for the owner with a recommendation (autonomous: `NEEDS_HUMAN`), and writes no entry. Severity-0 and `existing` findings are never built in this story; each gets a decision under § Discrepancies not fixed here. **New scope** is never built and never a story here: write each unmatched entry that meets the Idea Board's § Entry threshold to the board (`ideas.board`; policy in `ideas.policy`), or under `## Ideas for the Idea Board` in the story's plan file when it cannot be written; the rest are plans-file notes. List each in the test plan.

## Discrepancies not fixed here — decide each one, recommend a story only when it earns one

A finished story is rarely reread, so a finding left only in its own plan file is lost. Some findings are not fixed in this story: an `existing` UX finding, a review-gate note, an owner's remark, or a gap found while building outside this story's work. A `story` finding is never one: it is fixed here (Phase 6.5). **New scope is not a discrepancy:** a capability the story did not promise, whoever noticed it, is an Idea Board entry and only the owner turns it into a story. **Every one gets a decision; not every one gets a story.** A follow-up is a recommendation you make on the merits, never a quota the template fills. Decide each finding:

- **An existing open sibling whose scope it is.** Name the key; `/giga-workflow:epic-story-complete` Step 2 edits that sibling's plan file.
- **A recommended new story** — only when the finding is worth someone's time later: a user-facing defect, a real gap in a flow, a risk to a release, or something the owner asked for. Group related findings by area, about one story per area, as one story per area.
- **No follow-up**, with a one-line reason: cosmetic polish on a developer-only or internal surface, a test-fixture quirk with no product effect, behaviour that is already correct on inspection, or anything whose cost to track exceeds its value. The decision is recorded so it is a choice, not an omission.

The moment a batch of findings is in hand, present them in this block, apart from the rest of the report, so they cannot be skimmed past:

```
Discrepancies not fixed in <KEY>
| # | Finding | Found by | Decision |
| 1 | <finding> | UX review sev 1 · owner · 5b · build | <new story: summary> · <ABC-123> · No follow-up — <reason> |
```

Print the same block in the Phase 7 test plan. `/giga-workflow:epic-story-complete` Step 2 takes every **story** row as an evolution item, and its gate mints the new ones; a "No follow-up" row is not minted. The story's plan file may record the evidence, but each item there names its decision. A row with no decision is not done.

## Phase 7: Generate Test Plan

> **This phase always runs** — even when Phase 6 is skipped.

**Write the test plan yourself — do not spawn an agent for it.** By this point you already hold
every input: the ticket key, summary and acceptance criteria (Phase 1), the Stitch project and
screens (Phase 2.5), the routes touched (the approved plan), and the affected paths (Phase 6). An
agent would pull all of that into a second context purely to reformat it.

The serve command and port come from the **`ux.devServerSkill` skill's per-app table** (or the
`devServers` entries); the commands doc (`docs.commands`) deliberately does not carry them. Load that
skill only if the app's port is not already in this conversation.

Then write step-by-step navigation instructions to reach each affected route from the app's home
screen, and output the plan in this format:

```
Test Plan — <TICKET-KEY>

## Run the app
<serve command>
Open: localhost:<port>

## Navigate to the feature
1. <step — e.g. "Click the nav menu">
2. <step>
...

## Acceptance Criteria
- [ ] <AC item verbatim from ticket>
- [ ] <AC item verbatim from ticket>

## Skills repo (only when 5s ran)
Changed in <skillsRepo.path>-<key-lower> (branch <branch-name>, off <skillsRepo.branch>): <files>
Try it: <how the skills repo's build guide tries a change from a worktree — e.g. a fresh session loading its plugins from there>, in a separate session: ship from one that loads the live copy, because `/giga-workflow:epic-story-complete` removes this worktree

## Design Validation (Stitch)
Board: <project name>
- <screen name> — https://stitch.withgoogle.com/projects/<projectId>/screens/<screenId> — verify: <what to check against the implementation>

## UX Review
<verdict per task and persona from Phase 6.5 · findings fixed>

## Discrepancies not fixed here
<the § Discrepancies not fixed here block: every unfixed finding with its decision — existing key, recommended new story, or No follow-up with its reason>

## Ideas sent to the Idea Board
<each entry written this story — kind · title · source — or "none">


## Edge Cases
- <anything tricky or non-obvious>
```

Print the test plan output in the conversation.

## Error Handling

- If `$ARGUMENTS` is empty, ask the user for a ticket ID and stop.
- If the ticket is not found, inform the user and stop.
- If on an unexpected branch, confirm with the user before proceeding.
- If the Jira comment fails, report the error but continue with coding — the update is non-blocking.
- If the transition fails, report it but continue.
- Never force push. Never discard uncommitted changes.
- **Never commit.** Do not run `git add` or `git commit` at any point during this skill, in this repo or the skills-repo worktree. Leave all changes staged/unstaged for the user to review.
