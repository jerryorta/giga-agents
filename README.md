# giga-agents

Claude Code plugins for product, UX and delivery workflows, published from the `.claude/` of a production Nx monorepo (Angular, NgRx, Capacitor, Firebase) where they run every day.

| Plugin | What it does |
| --- | --- |
| `giga-ux` | UX architecture and review. A `ux-design` skill plus three subagents: `ux-architect` wireframes a feature before its visual design, `ux-reviewer` reviews it in the running app after it is built, and `ux-blind-user` answers blind first-click and expectation tests with no access to the code. |
| `giga-workflow` | A Jira epic workflow in 15 skills. `/epic-plan` cuts an epic into conflict-minimising waves; `/epic-next` + `/jira` take one story from ticket to plan to code; `/epic-story-complete`, `/epic-merge-pr` and `/epic-story-ship` commit, open, merge and close it; `/epic-loop` runs a whole board unattended, one agent per story, pausing only for what needs a human. Around them: `/epic-config`, `/epic-evolution-audit`, `/epic-review`, `/create-jira`, `/post-merge-cleanup`, `/epic-cross-actor-test`, `/dev-server` and `/clean-exit`. |
| `giga-angular` | Two Angular skills that take your repo's conventions from config. `/create-storybook` writes a component's four-file story set inside your Storybook review container, shaped like your example stories; `/ngrx-component-state` decides where each piece of a component's state belongs and builds its colocated NgRx SignalStore, laid out like your reference stores. |

## Install

```bash
claude plugin marketplace add jerryorta/giga-agents
claude plugin install giga-ux@giga-agents
claude plugin install giga-workflow@giga-agents
claude plugin install giga-angular@giga-agents
```

To enable them for everyone working in a repo, commit this to the repo's `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "giga-agents": { "source": { "source": "github", "repo": "jerryorta/giga-agents" } }
  },
  "enabledPlugins": {
    "giga-ux@giga-agents": true,
    "giga-workflow@giga-agents": true,
    "giga-angular@giga-agents": true
  }
}
```

Components are namespaced by the plugin: `/giga-ux:ux-design`, the agents `giga-ux:ux-architect`, `giga-ux:ux-reviewer` and `giga-ux:ux-blind-user`, `/giga-workflow:epic-next`, `/giga-angular:create-storybook` and so on. Where config names a skill (`ux.devServerSkill`, `workflow.epicCloseSkill`), use the namespaced name, e.g. `giga-workflow:dev-server`.

## What `giga-workflow` expects

- **Jira**, through the Atlassian MCP connector, for status: transitions, comments, new issues.
- **A plans repo** holding each ticket's content as Markdown (`<board>/<KEY>.md`), with a script that implements `ensure <KEY>` (fetch a ticket to its file), `board --jql <jql>` (list a board's status), `section <KEY> <heading>` and `stub <KEY>`. Ticket content lives there rather than in Jira; Jira keeps status. The script is not part of this repo.
- **Board configs**: one `.claude/giga/epic.<board>.json` per board (epic key, JQL, story order, commit scope, build command, app and libraries, conventions). `/giga-workflow:epic-plan` writes them and `/giga-workflow:epic-config` edits them.
- **GitHub** and the `gh` CLI for pull requests.
- `giga-ux`, for the UX phases of `/jira` and for `/epic-review`. Without it those phases are skipped.

## Per-repo config

The plugins carry the method; each repo keeps its own data in `.claude/giga/config.json`. Each skill lists the fields it reads in its own `## Project config` section, with what it does when a field is absent.

```json
{
  "ideas": {
    "policy": "docs/process/ideas.md",
    "board": "https://example.com/idea-board"
  },
  "ux": {
    "brandVoice": {
      "guides": [
        {
          "brand": "Acme",
          "apps": ["acme-app", "acme-site"],
          "file": "docs/brand-voice/acme.md",
          "status": "draft",
          "note": "optional"
        }
      ]
    },
    "devServerSkill": "giga-workflow:dev-server",
    "viewportDoc": "docs/viewports.md",
    "backNavigationRule": "docs/constraints.md § Back Navigation"
  },
  "angular": {
    "prefix": "acme",
    "storybook": {
      "reviewContainerImport": "@acme/storybook",
      "storyExamples": [{ "name": "Button", "path": "libs/ui/src/lib/button/stories/" }]
    },
    "componentState": {
      "references": [{ "path": "libs/feature/src/lib/feature.store.ts", "note": "single-file store over facades" }],
      "standards": ["docs/constraints.md § Component State"]
    },
    "ngrxDocs": "~/src/ngrx-platform",
    "globalStoreSkill": "ngrx-global-store"
  },
  "workflow": {
    "plans": { "repo": "~/plans", "script": "~/plans/scripts/plans.py", "guide": "~/plans/AGENTS.md", "autoPush": false },
    "jira": { "site": "<your Jira site>", "cloudId": "<cloud id>", "mcpPrefix": "mcp__atlassian__", "createStatus": "To Do" },
    "git": { "mainBranch": "main", "branchPrefix": "feat/", "mergeMethod": "squash", "autoMerge": false, "hasCI": true },
    "commit": { "format": "<type>(<scope>): <KEY> <subject>", "scopeRules": "docs/commit-scopes.json", "hooks": true, "refactorCommitFirst": true },
    "checks": { "gate": "npm run verify", "affected": "npm run verify:affected", "single": "npm run <target> -w <project>", "antiPatterns": null },
    "docs": { "constraints": "docs/CONSTRAINTS.md", "agentsMd": ["AGENTS.md", "packages/<domain>/AGENTS.md"] },
    "devServerPrelude": ["nvm use"],
    "devServers": [
      { "app": "web", "command": "npm run dev", "port": 3000, "logFile": "/tmp/web-dev-server.log", "kind": "app" },
      { "app": "storybook", "command": "npm run storybook", "port": 6006, "logFile": "/tmp/storybook.log", "kind": "storybook" }
    ],
    "loop": { "ledgerDir": "~/.claude/epic-loop", "neverUnattended": ["database migrations", "anything touching secrets or a prod deploy"] },
    "browser": { "renderingFiles": "\\.(tsx|css)$" },
    "notify": null,
    "memoryDir": null,
    "epicCloseSkill": null
  }
}
```

