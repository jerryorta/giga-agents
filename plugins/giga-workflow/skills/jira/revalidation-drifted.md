# 2.75c — DRIFTED result — detail

- **DRIFTED** →
  1. Print the drift findings + intent inference.
  2. If any open questions exist, ask the user via `AskUserQuestion`. Cannot revise until they are answered. After answers come back, re-spawn the subagent with the answers folded into the prompt (under a new `## Human-resolved questions` section) so it can produce a final revised description.
  3. Otherwise, gate via `AskUserQuestion`: *"Replace ticket description with revised version? (yes / preview / no)"*
     - `preview` → print the full proposed new description, then re-ask
     - `yes` → proceed to 2.75d
     - `no` → continue to Phase 3 with the ORIGINAL description (the audit becomes informational only; the human implicitly accepts that the plan will be against the as-written description)
