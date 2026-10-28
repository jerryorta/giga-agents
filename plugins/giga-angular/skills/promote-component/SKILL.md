---
name: promote-component
description: >-
  Promote ONE presentational component UP the placement hierarchy, from a domain design library to the shared design library, in a monorepo. It is a pure prefix swap across folder, files, selector, host class, class name, tokens, CSS and story title, a `git mv` into the shared library, a barrel update (remove the domain export, add the shared export, never re-export the shared component from the domain barrel), and a full repoint of every consumer. Runs pre-flight guardrails and verifies with affected lint and test. Use when the user says "promote <component> to shared" or names a domain design-library component to move up. Args: the component selector or its source folder path ($ARGUMENTS).
---

# Promote a design-library component: domain to shared

Move ONE presentational primitive from a domain's own design library UP to the cross-app shared design library, when a second application needs it. This is the mechanical half of the "build in the domain first, promote to shared when shared" rule.

It is a **prefix swap** from the domain prefix to the shared prefix (`Dm` to `Sh`, `dm-` to `sh-`, `--dm-` to `--sh-`, `.dm-` to `.sh-`, with `dm` standing for any domain prefix) plus a `git mv` into the shared library and a full repoint of every consumer. The impact set (the consumers) is discovered at execution time, never pre-listed.

**Component: `$ARGUMENTS`**: a selector (`<prefix>-fab`) or a source folder.

Run from the workspace root. All paths are repo-relative.

## Project config

Repo-specific values come from `.claude/giga/config.json` at the repository root, under `angular` unless a field is named from the root. Read it once at the start. A missing file or field takes the fallback below, never a guess.

| Field | Used for | When absent |
| --- | --- | --- |
| `promote` | the whole block | ask the user for the shared library's path, prefix and alias, then stop until they answer |
| `promote.sharedLibrary.path` · `.prefix` · `.alias` | the shared library's folder, component prefix and import alias | as `promote` absent |
| `promote.sharedLibrary.storyTitle` | the story-title group a promoted component moves to | keep the story title's tail and ask for the group |
| `promote.sharedLibrary.alsoCheck` | other library paths searched for a name collision (a deprecated twin of the shared library) | check the shared library only |
| `promote.domains` | `[{ "domain", "prefix", "storyTitle" }]`: each domain whose design library can be a source, its prefix and the story-title group its stories use | the prefix comes from the source library's `project.json`; the story-title group is the part of the story title before the first `/` |
| `promote.domainLibraryPath` | the domain design library's folder, with a `<domain>` placeholder | locate the source library by the `project.json` whose folder holds the component |
| `promote.libraryDoc` | the repo's library-placement doc, named in the final report | no doc is named |
| `promote.banned` | strings whose presence in the component blocks a promotion (a banned dependency or token namespace) | only the coupling and collision guardrails run |
| `promote.commitScope` | the commit scope for the promotion | take the scope from `workflow.commit.scopeRules` (root), else ask |
| `promote.verify` | the verification command | `workflow.checks.affected` (root); absent too, ask |

## Identity map: full prefix swap, the shared prefix kept everywhere

Source prefix `<p>` is the domain design library's `project.json` `prefix`. Target prefix is `promote.sharedLibrary.prefix`, written `<t>` below. `<P>` and `<T>` are the PascalCase forms.

| Surface | Source | Target |
| --- | --- | --- |
| Folder | `<domainLibraryPath>/src/lib/<p>-<name>/` | `<sharedLibrary.path>/src/lib/<t>-<name>/` |
| Files | `<p>-<name>.component.{ts,html,scss,spec.ts,stories.ts}` | `<t>-<name>.component.*` |
| Selector and `host.class` | `<p>-<name>` | `<t>-<name>` |
| Class name | `<P><Name>Component` | `<T><Name>Component` |
| Tokens | `--<p>-<name>-*` (any `--<p>-`) | `--<t>-<name>-*` |
| CSS and BEM classes | `.<p>-<name>`, `.<p>-<name>__el` | `.<t>-<name>...` |
| Story `title` | `'<domain group>/...'` | `'<sharedLibrary.storyTitle>/...'` |
| Alias in consumers | the source library's alias, read from `tsconfig.base.json` by its `src/index.ts` path | `promote.sharedLibrary.alias` |

