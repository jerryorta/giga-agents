# Phase 2.8: UX Frame — detail

**Size it like the change:**

| Story | Run |
| --- | --- |
| One component, no new route or nav entry | Inline, in your own context: `giga-ux:ux-design` Frame steps 1, 5, 6 and 7 — no agent |
| A page, a flow, a new route or nav entry, or a dashboard / hub change | **One** `giga-ux:ux-architect` agent (`model: sonnet`) |

Hand `giga-ux:ux-architect` the plan-file path, the Phase 2.5 comp summary, any spec or `designReferences` the board config names, and the app's voice guide path (`ux.brandVoice.guides` in `.claude/giga/config.json`, or "none yet"); it reads the code itself. It returns the **UX brief** and **Decisions for the owner**, at most three per story.

- The brief is a planning requirement in Phase 3, beside the acceptance criteria — its entry points, states, vocabulary and words are slices of this story, not follow-ups.
- The brief's **Ideas** go to the Idea Board (`ideas.board`) only when they meet the idea policy (`ideas.policy`) § Entry threshold and nothing matches them (§ Check for a match first); a match is recorded as "covered by <key or id>", and the rest are plans-file notes. An idea that qualifies but cannot be written (no `ideas.board`, or no `ArtifactData` in this context) goes in the story's plan file under `## Ideas for the Idea Board`, where `/giga-workflow:epic-review` posts it; a note that fails the threshold never goes under that heading. Never into the plan.
- **Interactive:** put the Decisions for the owner to the user at the plan gate (`ExitPlanMode`), in plain terms. A recommended cut is a decision like any other, and the story is built as written unless the user agrees to it.
- **Autonomous** (`/giga-workflow:epic-next` under `/giga-workflow:epic-loop`): build the brief as framed, record each decision for the owner in the story's plans file under `## UX decisions for the owner` with the default taken, and list them in the final report so none is defaulted unseen (the loop relays them). Never copy them into the epic's plan file: the epic carries decisions, the wave plan and Shipped one-liners only, and must not grow per story. The default for a recommended cut is always to build the story as written. STOP only when a decision blocks an acceptance criterion — the same rule as 2.75e.
