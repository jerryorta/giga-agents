---
name: create-jira
description: "Capture ONE Jira finding (bug / task / story) under an epic during an app review — board-parameterized, born-split, evidence-as-asset. Stateless so you can `/clear` between tickets: $ARGUMENTS"
---

Capture ONE Jira finding (bug / task / story) under an epic during an app review — board-parameterized, born-split, evidence-as-asset. Stateless so you can `/clear` between tickets: $ARGUMENTS

## Project config

Repo-specific values come from `.claude/giga/config.json` at the repository root, under `workflow`. Read it once at the start. A missing file or field takes the fallback below, never a guess.

| Field | Used for | When absent |
| --- | --- | --- |
| `plans.repo` | the plans repo holding `<board>/<KEY>.md`, assets and the epic index | stop and say the repo has no `plans.repo` in `.claude/giga/config.json` |
| `plans.script` | the `board` (epic check) and `stub` calls | stop and say the repo has no `plans.script` in `.claude/giga/config.json` |
| `plans.guide` | the born-split convention shared with `/giga-workflow:jira` | skip the reference |
| `plans.autoPush` | whether the plans repo commits and pushes itself | commit, then report the plans repo as unpushed |
| `jira.site` | the browse link in the report | omit the link line |
| `jira.cloudId` | the Jira cloud for every MCP call | read `cloudId` from `jira.credentialsFile`; with neither, call `<jira.mcpPrefix>getAccessibleAtlassianResources` |
| `jira.credentialsFile` | where `cloudId` is read when `jira.cloudId` is absent | skip that read |
| `jira.mcpPrefix` | the prefix of the Jira MCP tool ids | stop and say the repo has no `jira.mcpPrefix` in `.claude/giga/config.json` |
| `jira.createStatus` | the status a new ticket is moved to after creation | `To Do` |
| `docs.constraints` | the refactor-when-touched rule | state the rule as written here, with no doc link |
| `memoryDir` | the domain memory index named by the board config | skip the domain-memory read |

## What this does

Logs a single reviewer finding as a child ticket of a named epic, on **any** board in this repo, following the plans-repo **born-split** (Jira = status stub, `<plans.repo>/<board>/<KEY>.md` = content). Screenshots are saved as git-versioned assets next to the ticket. Root cause is researched in a **subagent** so the verbose output never lands in your main context.

**Use it like this:** `/giga-workflow:create-jira abc 50` → describe the finding + drop a screenshot path → a ticket is filed under ABC-50 → you `/clear` → repeat. One finding per invocation.

Companion to (not a caller of) `/giga-workflow:jira` (works a ticket). Both share the born-split convention in the plans guide (`plans.guide`).

## Design invariants (preserve when editing)

- **Stateless across invocations.** Everything comes from `$ARGUMENTS` + files on disk (plans repo, `epic.<board>.json`, the Jira credentials file) — NEVER from conversation history. This is what makes `/clear` between tickets lossless.
- **Args win over config.** The board arg is authoritative for project + plans-dir; the epic is authoritative from the id arg. `epic.<board>.json` is read ONLY for optional domain enrichment and its `epicKey` is IGNORED. This keeps `/giga-workflow:create-jira` independent of whatever `/giga-workflow:epic-next` is doing on the same board.
- **Offload verbose work to a subagent.** Code research + screenshot triage run in an Agent; only a compact result returns to the main context.
- **Capture only.** Never fix code or open a PR here — that's `/giga-workflow:jira`.
- **Never for refactors.** A finding that is "this code does not meet the standard" is done in the story in progress, in place, before it is tested (`docs.constraints` § Refactor When Touched) — never filed as a ticket, anywhere in the repo, with no exceptions.
- **Backend + frontend findings are still one ticket.** A finding that needs both backend and frontend work is still ONE ticket here (one finding per invocation), but its plan file names the backend part first and says the ticket is to be split backend-first by `/giga-workflow:epic-plan` Step 7.5 before it is worked.

## Arguments

`/giga-workflow:create-jira <board> [epic-id] [type] [free-text description…]`

- **`<board>`** (required) — the lowercased Jira project key, which is also its plans-repo folder: a folder name under `plans.repo` → `projectKey = board.upperCase()`, `plansDir = <plans.repo>/<board>/`.
- **`[epic-id]`** (optional) — the parent epic. A bare number (`50` → `<PROJECT>-50`) or a full key (`ABC-50`). If **omitted**, fall back to `epic.<board>.json`'s `epicKey` and **echo which epic you're filing under before creating anything**.
- **`[type]`** (optional) — `bug` | `task` | `story`. If omitted, infer and state it.
- Remaining tokens (and anything the user says this turn) = the finding description + screenshot path(s).