Match whole identifiers or the prefix at the start of a word, so `DmFab` never corrupts an unrelated name that happens to contain the letters. Preserve git history: `git mv`, never delete and recreate.

## Pre-flight guardrails: HARD STOP, report, do NOT proceed

Run these before moving anything. If one trips, stop and tell the user exactly what to fix.

1. **No banned content.** Search the component folder for each `promote.banned` string. A hit means the component must be modernized first; do not auto-rewrite it, that is design work. With `promote.banned` absent, skip this guardrail.
2. **No domain coupling.** A shared component may depend only on the framework, `@angular/cdk`, generic shared infrastructure, and the shared design library itself. If its `.ts` imports any alias that `tsconfig.base.json` maps under the source domain's folder, or relative-imports a sibling `<p>-*` component, STOP and list them: promote or extract those first.
3. **No collision.** If `<sharedLibrary.path>/src/lib/<t>-<name>/`, the selector `<t>-<name>` or the class `<T><Name>Component` already exists in the shared library or in any `promote.sharedLibrary.alsoCheck` path, STOP.

## Procedure

1. **Resolve** `<domain>`, `<p>`, `<name>` and the file set from the argument. A selector: search for `selector: '<p>-<name>'`. A folder: read its `.component.ts`. Read `<p>` from the source library's `project.json` and the source alias from `tsconfig.base.json`.
2. **Run the pre-flight guardrails.** Stop on any failure.
3. **Print the plan**: every file rename and every identifier, selector, token and class swap, before touching anything.
4. **`git mv`** each file from the source folder into `<sharedLibrary.path>/src/lib/<t>-<name>/`, renamed to the target names (create the target folder first).
5. **Inside the moved files**, apply the identity map: class name, selector, `host.class`, `templateUrl` and `styleUrl` (new filenames), tokens, CSS classes, and the story `title`.
6. **Barrels, the cycle-safe rule:**
   - REMOVE the export from the source library's `src/index.ts` (and any sub-barrel).
   - NEVER replace it with an `export ... from '<shared alias>'`: that makes the domain library depend on the shared library and invites a cycle.
   - ADD `export * from './lib/<t>-<name>/<t>-<name>.component';` to the shared library's `src/index.ts`.
7. **Repoint every consumer, discovered now across the whole workspace:**
   - Symbol: search `*.ts` for `\b<P><Name>Component\b` and rename it to `<T><Name>Component` (imports, `imports: []`, types, injection).
   - Import specifier: in those files, swap the source alias for the shared alias for this symbol. If the same import statement also pulls other symbols from the source library, split it and keep the rest on the source import.
   - Template selector: search `*.html` for `<p>-<name>` and rewrite the open and close tags, plus any `[attr]` or comma-selector forms, to `<t>-<name>`.
8. **Post-check (cycle guard):** no file under any domain design library's `src` imports the shared alias, and the old `<p>-<name>` selector and `<P><Name>Component` do not resolve from the source library.
9. **Verify** with `promote.verify`. It must exercise the shared library, the source library and every touched consumer. Fix all fallout; never leave red.
10. **Commit** on a branch. Message: `refactor(<commitScope>): promote <p>-<name> to <t>-<name> (<domain> to shared)`, in the repo's commit format.

## Rules

- **One component per run.** Its `.ts`, `.html`, `.scss`, `.spec.ts` and `.stories.ts` move together; nothing else.
- **Full prefix swap.** Keep the shared prefix everywhere: folder, files, selector, host class, class name, tokens, CSS. Never strip to bare names.
- **Never re-export a shared component from a domain barrel.** Remove the domain export and repoint consumers instead; this is the most common cycle source.
- **Whole-identifier matches only.** After the run, a search for `\b<P><Name>Component\b` and for `<p>-<name>` returns nothing across the workspace, barring unrelated names.
- If the component trips a guardrail, it is NOT ready to promote: stop and report; never force it.
- Shared components stay presentational (no store); follow the repo's design-library standard.
