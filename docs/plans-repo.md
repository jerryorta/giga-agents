# The plans repo

`giga-workflow` keeps each ticket's content in a git repo of Markdown files, one file per ticket. Jira keeps status, transitions and comments, through the Atlassian MCP. The skills reach the files through a script the repo names in its config.

This page is the contract between the skills and that script: every command they call, its arguments and its output, and the file shape they read and write. It is taken from what the skills do, so you can write your own script.

## Config

The keys sit under `workflow` in `.claude/giga/config.json`.

| Field | What it is | When absent |
| --- | --- | --- |
| `plans.repo` | the plans repo's checkout | most skills stop and say so; a few skip the steps that need it |
| `plans.script` | the script | most skills stop and say so; a few skip the steps that need it |
| `plans.guide` | an optional guide in the plans repo, which the skills point to for its rules | the skills follow their own steps |
| `plans.autoPush` | `true` when the plans repo commits and pushes itself (a hook or a timer) | the skills push right after each plans-repo commit |
| `jira.credentialsFile` | the file the script authenticates from | the script's own default |

One push rule holds for every skill that commits the plans repo. With `plans.autoPush` true the repo pushes itself, so the skill commits and never pushes, and never reports the commit as unpushed. With it false or absent, the skill pushes right after its commit.

The skills never pass credentials to the script; it authenticates itself. `/giga-workflow:create-jira` also reads `cloudId` from `jira.credentialsFile` when `jira.cloudId` is absent, so that file is a JSON object with a `cloudId` key.

Some skills cite the guide by section number: §2 is the hybrid read (content from the file; status, comments and labels from Jira), §4 is the rule that content lives in the file and Jira's description is a stub, §5 is creating a ticket born split. Number a guide you write the same way, or leave `plans.guide` out.

## Layout

```
<plans.repo>/
  abc/                                  one folder per board
    ABC-100.md                          the epic
    ABC-124.md                          a story under it
    assets/ABC-124/01-empty-state.png   a screenshot for ABC-124
```

- **One file per ticket:** `<board>/<KEY>.md`, where the board is the lowercased key prefix. `ABC-124` lives at `abc/ABC-124.md`. Some skills open this path directly instead of asking the script.
- **Board folders sit at the root.** `/giga-workflow:create-jira` offers the root's folders as the list of boards.
- **Screenshots** go in `<board>/assets/<KEY>/NN-<slug>.png` and are linked relatively from the plan file: `![Empty inbox](assets/ABC-124/01-empty-state.png)`.
- **It is a git repo.** Skills stage by path (`git add <board>/…`) and commit with `docs(<board>): <KEY> …` subjects. `/giga-workflow:jira` dates a description by its file's last commit, and treats a history of one commit as the migration, not the writing.
- **Content here, status in Jira.** No skill writes a description to Jira.

## The script

Every call is `python3 <plans.script> <command> …`, so the script must run under `python3`. `ensure`, `section` and `stub` take one key per call. stdout carries only the result, because the skills capture it with `$(…)` or parse it as JSON. Messages go to stderr. Any failure exits non-zero.

### `ensure <KEY>`

Makes sure the ticket's plan file exists and prints its path.

| | |
| --- | --- |
| stdout | one line: the full path of `<plans.repo>/<board>/<KEY>.md` |
| file missing | create it from the Jira description, with the front matter below, then print the path |
| file present | print the path and change nothing |
| failure | non-zero exit, the error on stderr, nothing on stdout |

Never overwrite an existing file. Once the ticket is stubbed, the file is the only copy of its content.

```bash
plan=$(python3 <plans.script> ensure ABC-124)          # then Read or Edit "$plan"
grep -m1 '^effort:' "$(python3 <plans.script> ensure ABC-124)"
```

Called by every skill that reads a ticket's content: `/giga-workflow:epic-next`, `/giga-workflow:epic-plan`, `/giga-workflow:jira`, `/giga-workflow:epic-evolution-audit`, `/giga-workflow:epic-merge-pr` and `/giga-workflow:epic-review`.

### `board --jql '<jql>'`

Lists the issues a JQL query matches, with live status from Jira.

stdout is one JSON array, one row per issue:

```json
[
  { "key": "ABC-124", "status": "To Do", "category": "To Do", "type": "Story",
    "priority": "Medium", "parent": "ABC-100", "summary": "Show the empty state on the inbox" }
]
```

