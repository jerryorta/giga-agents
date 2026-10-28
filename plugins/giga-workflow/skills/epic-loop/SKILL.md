---
name: epic-loop
description: "Run an epic board to empty, unattended. A thin in-session orchestrator that spawns one autonomous agent per story — each agent takes a single ticket from To Do all the way to merged on `<git.mainBranch>` — and surfaces to the user only when genuinely stuck. The orchestrator itself does no work beyond picking the next story, spawning, verifying, and recording, which is what lets a multi-day run stay small in context: $ARGUMENTS"
---

Run an epic board to empty, unattended. A thin in-session orchestrator that spawns one autonomous agent per story — each agent takes a single ticket from To Do all the way to merged on `<git.mainBranch>` — and surfaces to the user only when genuinely stuck. The orchestrator itself does no work beyond picking the next story, spawning, verifying, and recording, which is what lets a multi-day run stay small in context: $ARGUMENTS

**Usage:**
- `/giga-workflow:epic-loop <board>` — every To-Do story on the board, until none remain. `--until-empty` says the same thing explicitly.
- `/giga-workflow:epic-loop <board> <N>` — up to N stories, sequentially (`1` runs a single story, then stops and reports).
- `/giga-workflow:epic-loop <board> --dry-run` — resolve the next story and print the exact agent prompt. Spawns nothing.
- `/giga-workflow:epic-loop <board> --skip-triage` — skip the per-story readiness pre-flight.
- `/giga-workflow:epic-loop <board> --model <m>` — override `loop.storyModel` for this run. A story's own `model:` front matter beats both.
- `/giga-workflow:epic-loop <board> --resume "<answer>"` — restart the story that escalated an unresolved decision, with the answer supplied.
- `/giga-workflow:epic-loop <board> --actor-passed [N]` — the paused story's cross-actor test passed: ship and merge it, then carry on until the board is empty. The paused story counts toward `N`, so `--actor-passed 1` ships only it.

**Available boards:** any `epic.<board>.json` under `.claude/giga/` whose `hybridMode` is
`false`, omitted or `"conditional"`. A `"conditional"` board ships every story unattended except one
that needs cross-actor testing, which pauses the run before its PR (Step 3a).

> **Relationship to the other epic skills.** `/giga-workflow:epic-next` is the interactive single-story flow and
> stays exactly as it is; this skill drives it, through in-session agents that reach the Atlassian
> MCP and `claude-in-chrome`.

## Project config

Repo-specific values come from `.claude/giga/config.json` at the repository root, under `workflow`. Read it once at the start. A missing file or field takes the fallback below, never a guess. The story agents get the same values from this table: their `autonomy-contract.md` points back here.

| Field | Used for | When absent |
| --- | --- | --- |
| `plans.script` | the script behind `board` (Steps 1, 2a, 2b, 4) | stop and say the repo has no `plans.script` in `.claude/giga/config.json` |
| `plans.repo` | the plans repo holding `<board>/<KEY>.md` plan files and the wave plan | stop and say the repo has no `plans.repo` in `.claude/giga/config.json` |
| `git.mainBranch` | the base branch the run starts from and merges to | `main` |
| `git.branchPrefix` | the prefix of a story's feature branch | `feat/` |
| `git.mergeMethod` | how a PR is merged (the `gh pr merge` flag, and the merge the story agent runs) | `squash` |
| `git.hasCI` | whether a side-change PR waits for checks before merging | `false`: merge without waiting on checks |
| `loop.ledgerDir` | the directory holding `<board>.jsonl`, the run's durable state | `~/.claude/epic-loop` |
| `browser.runProfileLabel` | the browser profile the user connects for the run's browser checks (Step 1.4) | say "the profile you use for this repo" |
| `browser.renderingFiles` | the regex for files that render UI, used by the Step 2d.5 browser check | count every changed file, so a `not-applicable` browser result always stops the run |
| `notify` | the command that queues a desktop notification | send no desktop notification; the printed block is the only signal |
| `epicCloseSkill` | the skill that closes an epic in the cross-board order (Step 4) | skip the epic-close hand-off |

