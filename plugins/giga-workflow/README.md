# giga-workflow

A Jira epic workflow in 15 skills. Plan an epic into waves, take one story at a time from ticket to merged pull request, or run a whole board unattended. [The epic workflow](../../docs/workflow.md) walks an epic through these skills in the order you type them. This page says what the plugin needs and when to use each skill.

## What it needs

- **Jira**, through the Atlassian MCP connector, for status: transitions, comments and new issues.
- **A plans repo**: a git repo of Markdown files, one per ticket, and a script the skills call to read and write them. Jira keeps status; the plans repo keeps content. The contract is in [The plans repo](../../docs/plans-repo.md).
- **GitHub and the `gh` CLI** on a `pr` board, which opens and merges a pull request per story. On an `epic-branch` board you open the epic's one pull request yourself, and a `direct` board opens none.
- **`giga-ux`**, optional. It runs the UX frame and UX review in `/giga-workflow:jira` and the whole-app UX review in `/giga-workflow:epic-review`. Without it, `/giga-workflow:jira` skips its UX phases.

## With an empty config

The skills read their values from `workflow` in `.claude/giga/config.json`. Each `SKILL.md` has a `## Project config` table that lists the fields it reads and what it does without each.

Without `plans.repo` and `plans.script`, most skills stop and say so, and a few skip only the steps that need them; see [The plans repo § Config](../../docs/plans-repo.md#config). `/giga-workflow:clean-exit`, `/giga-workflow:dev-server`, `/giga-workflow:epic-config` and `/giga-workflow:epic-cross-actor-test` never read the plans repo.

## Skills

The epic path comes first, in the order an epic runs. **Started by** says whether you type the skill or another skill runs it. Four skills are both: the ship step runs them, and you type `/giga-workflow:epic-evolution-audit`, `/giga-workflow:epic-story-complete` and `/giga-workflow:epic-merge-pr` when someone must review the PR first, and `/giga-workflow:post-merge-cleanup` to close an `epic-branch` epic.

| Skill | Use it to | Started by |
| --- | --- | --- |
| [`/giga-workflow:epic-plan`](skills/epic-plan/SKILL.md) | plan an epic into waves, create its stories and point its board at it, once per epic | you |
| [`/giga-workflow:epic-next`](skills/epic-next/SKILL.md) | pick the board's next story and cut its branch, once per story, in a new session | you |
| [`/giga-workflow:jira`](skills/jira/SKILL.md) | plan, build and gate one story, and leave the diff unstaged | `/giga-workflow:epic-next` |
| [`/giga-workflow:epic-story-ship`](skills/epic-story-ship/SKILL.md) | take a reviewed story to main and Done behind one gate | you |
| [`/giga-workflow:epic-evolution-audit`](skills/epic-evolution-audit/SKILL.md) | check the epic's other open stories against what shipped | `/giga-workflow:epic-story-ship`; you, before `/giga-workflow:epic-story-complete`, when the story settled something its siblings depend on |
| [`/giga-workflow:epic-story-complete`](skills/epic-story-complete/SKILL.md) | commit and push the story; on a `pr` board, open its PR and move the ticket to In Review | `/giga-workflow:epic-story-ship`, or `/giga-workflow:epic-next` when you let it carry on; you, when someone must review the PR first |
| [`/giga-workflow:epic-merge-pr`](skills/epic-merge-pr/SKILL.md) | merge a reviewed story PR, then clean up | `/giga-workflow:epic-story-ship`; you, once the PR is reviewed |
| [`/giga-workflow:post-merge-cleanup`](skills/post-merge-cleanup/SKILL.md) | delete the merged branch, move the ticket to Done and update the wave plan | `/giga-workflow:epic-story-ship` and `/giga-workflow:epic-merge-pr` (on a `direct` board, `/giga-workflow:epic-story-complete`); you, to close an `epic-branch` epic after its PR merges |
| [`/giga-workflow:epic-review`](skills/epic-review/SKILL.md) | review a finished epic against the whole app and send its ideas to the Idea Board | you, after the epic closes |
| [`/giga-workflow:epic-config`](skills/epic-config/SKILL.md) | show or edit a board, or repoint it at the domain's next epic by hand | you |
| [`/giga-workflow:epic-loop`](skills/epic-loop/SKILL.md) | work a board until it is empty, unattended, one agent per story | you |
| [`/giga-workflow:epic-cross-actor-test`](skills/epic-cross-actor-test/SKILL.md) | check a change across two signed-in personas in two browser profiles | you, at a loop's cross-actor pause or during any story |
| [`/giga-workflow:create-jira`](skills/create-jira/SKILL.md) | file one finding from an app review as a ticket under an epic | you, once per finding |
| [`/giga-workflow:dev-server`](skills/dev-server/SKILL.md) | start and watch a dev server or Storybook | `/giga-workflow:jira`'s UX review, when `ux.devServerSkill` names it; Claude, whenever a task runs the app |
| [`/giga-workflow:clean-exit`](skills/clean-exit/SKILL.md) | stop what this session and checkout left running, before `/exit` | you |

`/giga-workflow:epic-loop` runs the per-story skills itself, with no gate: each story's agent runs `/giga-workflow:epic-next`, `/giga-workflow:jira`, `/giga-workflow:epic-evolution-audit` when `loop.evolutionAudit` is set, `/giga-workflow:epic-story-complete --yes` and `/giga-workflow:epic-merge-pr --yes`, so each story merges unattended. On a `direct` board the chain ends at `/giga-workflow:epic-story-complete`.
