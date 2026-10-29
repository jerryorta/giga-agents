---
name: epic-plan
description: "Plan or re-plan an epic: fetch its child stories (or cut them when it has none), challenge the epic with a red team and a domain expert whose ideas the owner adopts, parks or declines on the Idea Board, analyse route depth and dependencies, organise into conflict-minimising waves (root routes first, deeper routes later), create the confirmed stories and move them and the epic to the ticket-ready status (`jira.createStatus`; Jira may create them in Backlog, where /giga-workflow:epic-next cannot see them), write the wave plan to the epic's local plan file (the plans repo), and create/update the `epic.<board>.json` config for `/giga-workflow:epic-next`."
---

Plan or re-plan an epic: fetch its child stories (or cut them when it has none), analyse route depth and dependencies, organise into conflict-minimising waves (root routes first, deeper routes later), create the confirmed stories and move them and the epic to the ticket-ready status (`jira.createStatus`; Jira may create them in Backlog, where /giga-workflow:epic-next cannot see them), write the wave plan to the epic's local plan file (the plans repo), and create/update the `epic.<board>.json` config for `/giga-workflow:epic-next`.

**Usage:** `/giga-workflow:epic-plan <EPIC-KEY>`

Examples: `/giga-workflow:epic-plan ABC-123`, `/giga-workflow:epic-plan XYZ-45`

---

## Project config

Repo-specific values come from `.claude/giga/config.json` at the repository root, under `workflow` (plus the top-level `ideas` and `ux` keys that every plugin shares). Read it once at the start. A missing file or field takes the fallback below, never a guess.

| Field | Used for | When absent |
| --- | --- | --- |
| `plans.repo` | the plans repo that holds each ticket's content file `<plans.repo>/<board>/<KEY>.md` | stop and say the repo has no `plans.repo` in `.claude/giga/config.json` |
| `plans.script` | board navigation (`board`), ticket content (`ensure`) and the Jira stub pass (`stub`) | stop and say the repo has no `plans.script` in `.claude/giga/config.json` |
| `plans.guide` | the plans guide (born-split stories, the stub rule) | follow Step 10.5 and Step 11 as written |
| `jira.credentialsFile` | the credentials the plans script reads with | the script's own default |
| `jira.cloudId` | the `cloudId` for the Jira MCP writes in Step 10.5 | one `getAccessibleAtlassianResources()` call supplies it |
| `jira.mcpPrefix` | the Jira MCP tool-id prefix, for the Step 3 `ToolSearch` and the Step 10.5 calls | skip Step 10.5's creates and moves and list them in Step 13 as not done |
| `jira.createStatus` | the status every created story, the epic and kept Backlog stories are in, and the status the `/giga-workflow:epic-next` JQL reads | `To Do` |
| `git.mainBranch` | the base branch an epic PR lands on | `main` |
| `git.branchPrefix` | the prefix of the epic integration branch | `feat/` |
| `boardTemplate` | the path, from the repo root, of a starter board JSON that Step 2 seeds a new board from when no `epic.*.json` matches | a new board starts from the Step 12 skeleton |
| `ux.brandVoice.guides[]` (top level `ux`) | the voice guide for the app the red team and domain expert read | pass "none yet" |
| `planning.dependencySignals[]` | the backend and infrastructure phrases that count as dependency-driven signals in Step 6.5a | only the "depends on / blocked by / prerequisite" links and foundation summaries count |
| `planning.backendGlobs[]` | the backend paths that count as dependency-driven signals (Step 6.5a) and mark the backend layer (Step 7.5) | judge the backend layer from the story's description |
| `planning.frontendGlobs[]` | the frontend paths that mark the store and UI layers (Step 7.5) | judge the frontend layer from the story's description |
| `ideas.board` (top level) | the Idea Board Step 6.7 reads and writes | skip Step 6.7 and the challenge lines of Steps 9 and 13, and say so in the Step 13 summary |
| `ideas.policy` (top level) | the rules for Step 6.7: its match check and entry threshold | apply the stopping test as Step 6.7 states it |

## Step 1 — Enter plan mode

Call `EnterPlanMode` immediately.

## Step 2 — Parse argument and resolve board name

Read `$ARGUMENTS`. Extract the epic key (e.g., `ABC-123`). Parse the **key prefix** — the uppercase letters before the first `-` (e.g., `ABC`).

**Optional directives in the args:**
- **`using the key <board>`** (or `--board <board>`) — override the auto-resolved board name with `<board>` (e.g. `using the key payments` → board `payments`). Use this to give an epic its own board instead of overwriting an existing same-prefix board's config.
- **`epic-branch`** (or `--epic-branch` / `epic`; `worktree` accepted as a back-compat alias) — set `mergeMode = "epic-branch"` for this board: every story is committed directly onto a shared epic branch (no per-story PRs); the epic lands on `<git.mainBranch>` via one PR at the end.
- **`direct`** (or `--direct`) — set `mergeMode = "direct"` for this board: every story gets its own branch, and `/giga-workflow:epic-story-complete` fast-forwards `<git.mainBranch>` to it and pushes (no PRs), so stories land on `<git.mainBranch>` one by one.