---

## The orchestrator does almost nothing — on purpose

This skill's whole value is what it refuses to do. **As the orchestrator you may only:**

- `Bash` — git status reads, `gh pr view`, `<plans.script>`, ledger appends
- `Read` — the board config, the ledger, the epic's wave plan
- `Agent` — spawn story / triage / research agents
- `Write` — the ledger only
- `claude-in-chrome` — the one-time browser connect in Step 1.4, and nothing else

**Side changes the owner asks for mid-run merge inside the loop.** When the owner asks for a process,
skill or tooling change while the run is going, the orchestrator has an `Agent` make it in an isolated
worktree, open the PR, and merge it (`git.mergeMethod`) once its checks pass (with `git.hasCI` false, merge without waiting on checks): verify `state: MERGED`, delete the
remote branch, remove the worktree, then report the merged PR. Run `gh pr merge <n> --<git.mergeMethod>` without
`--delete-branch` (a worktree holds the branch) and delete the remote ref separately with
`gh api -X DELETE`. The PR stays open only when the owner says to open it without merging, or when the
change goes beyond what they asked.

**You must never** read a source file, open a diff, edit anything, run a build or test, or drive a
browser. Every one of those belongs to a spawned agent, whose tool output never enters your context —
only its final report does.

Per story you should accumulate roughly: a ~250-token spawn prompt, a ~200-token JSON report, ~150
tokens of ground-truth output, and one status line. **Under 1k tokens per story.** If you find
yourself reading a component to understand a failure, you have broken the contract — spawn an agent
to do it and take its answer.

## Step 0 — Parse arguments and load state

**First token** is the board (required). If absent, list the available `epic.*.json` boards and stop;
do not default.

Remaining tokens: a bare integer → `maxStories`; the flags above. Default `maxStories` is unbounded,
so the run goes until the board is empty; `--until-empty` is accepted and changes nothing.

Read `.claude/giga/epic.<board>.json`. Bind it as `config`. Missing file → list available
boards and stop.

**Validate `hybridMode`.** It must be `false`, omitted or `"conditional"`; any other value (a legacy
`true`) → stop and point at `/giga-workflow:epic-config <board>` to set `"conditional"`. Bind
`conditional = config.hybridMode === "conditional"`.

Bind the `config.loop` block, applying these defaults when the field is absent:

| Field | Default | Purpose |
|---|---|---|
| `storyModel` | `opus` | model for the per-story agent; a story's `model:` front matter (`sonnet` / `opus` / `haiku`) beats `--model`, which beats this |
| `triage` | `true` | run the cheap readiness pre-flight |
| `triageModel` | `sonnet` | model for the triage agent |
| `decisionResearchModel` | `opus` | model the story agent's nested research agent uses |
| `designSkills` | `[]` | design authorities for the decision ladder |
| `architectureSkills` | `[]` | state/architecture authorities for the decision ladder |
| `evolutionAudit` | `false` | run `/giga-workflow:epic-evolution-audit` before each ship |
| `maxConsecutiveFailures` | `2` | consecutive non-`SHIPPED` outcomes before escalating |
| `browserVerification` | `false` | story agents check UI changes in Storybook or the running app before shipping (contract §7); the run connects a browser once, in Step 1.4 |

**Read the ledger** at `<loop.ledgerDir>/<board>.jsonl` (create the directory on first write). It
lives outside the repo so it survives sessions and never dirties the tree. The ledger — not this
conversation — is the durable state: after a context compaction, re-read it rather than trusting a
summary.

Line shapes:

```json
{"ts":"2026-08-05T14:22:10Z","type":"story","key":"ABC-123","status":"SHIPPED","pr":962,"branch":"feat/abc-123-short-slug","attempt":1,"summary":"…","blocker":null}
{"ts":"2026-08-05T14:05:02Z","type":"waveOrder","keys":["ABC-123","ABC-124","ABC-125","ABC-126","ABC-127","ABC-128"]}
```

