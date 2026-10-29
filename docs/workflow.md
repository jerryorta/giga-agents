# The epic workflow

An epic run takes an epic from a plan to Done, one story at a time. You plan the epic once. Then each story runs in its own session: you approve the pick, approve the plan, review the diff and ship it. The skills do the rest: the branch, the build, the reviews, the commit, the pull request, the merge, the Jira status and the wave plan. Per story you type two or three commands.

This page follows the commands you type. Each skill's `SKILL.md`, linked below, holds its steps.

## The model

- **A board** is `.claude/giga/epic.<board>.json`. It names the epic being worked, the JQL that finds its To Do stories, how the stories are ordered, the merge mode, the app and libraries, and the conventions every story follows. [`/giga-workflow:epic-plan`](../plugins/giga-workflow/skills/epic-plan/SKILL.md) writes it, and names it after the epic key's prefix in lower case (`ABC-100` → `abc`), or takes the board whose epic shares that prefix. [`/giga-workflow:epic-config`](../plugins/giga-workflow/skills/epic-config/SKILL.md) shows it and edits it.
- **One board per domain.** When an epic finishes, its board is repointed at the domain's next epic. A second board for the same domain forks its conventions, and they drift. `/giga-workflow:epic-plan` repoints the board when you plan that epic. `/giga-workflow:epic-config` repoints it by hand and moves the new epic to In Progress.
- **Jira holds status. The plans repo holds content.** Each ticket's text is a Markdown file, `<board>/<KEY>.md`, in a git repo of its own. The epic's file carries its `## Wave Plan` and its `## Shipped` list. The contract is in [The plans repo](plans-repo.md).
- **Repo values** live under `workflow` in `.claude/giga/config.json`: the main branch, the branch prefix, the merge method, the plans repo and the rest. Each skill lists the fields it reads, and what it does without them, in its own `## Project config` table.

## The path you type

On a board in the default `pr` mode, a first epic runs like this:

```
/giga-workflow:epic-plan ABC-100            you type it, once per epic
/giga-workflow:epic-next abc                you type it, once per story, in a new session
  └ /giga-workflow:jira ABC-124             starts on its own, then asks you to approve its plan
/giga-workflow:epic-story-ship              you type it, after you review the diff
  ├ /giga-workflow:epic-evolution-audit     runs on its own
  ├ /giga-workflow:epic-story-complete      runs on its own
  ├ /giga-workflow:epic-merge-pr --yes      runs on its own
  └ /giga-workflow:post-merge-cleanup       runs on its own
```

| Command | When | Started by | What it asks you |
| --- | --- | --- | --- |
| [`/giga-workflow:epic-plan <EPIC-KEY>`](../plugins/giga-workflow/skills/epic-plan/SKILL.md) | once per epic | you | One gate, before it writes anything: the epic type it detected; the wave plan, to accept or amend; how to write it into the epic's plan file (replace the wave plan, append, skip, or rewrite all); the stories to create, and any split, backend first; whether Backlog stories move to To Do; and, with an Idea Board, to adopt, park or decline each idea its red team and domain expert raised. When the board still points at an epic that is not Done, it first asks whether to overwrite that board or keep it and add a second one. A new board then asks for its app and library paths. |
| [`/giga-workflow:epic-next <board> [KEY]`](../plugins/giga-workflow/skills/epic-next/SKILL.md) | once per story, in a new session | you | To approve the pick: the story, its place in the epic, the branch it will cut, and the effort its plan file recommends. When the story waits on another epic's work (`blocked_by`), it names the board to work instead and stops, or offers a later story that is not blocked. |
| [`/giga-workflow:jira <KEY>`](../plugins/giga-workflow/skills/jira/SKILL.md) | right after you approve the pick | `/giga-workflow:epic-next` | To approve the plan, with its UX decisions for you and any proposed split. When the ticket's text has drifted from the code, it first asks whether to replace the text with a revised version. |
| [`/giga-workflow:epic-story-ship`](../plugins/giga-workflow/skills/epic-story-ship/SKILL.md) | once you have reviewed the diff | you | One gate, `Story ship`: the commit message, the sibling stories the audit found stale, any new stories to create, the PR, the merge and the cleanup, and any pending secrets-repo paths. Answer yes, no, or edit to change the message or strike an item. There is no second prompt. |

