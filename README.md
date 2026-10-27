# giga-agents

Claude Code plugins for product and UX workflows, published from the `.claude/` of a production Nx monorepo (Angular, NgRx, Capacitor, Firebase) where they run every day.

| Plugin | What it does |
| --- | --- |
| `giga-ux` | UX architecture and review. A `ux-design` skill plus three subagents: `ux-architect` wireframes a feature before its visual design, `ux-reviewer` reviews it in the running app after it is built, and `ux-blind-user` answers blind first-click and expectation tests with no access to the code. |

## Install

```bash
claude plugin marketplace add jerryorta/giga-agents
claude plugin install giga-ux@giga-agents
```

To enable it for everyone working in a repo, commit this to the repo's `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "giga-agents": { "source": { "source": "github", "repo": "jerryorta/giga-agents" } }
  },
  "enabledPlugins": { "giga-ux@giga-agents": true }
}
```

Components are namespaced by the plugin: the skill is `/giga-ux:ux-design` and the agents are `giga-ux:ux-architect`, `giga-ux:ux-reviewer` and `giga-ux:ux-blind-user`.

## Per-repo config

The plugins carry the method; each repo keeps its own data in `.claude/giga/config.json`. Every field is optional, and each skill states what it does without one.

```json
{
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
    "ideas": {
      "policy": "docs/process/ideas.md",
      "board": "https://example.com/idea-board"
    },
    "devServerSkill": "dev-server",
    "viewportDoc": "docs/viewports.md",
    "backNavigationRule": "docs/constraints.md § Back Navigation"
  }
}
```

| Field | Used for |
| --- | --- |
| `ux.brandVoice.guides` | the voice guide checked for each app's copy |
| `ux.ideas.policy` · `ux.ideas.board` | how ideas and out-of-scope findings reach the owner |
| `ux.devServerSkill` | the skill that starts the app for a review |
| `ux.viewportDoc` | breakpoints beyond the default 320 px, 390 px and 768–1023 px |
| `ux.backNavigationRule` | the repo's rule for in-app Back |

## How this repo is built

The source monorepo stays the source of truth: skills change there, in the same pull request as the code they describe. `scripts/sync_from_monorepo.py` publishes the components listed in `sync.json` verbatim, with two mechanical changes — it namespaces skill and agent names for the plugin, and it refuses to write anything if a copied file matches a `forbidden` pattern (home paths, private emails, private links, token prefixes).

```bash
scripts/sync_from_monorepo.py --dry-run   # build and check only
scripts/sync_from_monorepo.py             # write plugins/
claude plugin validate .
```

For local development, load a plugin straight from the working tree: `claude --plugin-dir plugins/giga-ux`.
