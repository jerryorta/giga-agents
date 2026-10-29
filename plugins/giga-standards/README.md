# giga-standards

Write-time coding standards. When an agent writes a file, with Write, Edit or MultiEdit or with a Bash command that writes a source file, a `PreToolUse` hook ([`inject-standards.sh`](hooks/inject-standards.sh)) injects the constraints sections, anti-patterns, standards fragments, library-type standard and nearest `AGENTS.md` that govern it. A table in your repo's config routes them, under a size budget, once per agent context. After a compaction, a `SessionStart` hook ([`reset-standards-markers.sh`](hooks/reset-standards-markers.sh)) clears that agent's markers, so its next write injects again.

## What it needs

- **`jq` and `git`** on `PATH`.
- **Docs in these shapes**, each optional:
  - a constraints doc made of `## ` sections, injected by heading prefix
  - an anti-patterns JSON: `{ "patterns": [{ "id", "severity", "description", "fix" }] }`
  - standards fragments, library-type standards and guides, each routed by an `applyTo:` front-matter glob (a precise glob injects; `'**'` never does)
  - library notes: the nearest `AGENTS.md` above the written file
- **No second copy of the hooks.** Hooks are not namespaced: if `.claude/settings.json` runs its own copy of `inject-standards.sh` or `reset-standards-markers.sh`, remove it, or both run.

## With an empty config

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
