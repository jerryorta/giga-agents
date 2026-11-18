# Discrepancies not fixed here — detail

A finished story is rarely reread, so a finding left only in its own plan file is lost. Some findings are not fixed in this story: an `existing` UX finding, a review-gate note, an owner's remark, or a gap found while building outside this story's work. A `story` finding is never one: it is fixed here (Phase 6.5). **New scope is not a discrepancy:** a capability the story did not promise, whoever noticed it, is an Idea Board entry and only the owner turns it into a story. **Every one gets a decision; not every one gets a story.** A follow-up is a recommendation you make on the merits, never a quota the template fills. Decide each finding:

- **An existing open sibling whose scope it is.** Name the key; `/giga-workflow:epic-story-complete` Step 2 edits that sibling's plan file.
- **A recommended new story** — only when the finding is worth someone's time later: a user-facing defect, a real gap in a flow, a risk to a release, or something the owner asked for. Group related findings by area, about one story per area, as one story per area.
- **No follow-up**, with a one-line reason: cosmetic polish on a developer-only or internal surface, a test-fixture quirk with no product effect, behaviour that is already correct on inspection, or anything whose cost to track exceeds its value. The decision is recorded so it is a choice, not an omission.

The moment a batch of findings is in hand, present them in this block, apart from the rest of the report, so they cannot be skimmed past:

```
Discrepancies not fixed in <KEY>
| # | Finding | Found by | Decision |
| 1 | <finding> | UX review sev 1 · owner · 5b · build | <new story: summary> · <ABC-123> · No follow-up — <reason> |
```

Print the same block in the Phase 7 test plan. `/giga-workflow:epic-story-complete` Step 2 takes every **story** row as an evolution item, and its gate mints the new ones; a "No follow-up" row is not minted. The story's plan file may record the evidence, but each item there names its decision. A row with no decision is not done.