Parse tokens left-to-right: token 0 = board; token 1 = epic-id iff it matches `^\d+$` or `^[A-Za-z]+-\d+$` (else there is no id → config fallback); next token = type iff it matches `^(bug|task|story)$`; the rest is free text.

---

## Step 0 — Resolve board + epic (cheap, do first)

1. Parse `$ARGUMENTS`. If no board token, list `<plans.repo>/*/` folders as the valid boards and stop.
2. `projectKey = board.toUpperCase()`; `plansDir = <plans.repo>/<board>`.
3. **Epic key:**
   - id given → `epicKey = <PROJECT>-<num>` (or the full key as-is).
   - id omitted → read `.claude/giga/epic.<board>.json` and use its `epicKey`; **print** `Filing under <epicKey> (default from epic.<board>.json — pass an explicit id to override).`
4. **Verify the epic exists** (never assume): `python3 <plans.script> board --jql 'key = <epicKey>'` → confirm one row of `type: Epic`. If missing/not an epic, stop and report (likely a wrong board or number).
5. **cloudId:** `jira.cloudId`; when absent, read from `jira.credentialsFile` (`python3 -c "import json;print(json.load(open('<jira.credentialsFile>'))['cloudId'])"`).
6. **Optional domain enrichment** — if `.claude/giga/epic.<board>.json` exists, read only these domain-stable fields and bind them: `commitScope`, `app`, `libraries` (research-scope hints), `conventions`, `domainMemoryIndex`. **Ignore `epicKey`.** If `domainMemoryIndex` is set, Read `<memoryDir>/<domainMemoryIndex>`. Missing config → skip enrichment; `commitScope` defaults to `<board>` and research falls back to a scoped repo search.
7. **Load MCP tools:** `ToolSearch("select:<jira.mcpPrefix>createJiraIssue,<jira.mcpPrefix>getTransitionsForJiraIssue,<jira.mcpPrefix>transitionJiraIssue")`.

## Step 1 — Capture the finding

1. Collect from the user this turn: the description, an optional `type`, and screenshot path(s).
2. **Copy-on-receipt (FIRST action for any screenshot path).** macOS screenshot temp files are purged fast and their names use a narrow no-break space (`U+202F`) before AM/PM — so **glob, never exact-name**:
   ```bash
   FILE=$(find "<dir-of-the-given-path>" -maxdepth 1 -type f -iname '<prefix>*.png' | head -1)
   cp "$FILE" "<scratchpad>/cj-shot-NN.png"
   ```
   Then `Read` the staged copy to triage it (or delegate this to the Step 2 subagent to keep image tokens out of your context).
3. Ask a clarifying question ONLY if the ticket would otherwise be ambiguous. Default to proceeding.

## Step 2 — Research root cause (subagent)

For a code-related finding, spawn ONE subagent (Agent tool, `Explore` or `general-purpose`) scoped to `app` + `libraries` from Step 0. Prompt it to return **only**: the root cause, the `file:line` anchors (handler + template + spec), and a one-line suggested fix. Do the grep/read there, not in the main context. Skip for non-code findings (copy, content, pure-visual) or research inline if trivial.

## Step 3 — Create the ticket (born-split)

1. **Type:** use the given `type`, else infer — broken / regressed / wrong-behavior → **Bug**; polish / copy / small enhancement / standards-alignment → **Task**; needs real acceptance criteria / multi-part → **Story**. State the chosen type.
2. **Mint the KEY** — `createJiraIssue(cloudId, projectKey, issueTypeName=<Bug|Task|Story>, parent=<epicKey>, summary=<concise, <80 chars>, description="See <plans.repo>/<board>/<KEY>.md")`. Read `key` from the response.
3. **Write** `<plansDir>/<KEY>.md` using the matching template below (front matter `jira/project/board/type/epic/summary` + body).
4. **Assets** — for each staged screenshot: `mkdir -p <plansDir>/assets/<KEY>` then `cp` it to `<plansDir>/assets/<KEY>/NN-<slug>.png`, and embed in the md with a **relative** link: `![<alt>](assets/<KEY>/NN-<slug>.png)`.
5. **Epic index — REQUIRED, never skipped.** Add `- <KEY> — <summary> · <Type>` to `<plansDir>/<epicKey>.md`:
   - **Wave-plan epic** (a `## Wave plan` section with `### Wave N` subheads — the common shape): append the one-liner to the wave the finding belongs to, or open the next `### Wave <N> — <theme>` if none fits. One line only; scope lives in the child ticket.
   - **Findings/index epic:** append under the right area subheader (create it if absent).
   - **Neither shape:** add a `## Wave plan` section with a first wave and put it there.

   A ticket that exists outside its epic's plan is drift — the Jira parent link alone is not enough, because every `/epic-*` skill reads the wave plan for ordering. This step used to be conditional and silently skipped on wave-plan epics; it is now unconditional.