Neither directive → `mergeMode` resolves in Step 10 (base config, then the board template, else `"pr"`, the per-story-PR "git flow"). Save `mergeModeArg` = `"epic-branch" | "direct" | null`.

**Resolve board name automatically** (unless `using the key <board>` overrode it):

Read all files matching `.claude/giga/epic.*.json`. For each file, read the `epicKey` field and extract its prefix. Find the file whose prefix matches the argument's prefix.

- **Match found** → the board name is the `*` portion of the filename (e.g., `epic.abc.json` → `abc`). Load the entire matching config as the **base config** to carry forward unchanged fields (e.g., `app`, `libraries`, `conventions`, `designReferences`).
- **No match** → board name = lowercase of the prefix (e.g., `XYZ` → `xyz`). A new config will be created from scratch; prompt the user after Step 9 to fill in the app/library paths. When `boardTemplate` names a file that exists, seed the new config from it instead: load that file as the **base config**, drop every key that starts with `_`, and hold their text as `templateNotes` for the Step 9 gate (`baseFromTemplate = true`). Step 12 still writes `name`, `epicKey`, `jql`, `completionMessage` and the other epic-specific fields from this epic.

Save: `epicKey`, `boardName`, `baseConfig` (may be null), `baseFromTemplate`, `templateNotes`, `mergeModeArg`.

## Step 3 — Plans-repo access (board nav + content — NOT the MCP)

