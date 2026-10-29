# giga-agents

Claude Code plugins for product, UX and delivery workflows, built and run every day in a production Nx monorepo (Angular, NgRx, Capacitor, Firebase).

| Plugin | What it does |
| --- | --- |
| `giga-ux` | UX architecture and review. A `giga-ux:ux-design` skill plus three subagents: `giga-ux:ux-architect` wireframes a feature before its visual design, `giga-ux:ux-reviewer` reviews it in the running app after it is built, and `giga-ux:ux-blind-user` answers blind first-click and expectation tests with no access to the code. |
| `giga-workflow` | A Jira epic workflow in 15 skills. `/giga-workflow:epic-plan` cuts an epic into conflict-minimising waves; `/giga-workflow:epic-next` + `/giga-workflow:jira` take one story from ticket to plan to code; `/giga-workflow:epic-story-complete`, `/giga-workflow:epic-merge-pr` and `/giga-workflow:epic-story-ship` commit, open, merge and close it; `/giga-workflow:epic-loop` runs a whole board unattended, one agent per story, pausing only for what needs a human. Around them: `/giga-workflow:epic-config`, `/giga-workflow:epic-evolution-audit`, `/giga-workflow:epic-review`, `/giga-workflow:create-jira`, `/giga-workflow:post-merge-cleanup`, `/giga-workflow:epic-cross-actor-test`, `/giga-workflow:dev-server` and `/giga-workflow:clean-exit`. |
| `giga-angular` | Seven Angular skills that take your repo's conventions from config. `/giga-angular:create-storybook` writes a component's four-file story set inside your Storybook review container, shaped like your example stories; `/giga-angular:ngrx-component-state` decides where each piece of a component's state belongs and builds its colocated NgRx SignalStore, laid out like your reference stores; `/giga-angular:ngrx-global-store` authors a global `@ngrx/store` slice; `/giga-angular:new-domain` scaffolds a domain's app and library set with Nx generators; `/giga-angular:verify-theming` and `/giga-angular:verify-accessibility` check and fix a file's theme tokens, accessible names and test selectors; `/giga-angular:promote-component` moves a component into a shared or domain design library. |
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
- **A plans repo** holding each ticket's content as Markdown (`<board>/<KEY>.md`), with a script that implements `ensure <KEY>` (fetch a ticket to its file), `board --jql <jql>` (list a board's status), `section <KEY> <heading>` and `stub <KEY>`. Ticket content lives there rather than in Jira; Jira keeps status. The script is not part of this repo; its contract is in [docs/plans-repo.md](docs/plans-repo.md).
- **Board configs**: one `.claude/giga/epic.<board>.json` per board (epic key, JQL, story order, commit scope, build command, app and libraries, conventions). `/giga-workflow:epic-plan` writes them and `/giga-workflow:epic-config` edits them. Each board picks a `mergeMode`: `pr` (the default) opens a pull request per story; `epic-branch` commits every story onto one epic branch that lands through one pull request; `direct` fast-forwards each story into the main branch and pushes it, with no pull request.
- **GitHub** and the `gh` CLI for pull requests, which only `pr` boards and an epic-branch landing need.
- `giga-ux`, for the UX phases of `/giga-workflow:jira` and for `/giga-workflow:epic-review`. Without it those phases are skipped.

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
| `workflow.plans` | the plans repo, its script and guide; whether it pushes its own commits |
| `workflow.jira` | the Jira site, cloud id, MCP tool prefix, and the status a ready story sits in |
| `workflow.git` · `workflow.commit` | base branch, branch prefix, merge method, auto-merge, CI; commit format and scope rules |
| `workflow.checks` · `workflow.docs` | the build/lint/test gate and single-target command; the standards docs and `AGENTS.md` locations |
| `workflow.devServers` · `workflow.devServerPrelude` · `workflow.storybook` | how to start each app and Storybook, and on which port |
| `workflow.planning` · `workflow.boardTemplate` | dependency signals and path globs `/giga-workflow:epic-plan` and `/giga-workflow:jira` use to split and order work; the starter board `/giga-workflow:epic-plan` seeds a new board from |
| `workflow.loop` · `workflow.browser` | what an unattended run must hand to a human, where it keeps its ledger, precedent sources, browser checks |
| `workflow.skillsRepo` | optional: a second repo holding skills a story may change — its checkout, live branch, check and push commands; the epic workflow lands and pushes it with the story |
| `workflow.secrets` · `workflow.notify` · `workflow.memoryDir` · `workflow.epicCloseSkill` | optional: secrets repos to sync after a merge, desktop notifications, a personal memory folder, a skill to run when an epic closes |
| `standards` | which docs `giga-standards` injects for each kind of file, the Bash source-file pattern and the byte budget (see What `giga-standards` expects) |

## How this repo is built

This repo is the only copy of the plugins. Two branches carry them: `beta`, held by its own worktree, is the live copy every repo on this machine runs, and `main` is the published copy. Neither is edited in place: each change is made and tried in a worktree of its own, off `beta`, before it lands there.

1. Create the `beta` worktree once: `git worktree add ../giga-agents-beta -b beta`, and put a direnv `.envrc` above your repos that names its `plugins` dir: `path_add CLAUDE_CODE_PLUGIN_DIRS "$HOME/<path to the beta worktree>/plugins"`. For each change, add a worktree off `beta`: `git worktree add ../giga-agents-<name> -b <name> beta`. Work and commit there.
2. Run `git config core.hooksPath .githooks` once per clone. Then `scripts/check.sh` gates every commit and push: `python3 -m unittest discover -s tests`, `scripts/check_plugins.py` and `claude plugin validate .`. `check_plugins.py` refuses private content (home paths, private emails, private links, token prefixes) in `plugins/`, `docs/` and this README, a skill that reads another plugin's file through `${CLAUDE_SKILL_DIR}`, and a bare skill or agent name. Names in skills are written namespaced (`/giga-workflow:epic-next`, `giga-ux:ux-reviewer`), and hook files are never rewritten.
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
