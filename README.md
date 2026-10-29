# giga-agents

Claude Code plugins for product, UX and delivery workflows, built and run every day in a production Nx monorepo (Angular, NgRx, Capacitor, Firebase).

| Plugin | What it does |
| --- | --- |
| [`giga-ux`](plugins/giga-ux/README.md) | UX architecture and review, in one skill and three agents. Wireframe a feature, page or flow before its visual design, review it in the running app once it is built, and test its labels on someone who has never seen the app. |
| [`giga-workflow`](plugins/giga-workflow/README.md) | A Jira epic workflow in 15 skills. Plan an epic into waves, take one story at a time from ticket to merged pull request, or run a whole board unattended. |
| [`giga-angular`](plugins/giga-angular/README.md) | Seven Angular skills that take your repo's conventions from config. They write Storybook stories, place component and global state, scaffold a domain, check theming and accessibility, and promote a component to a shared library. |
| [`giga-standards`](plugins/giga-standards/README.md) | Write-time coding standards. When an agent writes a file, a hook injects the constraints sections, anti-patterns, standards fragments, library-type standard and nearest `AGENTS.md` that govern it, routed by a table in your repo's config. |

Each plugin's page says what it needs, what it does with an empty config, and when to use each skill and agent.

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

## Quickstart

The epic workflow runs on two files in your repo and three commands. It also needs Jira, through an MCP connector, and a plans repo: a git repo of Markdown files, one per ticket, with a script the skills call to read and write them. [The plans repo](docs/plans-repo.md) is the script's contract.