Board navigation and ticket content come from the **plans repo** (`plans.repo`), not the Atlassian MCP (which returns a ~5.5k-char fat envelope per issue and ignores field-narrowing — a query for an epic's children is tens of KB). Canonical guide: the plans guide (`plans.guide`). Two commands:

- **Board nav** (child list + live status): `python3 <plans.script> board --jql '<jql>'` → JSON `[{key,status,category,type,priority,parent,summary}]` (live status, ~200 B/issue).
- **Ticket content** (epic/story description): `python3 <plans.script> ensure <KEY>` prints the local `<prefix>/<KEY>.md` path (migrating on-miss); then `Read` it.

Reads need no MCP — the script authenticates via `jira.credentialsFile`. **Writes to Jira do:** minting a story and moving a status (Step 10.5) go through the Atlassian MCP. Once Step 9 is confirmed, load them in ONE `ToolSearch` — `select:<jira.mcpPrefix>getAccessibleAtlassianResources,<jira.mcpPrefix>createJiraIssue,<jira.mcpPrefix>getTransitionsForJiraIssue,<jira.mcpPrefix>transitionJiraIssue` — whenever Step 10.5 has anything to do, which is nearly every first plan of an epic.

## Step 4 — Cloud ID

The plans script handles auth + `cloudId` for reads. Step 10.5's MCP writes take the `cloudId` from `jira.cloudId`, or from one `getAccessibleAtlassianResources()` call when the field is absent. Proceed to Step 4.5.

## Step 4.5 — Verify the existing baseConfig isn't in flight (skipped if `baseConfig` is null)

Before this skill overwrites `epic.<boardName>.json`, check whether the **previously-configured** epic in that file is still active. Overwriting an in-flight epic's config silently strips the `/giga-workflow:epic-next <boardName>` and `/giga-workflow:epic-story-complete <boardName>` shortcuts that ongoing work depends on.

**Skip this step entirely if:**
- `baseConfig` is null (new board), OR
- `baseFromTemplate` (a new board seeded from the board template), OR
- `baseConfig.epicKey === epicKey` (re-planning the same epic, not switching to a new one)

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

## Step 5 — Fetch the epic

```
epicPath=$(python3 <plans.script> ensure <epicKey>)
```

`Read $epicPath` — the epic's local plan file (`<prefix>/<epicKey>.md`, migrating on-miss). Its front matter carries the `summary`; its body is the description Step 6.5b inspects. Save the epic `summary` (used to derive the branch name).

## Step 6 — Fetch all child stories

```
python3 <plans.script> board --jql 'parent = <epicKey> ORDER BY created ASC'
```

Returns JSON `[{key,status,category,type,priority,parent,summary}]` for every child — the list plus **live** status, but **not** descriptions. For each story, note its `key`, `summary`, and `status`. The per-story **description** that Steps 6.5–7 analyse comes from the child's local plan file: for each child, `python3 <plans.script> ensure <KEY>` then `Read` it (migrating on-miss).

> The `board` command paginates internally (100/page until exhausted), so it returns every matching child in one call — no manual `startAt` handling.

Run the same query for the epic itself (`board --jql 'key = <epicKey>'`, in the same call) and keep its live `status` — Step 9 shows it and Step 10.5 moves it.

**No children yet?** A new epic often arrives with only a description and a spec. Then this skill **cuts** the stories as well as ordering them: derive the story list from the epic's description and the spec it points at (backend first, per Step 7.5), run Steps 7–8 on that proposed list, and present it at Step 9 under "Stories to create". Nothing is created before the user confirms; Step 10.5 mints them.

## Step 6.5 — Classify the epic + detect existing description content

**Why this step exists.** The route-depth heuristic in Step 7 is right for Angular UI epics (page builds, feature shells, route trees) but **wrong for backend / foundation / dependency-driven epics** (data pipelines, schema work, infrastructure). For the latter, route depth produces nonsense waves because most stories don't create routes at all. This step picks the right analysis path before the heuristic runs.

**Why this also exists.** Step 11 writes back to the epic description. If the description already has substantial curated content (Reference docs, Locked decisions, Constraints, hand-built Wave Plan, etc.), a blind rewrite can clobber it. This step records what's there so Step 9 can ask before overwriting.

### 6.5a — Classify the epic

Compute classification signals:

**Route-driven signals** (each child story checked):
- Description references an Angular route pattern (`/route/:param`, `/dashboard`, `/settings/profile`)
- Description references files under `config.libraries.ui` (component / page paths)
- Summary names a page or screen ("Contact Detail Page", "Settings Page", "Mobile Home")

**Dependency-driven signals** (each child story checked):
- Description contains "depends on ABC-XXX" / "blocked by" / "blocks ABC-XXX" / "prerequisite"
- Description references backend infrastructure: any of `planning.dependencySignals`
- Description references files under any of `planning.backendGlobs`
- Summary names a foundation / pipeline / schema / writer / endpoint

**Decide:**
- Route signals dominate (≥ 70% of stories): `epicType = "route-driven"` (use Step 7 / 8 default analysis)
- Dependency signals dominate (≥ 70% of stories): `epicType = "dependency-driven"` (use Step 7b / 8b)
- Mixed (both signal sets significant, neither dominates): `epicType = "mixed"` (defer to user in Step 9)
- Unclassifiable (few signals either way): `epicType = "unknown"` (defer to user in Step 9)

### 6.5b — Detect existing description content

Read the epic description fetched in Step 5. Identify:

- **Section headings** present (e.g., `## Goal`, `## Scope`, `## Constraints`, `## Reference documents`, `## Wave Plan`, `## Acceptance Criteria`).
- **`## Wave Plan` exists?** boolean.
- **Substantial non-wave-plan content?** boolean — true if any sections beyond a one-line title exist outside the wave-plan section.
- **Linked decision / architecture docs** referenced inline in the description.

Save: `descriptionStructure`, `descriptionHasWavePlan`, `descriptionHasRichContent`, `descriptionLinkedDocs`.

### 6.5c — Provide diagnostic to user (no decision yet — Step 9 confirms)

Hold all the above for Step 9's confirmation block. Don't print anything yet; the user sees one consolidated picture in Step 9.

## Step 6.7 — Challenge: red team, domain expert, the Idea Board

An epic's shape is cheapest to change before its stories are cut and waved, so this is where it gets its cuts and any adds the evidence forces. "No cuts, no adds — the epic covers its goal" is a valid result. Every idea here is a recommendation: no story is dropped, parked or rewritten, and nothing in the app is removed, unless the owner adopts it at Step 9. Rules: the ideas policy (`ideas.policy`).

Skip this step when `ideas.board` is absent: no agents are spawned, Step 9 has no Challenge block or question 6, and the Step 13 summary says Step 6.7 was skipped because the repo has no Idea Board.

1. **Read what is already decided.** Load `ArtifactData` (`ToolSearch` `select:ArtifactData`) and `query` the Idea Board's (`ideas.board`) `ideas` collection where `board == <boardName>`. Hold three lists: `adopted` with no `storyKey` (candidate stories when they serve this epic's goal), `parked` (re-weighed only with new evidence), and `declined` (never re-proposed; their titles and reasons go to the agents below). Keep the whole result, `proposed` included, and the board's open tickets (`python3 <plans.script> board --jql 'project = <KEY> AND statusCategory != Done'`) for step 4's match check.
2. **Read the last epic review.** When `baseConfig` points at a different epic that is Done (Step 4.5), read that epic's plan file for its `## Epic review` section. When there is none, Step 9 says so and recommends `/giga-workflow:epic-review <baseConfig.epicKey>` first. The owner may skip it.
3. **Spawn two read-only agents in one message** (`general-purpose`, `model: sonnet`). Give each the epic plan file path, the child list with summaries, the app and its dev-server port, the brand's voice guide path (from `ux.brandVoice.guides[]`, or "none yet"), the declined titles and reasons, the last epic review, and the idea rules. Story-order and gating notes come back for the plan file, never as ideas.
   - **Red team** — argue against the epic. Which stories have no user job behind them, duplicate what the app already does, or make its navigation or its model of the work worse? What does the epic's own goal need that no story covers? Read usage for the area (sources in the ideas policy) and cite numbers with their source and date range. Return the cuts, fixes or adds that have observed evidence, most severe first, or "no cuts, no adds — the epic covers its goal".
   - **Domain expert** — be the app's real user (the voice guide's audience; with none, the users the app's onboarding and marketing describe). Walk the jobs this epic serves the way that person actually does the work, and say where the stories miss it. Act out the jobs in the running app or its source; do not role-play opinions. Return the adds or cuts that have observed evidence, most severe first, each with its job, or none.
   - **Section review** (optional, when a story reworks a section or page that is already live): one `giga-ux:ux-reviewer` per such section, in `giga-ux:ux-design` § Section review mode. Its one batched list is a single `fix` candidate for step 4.
