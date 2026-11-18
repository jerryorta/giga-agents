---
name: epic-next
description: "Generic epic story orchestrator. Picks the next unstarted story from any configured epic and starts work on it — one story per session — on a **per-story feature branch** (PR and direct modes) or **directly on the shared epic branch** (epic-branch mode)."
---

**Usage:**
- `/giga-workflow:epic-next <board>` — the next unstarted story
- `/giga-workflow:epic-next <board> KEY-123` — a specific ticket

**One story per session.** This skill runs exactly one story and stops. To work two stories at once,
run the second in a **separate repo clone and a separate session** — never a second story in this
conversation. A session's cost is `turns × context`: story two inherits every token story one accumulated and pays for it again on every remaining turn.

**One turn, many calls.** The other half of `turns × context` is how many turns you spend. The steps below are numbered for reading order, **not** for one-call-per-message
execution. Whenever the next calls do not consume each other's output, issue them in a single
message; whenever they are shell commands, join them with `&&` or newlines in one `Bash` call.
Explicit batch points are marked ⚡ below.

**Branch model — set by `config.mergeMode`:**
- **`"pr"` (default / field absent):** every story gets its own `<git.branchPrefix><key>-<slug>` branch cut from `origin/<git.mainBranch>`. After `/giga-workflow:jira` finishes its in-conversation phases, hand off to `/giga-workflow:epic-story-complete` to commit + push + open the PR + transition the ticket to In Review. The next story starts fresh from a freshly-pulled `<git.mainBranch>`. No shared long-lived epic branches.
- **`"epic-branch"`** (one shared `config.epicBranch`, no per-story PR) and **`"direct"`** (per-story branch fast-forwarded into `<git.mainBranch>`, no PR): **when `config.mergeMode` is one of these**, read `${CLAUDE_SKILL_DIR}/merge-modes.md` § "Branch model" and follow it.

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


**When you need a board-config field's meaning or allowed values:** read `${CLAUDE_SKILL_DIR}/config-schema.md`.

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

**When `config.storyOrdering === "epic-description"` and `specificKey` is null:** read `${CLAUDE_SKILL_DIR}/epic-description-ordering.md` and follow it.

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
`python3 <plans.script> board --jql 'parent = <config.epicKey>'` → `total` = rows, `done` = rows with `category == "Done"`.
Every child issue type (Story and Bug) counts; children moved out of the epic no longer have it as parent and drop out.

**When no stories are in "To Do":** read `${CLAUDE_SKILL_DIR}/epic-complete.md` and follow it.

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

Every blocker `Done` → continue to Step 8. Otherwise (any blocker not `Done`) **redirect**:

**When any blocker is not `Done`:** read `${CLAUDE_SKILL_DIR}/blocker-redirect.md` and follow it.

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

**When `config.mergeMode === "epic-branch"`:** read `${CLAUDE_SKILL_DIR}/merge-modes.md` § "9a" and follow it.

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
- **Subagent budget** — /giga-workflow:jira owns every subagent this story will spawn, under the rules in its own § Subagent budget: the Phase 2.75 drift gate is settled with `git log` before any agent is considered, Phase 5a spawns **one** implementation agent unless the plan clears its ≥2-projects-AND-≥8-files threshold, the Phase 5b review gate is sized to `git diff --stat` and pinned to `sonnet`, and Phase 7 writes the test plan in-conversation with no agent at all. Do not ask /giga-workflow:jira to pre-emptively fan out "to save wall-clock" — an unearned parallel split is the most expensive thing this pipeline can do.

Let /giga-workflow:jira run its phases normally. It will NOT create a PR (Phase 6 is no-PR by design); `/giga-workflow:epic-story-complete` handles that next.

### 9c — Hand off to /giga-workflow:epic-story-complete

After /giga-workflow:jira finishes and the user has reviewed the diff, invoke `/giga-workflow:epic-story-complete` with the board + ticket key (it can also infer them from conversation context).

`/giga-workflow:epic-story-complete` will commit the unstaged changes with a cz-conventional-changelog subject (`commit.format`), then, per `config.mergeMode`:
- **PR mode:** push the branch with `-u origin`, open the PR via `gh pr create` with the test plan in the body, and transition the ticket to **In Review** (`/giga-workflow:epic-merge-pr` merges it and chains `/giga-workflow:post-merge-cleanup` → Done).
- **Epic-branch mode, direct mode, a skill-only story, or a mixed story:** read `${CLAUDE_SKILL_DIR}/merge-modes.md` § "9c" for each outcome.

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

> **Desktop notification** (skip when `notify` is absent). `/giga-workflow:epic-next` is always interactive, so this path is safe to ping. The delegated `/giga-workflow:epic-story-complete` (Step 9c) already queued a completion line with `<notify>` from its ship script; overwrite it here so the global Stop hook fires one persistent ping at turn end: `<notify> '<KEY> · single story complete — PR #<N> ready for review'` (direct mode: `'<KEY> · single story complete — merged to <git.mainBranch> + Done'`). Use the real KEY/PR values. **Body format is `<KEY> · <task>` — lead with the Jira key (it already encodes the board, so do NOT add the board name). Do NOT include the repo name or path either; the Stop hook auto-stamps those as the notification title + subtitle from the session's cwd.** One ping only (same session, file consumed once). Ignore write failures.
>
> **Canonical notification behavior** (per-repo handoff file queued by `<notify>`, keyed by the session's git toplevel so sessions in sibling clones never take each other's message; `<KEY> · <task>` body, `CLAUDE · <status>` title + `~`-repo-path subtitle auto-stamped by the global Stop hook in `~/.claude/settings.json`) is shared across `/giga-workflow:epic-story-complete`, `/giga-workflow:epic-next`, and `/notify`, and documented in the notify memory. If you change the format, update all of them together.
