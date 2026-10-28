---
name: epic-review
description: "Review a finished epic against the whole app: does what it shipped fit the app's navigation, names, patterns and voice, is it being used, and what should be cut, fixed or added next. Runs a whole-app UX review, a red team and a usage read in parallel, writes their ideas (add / cut / fix) to the Idea Board for the owner to decide, and records the review in the epic's plan file. Creates no stories and edits no code. Use after an epic's last story ships (the epic-close blocks name it), before `/giga-workflow:epic-plan` on that board's next epic, or when the user says \"review the epic\", \"does this epic fit the app\" or \"epic retro\": $ARGUMENTS"
---

# Epic review

**Usage:** `/giga-workflow:epic-review <EPIC-KEY>`

Each story in an epic was reviewed on its own. This review asks what only the finished whole shows: whether the features fit the app, whether the stories drifted apart, whether anyone uses what shipped, and what the app would be better without. It fixes nothing and creates no stories; everything it finds reaches the owner through the Idea Board. Rules: the ideas policy (`ideas.policy`).

## Project config

Repo-specific values come from `.claude/giga/config.json` at the repository root, under `workflow` (plus the top-level `ideas` and `ux` keys that every plugin shares). Read it once at the start. A missing file or field takes the fallback below, never a guess.

| Field | Used for | When absent |
| --- | --- | --- |
| `plans.script` | `ensure` and `board` calls for the epic, its children and open tickets | stop and say the repo has no `plans.script` in `.claude/giga/config.json` |
| `plans.repo` | the plans repo whose `<board>/*.md` files Step 4 greps | skip that grep; match against open tickets and the Idea Board only |
| `plans.autoPush` | whether the plans repo commits and pushes itself | commit and push the plans repo's change after Step 5 |
| `ideas.policy` (top level) | the § Entry threshold and § Check for a match first every entry passes | check open tickets for a match; keep only entries with observed evidence |
| `ideas.board` (top level) | the Idea Board the entries are written to (Steps 2, 4, 5, 6) | no board: skip Step 2 and the `ArtifactData` writes; findings and ideas stay in the report and the plan file for the owner |
| `docs.usage[]` | where the shipped features' events and the usage read are documented (Step 3) | find events from the code alone |
| `ux.devServerSkill` (top level) | the skill that runs the app for the UX lens | use the URL the dispatcher gave; with none, the app cannot be run |
| `epicCloseSkill` | the epic-close block that names the next epic (Step 6) | write `/giga-workflow:epic-plan <next epic>` |
| `ux.brandVoice.guides[]` (top level) | the voice guide handed to the UX lens | pass `none yet` |

## Step 1 — Resolve the epic

In one message:

```bash
epicPath=$(python3 <plans.script> ensure <EPIC-KEY>)
python3 <plans.script> board --jql 'key = <EPIC-KEY> OR parent = <EPIC-KEY>'
```

Read `$epicPath` (its Shipped ledger says what each story delivered). Find the board whose `epicKey` is this epic among `.claude/giga/epic.*.json` and read its app and libraries. When none matches (the board has since been repointed), use a board whose `epicKey` has the same key prefix: a domain's boards share their app and libraries.

- **Epic not Done:** say so and ask whether to review it in flight. A review of an open epic is labelled `in flight` in Step 5.
- **The plan file already has `## Epic review`:** ask whether to run it again; a re-run appends a dated section.

## Step 2 — Sweep ideas left in story plan files

A story that could not reach the Idea Board left its ideas in its plan file under `## Ideas for the Idea Board`. For each child, `ensure` its plan file and look for that heading. Load `ArtifactData` (`ToolSearch` `select:ArtifactData`) and post every entry found in one `batch` to the `ideas` collection, keeping its recorded `source`. Skip an id the board already holds. Also `query` the board for this board's entries of every status (Step 3 needs the `declined` ones, Step 4 all of them) and list the board's open tickets: `python3 <plans.script> board --jql 'project = <KEY> AND statusCategory != Done'`.

## Step 3 — Three lenses, in parallel

Load the dev-server skill (`ux.devServerSkill`) and make sure the app is running; never stop a server you did not start. Then spawn all three in one message:

- **Whole-app UX** — one `giga-ux:ux-reviewer` agent: *"Run `giga-ux:ux-design` § Epic review on `<app>` at `localhost:<port>` (already running — do not start another). The epic shipped: `<Shipped one-liners>`. Brand voice guide: `<the app's guide from ux.brandVoice.guides, or none yet>`."*
- **Red team** — one read-only `general-purpose` agent (`model: sonnet`): argue against what shipped. What overlaps with something the app already had, what grew the navigation without earning it, what a user would not miss? Give it the Shipped one-liners, the app's routes and nav components, and the declined ideas with their reasons. Return the cuts, fixes or adds that have observed evidence, most severe first, or "no cuts, no adds — the epic covers its goal".
- **Usage** — one read-only `general-purpose` agent (`model: sonnet`): for each shipped feature, find the events and routes that show whether it is used (the `docs.usage` docs and the code), then read what exists so far through the analytics sources those docs name, and the board's event table (`usage.bigQueryTable` in its board config) when it has one. Report numbers with their source and date range, or `too early — watch <events>`. Usage that shows a feature unused is a `cut` candidate, not a reason to add.

## Step 4 — Merge, rank, write

- The stopping test is the only gate; rank the entries across all three lenses by severity, most severe first, and say so in the report with a one-line reason when more than a handful survive. "No cuts, no adds — the epic covers its goal" is a valid result.
- Drop anything that fails the ideas policy's § Entry threshold, and anything repeating a declined idea unless new evidence answers its decline reason.
- Drop anything an open ticket or an Idea Board entry of any status already names (§ Check for a match first; also grep `<plans.repo>/<board>/*.md`). Record "covered by <key or id>" in the report and the epic's plan file, with any evidence the match lacks; never edit the match.
- UX findings of severity 3–4 in what shipped become `fix` entries and lead the report, so the owner sees them first. The rest, cosmetic included, are batched into one polish `fix` per section or page, never one entry per finding.
- Story-order and gating notes go to the epic's plan file (Step 5), never the board.
- Write every survivor in one `batch`: `status: "proposed"`, `source: "epic-review"`, this epic's key.

## Step 5 — Record it in the epic's plan file

Append to `$epicPath`, one line per item:

```markdown
## Epic review — <YYYY-MM-DD> <(in flight)>

- Fit: <the whole-app verdict in one line>
- Drift: <names, patterns or voice that diverged, or "none found">
- Usage: <numbers with source and range, or "too early">
- Watch: <events / routes that will show use, and where to read them>
- Ideas posted: add <n> · cut <n> · fix <n> — <ideas.board>
```

When `plans.autoPush` is true the plans repo commits and pushes itself; never push it by hand.

## Step 6 — Report

```
Epic review — <EPIC-KEY> <summary>
  Fit:    <one line>
  Usage:  <one line>
  Ideas:  add <n> · cut <n> · fix <n> → <ideas.board>
  Next:   decide them on the Idea Board, then /giga-workflow:epic-plan <NEXT-KEY>
```

`<NEXT-KEY>` comes from the epic-close block (the `epicCloseSkill` hand-off) when it is in this conversation; otherwise write `/giga-workflow:epic-plan <next epic>`.

## What this skill never does

Edit code, delete, remove, rewrite or refactor anything in the app, create or transition a Jira issue, change an Idea Board entry's `status`, or turn an idea into a story. Every cut, fix and add it finds is a recommendation. Those belong to the owner, and to `/giga-workflow:epic-plan` once the owner adopts.
