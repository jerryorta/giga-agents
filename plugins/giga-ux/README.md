# giga-ux

UX architecture and review, in one skill and three agents. Wireframe a feature, page or flow before its visual design, review it in the running app once it is built, and test its labels on someone who has never seen the app. This page says what the plugin needs, what it reads from config, and when each part runs.

## What it needs

- **Nothing, to frame.** `giga-ux:ux-architect` works from the code, specs and plans, so a wireframe needs no running app.
- **A running app and Claude in Chrome, to review.** `giga-ux:ux-reviewer` starts the app with the skill `ux.devServerSkill` names, or opens a URL you give it, and drives it in Chrome. With no browser connected, it says so and reviews from the source alone.
- **`giga-workflow`, optional.** With it installed, `/giga-workflow:jira` frames a story before it plans and reviews it after its gate, and `/giga-workflow:epic-review` reviews the whole app when an epic closes. Without it, you dispatch the agents yourself, in the order `/giga-ux:ux-design` § Where this sits gives.
- **The `frontend-design` plugin, optional.** The skill hands the visual design between frame and review to `frontend-design:frontend-design`.

## With an empty config

The skill and agents read their values from `ux` in `.claude/giga/config.json`. The skill's [`## Project config`](skills/ux-design/SKILL.md#project-config) table lists every field they read, including the shared `ideas` key, and what each does without it. Two fields shape what you get:

- **`ux.devServerSkill`** names the skill that starts your app, by its namespaced name, such as `giga-workflow:dev-server`. `giga-ux:ux-reviewer` loads it before a review. Without it, the reviewer uses the URL it was given. With no URL either, it cannot run the app.
- **`ux.brandVoice.guides`** lists each brand's voice guide: the `brand`, the `apps` it covers, the guide's `file`, its `status` and an optional `note`. The frame drafts its words to the guide for the app in hand, and the review checks every word a user reads against it. Without a guide, both apply the skill's own rules for words.

## Skill and agents

| Skill or agent | Use it to | Started by |
| --- | --- | --- |
| [`/giga-ux:ux-design`](skills/ux-design/SKILL.md) | frame a feature before its visual design, review it once it is built, or answer how users move through an app | you; Claude, when you ask where something should live or how a user reaches it; `giga-ux:ux-architect` and `giga-ux:ux-reviewer`, which preload it |
| [`giga-ux:ux-architect`](agents/ux-architect.md) | wireframe a feature, page or flow, and return the UX brief with the decisions only you can make | the session building the feature; `/giga-workflow:jira`, before it plans a story that adds a page, route or flow |
| [`giga-ux:ux-reviewer`](agents/ux-reviewer.md) | review a feature, a section or the whole app in the running app, and return a report whose outcome is `Ship`, `Owed`, `Revise` or `Stop for the owner` | the session that built it; `/giga-workflow:jira`, after its gate; `/giga-workflow:epic-review`, for the whole app; `/giga-workflow:epic-plan`, for a live section a story reworks |
| [`giga-ux:ux-blind-user`](agents/ux-blind-user.md) | answer one first-click or expectation question as a first-time user, with no tools and no code | `giga-ux:ux-architect` and `giga-ux:ux-reviewer`, once per screen or label |

A change to one component needs no agent. `/giga-ux:ux-design` checks it inline.
