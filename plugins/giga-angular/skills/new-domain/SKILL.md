---
name: new-domain
description: Set up a complete new domain in an Nx monorepo — an Angular app plus its library set — from the repo's own config. Settles the domain name, prefix and port with the user, runs the Nx generators in order, hands post-generation configuration to parallel worker agents, checks their work with QA agents, writes each library's AGENTS.md pointer, and validates lint, tests and build. Each repo-specific step (placeholder directories, module boundaries, Storybook registration, release wiring, a framework-free lint rule, the brand voice guide) runs only when its config field is set. Use when the user wants a new domain, vertical or product area with its own app and libraries. Does NOT add a library to an existing domain, build features, or create a backend, a secrets payload, or a desktop or mobile app.
---

# New Domain

Set up a new domain — `<appsRoot>/<domain>/app` and its libraries under `<libsRoot>/<domain>/` — and leave it linting, testing and building. This skill orchestrates: the Nx generators make the projects, worker agents apply what the generators don't, QA agents check the workers, and a validation agent proves the result. The repo's domain guide (`newDomain.guide`) is the authoritative source for file contents; every agent reads its section before acting, and the reference domain (`newDomain.referenceDomain`) shows the shape wherever the guide is silent.

## Project config

Repo-specific values come from `.claude/giga/config.json` at the repository root, under `angular` unless a field is named from the root. Read it once at the start. A missing file or field takes the fallback below, never a guess.

| Field | Used for | When absent |
| --- | --- | --- |
| `newDomain.scope` | the path-alias scope: libraries import as `<scope>/<domain>-<type>` | the scope most `paths` in `tsconfig.base.json` share, confirmed with the user in Phase 1 |
| `newDomain.appsRoot` · `newDomain.libsRoot` | where the app and the libraries go | `apps` · `libs` |
| `newDomain.app` | `{ generator, flags }` for the app | `@nx/angular:application` with `--routing=true --e2eTestRunner=none` |
| `newDomain.libs` | the library set, in generation order: `{ type, generator, flags, tests }` (`tests: false` for a library generated without a test runner) | propose `models`, `store`, `themes`, `ui`, `design-library` and `utils`, and generate nothing until the user confirms the set and each generator |
| `newDomain.tags` | the tag pattern every project carries; `<type>` is the library type, or `app` for the app | the tags the reference domain's projects carry, with its name replaced; with no reference domain, ask |
| `newDomain.guide` | the repo's domain guide; each agent reads its section before acting, and it wins over the briefs | the briefs' own steps are the standard |
| `newDomain.referenceDomain` | the existing domain whose app and libraries the workers copy where the guide is silent | the guide alone, then the briefs' own steps |
| `newDomain.themeExample` | the themes styles folder the Themes worker models its structure on | the guide's themes section, then the brief's built-in structure |
| `newDomain.scripts` | `{ serve, build }`, each `{ name, command }`: the root `package.json` scripts for the app; the `serve` name pattern also finds the ports in use | no scripts are written |
| `newDomain.stubs` | `{ dirs, nxignore, eslintExclude }`: placeholder directories outside the Nx graph and the ignore entries that keep them out | no placeholder directories |
| `newDomain.moduleBoundaries` | the ESLint config whose module-boundary constraints get the new `scope:` entries | no boundary rule is touched, and the final report says the new scope has none |
| `newDomain.release` | `{ symbol, module, doc, check, followUps }`: the shared release-update provider the app wires | no release wiring |
| `newDomain.frameworkFreeLib` | `{ config, export, libs, example }`: the lint rule that keeps the named libraries free of framework imports | no framework-free rule |
| `newDomain.backend` | `{ dir, aliasFiles, aliasLibs, shared, example }`: how a backend compiles the domain's framework-free libraries from source, given as a next step | no backend step |
| `newDomain.secrets` | `{ doc }`: how a domain gets its secrets library | no secrets question or step |
| `newDomain.agentsMd` | `{ typeStandards, constraints, deltaExample, sync }`: the per-type standards each library's AGENTS.md points at, the constraints doc, the library whose AGENTS.md shows domain-specific additions, and the command that regenerates files derived from AGENTS.md | no Phase 4b |
| `newDomain.voiceGuide` | `{ questionnaire, model, rule }`: the owner questionnaire, the guide the new one is shaped like, and the rule that a brand's voice comes before its copy | no Phase 1b |
| `newDomain.nextSteps` | extra lines for the final report's next steps | none |
| `prefix` | the shared component prefix the new prefix must not reuse | only the `prefix` in each `project.json` is checked |
| `storybook.app` | the Storybook app the new design library registers with | no Storybook worker |
| `globalStore.stores` · `globalStoreSkill` | the store libraries named as state-pattern references in Phase 4b; the skill that builds a global slice | none named · `/giga-angular:ngrx-global-store` |
| `workflow.devServers` (root) | the ports already in use, and the entry Phase 6 adds for the new app | the port comes from the serve scripts alone, and no entry is added |
| `ux.brandVoice.guides` (root) | where Phase 1b registers the new brand's voice guide | Phase 1b writes the guide and reports that the repo has no guide registry |

