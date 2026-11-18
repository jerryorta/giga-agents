# Steps 7–9 — detail

## Step 7 — Confirmation gate

Print a digest of the audit findings followed by a confirmation prompt via `AskUserQuestion`:

```
/giga-workflow:epic-evolution-audit — findings

Just-completed:  <KEY> — <summary>   (status: <status>)
Parent epic:     <config.epicKey>
Audited:         <N> candidates
Verdicts:        <X> stale  •  <Y> clean  •  <Z> new-story-recommended
Mode:            apply | dry-run

Stale candidates:
  - ABC-A — <one-line drift summary>
  - ABC-B — …

New story recommendations:
  - <title> — <one-line why>
  - …

Clean (no edits proposed):
  - ABC-C, ABC-D, …

Apply all proposed edits to the stale candidates? (yes / pick / no)
  yes  → apply every proposed edit to its local plan file
  pick → ask, candidate by candidate, which to apply
  no   → stop, print the audit so the user can act manually
```

Three responses to handle:

- **yes** → proceed to Step 8 with the full edit set.
- **pick** → for each stale candidate, ask `AskUserQuestion` "apply edit to ABC-X? (yes/no/preview)". `preview` re-shows the proposed-vs-replacing blocks.
- **no** → print the full audit verbatim and stop. The user takes manual action.

If `--dry-run` was passed, skip the prompt entirely and behave as if the user picked **no** (print the audit, stop).

## Step 8 — Apply description edits

For each candidate the user approved, edit its **local plan file** directly (per §4 of the plans guide — descriptions are files, never `editJiraIssue`). Resolve the file path once, then apply the audit's edit as a literal find-and-replace of the "Replacing" block with the "Proposed edit" block:

```
plan=$(python3 <plans.script> ensure <KEY>)   → <prefix>/<KEY>.md
```

Use the `Edit` tool on `$plan` to swap the "Replacing" block for the "Proposed edit" block (or `Write` the full updated file if the block spans too much to match safely).

> **Atomicity note:** edit each candidate's file in its own `Edit` / `Write` call. Failures on one don't affect the others.
> If the find-and-replace match fails (the "Replacing" block isn't found verbatim in the local file), report it to the user
> and skip that candidate — never let the description go to the file partially mangled.
> The plan file is the only copy of the description; Jira keeps status. Re-pointing Jira's stub description at the file (the DESTRUCTIVE `python3 <plans.script> stub <KEY>` pass, §4) is a separate user action — this skill never writes descriptions to Jira.

## Step 9 — Final report

```
✓ Epic evolution audit complete

Audited:      <N> candidates of <config.epicKey>
Edits applied: <K> of <X> stale candidates
Skipped:      <Z> (user declined or find-and-replace mismatch)

Updates:
  - ABC-A — <one-line summary of edit>
  - ABC-B — …

New story recommendations (NOT auto-created — user action):
  - <title> — <why> — create in '<jira.createStatus>' status with parent <config.epicKey>
    Suggested: /giga-workflow:create-jira or manual creation in Jira

Next: run /giga-workflow:epic-story-complete to wrap up <KEY>.
```

If any new-story recommendations exist, suggest the user create them **before** running `/giga-workflow:epic-story-complete` so the parent epic's wave-plan edit (if applicable) can reference them by key. The audit re-run is idempotent — re-running after creation will pick up the new sibling and add it to the wave plan if needed.
