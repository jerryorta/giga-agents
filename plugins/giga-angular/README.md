# giga-angular

Seven Angular skills that take your repo's conventions from config. They write Storybook stories, place component and global state, scaffold a domain, check theming and accessibility, and promote a component to a shared library. This page says what the plugin needs, what each skill reads, and what it does when your config has no `angular` key.

## What it needs

- **Angular**, for every skill.
- **Nx**. `/giga-angular:new-domain` runs the Nx generators, and `/giga-angular:ngrx-component-state` and `/giga-angular:ngrx-global-store` check their work with `npx nx run <project>:lint` and `:test`.
- **NgRx**, and a local clone of the NgRx `platform` repo for the two NgRx skills, which take their API guidance from it. They find it through `angular.ngrxDocs` or `$NGRX_DOCS`.
- **Storybook**, for `/giga-angular:create-storybook`.
- **Nothing from the other plugins.** A few skills read an optional field outside `angular`, named in its row below, and each has a fallback.

## With an empty config

The skills read their values from `angular` in `.claude/giga/config.json`. Each `SKILL.md` has a `## Project config` table that lists the fields it reads and what it does without each. [Per-repo config](../../README.md#per-repo-config) shows an `angular` block in full.

No skill guesses. Each missing field falls back to a default the skill ships with, to what your code already shows, or to a question for you; the last column below sums up each skill.

## Skills

| Skill | Use it to | Reads | With no config |
| --- | --- | --- | --- |
| [`/giga-angular:create-storybook`](skills/create-storybook/SKILL.md) | write a component's four-file story set, inside your Storybook review container | `prefix`, `storybook` | renders the component in a plain wrapper with no review container, shaped like the story nearest it |
| [`/giga-angular:ngrx-component-state`](skills/ngrx-component-state/SKILL.md) | decide where each piece of a component's state belongs and build its colocated SignalStore | `componentState`, `ngrxDocs`, `globalStoreSkill` | builds from the NgRx docs and its own generic layout; asks for the NgRx clone and stops until you answer, unless `$NGRX_DOCS` is set |
| [`/giga-angular:ngrx-global-store`](skills/ngrx-global-store/SKILL.md) | create or refactor a global `@ngrx/store` slice and register it | `globalStore`, `ngrxDocs` | asks for the NgRx clone the same way, and for the target library; follows that library's existing slices, with no Firestore section |
| [`/giga-angular:new-domain`](skills/new-domain/SKILL.md) | scaffold a new domain's app and library set with the Nx generators | `newDomain`, `prefix`, `storybook.app`, `globalStore.stores`, `globalStoreSkill`; `workflow.devServers` and `ux.brandVoice.guides` from the root | proposes a library set and generates nothing until you confirm it; skips every optional step |
| [`/giga-angular:verify-theming`](skills/verify-theming/SKILL.md) | replace a file's hardcoded colors and stray classes with its library's design tokens | `prefix`, `theming`; `workflow.notify` from the root | takes the prefix from the library's `project.json` and the token file from a themes library beside it, asking when either is missing; flags no banned namespace |
| [`/giga-angular:verify-accessibility`](skills/verify-accessibility/SKILL.md) | add the accessible names and test ids a file's templates are missing | `accessibility` | applies its generic rules only |
| [`/giga-angular:promote-component`](skills/promote-component/SKILL.md) | move one component from a domain design library into the shared one | `promote`; `workflow.commit.scopeRules` and `workflow.checks.affected` from the root | asks for the shared library's path, prefix and alias, and stops until you answer |

`/giga-angular:verify-theming` ends by running `/giga-angular:verify-accessibility` on the same file. `/giga-angular:ngrx-component-state` hands a new global slice to the skill named in `angular.globalStoreSkill`, which defaults to `/giga-angular:ngrx-global-store`.