After the plan gate, `/giga-workflow:jira` builds the story. It runs a review gate on the diff, then the build, typecheck, lint and test gate. When the story changes what a user sees, a UX review in the running app follows; the app is started through the skill `ux.devServerSkill` names, such as [`/giga-workflow:dev-server`](../plugins/giga-workflow/skills/dev-server/SKILL.md). It prints a test plan, with a decision for each discrepancy it did not fix. It never commits. A UX review that fails twice, or that stops for the owner, puts its decision to you.

`/giga-workflow:epic-story-ship` then runs four skills in order, behind its one gate:

1. [`/giga-workflow:epic-evolution-audit`](../plugins/giga-workflow/skills/epic-evolution-audit/SKILL.md) checks the epic's other open stories against what shipped. Its edits wait for the gate.
2. [`/giga-workflow:epic-story-complete`](../plugins/giga-workflow/skills/epic-story-complete/SKILL.md) commits, pushes, opens the PR and moves the ticket to In Review.
3. [`/giga-workflow:epic-merge-pr --yes`](../plugins/giga-workflow/skills/epic-merge-pr/SKILL.md) merges the PR by `git.mergeMethod`, checks it merged, and syncs your local main branch.
4. [`/giga-workflow:post-merge-cleanup`](../plugins/giga-workflow/skills/post-merge-cleanup/SKILL.md) deletes the branch, moves the ticket to Done, and moves the story from the wave plan to `## Shipped`.

When secrets repos are configured (`secretsRepo` in the board, `secrets.sharedRepo` in the repo config), the ship step then commits and pushes the pending paths you approved at the gate. The gate lists paths only, never their contents. The report ends with the next story and its effort.

### When someone must review the PR first

Type `/giga-workflow:epic-story-complete` instead of `/giga-workflow:epic-story-ship`. Its gate, `Story complete`, shows the board and key it inferred, the commit message, the push, the PR and any follow-up stories. Answer yes, no or edit. It commits, pushes, opens the PR, moves the ticket to In Review, and stops. This is also the path `/giga-workflow:epic-next` hands off to when you let it carry on after reviewing the diff, instead of typing a command.

It runs a lighter scan of the epic's other stories than the audit does. Type `/giga-workflow:epic-evolution-audit` first when the story settled something its siblings depend on.

Once the PR is reviewed, type `/giga-workflow:epic-merge-pr <N>`. Its gate, `Merge pre-flight`, asks merge or cancel. It merges the PR, then runs `/giga-workflow:post-merge-cleanup`. Run it even when you merged on github.com: it reads the PR as merged and goes straight to the cleanup.

| Path | You type, per story |
| --- | --- |
| Ship and merge | `/giga-workflow:epic-next <board>`, then `/giga-workflow:epic-story-ship` |
| Review the PR first | `/giga-workflow:epic-next <board>`, then `/giga-workflow:epic-story-complete`, then `/giga-workflow:epic-merge-pr <N>` |

## Rules of the road

- **One story per session.** A session costs `turns × context`, and context only grows. A second story in the same session carries the first story's context and pays for it again on every turn. Start each story with `/clear`, then `/giga-workflow:epic-next`.
- **Two stories at once need two clones.** Run the second in another clone of the repo, in its own session.
- **The board sets the order.** `/giga-workflow:epic-next` takes the first To Do story in the board's `storyOrdering`: the order of the epic's `## Wave Plan`, or the order the JQL returns. Name a key to take a specific story.
- **The effort is yours to set.** `/giga-workflow:epic-next` reports the effort a story's plan file recommends. Run `/effort <level>` yourself when the session differs.
- **Leave the diff unstaged.** `/giga-workflow:jira` never commits. The ship step makes the commits.
- **Shut down before you leave.** A story can leave a dev server or Storybook running. Before `/exit`, [`/giga-workflow:clean-exit`](../plugins/giga-workflow/skills/clean-exit/SKILL.md) stops what this session and checkout left running, and leaves uncommitted work alone.

## How an epic closes

When the cleanup moves a story to Done, `/giga-workflow:post-merge-cleanup` counts the epic's open children. With none left, it moves the epic to Done, without asking. When `workflow.epicCloseSkill` names a skill, it then runs that skill with `closed <EPIC-KEY>`. That skill's block names the next epic to plan, and a review line follows it. `/giga-workflow:epic-next` runs the same hand-off when it finds the board empty.

Then you type:

1. [`/giga-workflow:epic-review <EPIC-KEY>`](../plugins/giga-workflow/skills/epic-review/SKILL.md). It reviews the finished epic against the whole app, through a whole-app UX review, a red team and a usage read. It writes their ideas to the Idea Board and records the review in the epic's plan file. It creates no stories and changes no code. It asks only whether to review an epic that is not Done yet, or one it has reviewed before.
2. Decide its ideas on the Idea Board.
3. `/giga-workflow:epic-plan <NEXT-KEY>`. It plans the next epic and repoints the board.

## Merge modes

Each board picks a `mergeMode`. Pass `epic-branch` or `direct` after the epic key to `/giga-workflow:epic-plan` to set it. Without one, the board keeps its mode, and a new board takes the mode in `boardTemplate`, or `pr`.

| | `pr` (default) | `epic-branch` | `direct` |
| --- | --- | --- | --- |
| Where the story is committed | its own branch, cut from the main branch | the shared epic branch (`epicBranch`), in the main checkout | its own branch, cut from the main branch |
| Pull request | one per story | one for the whole epic, which you open once every story is Done | none |
| The ticket reaches Done | when its PR merges, in the cleanup | at `/giga-workflow:epic-story-complete` | at `/giga-workflow:epic-story-complete`, which fast-forwards the main branch to the story and pushes it |
| `/giga-workflow:epic-story-ship` | the full chain above | runs `/giga-workflow:epic-story-complete` alone | runs `/giga-workflow:epic-story-complete` alone, which runs the cleanup itself |
| `/giga-workflow:epic-merge-pr` | merges the story's PR | refuses; once the epic is Done, it prints the epic PR to open | refuses; it points at `/giga-workflow:epic-story-complete` |

On an `epic-branch` board, the epic closes after its PR merges: type `/giga-workflow:post-merge-cleanup <epicBranch>`. It deletes the epic branch and moves the epic to Done. A `direct` board suits a repo that deploys on every push to the main branch.

## Later

### Run a board unattended

[`/giga-workflow:epic-loop <board>`](../plugins/giga-workflow/skills/epic-loop/SKILL.md) works the board until it is empty. It spawns one agent per story, and each agent takes its story from To Do to merged. Add a number to stop after that many stories. It checks once, before it starts: a clean tree, GitHub, Jira, and the browser when the run uses one.

It stops only when it needs you, such as for a decision it cannot settle, a story marked `loop: manual`, a merge conflict, a failed login, failures in a row, or a cross-actor test. A decision stop prints the question and the line that resumes the run: `/giga-workflow:epic-loop <board> --resume "<answer>"`.

### Cross-actor testing

A cross-actor test checks a change across two signed-in people: one persona acts in one browser profile, and another checks the result in a second. On a board with `hybridMode: "conditional"`, the loop ships every story unattended except one that needs this test. It pauses that story before its PR, with the gate green and the work uncommitted. A story's `crossActor:` front matter decides the need ahead of the loop's own triage.

At the pause, type [`/giga-workflow:epic-cross-actor-test <board> "<scenario>"`](../plugins/giga-workflow/skills/epic-cross-actor-test/SKILL.md). Fix any finding on the same branch. Then `/giga-workflow:epic-loop <board> --actor-passed` ships the story and carries on. The test skill needs the board's `crossActor` block, which names the personas and the dev server.

The loop is not the only way in. On a board with a `crossActor` block, run the test directly during any story, before you ship it.

### A repo of skills

`workflow.skillsRepo` names a second repo that holds skills, such as this one. A story may then change a skill as well as the code:

- `/giga-workflow:jira` edits the skills in a story worktree cut from that repo's live branch, never in the live checkout. That repo's check (`skillsRepo.check`) runs beside the build gate.
- The ship step lands the skills commit on the live branch and pushes it before this repo's PR, so it is live while the PR is reviewed.
- A story that changes only skills goes to Done with no PR.
- `/giga-workflow:post-merge-cleanup` holds Done while a story's skills commit is unpushed.

### Where ideas come in

A story builds what it says. A finding in what the story built is fixed in that story. New scope, and cuts or fixes outside the story, go to the Idea Board (`ideas.board`, rules in `ideas.policy`). They come from three skills:

- `/giga-workflow:epic-plan`: its red team and domain expert.
- `/giga-workflow:jira`: a story's UX frame and UX review, and a defect seen while building outside the story.
- `/giga-workflow:epic-review`: its UX review, red team and usage read.

Only the owner adopts an idea. Only `/giga-workflow:epic-plan` turns an adopted idea into a story.
