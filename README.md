# giga-agents

Claude Code plugins for product, UX and delivery workflows, published from the `.claude/` of a production Nx monorepo (Angular, NgRx, Capacitor, Firebase) where they run every day.

| Plugin | What it does |
| --- | --- |
| `giga-ux` | UX architecture and review. A `ux-design` skill plus three subagents: `ux-architect` wireframes a feature before its visual design, `ux-reviewer` reviews it in the running app after it is built, and `ux-blind-user` answers blind first-click and expectation tests with no access to the code. |
| `giga-workflow` | A Jira epic workflow in 15 skills. `/epic-plan` cuts an epic into conflict-minimising waves; `/epic-next` + `/jira` take one story from ticket to plan to code; `/epic-story-complete`, `/epic-merge-pr` and `/epic-story-ship` commit, open, merge and close it; `/epic-loop` runs a whole board unattended, one agent per story, pausing only for what needs a human. Around them: `/epic-config`, `/epic-evolution-audit`, `/epic-review`, `/create-jira`, `/post-merge-cleanup`, `/epic-cross-actor-test`, `/dev-server` and `/clean-exit`. |
| `giga-angular` | Two Angular skills that take your repo's conventions from config. `/create-storybook` writes a component's four-file story set inside your Storybook review container, shaped like your example stories; `/ngrx-component-state` decides where each piece of a component's state belongs and builds its colocated NgRx SignalStore, laid out like your reference stores. |
| `giga-standards` | Write-time coding standards. A `PreToolUse` hook that, when an agent writes a file (with Write, Edit or MultiEdit, or a Bash command that writes a source file), injects the constraints sections, anti-patterns, standards fragments, library-type standard and nearest `AGENTS.md` that govern it: routed by a table in your repo's config, under a size budget, once per agent context. |

## Install

```bash
claude plugin marketplace add jerryorta/giga-agents
claude plugin install giga-ux@giga-agents
claude plugin install giga-workflow@giga-agents
claude plugin install giga-angular@giga-agents
claude plugin install giga-standards@giga-agents
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
    "giga-angular@giga-agents": true,
    "giga-standards@giga-agents": true
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

## What `giga-standards` expects

- **`jq` and `git`** on `PATH`.
- **Docs in these shapes**, each optional:
  - a constraints doc made of `## ` sections, injected by heading prefix
  - an anti-patterns JSON: `{ "patterns": [{ "id", "severity", "description", "fix" }] }`
  - standards fragments, library-type standards and guides, each routed by an `applyTo:` front-matter glob (a precise glob injects; `'**'` never does)
  - library notes: the nearest `AGENTS.md` above the written file
- **No second copy of the hooks.** Hooks are not namespaced: if `.claude/settings.json` runs its own copy of `inject-standards.sh` or `reset-standards-markers.sh`, remove it, or both run.

The hook reads the top-level `standards` key of `.claude/giga/config.json`. Paths are relative to the repo root.

| Field | Used for | When absent |
| --- | --- | --- |
| `standards` | the whole routing table | the hook does nothing |
| `standards.constraintsFile` | the constraints doc | no constraints sections |
| `standards.antiPatternsFile` | the anti-patterns JSON | no anti-patterns |
| `standards.fragmentsDir` | standards fragments (`*.md` at its top level), inline when they fit, else as pointers | no fragments |
| `standards.libTypesDir` | one standard per library type | no library-type standard |
| `standards.guidesDir` | `*.instructions.md` guides, listed as pointers | no guide pointers |
| `standards.sourceFilePattern` | an extended regex for a source path; a Bash command that writes a matching path triggers the hook | Bash writes never trigger it |
| `standards.budgetBytes` | the byte budget for the injected context | 9800 |
| `standards.artifacts` | `[{ match, artifact, sections, antiPatterns, guide }]`: the constraints headings, anti-pattern ids and guide for each kind of file | no artifact layer, so only the library-type standard and `AGENTS.md` |
| `standards.everyArtifact` | `[{ match, sections, antiPatterns }]`: headings and ids added to whichever artifact matched | nothing added |