On a `direct` board `pr` is `null`, and the summary table's PR column shows the story's short SHA instead.

## Step 1 — Pre-flight, once per run

Run these before the first spawn. Any failure stops the run before a branch exists.

1. **Clean tree** — `git status --porcelain` must be empty. The story agent runs `git checkout <git.mainBranch>`
   and cuts a branch; a dirty tree would be disrupted. Non-empty → surface the paths and stop.
   **Exception:** on `--actor-passed`, the paused story's uncommitted work on its `<git.branchPrefix>` branch is
   expected — Step 3a's resume checks it instead.
2. **GitHub auth** — `gh auth status`. A 403 later is a run-level failure, not a story failure.
3. **Jira reachable** — `python3 <plans.script> board --jql '<config.jql>'`.
4. **Browser connected** (only when `loop.browserVerification`). This is the run's one interactive
   moment, so it happens here, before anything starts. Every story agent drives the connection made
   here, and none of them may reconnect (contract §7).
   - Load `mcp__claude-in-chrome__tabs_context_mcp` and `mcp__claude-in-chrome__switch_browser` in
     one `ToolSearch`, then call `tabs_context_mcp`.
   - If no browser is selected, or several are connected, call `switch_browser` directly; do not ask
     which one. Say in one line that it is for the run's browser checks, so the user clicks Connect in
     the `browser.runProfileLabel` profile. Then call `tabs_context_mcp` again.
   - Still unconnected → stop. Tell the user to re-run once Chrome is connected, or to set
     `loop.browserVerification: false` to run without browser checks.

⚠️ **An empty board result is ambiguous.** It means either "the epic is finished" or "the scoped Jira
token expired" — an expired token returns nothing rather than an error, which reads as "no stories
found" in every `/epic-*` skill. Before declaring an epic complete, probe with a key that certainly
exists:

```bash
python3 <plans.script> board --jql 'key = <config.epicKey>'
```

Rows back → the board really is empty (Step 4). Nothing back → the token is dead; escalate.

## Step 2 — The loop

Repeat until `maxStories` is reached, the board is empty, or an escalation fires.

### 2a — Pick the next story

```bash
python3 <plans.script> board --jql '<config.jql>'
```

- `config.storyOrdering === "jql"` → take the first result.
- `config.storyOrdering === "epic-description"` → order by the epic's wave plan. Use the cached
  `waveOrder` ledger line if present; otherwise read `<plans.repo>/<board>/<config.epicKey>.md`
  **once**, extract the ordered keys, and write a `waveOrder` line. **If the JQL returns a key absent
  from the cache, the wave plan grew** (stories get added mid-epic by design) — re-read the plan file
  once and refresh the cached line.

Once the pick is made, compute the progress counts (below) and print `Working story <done+1> of <total> — <KEY> (<model>)`.

**Story progress.** One call, recomputed fresh every time and never cached (stories are added mid-epic):
`python3 <plans.script> board --jql 'parent = <config.epicKey>'` → `total` = rows, `done` = rows with `category == "Done"`.
Every child issue type (Story and Bug) counts; children moved out of the epic no longer have it as parent and drop out.

Skip any key the ledger records as terminal-non-shipped (`BLOCKED`, or `FAILED` twice). Nothing left
to pick → Step 4.

**Cross-epic blockers.** Before spawning, apply `/giga-workflow:epic-next` Step 7.5 to the pick: the `blocked_by` front matter
on the story and on its epic, checked in one `board --jql 'key in (…)'` call. If a blocker is not Done, record
the story `BLOCKED <blocker>` in the ledger and take the next unblocked story. If nothing unblocked remains,
escalate with the redirect line (`/giga-workflow:epic-next <blocker's board>`). An unattended run never works another board's
epic on its own initiative.