4. **Merge and rank.** Rank the entries across all agents by severity, most severe first; the stopping test is the only gate and zero is a valid result. When more than a handful survive, say so in the report with a one-line reason. Drop any that fails the ideas policy's § Entry threshold, and any that repeats a declined idea without new evidence answering its decline reason. Drop any that an open ticket or an Idea Board entry of any status already names (the ideas policy's § Check for a match first; also grep `<plans.repo>/<board>/*.md`): record "covered by <key or id>" in the report and the epic's plan file, with any evidence the match lacks, and never edit the match. Story-order and gating notes go to the epic's plan file (Step 11), never the board.
5. **Write each survivor to the Idea Board** (`set`, `status: "proposed"`, `source: "epic-plan"`, this epic's key) and hold them as `challengeIdeas` for Step 9.

---

## Step 7 — Analyse stories (branch on `epicType`)

### Route-driven path (default for UI epics)

For **each story**, read its description and extract:

1. **Route path(s)** — the Angular route segment(s) this story creates or significantly modifies. Look for patterns like `/crm/:id`, `/dashboard`, `/settings/profile`. If none are explicit, infer from the summary (e.g., "Contact Detail Page" → `/crm/:contactId`).

2. **Route depth** — count the segments: `/dashboard` = depth 1, `/crm/:id` = depth 2, `/crm/:id/timeline` = depth 3. Assign `depth = 0` for stories with no new route (shared components, services, navigation shells).

3. **Parent story dependency** — if this story creates a child route (depth N), it depends on the story that creates the parent route (depth N-1). Identify which story in the set creates the parent, if any.

4. **Sibling conflict** — two stories conflict if they modify the **same existing component file** (not just the same parent route). Flag these as needing sequential execution within the same wave.

### 7b — Dependency-driven path (for backend / foundation epics)

For **each story**, read its description and extract:

1. **Explicit dependencies** — match patterns like `depends on ABC-XXX`, `blocked by ABC-XXX`, `prerequisite: ABC-XXX`. Build a directed edge from the dependency to this story.
2. **Implicit dependencies** — if a story description names a piece of infrastructure another story is building (e.g., "uses the `events` table from ABC-253"), add an edge from the building story to this consumer.
3. **Sibling conflict** — same as route-driven (two stories touching the same file = sequential within a wave).

Then build a **directed acyclic graph** (DAG) of stories. Topological depth (longest path from any root) becomes the wave assignment:
- Stories with no incoming edges → Wave 1
- Stories whose dependencies are all in Wave N → Wave N+1
- Cycles flagged as errors (must resolve before continuing).

### 7c — Mixed / unknown path

If `epicType` is `"mixed"` or `"unknown"`, present both candidate wave plans in Step 9 and ask the user which to use. Do not pick silently.

## Step 7.5 — Split multi-layer stories, backend first

A story whose scope spans the backend (functions, rules, indexes, seed tooling under
`planning.backendGlobs`) AND the frontend (`planning.frontendGlobs`, the app) is split
before it is waved.

**The backend story** carries the functions, rules, indexes, seed, and the models / API contract the
frontend codes against. It is **always first**: every frontend story from the split depends on it (an
edge in the 7b DAG; ahead of them in a sequential wave on the route-driven path).

**The frontend story or stories** follow — one per layer (store vs UI) when each stands alone — and,
once the backend story has merged, run in parallel (separate clones / sessions).

Why: one multi-layer story runs its layers serially in one session whose context only grows; split, each
layer is its own session and the frontend layers run in parallel.

Skip the split only when the frontend change is a thin consumer of the backend change (a handful of
files) — say so in Step 9.

Proposed splits are presented in Step 9 and minted by Step 10.5 only after the user confirms, before Step
11 writes the wave plan; the original ticket becomes the backend story.

## Step 8 — Organise into waves

Apply these rules to produce a **wave plan**:

**Wave assignment:**
- `depth = 0` (shells, shared components, navigation) → Wave 1
- `depth = 1` (root-level pages) → Wave 1
- `depth = 2` (first child routes) → Wave 2, unless its parent is in an earlier wave already
- `depth = N` → Wave = max(wave of its parent dependency) + 1
- A backend story from a Step 7.5 split always precedes the frontend stories that consume it — never in the same parallel wave

**Within a wave:**
- Stories with no shared file conflicts → `parallel`
- Stories that touch the same component file → `sequential` (list them in dependency order)

**Ordering within a wave** (for the epic description):
- Parallel stories can appear in any order within the wave section
- Sequential stories must appear in the order they must execute

**Completeness check:**
- Every story must appear in exactly one wave. A story the user keeps parked at Step 9 goes in the wave it would run in, marked `_(Backlog — parked)_`. `/giga-workflow:epic-next` skips it until someone moves it to `<jira.createStatus>`, and the wave plan still matches the real story set.
- If a story's parent route is not covered by any other story in the batch (it already exists in the app), treat it as depth 1

## Step 9 — Present analysis + wave plan, ask the user, exit plan mode

Present a single consolidated picture so the user can catch a wrong inference (epic type, description-rewrite intent, dependency edges) BEFORE any writes happen:

```
Epic: <epicKey> — <summary>   (status: <epic status>)
Board: <boardName>
Total stories: <N> (<done> Done, <todo> <jira.createStatus>, <inprogress> In Progress, <backlog> Backlog)

Stories to create (none yet, or Step 7.5 splits):
  new: <summary> · <Story|Task> · <wave>
  (or: none)

Status moves (Step 10.5):
  <epicKey> epic: Backlog → <jira.createStatus>        ← only if the epic is in Backlog
  Every story created above → <jira.createStatus>       ← always; created straight into it, or moved there if Jira put it in Backlog
  Already in Backlog: <KEY-A>, <KEY-B> → <jira.createStatus>?   ← ask; one may be parked on purpose
  (or: none)

Epic type detected: <route-driven | dependency-driven | mixed | unknown>
  Route signals:      <X> stories (route patterns / page summaries / UI lib paths)
  Dependency signals: <Y> stories (depends-on links / backend / pipeline / schema)

Existing description content (from <epicKey>):
  Sections present:   <list of headings, e.g. Goal, Scope, Reference documents, Wave Plan, ...>
  Existing Wave Plan: <yes — N waves, M stories> | <no>
  Rich non-wave content: <yes — preserve required> | <no — safe to write fresh>
  Linked docs:        <list of doc paths referenced inline, if any>

Proposed Wave Plan (analysis mode: <route-depth | dependency-graph | both — pick one>):

Wave 1 (parallel) — <label>
  KEY-A  ...
  KEY-B  ...

Wave 2 ...

Proposed splits (Step 7.5):
  <KEY-X> → <KEY-X> (backend) · new: <summary> (store) · new: <summary> (ui)
  (or: none)

Challenge (Step 6.7) — Idea Board: <ideas.board>   (omit the block when ideas.board is absent)
  Adopted earlier, not yet a story: <summary> ← <entry ids> → new story in wave <n>   (or: none)
  New:  add · <title> — <evidence>          (ranked by severity; or: none — the epic covers its goal)
        cut · <KEY or title> — <evidence>
        fix · <title> — <evidence>
  Declined before, not re-proposed: <n>
  Last epic review: <present | missing — recommend /giga-workflow:epic-review <KEY> first | n/a>

Config file: .claude/giga/epic.<boardName>.json (will be <created | overwritten>; always created when seeded from <boardTemplate>)
<If baseFromTemplate:>
Seeded from <boardTemplate> — adjust the workspace shape below if this epic differs:
  <each templateNotes entry, its key and text>
</If>
Merge mode: <pr | epic-branch | direct>  <if epic-branch: → epic branch <epicBranch>>
(PR mode: per-story <git.branchPrefix> branches derived at /giga-workflow:epic-next time. Epic-branch mode: every story commits onto <epicBranch>; one epic PR at the end. Direct mode: per-story <git.branchPrefix> branches, each fast-forwarded into <git.mainBranch> and pushed by /giga-workflow:epic-story-complete; no PRs.)

Description rewrite policy options:
  [A] Replace ONLY the ## Wave Plan section; preserve all other sections verbatim
  [B] Append a new ## Wave Plan section at the end (existing sections including any old wave plan stay)
  [C] Skip description write entirely (config-only update)
  [D] Full rewrite (DESTRUCTIVE — only choose if you want a fresh description)

Default recommendation: <A if Wave Plan exists | B if no Wave Plan but rich content | C if user is hesitant | D never default>
```

Then call `ExitPlanMode`. Ask the user these questions explicitly (use AskUserQuestion if loaded, otherwise plain prompts):

1. **Epic type confirmation** — "Detected `<epicType>`. Use this analysis, or override (`route-driven` / `dependency-driven` / `mixed`)?"
2. **Wave plan acceptance** — "Accept the proposed wave plan above, or amend?"
3. **Description-rewrite policy** — "Pick A / B / C / D from the policy options above (default: `<recommendation>`)."
4. **Split confirmation** — "Accept the proposed splits (backend first), amend, or skip?" — and, for an epic with no children yet, "Create these stories?"
5. **Existing Backlog stories** (only when the epic already has children in Backlog) — "Move <KEYs> to <jira.createStatus>, or leave any parked?" The default is to move them: in this workflow every story gets worked, and `/giga-workflow:epic-next` cannot see a Backlog story. The question exists because a story the user parked on purpose stays parked (evolution rule 3).
6. **Challenge ideas** (only when Step 6.7 has any) — "Adopt, park or decline each one, here or on the Idea Board." Record each decision on the board (`ideas.board`; `update` `status`, `decision`, `decidedAt`); a decline needs a one-line reason. An adopted `add` joins "Stories to create"; an adopted `cut` removes or parks the story it names; an adopted `fix` becomes a story or an edit to the sibling whose scope it is. There is no one-to-one card-to-story ratio: group adopted entries into stories that make sense to build together. Cosmetic fixes on one page go in one story; entries that share a page, component or flow may share one too, at your judgement. Each story lists its source entry ids. Nothing the owner did not adopt changes the plan, and no idea is minted as a story any other way.
7. **Seeded board** (only when `baseFromTemplate`) — "Keep the seeded `app`, `libraries`, `routingFiles`, `buildCommand`, `commitScope` and `conventions`, or adjust them to the shape the template notes describe?"

Proceed to Step 10 ONLY when all of them are answered. If the user amends the wave plan or the splits, re-present and re-confirm before writing.

**Hard guardrails:**
- If `descriptionHasRichContent` is true and the user picked `D` (full rewrite), re-confirm with a destructive warning: "This will overwrite the existing curated description. Are you absolutely sure? (y/N)".
- If the user picked `C` (config-only), Step 11 is skipped.
- If `epicType` was `"unknown"` and the user didn't pick an override, stop with a diagnostic — don't guess.

---

## Step 10 — Derive config values

> **Merge mode + epic branch.** Set `mergeMode`: the explicit `epic-branch` or `direct` directive from Step 2 (`mergeModeArg`) wins; else carry forward `baseConfig.mergeMode`; else the board template's `mergeMode` (`boardTemplate`); else default `"pr"`. When `mergeMode === "epic-branch"`, also derive `epicBranch` — use the current git branch if it already looks like this epic's integration branch (`git rev-parse --abbrev-ref HEAD`, e.g. `<git.branchPrefix>abc-123-short-slug`), else `<git.branchPrefix><epicKey-lower>-<slug-from-epic-summary>` (same slugging as `/giga-workflow:epic-next`). In PR and direct modes, per-story `<git.branchPrefix>` branches are still derived at `/giga-workflow:epic-next` time — no shared branch needed, and `epicBranch` is `null`.

**JQL:**
```
parent = <epicKey> AND status = "<jira.createStatus>"
```

**Story ordering:** `"epic-description"` (we are writing the order to the description)

**Group label:** `"Wave"`

**Completion message:** `"All <epicKey> stories are complete!"`

**Hybrid mode:** carry forward from `baseConfig.hybridMode` if it exists (a legacy `true` is written as `"conditional"`); otherwise `false`. `false` = `/giga-workflow:epic-loop` ships every story unattended. Use `"conditional"` when stories' Phase 6/7 verification requires `/giga-workflow:epic-cross-actor-test`, which needs two browser profiles and a human: `/giga-workflow:epic-loop` then pauses on those stories and ships the rest unattended. A story whose need is already known can carry `crossActor: true` (or a scenario string) or `crossActor: false` in its front matter, and that overrides the loop's triage. A story that follows an established pattern (no new design, shared primitive or cross-library refactor) can carry an optional `model: sonnet` (or `opus` / `haiku`), which `/giga-workflow:epic-loop` uses for that story's agent. Surface a one-line note in the Step 13 summary so the user knows to hand-edit the field if the epic actually needs hybrid mode.

**App/library/convention/designReferences fields:** carry forward from `baseConfig` unchanged, as is every key it holds that the Step 12 skeleton does not list (e.g. `crossActor`, `domainMemoryIndex`). If `baseConfig` is null (new board), set placeholder values and note them to the user after writing.

## Step 10.5 — Create the confirmed stories and move statuses to `<jira.createStatus>`

**Why this step exists.** `/giga-workflow:epic-next` picks only stories in `<jira.createStatus>`, but Jira can create a new issue in **Backlog**. A story minted without a move to `<jira.createStatus>` is invisible to `/giga-workflow:epic-next`. With this config's `status = "<jira.createStatus>"` JQL, `/giga-workflow:epic-next` then reports the epic complete before any work has started. An epic left in Backlog reads as parked on the board while it is the one being worked.

Skip the step when Step 9 confirmed nothing to create and nothing to move. Otherwise load the MCP tools (Step 3) and fetch `cloudId` once, then:

1. **Create each confirmed story** (no-children cut, or a Step 7.5 split), born-split per the plans guide (`plans.guide`) §5:
   1. `createJiraIssue` with `parent=<epicKey>`, the type and the summary. Read the `key`.
   2. `Write` its content to `<plans.repo>/<board>/<KEY>.md`: front matter `jira/project/board/type/epic/summary`, plus the scope and acceptance, and its source Idea Board entry ids when it has any.
   3. Move it to **`<jira.createStatus>`** (step 2 below) when it is not already there.
   4. Run `python3 <plans.script> stub <KEY>`.

   5. When the story came from adopted Idea Board entries, `update` each source entry's `storyKey`.

   ⚡ Batch the `createJiraIssue` calls in one message. Batch the `stub` calls into one `Bash` call. The stub and the move are independent, so either order is fine. Do both for every story before Step 11.
2. **Move to `<jira.createStatus>`.** This covers every story just created, the epic if it is in Backlog, and the pre-existing Backlog stories the user did not keep parked. For each one, call `getTransitionsForJiraIssue`, pick the transition whose **name** is `<jira.createStatus>`, and call `transitionJiraIssue`. Never reuse a transition id from another board: the same id can name a different transition on each board. ⚡ Batch the reads in one message and the transitions in the next.
3. **Verify** with one `board --jql 'key = <epicKey> OR parent = <epicKey>'` call. Nothing that was meant to move should still read Backlog. Report any that do in Step 13 as a line, not silently.

A failed create or move does not stop the plan: the wave plan and config still get written. Each failure is a line in the Step 13 summary.

## Step 11 — Write the wave plan to the epic's local plan file (skipped if user picked policy C)

The wave plan is written to the epic's local plan file, not Jira — `$epicPath` from Step 5 (`<prefix>/<epicKey>.md`; re-resolve with `python3 <plans.script> ensure <epicKey>` if needed). **Never** `editJiraIssue` — Jira's description is a stub, not the content (the plans guide, `plans.guide`, §4).

Branch on the description-rewrite policy chosen in Step 9:

### Policy A — Replace ONLY the `## Wave Plan` section

Locate the existing `## Wave Plan` section in the description (any heading-2 named exactly "Wave Plan", case-insensitive). Replace its contents (everything from that heading until the next heading-2 or the end of the document) with the new wave plan rendered below. **Every other section stays byte-identical.**

If no `## Wave Plan` heading exists despite the policy, fall back to Policy B.

### Policy B — Append a new `## Wave Plan` section

Append the rendered wave plan as a new section at the end of the description. Existing content (including any old wave plan if present — leave it as historical context) stays.

### Policy C — Skip

Do nothing here. The config in Step 12 still gets written.

### Policy D — Full rewrite (only after the destructive-warning re-confirm in Step 9)

Replace the entire description with a freshly-rendered version. This is the legacy behavior; only use it when the user explicitly asked for it.

### Cross-epic blockers (`blocked_by`)

When the epic depends on another board's epic, its plan file carries a `### Wave 0 — Blocked by <KEY> (redirect)`
section, and `blocked_by: [<KEY>]` in the epic's front matter when the whole epic waits.

- **Every policy keeps Wave 0 verbatim** as the first wave. It is not a child of this epic, so it never enters the
  Step 7/8 analysis.
- When only some stories wait (Wave 0 names them), write `blocked_by: [<KEY>]` into each of those stories' front
  matter in the same pass. Newly minted stories get it at creation.

`/giga-workflow:epic-next` Step 7.5 and `/giga-workflow:epic-loop` 2a read these to redirect blocked work to the blocker's board.

### Wave plan rendering format (Markdown)

```
## Wave Plan

### Wave 1 — <label> (parallel)
- KEY-A: <summary>
- KEY-B: <summary>

### Wave 2 — <label> (parallel)
- KEY-C: <summary>
- KEY-D: <summary>

### Wave 3 — <label> (sequential)
- KEY-E: <summary>
- KEY-F: <summary>
```

The story keys must appear in the exact order `/giga-workflow:epic-next` should execute them within each wave. Keys for sequential waves appear in dependency order.

**Keep every wave-plan entry to a single line** — `KEY — short summary` (an optional status marker like `_(DONE)_` / `_(<jira.createStatus>)_` / `_(<jira.createStatus> — BLOCKED)_` is fine). Do NOT paste per-story implementation detail, acceptance criteria, dependency essays, or follow-up specs into the epic — that content belongs in each child ticket (or the linked design docs). The epic description carries ONLY: the overall description, this one-line-per-story wave order, and — at most — a few high-level pivot/architectural-lock bullets. This keeps story scope readable from the child ticket alone and keeps the description well under Jira's ~32,767-char cap (a bloated epic will hit it).

`Write` (or `Edit`) the rendered wave plan into `$epicPath` (`<prefix>/<epicKey>.md`) per the chosen policy. **Never** call `editJiraIssue` — the content lives in the file, not Jira (the plans guide, `plans.guide`, §4).

After writing, `Read` `$epicPath` back and diff it against the pre-write version. If a section the user expected to preserve has changed (substring fingerprint), surface a warning to the user with the diff — they can revert the file (it is git-tracked in the plans repo) or ask to re-run.

> **Optional — re-point Jira at the file.** Jira's description stays a stub. To refresh that stub (one-line summary + GitHub-blob link) after this write, run the DESTRUCTIVE stub pass (needs `write:jira-work`): `python3 <plans.script> stub <epicKey>`. `/giga-workflow:epic-next` reads the wave order from the local file regardless, so this only updates the Jira UI. (Plans guide §4.)

## Step 12 — Write the config file

The destination file path was determined in Step 4.5:
- `configFileMode === "overwrite"` (or step skipped) → `.claude/giga/epic.<boardName>.json`
- `configFileMode === "alternate"` → `.claude/giga/epic.<boardName>-<argEpicKey-lowercase>.json`

Write to the chosen path:

```json
{
  "name": "<epic summary>",
  "epicKey": "<epicKey>",
  "jql": "parent = <epicKey> AND status = \"<jira.createStatus>\"",
  "storyOrdering": "epic-description",
  "groupLabel": "Wave",
  "completionMessage": "All <epicKey> stories are complete!",
  "hybridMode": <from baseConfig.hybridMode or false — see notes above; "conditional" where stories need /giga-workflow:epic-cross-actor-test>,
  "mergeMode": "<from Step 10: the directive, baseConfig.mergeMode, the template's, or 'pr' — 'epic-branch' for boards where every story commits onto a shared epic branch; 'direct' for boards whose stories each fast-forward into <git.mainBranch> with no PR>",
  "epicBranch": <"<git.branchPrefix><epic-lower>-<slug>" when mergeMode is "epic-branch" (Step 10); null otherwise>,
  "commitScope": "<from baseConfig or derived from boardName>",
  "buildCommand": "<from baseConfig or null — e.g. 'npm run b.app.<domain>'. Run by /giga-workflow:jira Phase 6 to catch type/barrel drift. Set to null only if there is no buildable app.>",
  "app": "<from baseConfig or placeholder>",
  "libraries": <from baseConfig or placeholder>,
  "routingFiles": <from baseConfig or []>,
  "conventions": <from baseConfig or []>,
  "designReferences": <from baseConfig or null>,
  "epicEvolutionRules": <board-specific addenda only — [] unless this epic genuinely needs a rule no other board does; preserve any non-canonical entries from baseConfig>
}
```

**`epicEvolutionRules` holds board-specific ADDENDA only — write `[]` in the normal case.** The four
canonical evolution rules live in `/giga-workflow:epic-evolution-audit` ("The evolution rules"), bind every board,
and are sent by that skill on every run. Do **not** write them here.

- Carrying `baseConfig`'s value forward is right *if* it holds genuine addenda (the `rex` board's
  seed-fixture rule is the only one in the workspace today). Drop anything that merely restates a
  canonical rule.