**Placeholders.** `<domain>` (kebab-case), `<prefix>`, `<port>`, `<Domain Title>` (Title Case, e.g. `acme-portal` → `Acme Portal`) and `<type>` stand for the confirmed values in config strings and in the briefs. Every library is the Nx project `<domain>-<type>` at `<libsRoot>/<domain>/<type>`; the app is `<domain>-app` at `<appsRoot>/<domain>/app`. Substitute every placeholder literally before launching an agent.

---

## Phase 1 — Domain ideation

Ask the user:

> "Describe what this domain will build, solve, or present — its purpose, who uses it, what it does. I'll propose a domain name and prefix from your description."

From their response, propose:

- **Domain name** — kebab-case, concise, descriptive (e.g. `acme-portal`).
- **Prefix** — 2–3 letter initials (e.g. `ap`). It must differ from the shared prefix (`prefix`) and from every `prefix` in the repo's `project.json` files.
- **Port** — the next free one: above every `port` in `workflow.devServers` and every `--port` in the root `package.json` scripts named like `scripts.serve.name`. With neither, ask.

If the description is ambiguous, present 2–3 name options with reasoning. Do not proceed until the user confirms all three. With `newDomain.secrets` set, also ask whether the domain will consume a secrets payload (default no). Without `newDomain.libs`, confirm the library set now.

---

## Phase 1b — Voice guide (with the owner, while Phases 2–5 run)

Only when `newDomain.voiceGuide` is set. A brand's voice is set before its copy, never inferred from screens (`voiceGuide.rule`). Start once the Phase 1 values are confirmed and the Phase 2 and 3 work is running; it needs the owner, not the generated code.

1. Gather the owner's answers to the questions in `voiceGuide.questionnaire`: in chat one question at a time, or, when the owner will answer offline, in the form the questionnaire describes. Draft once the answers are back.
2. Draft the guide beside `voiceGuide.model`, as `<domain>.md`, in the model's shape. With no app copy yet, every example is written fresh to the voice.
3. Add the brand to `ux.brandVoice.guides`: its `apps` (`<domain>` and any marketing app), its `file`, and `status: "draft"`.
4. Walk the owner through the guide's open decisions one at a time and record the answers under `## Owner decisions — <date>`. Set the entry's `status` to `owner decisions recorded` once none is open.

The domain is not ready for its first user-facing story until the owner has approved the guide.

---

## Phase 2 — Root wiring (background agent)

Only when `newDomain.stubs` or `newDomain.moduleBoundaries` is set. Launch it as soon as Phase 1 is confirmed; it runs in parallel with Phase 3 and edits only root files the generators leave alone. Its brief is § Root wiring in `${CLAUDE_SKILL_DIR}/references/worker-briefs.md`.

