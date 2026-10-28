---
name: epic-config
description: "View or update an `/giga-workflow:epic-next` board config (`epic.<board>.json`)."
---

View or update an `/giga-workflow:epic-next` board config (`epic.<board>.json`).

**Usage:**
- `/giga-workflow:epic-config <board>` — view and edit by board name (e.g., `web`, `api`)
- `/giga-workflow:epic-config <EPIC-KEY>` — resolve board from epic key (e.g., `ABC-107`, `DEF-98`)
- `/giga-workflow:epic-config` (no argument) — list all available boards

## Project config

Repo-specific values come from `.claude/giga/config.json` at the repository root, under `workflow`. Read it once at the start. A missing file or field takes the fallback below, never a guess.

| Field | Used for | When absent |
| --- | --- | --- |
| `jira.mcpPrefix` | the prefix of the Atlassian MCP tool ids Step 8 loads and calls | skip Step 8 and say the repo has no `jira.mcpPrefix` in `.claude/giga/config.json` |
| `jira.cloudId` | the Jira site Step 8's calls address | look it up with `getAccessibleAtlassianResources` |

---

## Step 1 — Resolve board name

Read `$ARGUMENTS`.

**No argument:** Read all files matching `.claude/giga/epic.*.json`. List each board name and its `epicKey` and `name` fields:

```
Available boards:
  <board>  <epicKey>  <name>
  <board>  <epicKey>  <name>
```

Then stop — no further steps.

**Epic key argument** (matches `[A-Z]+-\d+`, e.g. `ABC-107`): Extract the key prefix (letters before the first `-`). Scan all `epic.*.json` files, match by `epicKey` prefix. The board name is the `*` portion of the filename. If no match, report: "No epic config found for prefix `<PREFIX>`. Available boards: <list>." and stop.

**Board name argument** (e.g. `web`, `api`): Use directly. Construct path `.claude/giga/epic.<board>.json`. If the file does not exist, report it and list available boards, then stop.

Save: `boardName`, `configPath`.

## Step 2 — Read and display the current config

Read `configPath`. Display the current config in a human-readable table:

```
Config: epic.<board>.json
─────────────────────────────────────────────────────
name              <value>
epicKey           <value>
jql               <value>
storyOrdering     <value>
groupLabel        <value>
completionMessage <value>
commitScope       <value>
buildCommand      <value or "(none)">
app               <value>
libraries.ui      <value>
libraries.store   <value or "(none)">
libraries.designLibrary  <value or "(none)">
routingFiles      <count> file(s)
conventions       <count> item(s)
designReferences  <"(none)" or summary of keys>
epicEvolutionRules <count> board addenda, or "(canonical only)" when [] / "(opted out)" when null
─────────────────────────────────────────────────────
```

> **Legacy fields silently ignored:** `mode`, `phaseNote`. Drop them on the next edit; do not display. `mergeMode` is `"pr"` (the default when absent), `"epic-branch"` or `"direct"`. `epicBranch` is live only on a `mergeMode: "epic-branch"` board, where it is the integration branch.

For `routingFiles` and `conventions`, if the count > 0, list the values indented below the row.
For `designReferences`, if set, list each key and its value indented below.

## Step 3 — Ask what to update

After displaying the config, ask the user:

> "Which fields would you like to update? Describe the changes (e.g. 'add a convention', 'change the JQL', 'update the buildCommand', 'set commitScope to web')."

If the user says nothing to change / "looks good" / "no changes": confirm the config is correct and stop.

## Step 4 — Apply changes

Parse the user's request and update the in-memory config object accordingly. Common patterns:

| Request | Action |
|---------|--------|
| `set <field> to <value>` | Replace the field value |
| `clear <field>` / `set <field> to null` | Set to `null` |
| `add convention: <text>` | Append to `conventions` array |
| `remove convention: <text>` | Remove matching entry from `conventions` array |
| `add routing file: <path>` | Append to `routingFiles` array |
| `remove routing file: <path>` | Remove matching entry from `routingFiles` array |
| `set libraries.store to <path>` | Update nested `libraries.store` |
| `set designReferences.<key> to <value>` | Update or create key in `designReferences` object |
| `clear designReferences` | Set `designReferences` to `null` |

If any request is ambiguous, ask for clarification before writing.

## Step 5 — Show diff and confirm

Display the proposed changes as a before/after diff of only the modified fields:

```
Proposed changes to epic.<board>.json:
  buildCommand: null → "npm run build:web"
  commitScope:  "web" → "web-backend"
```

Ask: "Apply these changes?"

If the user says no or requests further adjustments, return to Step 3.

## Step 6 — Write the updated config

Write the full updated JSON back to `configPath`. Preserve field ordering from the original file. Use 2-space indentation.

## Step 7 — Commit

```
git add .claude/giga/epic.<board>.json
git commit -m "chore(skills): update epic.<board>.json config"
```

## Step 8 — Put the board's epic In Progress

The epic a board points at is the one being worked, so its Jira status says so. Run this whenever `epicKey` is set
or changed (a repoint); skip it for edits that leave `epicKey` alone.

1. Load the tools in one `ToolSearch`:
   `select:<jira.mcpPrefix>getTransitionsForJiraIssue,<jira.mcpPrefix>transitionJiraIssue`
   (`jira.cloudId`, else `cloudId` via `getAccessibleAtlassianResources` if the session has none).
2. Read the epic's transitions and match **In Progress** by name — never guess the id. Skip if it is already
   In Progress; leave a Done epic alone and say so (a board pointed at a finished epic is a config mistake).
3. The previous `epicKey` is not touched here: `/giga-workflow:post-merge-cleanup` closes an epic once its last story is Done.

On an MCP error, report it and continue — the config change already landed.

Report: "Done — `epic.<board>.json` updated and committed; <EPIC-KEY> → In Progress (or "already In Progress" / "unchanged epicKey")."