**Per-story model.** Read the plan-file front matter key `model:` in the same pass as `blocked_by` and `loop: manual`. Bind
`storyModel` as the story's `model:`, else `--model`, else `loop.storyModel`; 2c and the `--resume` / `--actor-passed` re-spawns of
that story use it, and its ledger line records `"model":"<m>"`. Only the owner, or `/giga-workflow:epic-plan` when it cuts the story, sets the key,
never the orchestrator. A story fits Sonnet when it follows an established pattern: no new design, no new shared primitive, no
cross-library refactor.

**Manual stories.** A story whose plan-file front matter carries `loop: manual` is the owner's to run by hand
(a prod deploy, a content batch the owner must review before it merges). Read the key in the same pass as
`blocked_by`, and if it is set, stop the run before triage or any spawn (Step 3), with the notification
`'<KEY> · epic loop paused — manual story, run /giga-workflow:epic-next <board> <KEY>'`. Stop rather than skip: later
stories in the wave plan may depend on it. Once it is Done, a fresh `/giga-workflow:epic-loop <board>` carries on.

### 2b — Triage (skip if `--skip-triage` or `loop.triage === false`)

Spawn a cheap `loop.triageModel` agent, read-only, with the ticket key. It reads
`<plans.repo>/<board>/<KEY>.md` and answers one question: is this implementable as
written? It returns `READY` or `BLOCKED` plus one sentence.

`BLOCKED` → record it, skip the story, continue the loop. A ~30s Sonnet check that avoids sinking a
10–20 minute Opus session into an unworkable ticket pays for itself immediately.

**The triage agent also answers a size question**, read from the acceptance criteria, not the title:
`SIZE: one job` or `SIZE: multi-job — <job 1> | <job 2> [| …]`. A job is a distinct user goal worth
shipping on its own. A single flow with several steps is one job, and so are a story's states (empty,
error) and its role variants. Flag multi-job only when the jobs could ship separately, or when their
changes form disjoint slices that share no files. Record the answer on the story's ledger line as
`"size":"one"` or `"size":"multi"`. The size check runs only when triage runs; `--skip-triage` skips it.

`multi-job` → stop the run (Step 3) before spawning, with the notification
`'<KEY> · epic loop paused — multi-job story, split?'`, and print the jobs with two lines:
`keep as one: /giga-workflow:epic-loop <board> --resume "keep"` and `split: /giga-workflow:epic-plan <board>`. A `--resume "keep"`
spawns the story normally. The orchestrator never cuts or edits stories itself. It pauses rather than
skips because splitting is the owner's call, and every story pays a fixed per-story cost (setup, gate,
UX review, browser, ship), so a split is not free.

**On a `conditional` board the triage agent also marks cross-actor need**, and that half runs even
under `--skip-triage`. It reads the contract's §7.5 rule and answers `CROSS_ACTOR: yes — <scenario>`
or `CROSS_ACTOR: no — <reason>`. A `crossActor:` key in the story file's front matter decides
outright: `false` means no, and `true` or a scenario string means yes. When the key is present, the
triage agent reports it instead of judging. Bind the answer as `needsActor`, record it on the
story's ledger line, and print one line: `<KEY> · cross-actor: yes — <scenario>` or
`<KEY> · cross-actor: no`.

### 2c — Spawn the story agent

`Agent`, `subagent_type: "general-purpose"`, `model: storyModel` (per-story model, above).

⚠️ **Do not pass `name`.** A named agent delivers its result through the mailbox, so its final text —
the §8 JSON report — never returns to the `Agent` call, and the orchestrator is left reconstructing
the outcome from git alone. Spawned unnamed, the report comes back synchronously as the tool result,
which is where every check below expects it. (A named story agent can ship and go idle without the
orchestrator ever seeing its report.)

Keep the prompt this small — the contract file carries the weight, and it never enters your context:

> Read `${CLAUDE_SKILL_DIR}/autonomy-contract.md` in full and follow it verbatim. You are the
> story agent for board `<board>`, story `<KEY>` — `<summary>`.
>
> Execute the chain: `/giga-workflow:epic-next <board> <KEY>` → implement via `/giga-workflow:jira` (Phase 6 gate green, Phase 6.5 UX review passed)
> → *(when `loop.evolutionAudit`)* `/giga-workflow:epic-evolution-audit` → `/giga-workflow:epic-story-complete --yes`
> → `/giga-workflow:epic-merge-pr --yes`.
>
> End your turn with the §8 fenced JSON report and nothing after it.

On a board with `config.mergeMode === "direct"`, drop `→ /giga-workflow:epic-merge-pr --yes`: the chain ends at
`/giga-workflow:epic-story-complete --yes`, which fast-forwards `<git.mainBranch>` to the story and pushes it.

On `--resume`, append: *"A previous attempt escalated this decision: `<question>`. The answer is:
`<answer>`. Adopt it and proceed — do not re-open it."*

On a `conditional` board, append one of:
- `needsActor` yes: *"This story needs cross-actor testing (contract §7.5): `<scenario>`. Stop before
  `/giga-workflow:epic-story-complete` and return `AWAITING_ACTOR_TEST`."*
- `needsActor` no: *"Triage found no cross-actor need. Apply contract §7.5 to your diff before
  shipping; upgrade the story if it does need it."*

`--dry-run` → print this prompt and stop without spawning.

### 2d — Verify ground truth

**Never trust the report alone.** Both documented failure modes of the previous runner were
report-versus-reality mismatches — a shipped story reported as failed, and a story reported as
progressing that had never committed. Two cheap commands settle it:

```bash
git status --porcelain; git branch --show-current
gh pr view <pr> --json state,mergedAt --jq '{state,mergedAt}'
```

On a direct board there is no PR; the second command is
`git fetch -q origin && git log origin/<git.mainBranch> --oneline -E --grep '<KEY>([^0-9]|$)'`.