---

## Phase 3 — Sequential Nx generation (orchestrator)

Read the guide's section on creating a domain before running any command. Run each generator directly with Bash, one at a time, and verify the expected file after each. If a generator fails, stop and report the error to the user — do not continue.

**1. The app:**

```bash
npx nx generate <app.generator> <appsRoot>/<domain>/app \
  --name=<domain>-app \
  --prefix=<prefix> \
  <app.flags> \
  --tags="<tags, with <type> = app>"
```

Verify: `<appsRoot>/<domain>/app/src/main.ts` exists.

**2. Each library in `newDomain.libs`, in order:**

```bash
npx nx generate <lib.generator> <libsRoot>/<domain>/<type> \
  --name=<domain>-<type> \
  --prefix=<prefix> \
  <lib.flags> \
  --tags="<tags, with <type> = the library type>"
```

Pass `--prefix` only to an `@nx/angular:*` generator; `@nx/js:library` has no prefix. Verify: `<libsRoot>/<domain>/<type>/project.json` and `src/index.ts` exist.

> The Nx CLI adds the `tsconfig.base.json` path aliases and, given `--prefix`, the ESLint selector prefixes. The workers handle only what the CLI does not.

---

## Phase 4 — Post-generation workers (parallel)

Launch every worker that applies, at once. Each receives the confirmed values and the config values its brief names, and reads its guide section before changing anything. Briefs: `${CLAUDE_SKILL_DIR}/references/worker-briefs.md`.

| Worker | Runs when | Owns |
| --- | --- | --- |
| 1 — App | always | the app's styles, `index.html`, app config, release wiring, root `package.json` scripts |
| 2 — Themes | the set has a `themes` library | the themes library and the app's `project.json` |
| 3 — Libs | always | every library's test setup, lint config and `project.json` |
| 4 — Storybook | `storybook.app` is set and the set has a `design-library` | the Storybook app's config and styles |

One owner per file: the app's `project.json` belongs to the Themes worker alone, so no two agents edit it.

---

## Phase 4 QA — QA agents (parallel, after every worker completes)