| Field | Value | What the skills do with it |
| --- | --- | --- |
| `key` | the issue key | pick, list and match stories |
| `status` | the status name | show it; check a blocker or an old epic is Done |
| `category` | the status category: `To Do`, `In Progress` or `Done` | count done children with `category == "Done"` |
| `type` | the issue type name: `Epic`, `Story`, `Bug`, `Task`, … | `/giga-workflow:create-jira` checks the epic is one row of type `Epic` |
| `priority` | the priority name | the group label on a board ordered by `jql` |
| `parent` | the parent issue's key | find the epic a blocking story belongs to |
| `summary` | the title | show it |

- **Live.** Read from Jira on every call, never from a cache.
- **Every match, in the query's order.** The script pages through the results itself. A board with `storyOrdering: "jql"` takes the first row.
- **`[]` should mean the query ran and matched nothing.** The skills close an epic on `[]`, so a failed login or network call should exit non-zero rather than print `[]`. `/giga-workflow:epic-loop` checks `key = <epicKey>` returns a row before it calls a board empty, because an expired token can answer with no rows.

The skills single-quote the query, since JQL holds double quotes. These are the shapes they send, so a script for another tracker must answer each one:

| JQL | Sent by |
| --- | --- |
| the board config's `jql`, e.g. `parent = ABC-100 AND status = "To Do"` | `/giga-workflow:epic-next`, `/giga-workflow:epic-loop`, `/giga-workflow:epic-merge-pr` |
| `key = ABC-124` | most skills: one issue's status, or that an epic exists |
| `key in (ABC-124, DEF-310)` | `/giga-workflow:epic-next`, `/giga-workflow:epic-loop`, `/giga-workflow:epic-evolution-audit` |
| `parent = ABC-100` | an epic's children and story progress (`/giga-workflow:epic-next`, `/giga-workflow:epic-loop`, `/giga-workflow:epic-story-complete`) |
| `parent = ABC-100 ORDER BY created ASC` | an epic's children (`/giga-workflow:epic-plan`) and a story's sub-tasks (`/giga-workflow:jira`) |
| `parent = ABC-100 AND statusCategory != Done` | whether an epic has open children left |
| `parent = ABC-100 AND key != ABC-124 AND status != Done` | `/giga-workflow:epic-evolution-audit`'s siblings |
| `key = ABC-100 OR parent = ABC-100` | an epic and its children (`/giga-workflow:epic-plan`, `/giga-workflow:epic-review`) |
| `project = ABC AND statusCategory != Done` | a board's open tickets (`/giga-workflow:epic-plan`, `/giga-workflow:epic-review`) |

### `section <KEY> <heading> [--range]`

Prints part of a plan file, so a skill can edit a long epic without reading it whole.

- **Matching.** Every `## ` heading whose text starts with `<heading>`, ignoring case. A section runs from its heading to the line before the next `## ` heading, or to the end of the file, so its `### ` subsections come with it. `Wave` matches `## Wave Plan`, `## Wave plan`, `## Waves` and `## Wave order`. `Shipped` matches `## Shipped`.
- **Without `--range`.** stdout: the text of each matching section. stderr: the file's path and each section's line range. The skills read these by eye, so any clear format works; `<path>:<start>-<end>` is one.
- **With `--range`.** stdout: one line per matching section, `<path> <start> <end>`, and no text.
- **Line numbers** start at 1 and include both ends. The skills pass them to `sed -n '<start>,<end>p'` and to a ranged Read (`offset`/`limit`) before an Edit.
- **Exit 1** means the file was read and no heading matched, such as an epic with no wave plan or no `## Shipped` yet. stderr still names the file's path, because `/giga-workflow:epic-next` then reads the whole file. Use exit 1 for nothing else.

```bash
python3 <plans.script> section ABC-100 Wave
python3 <plans.script> section ABC-100 Shipped --range   # prints <path> 88 97
```

Called by `/giga-workflow:epic-next` (`Wave`), `/giga-workflow:epic-story-complete` (`Wave`) and `/giga-workflow:post-merge-cleanup` (`Wave`, then `Shipped --range`).

### `stub <KEY>`

Replaces the Jira description with a one-line summary and a link to the plan file.

