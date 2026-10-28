---
name: epic-next
description: "Generic epic story orchestrator. Picks the next unstarted story from any configured epic and starts work on it — one story per session — on a **per-story feature branch** (PR and direct modes) or **directly on the shared epic branch** (epic-branch mode)."
---

Generic epic story orchestrator. Picks the next unstarted story from any configured epic and starts work on it — one story per session — on a **per-story feature branch** (PR and direct modes) or **directly on the shared epic branch** (epic-branch mode).

**Usage:**
- `/giga-workflow:epic-next <board>` — the next unstarted story
- `/giga-workflow:epic-next <board> KEY-123` — a specific ticket

**One story per session.** This skill runs exactly one story and stops. To work two stories at once,
run the second in a **separate repo clone and a separate session** — never a second story in this
conversation. A session's cost is `turns × context`, and context only grows: story two inherits every
token story one accumulated and pays for it again on every remaining turn. Two 400-turn sessions cost
far less than one 800-turn session, and they genuinely run in parallel.

**One turn, many calls.** The other half of `turns × context` is how many turns you spend. Measured
on a real run of this skill: 491 tool calls across 491 turns — a mean of exactly 1.00, meaning not a
single independent pair was ever batched, each one re-reading a ~474k context to run a two-line
shell command. The steps below are numbered for reading order, **not** for one-call-per-message
execution. Whenever the next calls do not consume each other's output, issue them in a single
message; whenever they are shell commands, join them with `&&` or newlines in one `Bash` call.
Explicit batch points are marked ⚡ below.

**Branch model — set by `config.mergeMode`:**
- **`"pr"` (default / field absent):** every story gets its own `<git.branchPrefix><key>-<slug>` branch cut from `origin/<git.mainBranch>`. After `/giga-workflow:jira` finishes its in-conversation phases, hand off to `/giga-workflow:epic-story-complete` to commit + push + open the PR + transition the ticket to In Review. The next story starts fresh from a freshly-pulled `<git.mainBranch>`. No shared long-lived epic branches.
- **`"epic-branch"`:** every story is implemented in the main checkout **directly on the shared `config.epicBranch`** and committed there. `/giga-workflow:epic-story-complete` pushes the epic branch and transitions the ticket to Done (no per-story PR). The whole epic lands on `<git.mainBranch>` via **one PR at the end**. Requires `config.epicBranch`.
- **`"direct"`:** every story gets the same per-story `<git.branchPrefix><key>-<slug>` branch as PR mode, cut from `origin/<git.mainBranch>`, and no PR. `/giga-workflow:epic-story-complete` commits on it, fast-forwards `<git.mainBranch>` to it, pushes `<git.mainBranch>`, transitions the ticket to Done and chains `/giga-workflow:post-merge-cleanup`. Each story lands on `<git.mainBranch>` on its own, for repos that deploy on every push to it.

**Available boards:** one per `.claude/giga/epic.<board>.json`. List them from the files (board name, `epicKey`, `name`), never from memory: boards are repointed at each new epic, so any copied list goes stale.

> **One board per domain.** When a board's epic finishes, **repoint that board's existing
> `epic.<board>.json`** at the next epic — do not add a second config for the same domain. Only the
> epic-specific fields change (`name`, `epicKey`, `jql`, `storyOrdering`, `groupLabel`,
> `completionMessage`, `designReferences`, and the epic-specific conventions at the head of
> `conventions`); the domain conventions below them are reused verbatim. Two configs for one domain
> fork those conventions and they drift.

> Boards are defined by `epic.<board>.json` files in `.claude/giga/`. Run `/giga-workflow:epic-config` to view or update a board config.

## Project config

Repo-specific values come from `.claude/giga/config.json` at the repository root, under `workflow`. Read it once at the start. A missing file or field takes the fallback below, never a guess.