Launch one QA agent per worker that ran (the Storybook worker's checks fold into Libs QA). Each re-reads its guide section independently and checks the worker's output with fresh eyes. Briefs: `${CLAUDE_SKILL_DIR}/references/qa-briefs.md`.

- Fix minor issues directly (a wrong prefix string, a missing JSON property, an incorrect import path, a misplaced block).
- Report structural issues to the orchestrator without guessing at a fix: stop and say what is wrong and where.

---

## Phase 4b — AGENTS.md pointers (after QA completes)

Only when `newDomain.agentsMd` is set. Each library's AGENTS.md is a **thin pointer** to its per-type standard (`<agentsMd.typeStandards>/<type>.md`), the single source shared by every library of that type. The generated file carries only genuine domain-specific additions, added later as the domain grows (`agentsMd.deltaExample` shows the kind) — never a copy of the type standard.

The `store` and `ui` type standards keep the state layers apart: global domain data is a classic `@ngrx/store` slice in `<domain>-store`, exposed through a facade that `<domain>-ui` and the app inject; local UI state is a component-scoped SignalStore colocated with its component. The store libraries in `globalStore.stores` are the live shapes to mirror; slices are built with the skill in `globalStoreSkill` (absent: `/giga-angular:ngrx-global-store`) and component state with `/giga-angular:ngrx-component-state`.

Not an agent task — run it directly with Bash:

```bash
# Set these to the confirmed values, then run the rest verbatim.
DOMAIN="<domain>"
DOMAIN_TITLE="<Domain Title>"
LIBS_ROOT="<libsRoot>"
TYPE_STANDARDS="<agentsMd.typeStandards>"
CONSTRAINTS="<agentsMd.constraints>"
LIB_TYPES="<each newDomain.libs type, space-separated>"

for lib in $LIB_TYPES; do
  case "$lib" in
    ui) disp="UI" ;;
    *) disp=$(printf '%s' "$lib" | awk -F- '{for (i = 1; i <= NF; i++) $i = toupper(substr($i, 1, 1)) substr($i, 2)} 1' OFS=' ') ;;
  esac
  if [ ! -f "$TYPE_STANDARDS/$lib.md" ]; then echo "NO TYPE STANDARD for $lib — report it"; continue; fi
  cat > "$LIBS_ROOT/$DOMAIN/$lib/AGENTS.md" <<EOF
# $DOMAIN_TITLE $disp — Contributor Notes

> **Type standard** (auto-injected on write): \`$TYPE_STANDARDS/$lib.md\`
> **Workspace invariants**: \`$CONSTRAINTS\`

Add only genuine $DOMAIN_TITLE-specific content below (concrete primitive inventory, domain rules) — never restate the type standard or the constraints.
EOF
done

# Guard: every AGENTS.md points at its type standard.
grep -L "$TYPE_STANDARDS/" "$LIBS_ROOT/$DOMAIN"/*/AGENTS.md && echo "MISSING POINTER — investigate" || echo "OK: all AGENTS.md point at their type standard"
```

The guard must print `OK: all AGENTS.md point at their type standard`. Then run `agentsMd.sync` when it is set.

When a per-type convention changes, its one standard file is edited; every AGENTS.md points at it, so nothing needs regenerating.

---

## Phase 5 — Validation agent

Launch one agent with § Validation in `${CLAUDE_SKILL_DIR}/references/qa-briefs.md`, passing every project name and the names of the libraries with `tests: false`.

---

## Phase 6 — Register the app with the dev-server config

When the root config has `workflow.devServers` and `newDomain.scripts.serve` is set, add the new app's entry beside the others: `app: "<domain>"`, `command: "npm run <serve name>"`, `port: <port>`, a `logFile` named like its neighbours', `kind: "app"`. `/giga-workflow:dev-server` then launches it like any other app.

---

## Final report

Once Phase 5 completes, report to the user:

```
Domain `<domain>` is ready.

Structure:
  <appsRoot>/<domain>/app/
  <each stubs.dirs entry>   (placeholder, outside the Nx graph)
  <libsRoot>/<domain>/{<each library type>}/

Path aliases registered in tsconfig.base.json: pass
Scripts: <serve name> (port <port>) · <build name>          — when scripts are configured
Module boundaries: scope:<domain> added                       — or: none configured
Lint: pass · Tests: pass · Build: pass
Voice guide: <file> — <owner-approved | draft, N decisions open>   — when Phase 1b ran

Next steps:
- If the voice guide is still a draft, settle its open decisions with the owner before the first user-facing story
- Add the domain font and real color values to <libsRoot>/<domain>/themes/
- Replace the placeholder colors in <appsRoot>/<domain>/app/src/index.html
- <release.followUps, each>                                       — when release wiring ran
- When <backend.dir> exists: alias <scope>/<domain>-<each backend.aliasLibs type> (and its /* form) to its src in each of backend.aliasFiles the backend has, as <backend.example> does; alias <backend.shared.alias> the same way only when <backend.shared.when>
- Secrets: follow <secrets.doc> once the payload repo exists     — when the user said the domain needs one
- <each newDomain.nextSteps line>
```

If validation failed, list what needs manual attention before the domain is usable.

---

## What this skill deliberately does NOT do

- **Hand-write a project.** Every app and library comes from an Nx generator; workers only correct and extend generated files.
- **Guess the library set, tags or alias scope.** Without config they are confirmed with the user before Phase 3.
- **Create a backend, a secrets payload, or a desktop or mobile app.** Their placeholders and next steps are all it leaves.
- **Write the domain's features, components or slices.** It stops at a domain that lints, tests and builds.
- **Copy a type standard into an AGENTS.md.** The file points at the standard and carries only domain-specific additions.