6. **Transition** — `getTransitionsForJiraIssue(cloudId, KEY)`; pick the transition whose target status name is `<jira.createStatus>` and apply it (`transitionJiraIssue`). Never guess the id — it varies by project. ⚠️ Projects create in **`Backlog`** by default, so a skipped or failed transition leaves the ticket invisible to `/giga-workflow:epic-next`'s JQL. If there's no `<jira.createStatus>` transition, say so loudly in the report rather than leaving it as a footnote.
7. **Stub** — `python3 <plans.script> stub <KEY>`.
8. **Commit (plans repo — commit only, do NOT push: when `plans.autoPush` is true the repo auto-commits + auto-pushes itself, so never report it as unpushed; otherwise report it as unpushed):**
   ```bash
   cd <plans.repo> && git add <board>/<KEY>.md <board>/assets/<KEY> <board>/<epicKey>.md && \
   git commit -m "docs(<board>): <KEY> <short summary>"   # + the session's standard co-author trailer
   ```
9. **Desktop cleanup** — for any screenshot that came from `~/Desktop`, delete the original ONLY after a byte-verify against the committed asset:
   ```bash
   cmp -s "<desktop-original>" "<plansDir>/assets/<KEY>/NN-<slug>.png" && rm "<desktop-original>"
   ```
   Locate the original by glob (U+202F-safe). Never delete on a mismatch.

## Step 4 — Report, then clear

Print one compact block and nothing else verbose:

```
<KEY> · <type> · <jira.createStatus> · under <epicKey>
<summary>
root cause: <file:line> — <one line>
files: <board>/<KEY>.md · assets/<KEY>/NN-*.png
https://<jira.site>/browse/<KEY>
```

Then remind: `/clear` and run the next `/giga-workflow:create-jira <board> <epic>`.

---

## Content templates

### Bug — `<plansDir>/<KEY>.md`

```markdown
---
jira: <KEY>
project: <PROJECT>
board: <board>
type: bug
epic: <epicKey>
summary: "<summary>"
---

# <KEY> — <summary>

**Type:** Bug · **Epic:** <epicKey> · **Area:** <area> · **Viewport:** <mobile|desktop|both>

## Steps to reproduce
1. …

## Expected
…

## Actual
…

## Root cause
- `path/to/file.ts:LINE` — <what's wrong>

## Suggested fix
- <one or two lines>

## Evidence
![<alt>](assets/<KEY>/01-<slug>.png)

## Acceptance
- <verifiable outcome>
- `<domain>-*` lint + test green.
```

### Task / Story — `<plansDir>/<KEY>.md`

```markdown
---
jira: <KEY>
project: <PROJECT>
board: <board>
type: <task|story>
epic: <epicKey>
summary: "<summary>"
---

# <KEY> — <summary>

**Type:** <Task|Story> · **Epic:** <epicKey> · **Area:** <area> · **Viewport:** <mobile|desktop|both>

## Goal
<what should change and why>

## Scope
- `path/to/file` — <change>

## Evidence
![<alt>](assets/<KEY>/01-<slug>.png)

## Acceptance
- <criterion>
- `<domain>-*` lint + test green.
```

## Error handling

- Epic not found / not an Epic → stop, report (wrong board or number).
- No screenshot supplied → omit the Evidence section (don't fabricate one).
- `createJiraIssue` custom-field error → retry with a minimal payload; if it persists, report and leave no orphan file.
- Transition step fails → the ticket exists but is stranded in `Backlog`, where `/giga-workflow:epic-next` will never pick it up. Continue, but report it as a **warning line**, not a footnote: `⚠ <KEY> is still Backlog — transition it to <jira.createStatus>`.
- This skill never pushes and never touches app code.