| Field | Used for |
| --- | --- |
| `ideas.policy` · `ideas.board` | how ideas and out-of-scope findings reach the owner (top level: shared by every plugin) |
| `ux.brandVoice.guides` | the voice guide checked for each app's copy |
| `ux.devServerSkill` | the skill that starts the app for a review |
| `ux.viewportDoc` · `ux.backNavigationRule` | breakpoints beyond 320 px, 390 px and 768–1023 px; the repo's rule for in-app Back |
| `angular.prefix` · `angular.storybook` | the component prefix that names the Storybook review container, the module that exports it, and the example stories to copy |
| `angular.componentState` · `angular.ngrxDocs` · `angular.globalStoreSkill` | the reference stores and state standards a SignalStore follows; the local NgRx docs clone (`$NGRX_DOCS` wins); the skill that builds a global store slice |
| `workflow.plans` | the plans repo, its script and guide; whether it pushes its own commits |
| `workflow.jira` | the Jira site, cloud id, MCP tool prefix, and the status a ready story sits in |
| `workflow.git` · `workflow.commit` | base branch, branch prefix, merge method, auto-merge, CI; commit format and scope rules |
| `workflow.checks` · `workflow.docs` | the build/lint/test gate and single-target command; the standards docs and `AGENTS.md` locations |
| `workflow.devServers` · `workflow.devServerPrelude` · `workflow.storybook` | how to start each app and Storybook, and on which port |
| `workflow.planning` | dependency signals and path globs `/epic-plan` and `/jira` use to split and order work |
| `workflow.loop` · `workflow.browser` | what an unattended run must hand to a human, where it keeps its ledger, precedent sources, browser checks |
| `workflow.secrets` · `workflow.notify` · `workflow.memoryDir` · `workflow.epicCloseSkill` | optional: secrets repos to sync after a merge, desktop notifications, a personal memory folder, a skill to run when an epic closes |

## How this repo is built

The source monorepo stays the source of truth: skills change there, in the same pull request as the code they describe. `scripts/sync_from_monorepo.py` publishes the components listed in `sync.json` verbatim, with one mechanical change and two checks — it namespaces every skill and agent name across the plugins (backticked names, `/skill` invocations and agents' preloaded skills), and it refuses to write anything if a copied file matches a `forbidden` pattern (home paths, private emails, private links, token prefixes) or a skill reads another skill's file outside its own plugin.

A publish runs these steps in order:

1. `python3 -m unittest discover -s tests` tests the sync script: namespacing, the leak guard, the cross-plugin path check and an end-to-end run against a fixture tree.
2. `scripts/sync_from_monorepo.py --dry-run` builds and checks without writing anything.
3. `scripts/sync_from_monorepo.py` writes `plugins/`.
4. `claude plugin validate .`
5. Smoke-test each plugin as installed. The source repo never exercises the namespaced names, the files one skill reads from another, or the fallbacks a repo without config takes, so load each plugin into a scratch repo whose config is empty and ask, read-only, what it sees:

   ```bash
   root=$PWD scratch=$(mktemp -d)
   git -C "$scratch" init -q && mkdir -p "$scratch/.claude/giga" && echo '{}' > "$scratch/.claude/giga/config.json"
   for p in "$root"/plugins/*/; do
     (cd "$scratch" && claude -p --add-dir "$p" --setting-sources project --plugin-dir "$p" \
       "Read-only check: run no skill step and change no file. For the plugin at $p: \
   1) list every skill and agent it provides, by its namespaced name; \
   2) for each skill, open every file its SKILL.md reaches through \${CLAUDE_SKILL_DIR} and say whether it exists; \
   3) for each field in each skill's Project config table, give the fallback it takes in this repo, whose .claude/giga/config.json is empty." < /dev/null)
   done
   ```

   A missing file, a name without its plugin prefix, or a fallback that guesses instead of asking is a defect: fix it in the source repo and publish again from step 1.
6. Commit and push to `main`.
7. In each repo that uses the plugins, run `claude plugin marketplace update giga-agents`. Auto-update is off for this marketplace, so a repo stays on the previous commit until this step runs.

For local development, load a plugin straight from the working tree: `claude --plugin-dir plugins/giga-workflow --plugin-dir plugins/giga-ux`.