- **Destructive.** Whatever the description held is gone. Run it only once the file holds the content.
- **Writes to Jira**, so the script's credentials need write access (the `write:jira-work` scope).
- **stdout is ignored.** A failure exits non-zero: skills chain several stubs as `… stub ABC-124 && … stub ABC-125`.

Called by `/giga-workflow:create-jira`, `/giga-workflow:epic-plan` (each new story, and the epic after a wave plan if you ask), `/giga-workflow:epic-story-complete` (each follow-up story) and `/giga-workflow:epic-story-ship`. `/giga-workflow:epic-evolution-audit` names it as a step for you and never runs it.

## The plan file

### Front matter

A YAML block between `---` lines at the top of the file. Each key is one top-level `key: value` line, because the skills read keys with `grep -m1 '^<key>:'`.

```markdown
---
jira: ABC-124
project: ABC
board: abc
type: story
epic: ABC-100
summary: "Show the empty state on the inbox"
effort: high
model: sonnet
crossActor: false
blocked_by: [DEF-310]
loop: manual
---

# ABC-124 — Show the empty state on the inbox

## Goal
…

## Acceptance
- …
```

Every plan file has these (an epic's own file has no `epic`), and a file `ensure` creates has them too:

| Key | Value |
| --- | --- |
| `jira:` | the ticket's key |
| `project:` | the Jira project key |
| `board:` | the board folder |
| `type:` | the issue type; `/giga-workflow:create-jira` writes `bug`, `task` or `story` |
| `epic:` | the parent epic's key, on a child only; the epic's own file has none. `/giga-workflow:post-merge-cleanup` finds a story's epic with `grep -m1 '^epic:'` |
| `summary:` | the title, quoted. `/giga-workflow:epic-plan` reads an epic's summary here to name its branch |

These are optional. The owner sets them by hand. `/giga-workflow:epic-plan` may also set `model` and `crossActor` on a story it cuts, and writes `blocked_by` on an epic or a story that waits on another epic:

| Key | Read by | Value |
| --- | --- | --- |
| `effort:` | `/giga-workflow:epic-next`, `/giga-workflow:epic-merge-pr` | the `/effort` level recommended for the story; the skills report it and never apply it |
| `model:` | `/giga-workflow:epic-loop` | `sonnet`, `opus` or `haiku` for the story's agent; beats `--model` and `loop.storyModel` |
| `crossActor:` | `/giga-workflow:epic-loop` | `false`, `true`, or a scenario string; on a board with `hybridMode: "conditional"` it decides whether the story needs a cross-actor test, and the triage agent reports it instead of judging |
| `blocked_by:` | `/giga-workflow:epic-next`, `/giga-workflow:epic-loop` | `[<KEY>, …]` on the epic when the whole epic waits, or on a story when only it waits; the work waits until each key is Done |
| `loop:` | `/giga-workflow:epic-loop` | `manual`: the run stops before this story, and the owner runs it by hand |

### Body headings

The rest of the body is free Markdown. These are the headings the skills find by name:

| Heading | File | Written by | Read by |
| --- | --- | --- | --- |
| `## Wave Plan` | epic | `/giga-workflow:epic-plan`; new stories by `/giga-workflow:create-jira` and `/giga-workflow:epic-story-complete` | `/giga-workflow:epic-next`, `/giga-workflow:epic-loop`, `/giga-workflow:epic-merge-pr`; `/giga-workflow:post-merge-cleanup` removes a merged story's line |
| `### Wave <N> — <theme>` | epic, under the wave plan | as above | as above: the wave order is the story order |
| `### Wave 0 — Blocked by <KEY> (redirect)` | epic, first wave | `/giga-workflow:epic-plan` | `/giga-workflow:epic-plan`, which keeps it verbatim |
| `## Shipped` | epic | `/giga-workflow:post-merge-cleanup`; `/giga-workflow:epic-story-complete` on an epic-branch board | `/giga-workflow:epic-review`; `/giga-workflow:post-merge-cleanup` checks it before appending, so a line lands once |
| `## UX decisions for the owner` | story, and one list on the epic | `/giga-workflow:jira` in an unattended run | the owner |
| `## Epic review — <YYYY-MM-DD>` | epic | `/giga-workflow:epic-review` | `/giga-workflow:epic-review` on a re-run; `/giga-workflow:epic-plan` before the next epic |
| `## Refactor (in place)` | story | `/giga-workflow:jira` | `/giga-workflow:epic-story-complete`, which commits the listed files first |
| `## Ideas for the Idea Board` | story | `/giga-workflow:jira` and a `/giga-workflow:epic-loop` story agent, for an idea that meets the entry threshold but cannot be written to the board (no `ideas.board`, or no `ArtifactData` in that context); a note that fails the threshold never goes here | `/giga-workflow:epic-review`, which posts them |
| `## Outcome — shipped (PR #<N>)`, with a `### Pinned` list | story | `/giga-workflow:epic-story-complete` | `/giga-workflow:epic-story-complete`, which adds to it on a re-run |

Write the wave plan as `## Wave Plan`. `section` also matches `## Wave plan`, `## Waves` and `## Wave order`, but `/giga-workflow:epic-plan` and `/giga-workflow:epic-merge-pr` look for `## Wave Plan` by name.

Entries are one line each, and the skills find a story's line by its key:

- **Wave plan:** `- ABC-124 — Show the empty state on the inbox · Story`. Scope stays in the story's own file.
- **Shipped:** `- ABC-124 — <what shipped, past tense> *(Wave 2; PR #57)*`. On a board with no pull requests a short commit SHA takes the PR's place, and a story that only changed the skills repo gets `<repo name> <short-sha>`. With no wave plan, `Wave <N>; ` is dropped. A `## Shipped` kept as a table gets the same content in its own columns.
- **Outcome:** the heading names a commit instead of a PR on a board with no pull requests: `## Outcome — shipped (<short-sha>)`.

## Creating a ticket (born split)

A new ticket is born split: its content goes in the file, and Jira gets only status and a stub. `/giga-workflow:create-jira`, `/giga-workflow:epic-plan` and `/giga-workflow:epic-story-complete` create tickets this way:

1. **Mint the key.** Create the issue in Jira with its summary, type and parent epic. Read the key back.
2. **Write `<board>/<KEY>.md`** with the front matter and the body. Copy any screenshots to `<board>/assets/<KEY>/`.
3. **Add its line to the epic's wave plan.** Open a new `### Wave <N> — <theme>` when it fits no wave.
4. **Move it to `jira.createStatus`** (`To Do` when absent), matching the transition by name. Jira may create an issue in Backlog, where the board's `status = "<jira.createStatus>"` query never finds it.
5. **Stub it:** `python3 <plans.script> stub <KEY>`. Steps 4 and 5 can run in either order.
6. **Commit the plans repo:** `docs(<board>): <KEY> …`.

Do all of it or none of it. A key minted without its file fails silently: the next `ensure` fills the file from whatever Jira's description holds.

After the stub, the file is the only copy. Edit content in the file, never in Jira's description. Never delete a stubbed ticket's file to fetch it again: `ensure` would bring back the stub.

## Writing your own

A script meets this contract when:

- [ ] It runs as `python3 <script> <command> …` and authenticates itself. It takes no credentials as arguments.
- [ ] Every command prints only its result on stdout, writes messages to stderr, and exits non-zero on failure.
- [ ] `ensure` prints one line, the plan file's full path. It creates a missing file with the six required front-matter keys and never overwrites an existing one ([`ensure`](#ensure-key)).
- [ ] `board` prints one JSON array with the seven fields, live, every match, in the query's order. It should print `[]` only when the query ran and matched nothing, and it answers every JQL shape in the table ([`board`](#board---jql-jql)).
- [ ] `section` matches `## ` headings by prefix, ignoring case, and includes their subsections. It reports 1-based, inclusive line ranges, prints `<path> <start> <end>` with `--range`, and exits 1 only when nothing matched, still naming the path on stderr ([`section`](#section-key-heading---range)).
- [ ] `stub` replaces the Jira description with a summary and a link to the file, and exits non-zero on failure ([`stub`](#stub-key)). It should refuse a key whose file does not exist.
- [ ] The plans repo is a git repo with board folders at its root and one `<board>/<KEY>.md` per ticket, in the shape under [The plan file](#the-plan-file).

Then set `plans.repo` and `plans.script` in `.claude/giga/config.json`. Set `plans.autoPush` to `true` only when the repo pushes its own commits.