| Ground truth | Reading |
|---|---|
| Clean tree, on `<git.mainBranch>`, PR `MERGED` | genuinely `SHIPPED`, whatever the report said |
| Direct board: clean tree, on `<git.mainBranch>`, the story's commit on `origin/<git.mainBranch>`, no PR | genuinely `SHIPPED`, whatever the report said |
| Non-empty tree on a `<git.branchPrefix>` branch | implemented but never shipped — recoverable; treat as `FAILED` with that note, and let the retry run `/giga-workflow:epic-story-complete --yes` on the existing diff rather than redoing the work |
| PR `OPEN` and tree clean | `PR_OPEN_UNMERGED` — the merge is what failed, not the story |
| Report says `AWAITING_ACTOR_TEST`, non-empty tree on its `<git.branchPrefix>` branch, no PR | genuinely `AWAITING_ACTOR_TEST` |
| Report says `SHIPPED` but no PR exists (on a direct board: the story's commit is not on `origin/<git.mainBranch>`) | `FAILED`; trust the filesystem over the prose |

### 2d.5 — Decision-adherence check

Ground truth (2d) proves the story *shipped*. It cannot see whether the story shipped the *right*
thing — that is what this check is for, and it is the only safeguard standing between an unattended
merge and a decision nobody sanctioned.

Read the report's `decisions[]`, `reviews[]` and, when `loop.browserVerification` is set, `browser`.
**Hard-stop the run (Step 3) on any of:**

| Condition | Why it stops the run |
|---|---|
| a `decisions[]` entry with `confidence: "CLEAR"` where `implemented` ≠ `recommended` (exact string comparison — the contract requires a followed recommendation be copied verbatim) | contract §6.4 override — the agent commissioned a verdict and shipped against it |
| a `reviews[]` entry with `returned_before_ship: false` | contract §6.5 — a review that landed after the merge gated nothing |
| a `decisions[]` entry with `confidence: "CLEAR"` and no `evidence` | an unfalsifiable claim of precedent |
| `browserVerification` set, and `browser` missing or its `result` is not `pass` / `not-applicable` | contract §7: a UI change shipped without being looked at |
| `browserVerification` set, `result: "not-applicable"`, and the PR touched a rendering file | contract §7: `not-applicable` is only for diffs with no rendered surface |
| `conditional`, `needsActor` yes, and the story came back `SHIPPED` | contract §7.5: a story that needed a second persona merged without one |

The rendering-file test is one ground-truth command. It counts the files, not their contents, so it
is not a diff read:

```bash
gh pr view <pr> --json files --jq '[.files[].path | select(test("<browser.renderingFiles>"))] | length'
```

On a direct board, count the story's commits on `<git.mainBranch>` instead:
`git log origin/<git.mainBranch> -E --grep '<KEY>([^0-9]|$)' --name-only --format= | sort -u | grep -cE '<browser.renderingFiles>'`.

**Exempt: the conventional-commit type.** A `decisions[]` entry whose subject is the commit type
(`feat` vs `fix` vs `chore`) never trips this check, at any confidence. It changes no shipped
behavior, and halting a multi-day unattended run over a commit-message prefix is pure cost, even with stories still queued. Story agents are told to take
the recommended type and not to record it as a decision at all (contract §6.4); if one records it
anyway, skip the entry and audit the rest. Every other trigger stands as written.

This is a **string comparison over the report**, not a code review — you still never read the diff.
Quote both values in the escalation so the user can rule in one line.

The bluntness is deliberate and worth keeping: it is what caught a real override, where the
agent's own research returned `CLEAR` for 1-based numbers and base-26 letters merged anyway. Resist
widening the exemption list by judging severity case by case — that judgement is the thing this
check exists to remove. A new exemption is a decision for the user, not for the orchestrator.

⚠️ **A hard-stop here fires *after* the merge has already landed** — the story agent owns the whole
chain, so by the time its report is in hand the code is on `<git.mainBranch>`. The stop protects the *next*
story, and surfaces this one for a corrective follow-up. It is not a merge gate, and describing it
as one would be wrong.

### 2e — Record, and stay quiet

Append one `story` line to the ledger with the resolved (not merely reported) status.

Then recompute the progress counts as in 2a, after the ground-truth check has confirmed the ticket reached Done, and print
`<done> of <total> stories complete`.

Then `<notify> --clear` (with no `notify`, skip the notification handoff throughout). Inner skills queue a desktop notification on story
completion; across an unattended run that would ping the user on every iteration. The orchestrator
owns the notification handoff and fires exactly twice: once on escalation, once on run completion.

### 2f — Decide

| Resolved status | Action |
|---|---|
| `SHIPPED` | Next story. |
| `FAILED`, first attempt | Retry **once**, re-spawning with the `blocker` text appended to the prompt. |
| `FAILED`, second attempt | Record, skip to the next story. |
| `BLOCKED` | Record, skip to the next story. |
| `PR_OPEN_UNMERGED` | Record. If the block was `DIRTY` (conflict), escalate; otherwise skip on. |
| `NEEDS_HUMAN` | Escalate (Step 3). |
| `AWAITING_ACTOR_TEST` | Pause (Step 3a). The run stops here, so no later story is built on unverified work. |

**One bad ticket must not halt a three-day run** — that is why `BLOCKED` and exhausted `FAILED` skip
rather than stop. Systemic breakage is caught by the consecutive-failure trigger instead.

## Step 3 — Escalate: the "truly stuck" set

Stop the loop, queue one notification, print a compact block, and hand back to the user.

```bash
<notify> '<KEY> · epic loop paused, needs you — <short reason>'
```

Body format is `<KEY> · <task>` — lead with the Jira key (it already encodes the board). Never put the
repo name or path in the body; the global Stop hook stamps both from the session cwd. Ignore a write
failure; never let a notification block the report.

Triggers:

- a `NEEDS_HUMAN` report, or anything in the contract's §5 escalate list. A `blocker` of
  `browser not connected` means the Step 1.4 connection dropped mid-run. Say so plainly, so the user
  reconnects Chrome before resuming.
- a **decision-adherence failure** from Step 2d.5 — a `CLEAR` verdict overridden, or a review that
  returned after the ship
- **a missing or unparseable §8 report** — the orchestrator cannot run 2d.5 blind, and a story whose
  decisions cannot be audited is exactly the one not to build more stories on top of
- **auth failure** — the Jira token expired, or `gh` returned 403
- an **unexpected dirty tree** at the top of an iteration (something outside the loop wrote to the repo)
- **`loop.maxConsecutiveFailures` consecutive** non-`SHIPPED` outcomes — that is systemic, not
  story-specific, and burning further Opus sessions on it is waste
- a PR in `DIRTY` (real merge conflict)
- the next story is marked `loop: manual` (Step 2a); print its key and the `/giga-workflow:epic-next <board> <KEY>`
  line, and nothing was built for it
- a triage `SIZE: multi-job` flag (Step 2b)

### The decision fork — designed to be answered in one line

When `NEEDS_HUMAN` carries a `decisions[]` entry the ladder could not settle, print it in full:

```
ABC-123 · epic loop paused — unresolved decision

  Story:    ABC-123 — <summary>
  Branch:   feat/abc-123-short-slug (work in place, uncommitted)

  Question: <the fork, one line>
  Options:  A — <option>
            B — <option>
  Ruled out: <what the design skills and the tier 1-3 search eliminated, and why>

  Answer in one line, then:  /giga-workflow:epic-loop <board> --resume "<your answer>"
  Shipped so far this run:   <N> stories
```

The point is that the user answers a question, not re-derives a story. The branch and its work stay
exactly where the agent left them.

## Step 3a — Pause for cross-actor testing, then resume

An `AWAITING_ACTOR_TEST` story is finished but unshipped. Stop the loop and queue one notification:

```bash
<notify> '<KEY> · epic loop paused for cross-actor test'
```

Then print:

```
ABC-123 · epic loop paused — cross-actor test

  Story:     ABC-123 — <ticket summary>
  Branch:    feat/abc-123-short-slug (gate green, uncommitted)
  Scenario:  <crossActor.scenario>

  Test it:   /giga-workflow:epic-cross-actor-test <board> "<scenario>"
  Passed:    /giga-workflow:epic-loop <board> --actor-passed <stories left in this run, counting this one>
  Shipped so far this run:   <N> stories
```

On an unbounded run, the `Passed` line is a bare `/giga-workflow:epic-loop <board> --actor-passed`.

When `config.crossActor` is absent, the board has no personas for `/giga-workflow:epic-cross-actor-test`. Replace the
`Test it` line with `Test it:   by hand, signed in as each persona the scenario names`.

A finding in the test is fixed in place on the same branch (actor testing finds *and* fixes). The
fix rides into the same PR.

**Resume (`--actor-passed`).** Take the last ledger line for the board. It must be
`AWAITING_ACTOR_TEST`, and `git branch --show-current` must be that line's branch. Otherwise stop and
say which one is wrong. Then spawn one unnamed `general-purpose` agent at `loop.storyModel`:

> Read `${CLAUDE_SKILL_DIR}/autonomy-contract.md` in full and follow it verbatim. You are the
> story agent for board `<board>`, story `<KEY>`. Its cross-actor test passed and the work is on
> `<branch>`, uncommitted. Re-run the `/giga-workflow:jira` Phase 6 gate if the tree changed since the pause, then
> run `/giga-workflow:epic-story-complete --yes` → `/giga-workflow:epic-merge-pr --yes` (on a direct board, `/giga-workflow:epic-story-complete --yes` alone). Report `crossActor.needed: true`,
> `source: "triage"`. End with the §8 fenced JSON report and nothing after it.

Run 2d and 2d.5 on its report. Skip the `needsActor` row of 2d.5, because the test was run. Record the
result, then continue the loop at 2a with the remaining `maxStories`.

## Step 4 — Board empty, or `maxStories` reached

Print `config.completionMessage` (board empty) or a stop-reason line, then a table built from this
run's ledger lines:

```
Epic loop — <config.name> (<config.epicKey>) — <done> of <total> stories complete

| # | Ticket | Status  | PR   | Summary |
|---|--------|---------|------|---------|
| 1 | ABC-123 | SHIPPED | #962 | …       |
| 2 | ABC-124 | BLOCKED | —    | …       |

Shipped <N> · blocked <M> · failed <K>     Ledger: <loop.ledgerDir>/<board>.jsonl
```

The header counts are recomputed fresh as in 2a. When the board is empty, count the epic's open children
(`python3 <plans.script> board --jql 'parent = <config.epicKey> AND statusCategory != Done'`). If the result is `[]`, invoke
`/<epicCloseSkill> closed <config.epicKey>` and print its block under the table. It is idempotent, so it is safe even if
the last story's cleanup already ran it. Then print `Review: /giga-workflow:epic-review <config.epicKey> — before /giga-workflow:epic-plan <NEXT-KEY>`;
the loop never runs the review itself, because the owner decides what it finds.

Check for a dev server or Storybook still listening from this checkout; if one is, report its port and pid
as a leak for the owner to stop (or `/giga-workflow:clean-exit`), not a normal state.

Queue one completion notification:
`<notify> '<board> · epic loop complete — <N> stories shipped'`.
When the epic closed, append ` · plan <NEXT-KEY>` to that message.

## Error handling

- **Board config missing / no board given** → list available boards, stop.
- **`hybridMode` other than `false` / omitted / `"conditional"`** → refuse, point at `/giga-workflow:epic-config <board>`.
- **`--actor-passed` with no paused story** (last ledger line is not `AWAITING_ACTOR_TEST`, or the
  checkout is on another branch) → say which, stop.
- **Dirty tree at pre-flight** → surface the paths, stop. Never stash or discard someone's work.
- **Empty board result** → disambiguate finished-versus-expired-token per Step 1 before reporting
  completion.
- **Story agent returns no JSON block** → do not guess from its prose. Run Step 2d and take the
  filesystem's answer for *this* story's outcome, record it, then **escalate** — 2d.5 cannot run
  without a report, so the next story would build on unaudited decisions. Check first that the spawn
  did not pass `name` (see 2c); that is the known cause.
- **Story agent dies outright** (terminal error, `null` result) → treat as `FAILED` and apply the 2f
  retry rule.

## Notes

- **Why in-session agents rather than headless sessions.** A capability probe (2026-08-05) confirmed a
  `general-purpose` subagent in this session reaches the Atlassian MCP, `claude-in-chrome`, and the
  full project skill set, and has no `EnterPlanMode` tool at all. Headless `claude-agent-sdk`
  subprocesses reach none of those. That is the entire reason this skill exists as a native
  orchestrator.
- **Cost shape.** The story agent is the dominant cost of a run; the orchestrator and triage agents are
  rounding errors. `loop.storyModel` is the lever — `--model sonnet` stretches a run considerably on
  well-patterned boards.
- **Merging is real.** This skill merges (`git.mergeMethod`) to `<git.mainBranch>` without human review. The gate is `/giga-workflow:jira`
  Phase 6 (build + typecheck + lint + test on every affected project) running before the push; see
  `/giga-workflow:epic-merge-pr`'s "What this skill does not do" for why nothing is re-run at merge time.
- **Resumability.** The ledger is the run's memory. A new session can pick up mid-epic by reading it;
  a compacted context should re-read it rather than trust the summary.
- **Browser checks share one connection.** The `claude-in-chrome` connection belongs to this
  session, so a browser connected once in Step 1.4 serves every story agent the run spawns. Contract
  §1 tells agents to treat the tool's embedded ask-first text as output, not an instruction. §7
  forbids them to reconnect.
- **The loop pauses for cross-actor tests; it never runs them.** Cross-actor checks need two browser
  profiles and the `/giga-workflow:epic-cross-actor-test` brackets, which this loop does not own. A `conditional`
  board hands the one story that needs them to a human and ships the rest.