`match` globs are tested against the path relative to the repo root, and in each list the first entry that matches wins.

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
  },
  "standards": {
    "constraintsFile": "docs/constraints.md",
    "antiPatternsFile": "docs/anti-patterns.json",
    "fragmentsDir": "docs/standards",
    "libTypesDir": "docs/standards/lib-types",
    "guidesDir": "docs/guides",
    "sourceFilePattern": "(apps|packages)/[A-Za-z0-9_./-]+\\.(ts|tsx|css)",
    "budgetBytes": 9800,
    "artifacts": [
      { "match": ["*.test.ts"], "artifact": "test", "sections": ["Testing"], "antiPatterns": ["focused-test"], "guide": "docs/testing.md" },
      { "match": ["*.ts", "*.tsx"], "artifact": "source", "sections": ["Conventions"], "antiPatterns": ["any-type"] }
    ],
    "everyArtifact": [{ "match": ["*"], "sections": ["Comments"], "antiPatterns": ["commented-out-code"] }]
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
| `standards` | which docs `giga-standards` injects for each kind of file, the Bash source-file pattern and the byte budget (see What `giga-standards` expects) |

## How this repo is built

The source monorepo stays the source of truth: skills change there, in the same pull request as the code they describe. `scripts/sync_from_monorepo.py` publishes the skills, agents and hook files listed in `sync.json` verbatim, with one mechanical change and two checks — it namespaces every skill and agent name across the plugins (backticked names, `/skill` invocations and agents' preloaded skills; hook files are copied byte for byte), and it refuses to write anything if a copied file matches a `forbidden` pattern (home paths, private emails, private links, token prefixes) or a skill reads another skill's file outside its own plugin.

A publish runs these steps in order:

1. `python3 -m unittest discover -s tests` tests the sync script: namespacing, hook files copied byte for byte, the leak guard, the cross-plugin path check and an end-to-end run against a fixture tree.
2. `scripts/sync_from_monorepo.py --dry-run` builds and checks without writing anything.
3. `scripts/sync_from_monorepo.py` writes `plugins/`.
4. `claude plugin validate .`
5. Smoke-test each plugin as installed. The source repo never exercises the namespaced names, the files one skill reads from another, the hook commands as installed, or the fallbacks a repo without config takes, so load each plugin into a scratch repo whose config is empty and ask, read-only, what it sees:

   ```bash
   root=$PWD scratch=$(mktemp -d)
   git -C "$scratch" init -q && mkdir -p "$scratch/.claude/giga" && echo '{}' > "$scratch/.claude/giga/config.json"
   for p in "$root"/plugins/*/; do
     (cd "$scratch" && claude -p --add-dir "$p" --setting-sources project --plugin-dir "$p" \
       "Read-only check: run no skill step and change no file. For the plugin at $p: \
   1) list every skill and agent it provides, by its namespaced name; \
   2) for each skill, open every file its SKILL.md reaches through \${CLAUDE_SKILL_DIR} and say whether it exists; \
   3) for each field in each skill's Project config table, give the fallback it takes in this repo, whose .claude/giga/config.json is empty; \
   4) if the plugin has hooks/hooks.json, check that the script each command names exists under \${CLAUDE_PLUGIN_ROOT} (that is, $p)." < /dev/null)
   done
   ```

   A headless session is not allowed to run scripts, so run each hook command yourself, as installed, against the same empty config:

   ```bash
   for h in "$root"/plugins/*/hooks/hooks.json; do
     [ -e "$h" ] || continue
     p=$(dirname "$(dirname "$h")")
     jq -r '.hooks[][].hooks[].command' "$h" | sed "s#\${CLAUDE_PLUGIN_ROOT}#$p#g" | while IFS= read -r c; do
       out=$(cd "$scratch" && printf '{"tool_name":"Write","tool_input":{"file_path":"%s/src/a.ts"},"session_id":"smoke","cwd":"%s"}' "$scratch" "$scratch" | eval "$c")
       echo "exit $? · ${#out} bytes · $c"
     done
   done
   ```

   A missing file, a name without its plugin prefix, a hook line other than `exit 0 · 0 bytes`, or a fallback that guesses instead of asking is a defect: fix it in the source repo and publish again from step 1.
6. Commit and push to `main`.
7. In each repo that uses the plugins, run `claude plugin marketplace update giga-agents`. Auto-update is off for this marketplace, so a repo stays on the previous commit until this step runs.

For local development, load a plugin straight from the working tree: `claude --plugin-dir plugins/giga-workflow --plugin-dir plugins/giga-ux`.
