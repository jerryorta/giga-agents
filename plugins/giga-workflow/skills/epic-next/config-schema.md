# Config schema reference — detail

Each `epic.<board>.json` file defines:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Human-readable epic name |
| `epicKey` | string | Jira tracker epic key |
| `jql` | string | Full JQL query to find To Do stories |
| `storyOrdering` | `"jql"` \| `"epic-description"` | `jql` = use JQL result order directly; `epic-description` = parse ordered list from epic description then cross-reference |
| `groupLabel` | string | Label for story groupings shown in reports (e.g. `Priority`, `Wave`, `Track`) |
| `completionMessage` | string | Shown when no To Do stories remain |
| `hybridMode` | `"conditional"` \| `false` \| undefined | Consumed by `/giga-workflow:epic-loop`. `"conditional"` = each story is marked for cross-actor need (autonomy contract §7.5, or the story file's `crossActor:` front matter); a story that needs it pauses the run before its PR, every other story ships and merges unattended. `false` / omitted = every story ships and merges unattended. Has NO effect on `/giga-workflow:epic-next` itself, which is always interactive. |
| `crossActor` | object \| undefined | Per-board cross-actor config consumed by `/giga-workflow:epic-cross-actor-test` (run by hand at an `/giga-workflow:epic-loop` cross-actor pause, or directly). Holds `devServer` (serveCommand/port/logFile/healthCheckUrl), `firestorePathPrefix`, `testAnchorPath`, `bracketMode` (`skill`\|`npm`), `e2eHook` (`window.__cgE2E`\|null), `personas[]` (displayName/email/seedAnchorKey/authModel/role), and `scenarioCatalogMemory` + `browserProfilesMemory` slugs plus `scenarioDir` (one scenario per file beside the catalog memory). Required when `hybridMode:"conditional"`. |
| `commitScope` | string | Angular commit scope (e.g. `billing`, `web`) — passed to `/giga-workflow:epic-story-complete` |
| `buildCommand` | string \| null | Shell command that builds the epic's app (e.g. `npm run build:web`). Run by `/giga-workflow:jira` Phase 6 if set. Optional; omit or set to `null` to skip the build gate. |
| `app` | string | Main app path |
| `libraries.ui` | string | UI library path |
| `libraries.store` | string \| null | Store library path (omit if unused) |
| `libraries.designLibrary` | string \| null | Design library path |
| `routingFiles` | string[] | Routing files for conflict analysis and `/giga-workflow:jira` plan-mode discovery |
| `conventions` | string[] | Project-specific conventions injected into the `/giga-workflow:jira` handoff prompt |
| `designReferences` | object \| null | Design system pointers (`boardsIndex`, `spec`, `agentsFile`, `tokens`) |
| `epicEvolutionRules` | string[] \| null | Board-specific **addenda** to the four canonical evolution rules, which live in `/giga-workflow:epic-evolution-audit` and bind every board. `[]` (the common case) = canonical only; `null` = this board opted out of evolution propagation entirely. Surface to `/giga-workflow:jira` for inclusion in the Phase 7 test plan when a shift gets surfaced. |
| `domainMemoryIndex` | string \| null | Filename of this board's domain memory index in the personal memory dir (e.g. `payments-index.md`). Read in Step 0 so domain-specific Project/Reference memories load without bloating the always-on `MEMORY.md`. Omit / `null` to skip. |
| `mergeMode` | `"pr"` \| `"epic-branch"` \| `"direct"` \| undefined | How stories integrate. `"pr"` / absent (default) = per-story `<git.branchPrefix>` branch → PR → `<git.mainBranch>`. `"epic-branch"` = every story is committed directly onto the shared `epicBranch` (no per-story PR); the epic lands on `<git.mainBranch>` via one PR at the end. `"direct"` = per-story `<git.branchPrefix>` branch, fast-forwarded into `<git.mainBranch>` and pushed by `/giga-workflow:epic-story-complete` (no PR). |
| `epicBranch` | string \| null | **Epic-branch mode only (required).** The long-lived integration branch every story commits onto (e.g. `feat/abc-123-short-slug`). |
| `loop` | object \| undefined | Consumed by the `/giga-workflow:epic-loop` skill (unattended in-session orchestrator); has NO effect on `/giga-workflow:epic-next` itself. Holds `storyModel` (default `opus`), `triage` + `triageModel`, `decisionResearchModel`, `designSkills[]` + `architectureSkills[]` (the authorities `/giga-workflow:epic-loop`'s decision-resolution ladder consults before falling back to a precedent search), `evolutionAudit`, `maxConsecutiveFailures`, `browserVerification` (default `false`; `true` = story agents check UI changes in Storybook or the running app before shipping, on one browser connection made at run start), and `unattendedAllowances[]` (default `[]`; each `{id, narrows, allows[], stillEscalates[]}` narrows one `workflow.loop.neverUnattended` entry, named verbatim in `narrows`, for this board only: see `/giga-workflow:epic-loop` Step 0 and its autonomy contract §5.1). Omit to run `/giga-workflow:epic-loop` on this board with its defaults. |

> `mode` and `phaseNote` are ignored. `epicBranch` is the integration branch of a `mergeMode:"epic-branch"` board; every story commits onto it directly.