1. **Write `.claude/giga/config.json`.** This is the least the epic workflow runs on:

   ```json
   {
     "workflow": {
       "plans": { "repo": "~/plans", "script": "~/plans/scripts/plans.py" },
       "jira": { "mcpPrefix": "mcp__claude_ai_Atlassian__" },
       "checks": { "gate": "npm run verify" }
     }
   }
   ```

   Without `plans.repo` or `plans.script`, the epic skills stop and name the missing field. Without `jira.mcpPrefix`, `/giga-workflow:jira` and the ship step stop, and `/giga-workflow:epic-plan` creates no stories in Jira. [The plans repo § Config](docs/plans-repo.md#config) covers the `plans` keys. `mcpPrefix` is the start of your Jira connector's tool names; [Per-repo config](#per-repo-config) says how to find yours. `checks.gate` is the command that builds, lints and tests your code; without it, `/giga-workflow:jira` asks for the check commands on every story. Every other field has a default.

2. **Get a board.** A board, `.claude/giga/epic.<board>.json`, names the epic being worked and the app, libraries and conventions its stories follow. For the epic `ABC-100`, `/giga-workflow:epic-plan` writes `.claude/giga/epic.abc.json`:

   ```json
   {
     "name": "Inbox empty states",
     "epicKey": "ABC-100",
     "jql": "parent = ABC-100 AND status = \"To Do\"",
     "storyOrdering": "epic-description",
     "groupLabel": "Wave",
     "completionMessage": "All ABC-100 stories are complete!",
     "hybridMode": false,
     "mergeMode": "pr",
     "epicBranch": null,
     "commitScope": "web",
     "buildCommand": "npm run build",
     "app": "apps/web",
     "libraries": { "ui": "libs/web/ui", "store": "libs/web/store", "designLibrary": null },
     "routingFiles": ["apps/web/src/app/app.routes.ts"],
     "conventions": ["Every component has its own spec file"],
     "designReferences": null,
     "epicEvolutionRules": []
   }
   ```

   The board comes from one of two places:

   - **The plan run writes it.** A new board then asks for its app and library paths. With `workflow.boardTemplate` naming a starter board, the run seeds the new board from that file instead.
   - **You write it first**, as `.claude/giga/epic.<board>.json` with `epicKey` set to the epic you are about to plan. `/giga-workflow:epic-plan` takes the board whose epic key shares the epic's prefix, keeps its app, libraries and conventions, and writes the epic's own fields.

3. **Run the epic.**

   ```
   /giga-workflow:epic-plan ABC-100     once: cuts the epic into waves and writes the board
   /giga-workflow:epic-next abc         once per story, in a new session; it hands the story to /giga-workflow:jira
   /giga-workflow:epic-story-ship       after you review the diff: commit, pull request, merge, Done
   ```

   [The epic workflow](docs/workflow.md) covers the rest: what each command asks you, the other merge modes, and how an epic closes.

## Guides

- [The epic workflow](docs/workflow.md): an epic from `/giga-workflow:epic-plan` to Done, in the order you type the commands.
- [The plans repo](docs/plans-repo.md): what the workflow reads and writes in your plans repo, and what its script must do.

## What `giga-workflow` expects

What the workflow needs, and what its skills do with an empty config, are on [the giga-workflow page](plugins/giga-workflow/README.md#what-it-needs).

## What `giga-standards` expects

What the hook needs, and each `standards` field with what it does when absent, are on [the giga-standards page](plugins/giga-standards/README.md).

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
      "app": "apps/storybook",
      "reviewContainerImport": "@acme/storybook",
      "storyExamples": [{ "name": "Button", "path": "libs/ui/src/lib/button/stories/" }]
    },
    "componentState": {
      "references": [{ "path": "libs/feature/src/lib/feature.store.ts", "note": "single-file store over facades" }],
      "standards": ["docs/constraints.md § Component State"]
    },
    "ngrxDocs": "~/src/ngrx-platform",
    "globalStoreSkill": "ngrx-global-store",
    "globalStore": {
      "layout": "folder-per-slice",
      "standards": [
        "docs/state.md § Global Store"
      ],
      "stores": [
        {
          "name": "acme",
          "lib": "libs/acme/store",
          "alias": "@acme/acme-store",
          "registration": "libs/acme/store/src/lib/acme-store.providers.ts",
          "registrationNote": "reducers in ACME_REDUCERS, effects in ACME_EFFECTS, listener services injected in its app initializer",
          "references": [
            {
              "path": "libs/acme/store/src/lib/+account/",
              "note": "single record with writes and a facade"
            }
          ],
          "standards": [
            "libs/acme/store/AGENTS.md"
          ],
          "helpers": {
            "writeEffect": {
              "symbol": "acmeWriteEffect",
              "module": "libs/acme/store/src/lib/firestore-write"
            }
          }
        }
      ],
      "firestore": {
        "helpers": {
          "firestoreService": {
            "symbol": "AcmeFirestoreService",
            "module": "@acme/firebase",
            "note": "setMergeDoc$ is the default write"
          },
          "listenerContract": {
            "symbol": "ListenerService",
            "module": "@acme/firebase"
          },
          "writeState": {
            "symbol": "WriteStateSlice",
            "module": "@acme/firebase"
          },
          "queryCache": {
            "symbol": "QueryCache",
            "module": "@acme/firebase"
          }
        },
        "standards": [
          "docs/constraints.md § Firestore"
        ]
      }
    },
    "newDomain": {
      "scope": "@acme",
      "appsRoot": "apps",
      "libsRoot": "libs",
      "app": {
        "generator": "@nx/angular:application",
        "flags": [
          "--routing=true",
          "--e2eTestRunner=none"
        ]
      },
      "libs": [
        {
          "type": "models",
          "generator": "@nx/js:library"
        },
        {
          "type": "store",
          "generator": "@nx/angular:library"
        },
        {
          "type": "themes",
          "generator": "@nx/angular:library",
          "flags": [
            "--unitTestRunner=none"
          ],
          "tests": false
        }
      ],
      "tags": [
        "scope:<domain>",
        "type:<type>"
      ],
      "guide": "docs/domains.md",
      "referenceDomain": "acme",
      "themeExample": "libs/acme/themes/src/lib/styles/",
      "scripts": {
        "serve": {
          "name": "serve:<domain>",
          "command": "npx nx run <domain>-app:serve --port <port>"
        },
        "build": {
          "name": "build:<domain>",
          "command": "npx nx run <domain>-app:build --configuration=production"
        }
      },
      "stubs": {
        "dirs": [
          "apps/<domain>/backend"
        ],
        "nxignore": [
          "apps/<domain>/backend"
        ],
        "eslintExclude": [
          "apps/<domain>/backend/**/*"
        ]
      },
      "moduleBoundaries": "eslint.config.mjs",
      "release": {
        "symbol": "provideAppRelease",
        "module": "@acme/release",
        "doc": "docs/release.md",
        "check": "npm run lint",
        "followUps": [
          "the update prompt"
        ]
      },
      "frameworkFreeLib": {
        "config": "eslint.config.mjs",
        "export": "frameworkFreeLib",
        "libs": [
          "models"
        ],
        "example": "libs/acme/models/eslint.config.mjs"
      },
      "backend": {
        "dir": "apps/<domain>/backend/functions",
        "aliasFiles": [
          "tsconfig.json"
        ],
        "aliasLibs": [
          "models"
        ],
        "example": "apps/acme/backend/functions"
      },
      "secrets": {
        "doc": "docs/secrets.md § Adding a domain"
      }
    },
    "theming": {
      "tokenFile": "libs/<domain>/themes/src/lib/styles/_<prefix>-tokens.scss",
      "tokenDocs": "libs/<domain>/themes/AGENTS.md",
      "standards": [
        "docs/constraints.md § Styling"
      ],
      "bannedTokens": [
        "--legacy-"
      ],
      "variants": [
        {
          "paths": [
            "libs/studio/",
            "apps/studio/"
          ],
          "skill": "verify-theming-studio"
        }
      ]
    },
    "accessibility": {
      "standards": [
        {
          "doc": "docs/a11y.md"
        },
        {
          "match": [
            "libs/shop/**",
            "apps/shop/**"
          ],
          "doc": "libs/shop/design-library/AGENTS.md"
        }
      ]
    },
    "promote": {
      "sharedLibrary": {
        "path": "libs/shared/ui",
        "prefix": "acme",
        "alias": "@acme/ui",
        "storyTitle": "Shared UI"
      },
      "domains": [
        {
          "domain": "shop",
          "prefix": "shp",
          "storyTitle": "Shop"
        }
      ],
      "domainLibraryPath": "libs/<domain>/design-library",
      "libraryDoc": "docs/libraries.md",
      "banned": [
        "@legacy/ui"
      ],
      "commitScope": "ui",
      "verify": "npx nx affected -t lint test"
    }
  },
  "workflow": {
    "plans": { "repo": "~/plans", "script": "~/plans/scripts/plans.py", "guide": "~/plans/AGENTS.md", "autoPush": false },
    "jira": { "site": "<your Jira site>", "cloudId": "<cloud id>", "mcpPrefix": "mcp__claude_ai_Atlassian__", "createStatus": "To Do" },
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
    "boardTemplate": ".claude/giga/board-template.json",
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
| `angular.prefix` · `angular.storybook` | the component prefix that names the Storybook review container, the module that exports it, the example stories to copy, and the Storybook app a new domain's design library registers with (`storybook.app`) |
| `angular.componentState` · `angular.ngrxDocs` · `angular.globalStoreSkill` | the reference stores and state standards a SignalStore follows; the local NgRx docs clone (`$NGRX_DOCS` wins); the skill that builds a global store slice |
| `angular.globalStore` | the global-store slice layout (`folder-per-slice` or `flat`); each store library's path, barrel alias, registration file and reference slices; the store standards; optional Firestore helpers (by key) and rules, which turn on the Firestore section |
| `angular.newDomain` | a new domain's library set, tags, alias scope and roots; the guide and reference domain the workers copy; the port scripts; optional steps: placeholder dirs, module boundaries, release wiring, framework-free lint rule, backend aliases, secrets, AGENTS.md pointers, voice guide |
| `angular.theming` | the token-file and token-docs path patterns (with `<domain>` and `<prefix>`), the styling standards, banned token prefixes, and path-scoped variant skills `/giga-angular:verify-theming` hands files to |
| `angular.accessibility` | `standards[]`: rule docs for `/giga-angular:verify-accessibility`, each applying to every file or only to files under its `match` globs, and winning over the skill's generic rules |
| `angular.promote` | the shared library's path, prefix, alias and story-title group; each source domain's prefix and story-title group; the domain library path pattern; the placement doc; banned content; commit scope; the verify command |
| `workflow.plans` | the plans repo and its script; each key, and what the skills do without it, is in [The plans repo § Config](docs/plans-repo.md#config) |
| `workflow.jira` | the Jira site, cloud id, MCP tool prefix, and the status a ready story sits in. `mcpPrefix` is a Jira tool's full name without the tool's own name: the hosted Atlassian connector's `mcp__claude_ai_Atlassian__getJiraIssue` gives `mcp__claude_ai_Atlassian__`, and a server you added yourself gives `mcp__<its name>__`, with its name as `/mcp` lists it |
| `workflow.git` · `workflow.commit` | base branch, branch prefix, merge method, auto-merge, CI; commit format and scope rules |
| `workflow.checks` · `workflow.docs` | the build/lint/test gate and single-target command; the standards docs and `AGENTS.md` locations |
| `workflow.devServers` · `workflow.devServerPrelude` · `workflow.storybook` | how to start each app and Storybook, and on which port |
| `workflow.planning` · `workflow.boardTemplate` | dependency signals and path globs `/giga-workflow:epic-plan` and `/giga-workflow:jira` use to split and order work; the starter board `/giga-workflow:epic-plan` seeds a new board from |
| `workflow.loop` · `workflow.browser` | what an unattended run must hand to a human, where it keeps its ledger, precedent sources, browser checks |
| `workflow.skillsRepo` | optional: a second repo holding skills a story may change — its checkout, live branch, check and push commands; the epic workflow lands and pushes it with the story |
| `workflow.secrets` · `workflow.notify` · `workflow.memoryDir` · `workflow.epicCloseSkill` | optional: secrets repos to sync after a merge, desktop notifications, a personal memory folder, a skill to run when an epic closes |
| `standards` | which docs `giga-standards` injects for each kind of file, the Bash source-file pattern and the byte budget (see [the giga-standards page](plugins/giga-standards/README.md)) |

## How this repo is built

This repo is the only copy of the plugins. Two branches carry them: `beta`, held by its own worktree, is the live copy every repo on this machine runs, and `main` is the published copy. Neither is edited in place: each change is made and tried in a worktree of its own, off `beta`, before it lands there.

1. Create the `beta` worktree once: `git worktree add ../giga-agents-beta -b beta`, and put a direnv `.envrc` above your repos that names its `plugins` dir: `path_add CLAUDE_CODE_PLUGIN_DIRS "$HOME/<path to the beta worktree>/plugins"`. For each change, add a worktree off `beta`: `git worktree add ../giga-agents-<name> -b <name> beta`. Work and commit there.
2. Run `git config core.hooksPath .githooks` once per clone. Then `scripts/check.sh` gates every commit and push: `python3 -m unittest discover -s tests`, `scripts/check_plugins.py` and `claude plugin validate .`. `check_plugins.py` refuses private content (home paths, private emails, private links, token prefixes) in `plugins/`, `docs/` and this README, a skill that reads another plugin's file through `${CLAUDE_SKILL_DIR}`, a bare skill or agent name, and a `$` followed by a digit in a `SKILL.md` or agent body: Claude Code replaces it with the skill's argument, so a script that needs one (awk's `$0`) goes in a file under the skill's `scripts/`. It also refuses a skill or agent that no table row on its plugin's `README.md` links. Names in skills are written namespaced (`/giga-workflow:epic-next`, `giga-ux:ux-reviewer`), and hook files are never rewritten.
3. Try the change in one session with `CLAUDE_CODE_PLUGIN_DIRS=<change worktree>/plugins claude`.
4. Smoke-test each plugin as installed. Load it into a scratch repo whose config is empty and ask, read-only, what it sees. Run this from the change's worktree:

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

   A missing file, a name without its plugin prefix, a hook line other than `exit 0 · 0 bytes`, or a fallback that guesses instead of asking is a defect: fix it in the worktree and run again from step 2.
5. Fast-forward `beta` to the change (`git merge --ff-only <name>` in the `beta` worktree), push `beta` to `origin/beta`, and remove the change's worktree and branch. That puts the change live on every repo of this machine: each session picks the plugins up at its next start or `/reload-plugins`. A skill that reads a new config field ships after the repos have that field. The epic workflow (`giga-workflow`) makes the change worktree, fast-forwards `beta` and pushes it itself for a repo whose `.claude/giga/config.json` names this clone in `workflow.skillsRepo`.
6. Publish: fast-forward `main` to `beta` (`git merge --ff-only beta` in the main working tree) and `git push`. Repos on other machines then run `claude plugin marketplace update giga-agents`, then `claude plugin update <plugin>@giga-agents --scope project` for each plugin they install, and restart their sessions. Auto-update is off for this marketplace and every install stays pinned to the commit it was installed at: the marketplace update refreshes the catalog only, and the plugin update moves the install.