- `null` still means the board opted out of evolution propagation entirely. `[]` is not an opt-out.

This field once held a verbatim copy of the canonical four in every board — seven byte-identical
copies of the same 1.6KB, written by this step on every re-plan. They drifted: one board lost the
discovery rule and forked a weaker epic-description rule. Restating them here is what regenerates
that drift, which is why this step no longer does it.

If `baseConfig` was null (new board), output a warning listing the fields that need to be filled in manually: `app`, `libraries`, `routingFiles`, `conventions`, `buildCommand`. When the board template seeded them (`baseFromTemplate`), list the same fields and `commitScope` as `seeded from <boardTemplate> — confirm` instead.

## Step 13 — Summary

```
Done:
<If Step 6.7 was skipped:> ○ Challenge skipped — the repo has no Idea Board (`ideas.board`)
</If>
<If Step 10.5 ran:>
✓ Created: <KEY> · <type> · <jira.createStatus> · <summary>   (one line each, or "none")
✓ Moved to <jira.createStatus>: <epicKey> (epic), <KEYs>       (or "none")
  <If any failed:> ⚠ Still Backlog / not created: <KEY or summary> — <reason>
</If>
<If Step 11 ran:>
✓ Wave plan written to <epicKey> local plan file (<prefix>/<epicKey>.md)
  Policy used: <A — replace section only | B — append | D — full rewrite>
  <N> waves, <M> stories
  <If diff warning fired:> ⚠ Diff warning: <list sections that changed unexpectedly>
<Else (policy C — skip):>
○ Plan file NOT touched (policy C — config-only update)
</If>
✓ Config written: <configFilePath>
  <If configFileMode === "alternate":>
  ⚠ Alternate file (existing <baseConfig.epicKey> is <status>, not Done — preserved its shortcut)
  </If>
  epicKey:           <epicKey>
  storyOrdering:     epic-description
  jql:               parent = <epicKey> AND status = "<jira.createStatus>"
  epicType:          <detected type from Step 6.5>  ← informational; not stored in config
  epicEvolutionRules: <N> board addenda (canonical rules live in /giga-workflow:epic-evolution-audit)
  hybridMode:        <value written>
  <If hybridMode === false:>
  ⚠ hybridMode=false (/giga-workflow:epic-loop ships every story unattended). If stories
    need cross-actor browser-driven verification before shipping (i.e.
    /giga-workflow:epic-cross-actor-test in Phase 6/7), hand-edit the config to
    hybridMode="conditional".
  </If>

Run /giga-workflow:epic-next <effectiveBoardName> to start the first story.
<If configFileMode === "alternate":>
(Note: <baseConfig.epicKey> work continues to use /giga-workflow:epic-next <boardName> via the existing config.)
</If>
```