| Field | Used for | When absent |
| --- | --- | --- |
| `plans.repo` | the plans repo that holds board navigation and ticket content | stop and say the repo has no `plans.repo` in `.claude/giga/config.json` |
| `plans.script` | the script behind `board`, `ensure` and `section` (Steps 3, 5, 6, 7.5, 8) | stop and say the repo has no `plans.script` in `.claude/giga/config.json` |
| `plans.guide` | the plans guide, canonical for the two commands in Step 3 | skip reading it |
| `jira.credentialsFile` | where the plans script authenticates from | omit the sentence naming it |
| `git.mainBranch` | the base branch stories are cut from and merged into | `main` |
| `git.branchPrefix` | the per-story branch prefix | `feat/` |
| `commit.format` | the commit subject `/giga-workflow:epic-story-complete` writes | `<type>(<scope>): <KEY> <subject>` |
| `memoryDir` | the personal memory directory holding each board's `domainMemoryIndex` | skip the domain-memory read |
| `epicCloseSkill` | the skill invoked when the epic's last story is Done | skip the epic-close hand-off and print `config.completionMessage` only |
| `notify` | the desktop-notification command queued at the end | no desktop notification |

---

## Config schema reference

Each `epic.<board>.json` file defines:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Human-readable epic name |
| `epicKey` | string | Jira tracker epic key |
| `jql` | string | Full JQL query to find To Do stories |
| `storyOrdering` | `"jql"` \| `"epic-description"` | `jql` = use JQL result order directly; `epic-description` = parse ordered list from epic description then cross-reference |
| `groupLabel` | string | Label for story groupings shown in reports (e.g. `Priority`, `Wave`, `Track`) |
| `completionMessage` | string | Shown when no To Do stories remain |
| `hybridMode` | `"conditional"` \| `false` \| undefined | Consumed by `/giga-workflow:epic-loop`. `"conditional"` = each story is marked for cross-actor need (autonomy contract §7.5, or the story file's `crossActor:` front matter); a story that needs it pauses the run before its PR, every other story ships and merges unattended. `false` / omitted = every story ships and merges unattended. Has NO effect on `/giga-workflow:epic-next` itself, which is always interactive. |
| `crossActor` | object \| undefined | Per-board cross-actor config consumed by `/giga-workflow:epic-cross-actor-test` (run by hand at an `/giga-workflow:epic-loop` cross-actor pause, or directly). Holds `devServer` (serveCommand/port/logFile/healthCheckUrl), `firestorePathPrefix`, `testAnchorPath`, `bracketMode` (`skill`\|`npm`), `e2eHook` (`window.__cgE2E`\|null), `personas[]` (displayName/email/seedAnchorKey/authModel/role), and `scenarioCatalogMemory` + `browserProfilesMemory` slugs plus `scenarioDir` (one scenario per file beside the catalog memory). Required when `hybridMode:"conditional"`. |
| `commitScope` | string | Angular commit scope (e.g. `billing`, `web`) — passed to `/giga-workflow:epic-story-complete` |
| `buildCommand` | string \| null | Shell command that builds the epic's app (e.g. `npm run build:web`). Run by `/giga-workflow:jira` Phase 6 if set. Optional; omit or set to `null` to skip the build gate. |
| `app` | string | Main app path |
| `libraries.ui` | string | UI library path |
| `libraries.store` | string \| null | Store library path (omit if unused) |
| `libraries.designLibrary` | string \| null | Design library path |
| `routingFiles` | string[] | Routing files for conflict analysis and `/giga-workflow:jira` plan-mode discovery |
| `conventions` | string[] | Project-specific conventions injected into the `/giga-workflow:jira` handoff prompt |
| `designReferences` | object \| null | Design system pointers (`boardsIndex`, `spec`, `agentsFile`, `tokens`) |
| `epicEvolutionRules` | string[] \| null | Board-specific **addenda** to the four canonical evolution rules, which live in `/giga-workflow:epic-evolution-audit` and bind every board. `[]` (the common case) = canonical only; `null` = this board opted out of evolution propagation entirely. Surface to `/giga-workflow:jira` for inclusion in the Phase 7 test plan when a shift gets surfaced. |
| `domainMemoryIndex` | string \| null | Filename of this board's domain memory index in the personal memory dir (e.g. `payments-index.md`). Read in Step 0 so domain-specific Project/Reference memories load without bloating the always-on `MEMORY.md`. Omit / `null` to skip. |
| `mergeMode` | `"pr"` \| `"epic-branch"` \| `"direct"` \| undefined | How stories integrate. `"pr"` / absent (default) = per-story `<git.branchPrefix>` branch → PR → `<git.mainBranch>`. `"epic-branch"` = every story is committed directly onto the shared `epicBranch` (no per-story PR); the epic lands on `<git.mainBranch>` via one PR at the end. `"direct"` = per-story `<git.branchPrefix>` branch, fast-forwarded into `<git.mainBranch>` and pushed by `/giga-workflow:epic-story-complete` (no PR). |
| `epicBranch` | string \| null | **Epic-branch mode only (required).** The long-lived integration branch every story commits onto (e.g. `feat/abc-123-short-slug`). |
| `loop` | object \| undefined | Consumed by the `/giga-workflow:epic-loop` skill (unattended in-session orchestrator); has NO effect on `/giga-workflow:epic-next` itself. Holds `storyModel` (default `opus`), `triage` + `triageModel`, `decisionResearchModel`, `designSkills[]` + `architectureSkills[]` (the authorities `/giga-workflow:epic-loop`'s decision-resolution ladder consults before falling back to a precedent search), `evolutionAudit`, `maxConsecutiveFailures`, and `browserVerification` (default `false`; `true` = story agents check UI changes in Storybook or the running app before shipping, on one browser connection made at run start). Omit to run `/giga-workflow:epic-loop` on this board with its defaults. |

> `mode` and `phaseNote` are ignored. `epicBranch` is the integration branch of a `mergeMode:"epic-branch"` board; every story commits onto it directly.

---

## Step 0 — Load board config

Read `$ARGUMENTS`. The **first token** is the board name (e.g., `web`, `api`).

Read `.claude/giga/epic.<board>.json` and bind all fields as named variables used in every subsequent step. Refer to them throughout as `config.field` (e.g., `config.epicKey`, `config.commitScope`).

If no board name is provided, or the config file does not exist, list available `epic.*.json` files in the skill directory and stop.

⚡ **Batch this with the domain-memory read below** — the config path and the memory path are both
known from `$ARGUMENTS` alone, so both Reads belong in one message. Read the config *file* directly;
do not `ls` the directory first to confirm it exists — a failed Read tells you the same thing in the
same turn.

**Load the board's domain memory.** If `memoryDir` and `config.domainMemoryIndex` are both set, Read `<memoryDir>/<config.domainMemoryIndex>` so the domain's Project + Reference memories are in context for the `/giga-workflow:jira` handoff. The always-on `MEMORY.md` core already carries global feedback + shared references + user context; this loads the domain-scoped slice on top. Read-only, so it's fine before Step 1's plan mode. Skip silently if either is absent or the file does not exist yet.

## Step 1 — Enter plan mode

Call `EnterPlanMode` immediately. Steps 2–8 run inside plan mode. All Atlassian MCP calls are read-only and are permitted in plan mode.

## Step 2 — Parse remaining arguments

After stripping the board name, parse the remaining token:

- **Specific ticket** — if it matches `[A-Z]+-\d+` (e.g. `ABC-123`): set `specificKey = token`. Skip Steps 5 and 6.
- **Default** — no remaining token: set `specificKey = null`.

A bare number is no longer a batch size. If the user passes one, tell them this skill runs one story
per session and ask which ticket they meant.

## Step 3 — Plans-repo access (board nav + content — NOT the MCP)

Board navigation and ticket content come from the plans repo (`plans.repo`), not the Atlassian MCP (which returns a ~5.5k-char fat envelope per issue and ignores field-narrowing — a 10-issue board query is ~55k chars). Canonical guide: the plans guide (`plans.guide`). Two commands:

- **Board nav** (which stories are To Do): `python3 <plans.script> board --jql '<config.jql>'` → JSON `[{key,status,category,type,priority,parent,summary}]` (live status, ~200 B/issue).
- **Ticket content** (epic/story description): `python3 <plans.script> ensure <KEY>` prints the local `<prefix>/<KEY>.md` path (migrating on-miss); then `Read` it.

No MCP tools or `cloudId` are needed here — the script authenticates via `jira.credentialsFile`. (Status transitions in the downstream `/giga-workflow:jira` + `/giga-workflow:epic-story-complete` still use the MCP.)

## Step 4 — (Cloud ID no longer needed)

The plans script handles auth + `cloudId` via `jira.credentialsFile` — no `getAccessibleAtlassianResources` call. Proceed to Step 5.

## Step 5 — Read the tracker epic description

> **Skip this step if `specificKey` is set** — jump straight to Step 7.
>
> **Skip this step if `config.storyOrdering === "jql"`** — jump straight to Step 6.

```
python3 <plans.script> section <config.epicKey> Wave
```

This prints only the epic's wave sections (`## Wave Plan` / `## Waves` / `## Wave order` with their `### Wave N` subsections), not the whole file, whose `## Shipped` and decision history can be several times longer. The epic plan file is the source of truth for ordering once epics are stubbed. Parse the output to extract the **ordered list of story keys** in the sequence they appear, top to bottom, preserving any section groupings (waves, tracks, etc.) as the `config.groupLabel` for each story. If it exits 1 (no `Wave` heading: the epic uses another shape), `Read` the path it names on stderr instead.

## Step 6 — Find To Do stories via JQL

> **Skip this step if `specificKey` is set** — jump straight to Step 7.

```
python3 <plans.script> board --jql '<config.jql>'
```

Returns JSON `[{key,status,category,type,priority,parent,summary}]` — the To-Do stories (`config.jql` already filters to them), with **live** status straight from Jira.

## Step 7 — Pick the next story

> **Skip this step if `specificKey` is set** — jump straight to Step 8.

- If `config.storyOrdering === "jql"`: take the first story from the JQL results directly.
- If `config.storyOrdering === "epic-description"`: cross-reference the ordered list from Step 5 against the JQL results. Take the first key from the ordered list that appears in the JQL results.

Note its `Key`, `summary`, and group name (from the `config.groupLabel` section it appears under, or from the `priority` field if ordering is `"jql"`).

**Story progress.** One call, recomputed fresh every time and never cached (stories are added mid-epic):
`jira_to_md.py board --jql 'parent = <config.epicKey>'` → `total` = rows, `done` = rows with `category == "Done"`.
Every child issue type (Story and Bug) counts; children moved out of the epic no longer have it as parent and drop out.

If **no stories are in "To Do"**: report `config.completionMessage`. Then count the epic's open children with
`jira_to_md.py board --jql 'parent = <config.epicKey> AND statusCategory != Done'`. If the result is `[]`, the epic is
finished: invoke the skill named in `epicCloseSkill` as `closed <config.epicKey>` (absent: skip this hand-off) and print its block, whose `Plan next` names the epic to
`/giga-workflow:epic-plan`, then `Review: /giga-workflow:epic-review <config.epicKey> — before /giga-workflow:epic-plan <NEXT-KEY>`. Stop either way.

## Step 7.5 — Blocker redirect (cross-epic dependencies)

Runs on the picked story, and on `specificKey` too. An epic can depend on another board's epic, e.g. two domain
connectors (ABC-210, DEF-310) on a shared core (GHI-410). The dependency is recorded as
`blocked_by: [<KEY>, …]` in plan-file front matter: on the **epic** file when the whole epic waits, or on the
**story** file when only some stories wait. The candidate's blockers are the union of its own `blocked_by` and its
epic's.

⚡ One `Bash` call reads both front matters and checks the blockers' live status:

```
python3 <plans.script> board --jql 'key in (<blocker keys>)'
```

Every blocker `Done` → continue to Step 8. Otherwise **redirect**. Do not build the blocked story; the blocker's
work comes first:

1. Resolve the blocker's board. A blocker that is an epic is its own target; a story's target is its `parent`.
   Find the `epic.*.json` whose `epicKey` is that target.
2. Report, and stop:
   ```
   <KEY> is blocked by <BLOCKER> (<status>) — <summary>
   Redirect: /giga-workflow:epic-next <target-board>
   ```
   If no config points at the target, say so. The fix is `/giga-workflow:epic-config` to repoint that prefix's board (one board
   per domain, never a second config), then `/giga-workflow:epic-plan <target>` if its children do not exist yet.

For the default pick, check whether a later, unblocked To Do story exists in the order before redirecting. If one
does, offer the choice (redirect, or take that story) instead of silently skipping ahead. Wave order stays the owner's.

## Step 8 — Present plan and exit plan mode

**If `specificKey` is set**, fetch the ticket details now:

```
python3 <plans.script> board --jql 'key = <specificKey>'
```

(one-row JSON with the key's summary + live status; run `ensure <specificKey>` + `Read` the plan file if you also need its full description).

Present the plan to the user, including the **planned branch name** (see Step 9a for the slug derivation) and the story's recommended effort — the `effort:` key in its plan file's front matter (`grep -m1 '^effort:' "$(python3 <plans.script> ensure <KEY>)"`, not a full `Read`; the owner edits that value by hand, so read it fresh every run):

```
Epic: <config.name> (<config.epicKey>)
Working story <done+1> of <total> — <KEY>
Next up: <KEY> — <summary> (<config.groupLabel>: <group value>)
Branch: <git.branchPrefix><key-lower>-<short-slug>
Effort: <effort> — run `/effort <effort>` before continuing if this session differs
```

Omit the `Effort` line when the front matter has no `effort:` key. The skill cannot change the session's effort itself; it only reports the recommendation.

Then call `ExitPlanMode`. Implementation proceeds only after the user confirms they want to continue.

---

## Step 9 — Process the story

This step is the unit of work, and it runs exactly once.

### 9a — Create the per-story branch (PR and direct modes) or check out the epic branch (epic-branch mode)

Derive the slug:
- Lowercase the ticket key (`ABC-123` → `abc-123`).
- Take the first 4–6 words of the Jira summary, lowercase, replace non-alphanumerics with `-`, collapse runs of `-`, trim leading/trailing `-`.
- Cap total length at ~60 chars. Drop trailing words to fit.

**PR and direct modes (`config.mergeMode !== "epic-branch"`)** — cut a `<git.branchPrefix><key-lower>-<slug>` branch (e.g. `feat/abc-123-short-slug`) fresh from `origin/<git.mainBranch>`:

⚡ One `Bash` call, not three:

```
git checkout <git.mainBranch> && git pull --ff-only && git checkout -b <git.branchPrefix><key-lower>-<slug> && git rev-parse --short HEAD
```

Report: `Created branch <git.branchPrefix><key-lower>-<slug> from origin/<git.mainBranch> at <short-sha>`.

**Epic-branch mode (`config.mergeMode === "epic-branch"`)** — work in the main checkout directly on `config.epicBranch`; the story is committed onto it (no per-story branch, no worktree). Ensure the epic branch exists and is current:

⚡ One `Bash` call:

```
git fetch origin
# First story of the epic? Create the epic branch from origin/<git.mainBranch>:
#   git checkout -b <config.epicBranch> origin/<git.mainBranch> && git push -u origin <config.epicBranch>
# Otherwise check out the existing epic branch and fast-forward it:
git checkout <config.epicBranch> && git pull --ff-only && git status --porcelain && git rev-parse --short HEAD
```

The `--porcelain` output in the same call answers the uncommitted-changes question below without a
second round trip.

Every later step (the `/giga-workflow:jira` hand-off, build/test, `/giga-workflow:epic-story-complete`) runs in the main checkout on `config.epicBranch`. Report: `On epic branch <config.epicBranch> at <short-sha>`.

**If the epic branch has uncommitted changes** (e.g. a prior story left work mid-flight) → surface them and ask the user whether to continue on top or stash first; do not discard in-progress work.

### 9b — Hand off to /giga-workflow:jira

Invoke the `giga-workflow:jira` skill with the ticket key as the argument (equivalent to `/giga-workflow:jira <KEY>`).

Pass these context hints to /giga-workflow:jira so its plan mode is grounded:

- **Build command** — if `config.buildCommand` is set, ensure /giga-workflow:jira Phase 6 runs it.
- **Conventions** — surface the entries from `config.conventions` so they appear in the implementation plan.
- **Design references** — if `config.designReferences` is non-null, point /giga-workflow:jira at:
  - `config.designReferences.boardsIndex` (if set)
  - `config.designReferences.spec` (if set)
  - `config.designReferences.agentsFile` (if set — read this first)
  - `config.designReferences.tokens` (if set)
- **Epic evolution awareness** — unless `config.epicEvolutionRules` is `null` (board opted out), surface the four canonical evolution rules from `/giga-workflow:epic-evolution-audit` plus any board addenda in `config.epicEvolutionRules`, and instruct /giga-workflow:jira to call out any architectural shift in its Phase 7 test plan under an "Epic evolution items" subheading so the user can act on it before invoking `/giga-workflow:epic-story-complete`. An empty array is not an opt-out — it means canonical rules only.
- **UX** — /giga-workflow:jira frames every story with a user-facing surface through the `giga-ux:ux-design` skill before it plans (Phase 2.8) and reviews it in the running app after the build gate (Phase 6.5). Do not ask it to skip either for a story that changes what a user sees.
- **Subagent budget** — /giga-workflow:jira owns every subagent this story will spawn, under the rules in its own § Subagent budget: the Phase 2.75 drift gate is settled with `git log` before any agent is considered, Phase 5a spawns **one** implementation agent unless the plan clears its ≥2-projects-AND-≥8-files threshold, the Phase 5b review gate is sized to `git diff --stat` and pinned to `sonnet`, and Phase 7 writes the test plan in-conversation with no agent at all. Do not ask /giga-workflow:jira to pre-emptively fan out "to save wall-clock" — measured across this workspace, subagents are 44% of all tokens and Opus subagents are 67% of that, so an unearned parallel split is the single most expensive thing this pipeline can do.

Let /giga-workflow:jira run its phases normally. It will NOT create a PR (Phase 6 is no-PR by design); `/giga-workflow:epic-story-complete` handles that next.

### 9c — Hand off to /giga-workflow:epic-story-complete

After /giga-workflow:jira finishes and the user has reviewed the diff, invoke `/giga-workflow:epic-story-complete` with the board + ticket key (it can also infer them from conversation context).

`/giga-workflow:epic-story-complete` will commit the unstaged changes with a cz-conventional-changelog subject (`commit.format`), then, per `config.mergeMode`:
- **PR mode:** push the branch with `-u origin`, open the PR via `gh pr create` with the test plan in the body, and transition the ticket to **In Review** (`/giga-workflow:epic-merge-pr` merges it and chains `/giga-workflow:post-merge-cleanup` → Done).
- **Epic-branch mode:** commit onto `config.epicBranch`, push it (`git push origin <config.epicBranch>`), and transition the ticket to **Done** (no per-story PR — the epic lands on `<git.mainBranch>` via one PR at the end).
- **Direct mode:** commit on the story branch, rebase it onto `origin/<git.mainBranch>` if that moved, fast-forward `<git.mainBranch>` to it and push `<git.mainBranch>` (no PR; the story branch is never pushed), transition the ticket to **Done**, and chain `/giga-workflow:post-merge-cleanup`, which deletes the local branch and moves the story out of its wave.
- **Skill-only story** (any mode; the whole diff is in the skills repo's story worktree): land it on the skills repo's live branch and push it, then take the ticket to **Done** with no PR.
- **Mixed story** (skills-repo files too): the skills leg lands on the skills repo's live branch and is pushed first, so it is live before this repo's PR is reviewed.

### 9d — Stop

Stop here. The user reviews the PR — on github.com or via `gh pr view` — and then runs
`/giga-workflow:epic-merge-pr <N>`, which merges it (`git.mergeMethod`), verifies it reached `MERGED`, repairs a stale local
`<git.mainBranch>`, and chains `/giga-workflow:post-merge-cleanup` → Done. **Point them at `/giga-workflow:epic-merge-pr`, not at
`/giga-workflow:post-merge-cleanup`, whichever way they reviewed:** it is idempotent, so a PR they already merged
in the GitHub UI reads as `MERGED` and it skips straight to cleanup.

Do **not** pick up another story in this conversation — a second story starts from this one's
accumulated context and pays for it on every turn. Offer the next one as a fresh `/giga-workflow:epic-next <board>`
instead:

```
<KEY> shipped — PR #<N>: <PR URL>
Merge it with /giga-workflow:epic-merge-pr <N> (fine to run after merging on github.com too).
Next on the board: <next-KEY> — <next-summary>
Run /giga-workflow:epic-next <board> in a new session (or another clone) to start it.
```

**Direct mode:** the story is already merged on `<git.mainBranch>` and Done, so there is no PR to review
and nothing to merge; do not point at `/giga-workflow:epic-merge-pr`. Print instead:

```
<KEY> merged to <git.mainBranch> — <short-sha>
Next on the board: <next-KEY> — <next-summary>
Run /giga-workflow:epic-next <board> in a new session (or another clone) to start it.
```

**Skill-only story** (any mode): it reached Done inside `/giga-workflow:epic-story-complete`, with no PR. Print the direct-mode block with the first line `<KEY> landed on <skills branch> — <repo name> <skills-sha>`, taken from that skill's `Skills:` report line; the notification reads `'<KEY> · single story complete — landed on <skills branch> + Done'`.

Print `<done> of <total> stories complete` with the shipped line, recomputed fresh as in Step 7 (epic-branch and direct modes: after the ticket reaches Done; PR mode: the story is counted once `/giga-workflow:epic-merge-pr` moves it to Done).

Getting `next-KEY` costs nothing extra — it is already in the Step 6 board results.

> **Desktop notification** (skip when `notify` is absent). `/giga-workflow:epic-next` is always interactive, so this path is safe to ping. The delegated `/giga-workflow:epic-story-complete` (Step 9c) already queued a completion line with `<notify>` at its own Step 11; overwrite it here so the global Stop hook fires one persistent ping at turn end: `<notify> '<KEY> · single story complete — PR #<N> ready for review'` (direct mode: `'<KEY> · single story complete — merged to <git.mainBranch> + Done'`). Use the real KEY/PR values. **Body format is `<KEY> · <task>` — lead with the Jira key (it already encodes the board, so do NOT add the board name). Do NOT include the repo name or path either; the Stop hook auto-stamps those as the notification title + subtitle from the session's cwd.** One ping only (same session, file consumed once). Ignore write failures.
>
> **Canonical notification behavior** (per-repo handoff file queued by `<notify>`, keyed by the session's git toplevel so sessions in sibling clones never take each other's message; `<KEY> · <task>` body, `CLAUDE · <status>` title + `~`-repo-path subtitle auto-stamped by the global Stop hook in `~/.claude/settings.json`) is shared across `/giga-workflow:epic-story-complete`, `/giga-workflow:epic-next`, and `/notify`, and documented in the notify memory. If you change the format, update all of them together.
