---
name: epic-evolution-audit
description: "Audit sibling and downstream stories of an in-progress epic for staleness against the just-completed story, then apply targeted edits so the rest of the epic reflects what actually shipped. Run **directly before `/giga-workflow:epic-story-complete`** as the canonical propagation step for `epicEvolutionRules`."
---

Audit sibling and downstream stories of an in-progress epic for staleness against the just-completed story, then apply targeted edits so the rest of the epic reflects what actually shipped. Run **directly before `/giga-workflow:epic-story-complete`** as the canonical propagation step for `epicEvolutionRules`.

**Usage:**
- `/giga-workflow:epic-evolution-audit` — preferred. Infer the board + just-completed ticket key from the current conversation context.
- `/giga-workflow:epic-evolution-audit <board> <KEY>` — explicit override.
- `/giga-workflow:epic-evolution-audit --dry-run` — produce the findings list, do not apply edits. Useful when you want to review before letting the skill write the edits to the local plan files.
- `/giga-workflow:epic-evolution-audit --include=KEY1,KEY2` — restrict the audit to a specific subset of sibling keys (skip the auto-discovery of children).
- `/giga-workflow:epic-evolution-audit --skip=KEY1,KEY2` — exclude specific siblings from the audit.

**Available boards:** same as `/giga-workflow:epic-next` — defined by `epic.<board>.json` files in `.claude/giga/`.

> **Session model:** assumes one story per session, same as `/giga-workflow:epic-next` and `/giga-workflow:epic-story-complete`. The conversation that planned, implemented, and validated the story is the same conversation that runs this audit.

## Project config

Repo-specific values come from `.claude/giga/config.json` at the repository root, under `workflow`. Read it once at the start. A missing file or field takes the fallback below, never a guess.

| Field | Used for | When absent |
| --- | --- | --- |
| `plans.script` | `ensure` and `board` calls: plan-file paths, live child status | stop and say the repo has no `plans.script` in `.claude/giga/config.json` |
| `plans.guide` | the plans repo's rules for plan files and the hybrid read | skip the guide references |
| `plans.repo` | the plans repo whose `<board>/<KEY>.md` files are read and edited | stop and say the repo has no `plans.repo` in `.claude/giga/config.json` |
| `jira.cloudId` | the scoped comment / status / labels read | call `<jira.mcpPrefix>getAccessibleAtlassianResources` for it |
| `jira.mcpPrefix` | the prefix of the Jira MCP tool ids (`getJiraIssue`, `getAccessibleAtlassianResources`) | stop and say the repo has no `jira.mcpPrefix` in `.claude/giga/config.json` |
| `jira.createStatus` | the status a newly proposed story is created in | `To Do` |
| `git.branchPrefix` | the story-branch prefix the branch fallback parses | `feat/` |
| `docs.constraints` | the repo's constraints doc, home of the refactor-when-touched rule | cite the rule as stated here; no doc link |
| `docs.longFormDesign[]` | long-form design docs the audit leaves for manual edit | name no path |

---

## When to use

- Right after `/giga-workflow:epic-next` finishes the per-story `/giga-workflow:jira` handoff, **before** running `/giga-workflow:epic-story-complete`. The story has been implemented and the test/build gate passed; the next step is to make sure the rest of the epic reflects what just landed.
- After any in-session decision that surfaced an architectural shift, naming canonicalization, deferred AC, new gap, or open question that got settled.
- Whenever the parent epic's wave plan mentions stories whose descriptions might have been written before the just-completed work changed something.

## When NOT to use

- The just-completed work was a pure refactor / typo fix / docs-only change with zero architectural surface area.
- `config.epicEvolutionRules` is `null` for this board (the board opted out of epic evolution propagation; respect that).
- The session has already left for an unrelated task — re-establish context first or use the explicit-args form.

---

## The evolution rules — canonical here, addenda per board

### Why the audit exists

Its first job is to keep **per-story context small**. A story that absorbs adjacent work grows its
session until the context compacts, and a compaction mid-story reliably causes problems. A separate
child story does the same work with a **fresh context**, which is the cheaper and more reliable
trade nearly every time.

So the calculus is: *extra work in this story now* versus *a clean story later* — and the default is
the clean story later. **Minting new stories is the expected outcome of an audit, not a last
resort.** The audit's other two jobs follow from the same aim: update the siblings that will build
on what just landed, so they need not re-derive it, and propose new stories for further refinement.

### The four canonical rules (binding on every board)

These hold regardless of board. Do not copy them into a board config.

1. Capture architectural shifts in THIS epic. When a story surfaces a constraint, pivot, or gap, update the subsequent stories that depend on the decision; do not silently absorb the *decision* in the current story, and do not split the work into a separate epic. The *refactor* a decision implies for code the story touches is a different matter: that is done in the story, in place (`docs.constraints` § Refactor When Touched) — propagate the decision, absorb the refactor.
2. Update downstream discovery / research stories with upstream decisions before they are picked up — discovery work should not re-derive choices that have already been settled in earlier stories of this epic.
3. Add newly-discovered work as CHILD tickets of THIS epic — never as prose in the epic description — but only work that is genuinely new. A refactor to the standard within a story's reach is not new work and is never a ticket: the story does it in place, each file refactored by the implementation agent that owns it. A refactor is never filed as a ticket, under any circumstance (`docs.constraints` § Refactor When Touched). Create every one **`<jira.createStatus>`, never `Backlog`** — this is a single-developer automated workflow in which every story gets worked, so there is no deferred tier, and `/giga-workflow:epic-next`'s JQL only picks up that status. Use `Backlog` ONLY when the user explicitly asks to park something. In the SAME action that mints the key, add the one-line `KEY — summary` entry to the epic's wave plan and say so in the report — a ticket that exists outside the wave plan is drift, and nothing downstream reconciles it.
4. The epic description holds ONLY: the overall description, the wave order (one line per story, `KEY — summary`), a one-line-per-story `Shipped` ledger, and a lock index whose every entry is ONE line naming the story that owns it. NEVER put per-story implementation detail, acceptance criteria, locked-invariant prose, or follow-up specs in the epic; that detail lives in the child ticket whose scope it is (or the linked design docs). Scope must be readable from the child ticket alone. Keep the wave plan and the actual story set in sync as scope evolves — never let them drift, and never let an entry grow past one line.

   **A shipped story's outcome belongs in that story's own plan file**, under `## Outcome — shipped (PR #N)` (2–5 sentences) with a `### Pinned` subsection of one-liners (`/giga-workflow:epic-story-complete` Step 9 writes it). A lock's substance lives in the code or the rulebook — a spec that fails when it is broken, a one-sentence rule in the library's `AGENTS.md`, or a comment at the site — and the story file holds only the claim and where it is pinned. Neither the epic nor the story file narrates a lock.

   **The audit never edits the epic description.** Its findings go into the child tickets that need them. If the epic has lock prose or an entry longer than one line, the audit reports it (dimension 9) and leaves the epic alone. The epic gets two kinds of one-line write, both made by the step that ships or mints a story and neither proposed by the audit: a new story's wave-plan entry, and a shipped story's `Shipped` entry.

A ticket already `Backlog` stays `Backlog`. Updating a parked ticket's content is in scope; unparking
it is the user's call, not the audit's.

### What `config.epicEvolutionRules` means

| Value | Meaning |
|---|---|
| `null` | the board opted out entirely — the audit does not run |
| `[]` | the four canonical rules, nothing more (the common case) |
| `[...]` | the four canonical rules **plus** these board-specific addenda |

The field is **additive**. It once held a verbatim copy of the canonical four in every board, which
put the same 1.6KB in seven identical places — and the copies drifted: one board silently lost the
discovery rule and forked a weaker version of the epic-description rule. Board configs now
carry only what is genuinely board-specific, and inherit the rest.

---

## Step 0 — Resolve board + just-completed ticket key

Same resolution chain as `/giga-workflow:epic-story-complete`:

1. **Explicit args first.** If `<board>` and `KEY-123`-shaped token both appear in args, use them.
2. **Branch fallback.** Read `git rev-parse --abbrev-ref HEAD`. The current branch should be `<git.branchPrefix><key-lower>-<slug>`. Extract the key from the first two segments after `<git.branchPrefix>`. Match the key's prefix (e.g. `ABC`) against each `epic.*.json`'s `epicKey` prefix to resolve the board.
3. **Conversation context.** If branch parsing fails, look for the most recent `/giga-workflow:epic-next <board>` and the dominant in-progress ticket key.
4. **Last resort: ask** via `AskUserQuestion`.

Echo the resolved values prominently in Step 7's confirmation block so a wrong inference is visible before edits fire.

## Step 1 — Load board config

Read `.claude/giga/epic.<board>.json` and bind fields as `config.field`. Fields this skill consumes:

- `config.epicKey` — the parent epic to audit children of
- `config.epicEvolutionRules` — board-specific **addenda** to the four canonical rules; `null` means the board opted out
- `config.commitScope` — passed into the audit context (optional)

If `config.epicEvolutionRules` is `null`, print a one-line note that the board opted out, and stop.
An empty array is not an opt-out — it is the common case, meaning the canonical four and no addenda.
A missing field is treated as `[]`.

## Step 2 — Parse remaining flags

After stripping board + ticket key:

- `--dry-run` — print the audit findings and proposed edits but skip writing them to the plan files
- `--include=KEY1,KEY2,…` — restrict siblings to this list (still includes the parent epic for wave-plan check unless explicitly excluded)
- `--skip=KEY1,KEY2,…` — exclude these from the audit

## Step 3 — Load Atlassian MCP tools

Board navigation and ticket content (descriptions / wave plans) come from the plans repo (`plans.repo`), not the Atlassian MCP (which returns a ~5.5k-char fat envelope per issue and ignores field-narrowing — a 10-issue board query is ~55k chars). Canonical guide: the plans guide (`plans.guide`). Descriptions are **read from and written to** the local `<board>/<KEY>.md` files; comments (and the scoped status / labels read) stay on the MCP, and board navigation goes through the plans board-nav script.

Load via ToolSearch the two tools this skill still calls on the MCP:

- `select:<jira.mcpPrefix>getAccessibleAtlassianResources`
- `select:<jira.mcpPrefix>getJiraIssue`

`getJiraIssue` is used only for the scoped `comment` read (plus status / labels) — the §2 hybrid pattern in the plans guide; descriptions come from the local plan files. `getAccessibleAtlassianResources` supplies the `cloudId` that scoped read needs when `jira.cloudId` is absent.

(Do **not** load `searchJiraIssuesUsingJql` — board nav goes through the plans board-nav script. Do **not** load `editJiraIssue` — description edits are written to the local plan files, never to Jira. Do **not** load create/transition/comment tools — this skill only edits descriptions. Creating new sibling stories is a separate user action.)

## Step 4 — Get cloud ID (`jira.cloudId`) + read the just-completed ticket

The **description** comes from the local plan file (source of truth); **comments + status + labels** come from a scoped MCP read (the §2 hybrid pattern in the plans guide) — drop `expand="renderedFields"` and `description` from the field list:

```
python3 <plans.script> ensure <KEY>   → prints the local <prefix>/<KEY>.md path; Read it for the description
<jira.mcpPrefix>getAccessibleAtlassianResources()  → cloudId   (skip when jira.cloudId is set)
<jira.mcpPrefix>getJiraIssue(cloudId, KEY, fields=["summary","comment","status","labels"], responseContentFormat="markdown")
```

Save: `summary`, `description` (from the local plan file), full comment body list, status, labels. The audit subagent uses these to understand what the just-completed story actually settled.

## Step 5 — Discover candidate sibling + downstream stories

Default candidate set:

1. **All child stories of the parent epic** that aren't the just-completed one and aren't already `Done` — via the plans board-nav script (live status, ~200 B/issue):
   ```
   python3 <plans.script> board --jql 'parent = <config.epicKey> AND key != <KEY> AND status != Done'
   ```
   Returns JSON `[{key,status,category,type,priority,parent,summary}]`; use `key`, `summary`, `status` for the candidate list.
2. **Explicitly referenced sibling keys** from the just-completed ticket's description and comments. Regex-match `[A-Z]+-\d+` against both, dedupe against the board-nav results, and status-check any extras with a second board-nav query (`board --jql 'key in (KEY1, KEY2, …)'`) — keep only To Do / In Progress / In Review.
3. **The parent epic itself** (`config.epicKey`), read for dimensions 7 and 9. The audit reports on it and never proposes an edit to it.

Apply `--include` / `--skip` filters from Step 2.

If the candidate set is empty after filters, print a one-line summary ("No siblings to audit; epic is clean.") and stop.

## Step 6 — Spawn the audit subagent

This is the heart of the skill. Use the `Agent` tool (subagent_type: `general-purpose`) to run the audit. Spawn **one foreground agent**, do not parallelize — the audit needs to reason about cross-story interactions and a single agent has the full picture.

Give the subagent:

1. The just-completed ticket: full summary, full description, all comments, status, labels.
2. The candidate sibling list: keys + summaries (the agent reads each description from its local plan file itself).
3. The relevant code surface: file paths the just-completed story touched (extract from the conversation transcript or from `git diff --stat HEAD~1` if the commit hasn't happened yet — Step 1 of /giga-workflow:epic-story-complete may have already produced this; otherwise re-derive).
4. The binding rules the audit enforces: the four canonical rules from "The evolution rules" above, followed by `config.epicEvolutionRules` verbatim as board-specific addenda. Send the canonical four every time — a board config no longer restates them.
5. The cloud ID + the tools it uses to read each candidate: the plans script (`ensure <KEY>` via `plans.script` + Read) for descriptions, and `<jira.mcpPrefix>getJiraIssue` for comments.

Subagent prompt template:

---
```
You are the epic-evolution audit agent for a single just-completed story. Your job is to find every place
the rest of the epic has gone stale because of what this story actually settled, and propose surgical
description edits per sibling/downstream story.

## Just-completed story
Key: <KEY>
Summary: <Jira summary>
Status: <status>
Labels: <labels>

Description (markdown):
<full description>

Comments (most recent first):
<each comment body>

## Code surface (files this story modified)
<list of file paths from the diff>

## Epic evolution rules (binding)

### Why you are running
Keep per-story context small. A story that absorbs adjacent work grows until its context compacts,
and a compaction mid-story reliably causes problems; a separate child story does the same work with
a fresh context. Minting new stories is the expected outcome, not a last resort. A ticket already
`Backlog` stays `Backlog` — update its content, never its status.

### Canonical rules
<the four canonical rules, verbatim from "The evolution rules" in this skill>

### Board-specific addenda
<verbatim copy of config.epicEvolutionRules; omit this subheading when the array is empty>

## Candidate siblings to audit
<for each: KEY — summary — current status>
Also audit the parent epic itself: <config.epicKey>.

## Ticket access
- Description / wave plan (source of truth): run
  `python3 <plans.script> ensure <KEY>` to print the local `<prefix>/<KEY>.md` path, then Read it.
- Comments: scoped MCP read — Cloud ID: <cloudId>; for each candidate call
  <jira.mcpPrefix>getJiraIssue(cloudId, KEY, fields=["summary","comment"], responseContentFormat="markdown")
- Read the full description (local plan file) plus all comments (MCP) before judging staleness.

## Audit dimensions

For each candidate, check whether the description (or a comment marked as authoritative)
contains any of the following types of staleness against the just-completed story. Dimensions 1–6 are
judged **against the just-completed story, on child tickets only**. Dimensions 7 and 9 are **report-only**
checks on the parent epic.

**Never propose an edit to the parent epic.** Suppose the epic's prose is stale: a table, a decision, a
measured fact. Route the finding to the child ticket whose scope it is. Drop it when a story file or a repo
doc already records it. The parent epic's verdict is always `CLEAN` or `REPORT`, never `STALE`.

1. **Field-name drift** — names that were renamed by the just-completed story (e.g. orgId → entityId).
2. **Type / enum drift** — added or removed enum values, narrowed types, new shared model interfaces.
3. **API contract drift** — callables, function signatures, HTTP endpoints whose shape was settled differently
   from what the candidate description assumed.
4. **Locked-decision drift** — questions the candidate description still treats as open that the just-completed
   story actually settled.
5. **Deferred AC propagation** — acceptance criteria from the just-completed story that were deferred to a
   sibling. Verify the right sibling has the deferred AC in its scope (or recommend creating a new sibling
   story if no existing sibling fits).
6. **Status / dependency drift** — descriptions saying "depends on ABC-X" / "ABC-X must ship first" when
   ABC-X is the just-completed story. Update to "shipped <date>" or "ABC-X provides X, Y, Z".
7. **Wave-plan currency (parent epic only, report-only)**: list any open child missing from the wave plan,
   and any wave-plan entry whose story no longer exists. Don't propose the entries. A new story's one-line
   entry is written by the step that mints its key.
8. **Cross-cutting pivots — propagate, never record in the epic.** Suppose this story settled something that
   changes how several siblings are built. Each sibling it changes gets its own dimension-4 edit, and the epic
   gets nothing.
9. **Epic-size regression (parent epic only, report-only)**: a standing check, independent of what the
   just-completed story did. List every entry that has outgrown one line: a `Shipped` entry carrying a
   paragraph, a lock bullet that has grown reasoning, a wave-plan entry with implementation annotations, a
   section of story-level detail. Report the epic's byte count so growth is visible across runs. The owner
   decides what to cut, and the audit proposes no cut.

## Audit non-goals

- Do NOT propose summary changes. Summaries usually outlive descriptions and renaming them creates
  notification noise.
- Do NOT touch acceptance criteria status checkboxes — those track work, not facts.
- Do NOT rewrite an entire description. Surgical edits only — change the smallest contiguous block that
  resolves the staleness.
- Do NOT propose creating new sibling stories yourself — only flag where one would be needed and let the
  user decide. (The user runs that creation step, not this skill.)
- Do NOT propose any edit to the PARENT EPIC description. Not detail, not a correction to a stale table,
  not a lock pointer, not a cut. Every finding lands in the child ticket whose scope it is, or is reported
  (dimensions 7 and 9). Scope must be readable from the child ticket alone.

## Output format

Return a single structured block in this exact shape, one section per candidate, in the order received:

EVOLUTION_AUDIT_START

### ABC-XXX — <summary>
Status: <status>
Verdict: STALE | CLEAN | NEW_STORY_RECOMMENDED | REPORT (parent epic only)

<If STALE:>
Findings:
  - <dimension #N>: <one-line description of the drift>
  - <dimension #N>: <…>

Proposed edit:
  ```
  <the EXACT replacement text — only the contiguous block that changes;
   include 2-3 lines of context above and below so the user can place it visually>
  ```
  Replacing:
  ```
  <the EXACT existing block being replaced>
  ```

<For the PARENT EPIC only, always. Its verdict is CLEAN or REPORT, and it carries no Proposed edit:>
Epic size: <N> bytes (<M> lines)
Wave-plan gaps: <open children missing from the wave plan, or "none">
Over-long entries: <count, or "none">
  - <section> / <entry> — <one-line why it is over-long>  (report only)

<If NEW_STORY_RECOMMENDED:>
Recommended new story:
  Title: <proposed summary>
  Why: <which dimension surfaced this — usually deferred AC>
  Status on creation: <jira.createStatus> — always, never Backlog (every story in this workflow gets worked, and
    /giga-workflow:epic-next's JQL only picks up that status). It is a CHILD ticket: its scope/detail lives in the ticket,
    never copied into the parent epic description, and its one-line entry goes in the epic's wave plan.
  Suggested parent: <config.epicKey>
  Suggested label hint: <e.g. observability, schema, adoption>

<If CLEAN:>
(no findings)

EVOLUTION_AUDIT_END

## Rules of conduct

- Quote exactly. Never paraphrase the existing description text in the "Replacing" block. The skill's
  next step does a literal find-and-replace in the candidate's local plan file.
- If the existing block is too long to embed verbatim safely (over ~200 lines), break it into smaller
  contiguous edits. Each "Proposed edit" / "Replacing" pair must be a unique substring of the existing
  description so the find-and-replace is unambiguous.
- Confidence threshold: only emit findings you are ≥80% sure of. Borderline cases stay silent. The user
  will catch anything missed and re-run if needed.
- Cite the source of each finding (e.g. "from ABC-253 description § Schema: timestamp is ISO 8601, not
  EpochMillis").
```
---

Wait for the subagent to return. Parse the content between `EVOLUTION_AUDIT_START` and `EVOLUTION_AUDIT_END`.

## Step 7 — Confirmation gate

Print a digest of the audit findings followed by a confirmation prompt via `AskUserQuestion`:

```
/giga-workflow:epic-evolution-audit — findings

Just-completed:  <KEY> — <summary>   (status: <status>)
Parent epic:     <config.epicKey>
Audited:         <N> candidates
Verdicts:        <X> stale  •  <Y> clean  •  <Z> new-story-recommended
Mode:            apply | dry-run

Stale candidates:
  - ABC-A — <one-line drift summary>
  - ABC-B — …

New story recommendations:
  - <title> — <one-line why>
  - …

Clean (no edits proposed):
  - ABC-C, ABC-D, …

Apply all proposed edits to the stale candidates? (yes / pick / no)
  yes  → apply every proposed edit to its local plan file
  pick → ask, candidate by candidate, which to apply
  no   → stop, print the audit so the user can act manually
```

Three responses to handle:

- **yes** → proceed to Step 8 with the full edit set.
- **pick** → for each stale candidate, ask `AskUserQuestion` "apply edit to ABC-X? (yes/no/preview)". `preview` re-shows the proposed-vs-replacing blocks.
- **no** → print the full audit verbatim and stop. The user takes manual action.

If `--dry-run` was passed, skip the prompt entirely and behave as if the user picked **no** (print the audit, stop).

## Step 8 — Apply description edits

For each candidate the user approved, edit its **local plan file** directly (per §4 of the plans guide — descriptions are files, never `editJiraIssue`). Resolve the file path once, then apply the audit's edit as a literal find-and-replace of the "Replacing" block with the "Proposed edit" block:

```
plan=$(python3 <plans.script> ensure <KEY>)   → <prefix>/<KEY>.md
```

Use the `Edit` tool on `$plan` to swap the "Replacing" block for the "Proposed edit" block (or `Write` the full updated file if the block spans too much to match safely).

> **Atomicity note:** edit each candidate's file in its own `Edit` / `Write` call. Failures on one don't affect the others.
> If the find-and-replace match fails (the "Replacing" block isn't found verbatim in the local file), report it to the user
> and skip that candidate — never let the description go to the file partially mangled.
> The plan file is the only copy of the description; Jira keeps status. Re-pointing Jira's stub description at the file (the DESTRUCTIVE `python3 <plans.script> stub <KEY>` pass, §4) is a separate user action — this skill never writes descriptions to Jira.

## Step 9 — Final report

```
✓ Epic evolution audit complete

Audited:      <N> candidates of <config.epicKey>
Edits applied: <K> of <X> stale candidates
Skipped:      <Z> (user declined or find-and-replace mismatch)

Updates:
  - ABC-A — <one-line summary of edit>
  - ABC-B — …

New story recommendations (NOT auto-created — user action):
  - <title> — <why> — create in '<jira.createStatus>' status with parent <config.epicKey>
    Suggested: /giga-workflow:create-jira or manual creation in Jira

Next: run /giga-workflow:epic-story-complete to wrap up <KEY>.
```

If any new-story recommendations exist, suggest the user create them **before** running `/giga-workflow:epic-story-complete` so the parent epic's wave-plan edit (if applicable) can reference them by key. The audit re-run is idempotent — re-running after creation will pick up the new sibling and add it to the wave plan if needed.

---

## Composition with neighbouring skills

| Skill | Relationship |
|---|---|
| `/giga-workflow:epic-next` | Produces the just-completed story. This skill audits the rest of the epic for drift the story introduced. |
| `/giga-workflow:epic-story-complete` | Runs **after** this skill. Its built-in Step 5b (`Epic evolution check`) becomes a no-op once this skill has propagated the decisions explicitly. |
| `/giga-workflow:epic-story-ship` | Runs this skill as its composition step 0 (Steps 0 → 6 only): the findings print in its single `Story ship` gate instead of Step 7's prompt, approved edits apply after that gate in its one plans-repo commit, and new-story recommendations are minted by `/giga-workflow:epic-story-complete` Step 10(a). `--no-audit` skips it. |
| `/giga-workflow:epic-config` | View / update the `epicEvolutionRules` field that drives this skill's audit dimensions. |
| `/giga-workflow:epic-plan` | Uses the same wave-plan structure this skill keeps in sync. |

---

## Error handling

- **Missing board / KEY** → resolve via Step 0 chain; ask if all four paths fail.
- **`config.epicEvolutionRules` is null** → stop with a one-line note. The board opted out.
- **Empty candidate set after filters** → stop, no audit needed.
- **Subagent returns malformed output** (no `EVOLUTION_AUDIT_START` / `EVOLUTION_AUDIT_END` markers, or unparseable sections) → re-prompt the agent once with stricter formatting instructions, then surface the raw response and stop.
- **find-and-replace mismatch** during Step 8 → report the candidate, skip it, continue with the rest. Do not partial-write.
- **Atlassian API error on a single candidate** → report it, continue with the rest.
- **`--dry-run`** → skip Step 7's prompt and Step 8; print the audit findings and stop.

## Notes

- This skill makes **description edits only**. It does not transition tickets, create new stories, or post status comments. Those are deliberate user actions — the skill's job is to surface what needs them.
- The audit is conservative: it errs on the side of leaving descriptions alone when the staleness is borderline. The user can always re-run with a tighter `--include=` set if a sibling slipped through.
- Re-running after creating new sibling stories is idempotent and safe — the audit picks up new children and updates the wave plan accordingly.
- The skill does NOT auto-update the architecture / decision-log / mock-inventory documents under the `docs.longFormDesign` paths — those edits stay manual since they often need human judgement about what to add. (A future variant could surface document drift, but it's intentionally out of scope here.)
