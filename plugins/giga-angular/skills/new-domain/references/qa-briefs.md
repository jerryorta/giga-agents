# QA and validation briefs

The orchestrator substitutes every placeholder and drops each *(only when …)* line whose value is absent, as for the worker briefs. Every QA agent follows the same rules: fix minor issues directly (a wrong prefix string, a missing JSON property, an incorrect import path, a misplaced block); report structural issues without guessing at a fix — stop and say what is wrong and where.

---

## QA 1 — App

```
You are a QA agent verifying a new domain's app post-generation setup.

Domain: <domain> | Prefix: <prefix> | Port: <port>
App: <appsRoot>/<domain>/app | Reference app: <appsRoot>/<ref>/app

FIRST — re-read the app sections of <guide> independently. Do not assume the worker
was correct.

Read and verify, against the guide and the reference app:
- the app's Tailwind entry: it scans the app and every library it depends on
- src/styles.scss: the theme @use comes before Tailwind, the mixin call comes last
- src/index.html: the theme class on <html>, the inline body background, the icon font
  the reference app loads, <prefix>-root in the body
- src/app/app.config.ts: the reference app's change detection (zoneless: no Zone.js
  provider or polyfill)
- (only when release is given) app.config.ts calls <release.symbol>({ ... }) with a
  served version JSON; no domain-specific release watcher exists (<release.check>
  reports none)
- (only when scripts are given) root package.json: <scripts.serve.name> serves
  <domain>-app on port <port>; <scripts.build.name> builds <domain>-app

Fix minor issues. Report structural issues without fixing.
```

---

## QA 2 — Themes

```
You are a QA agent verifying a new domain's themes library.

Domain: <domain> | Prefix: <prefix>

FIRST — re-read the themes section of <guide>, and <agentsMd.typeStandards>/themes.md
(only when given), independently.

Read and verify:
- every file under <libsRoot>/<domain>/themes/src/lib/styles/
- <appsRoot>/<domain>/app/project.json

Check specifically:
- <prefix>-themes.scss @uses every partial and exposes <prefix>-theme-mixin()
- every partial wraps its rules in a mixin: no top-level CSS rules
- the dark theme defines the --<prefix>-* tokens under the theme class the guide names
- stylePreprocessorOptions sits in the build target's top-level options block, NOT
  inside a named configuration, and its includePaths names
  <libsRoot>/<domain>/themes/src/lib/styles
- (only when scripts are given) every configuration <scripts.serve.command> names
  exists on BOTH the build and the serve targets, and serve's buildTarget points at
  <domain>-app:build:<that configuration>

Fix minor issues. Report structural issues without fixing.
```

---

## QA 3 — Libs (and Storybook, when its worker ran)

```
You are a QA agent verifying the post-generation corrections of a new domain's libraries.

Domain: <domain> | Prefix: <prefix>
Libraries (type → generator): <each newDomain.libs entry>

FIRST — re-read the post-generation corrections in <guide> independently.

For every library made by an @nx/angular:* generator that has tests:
- src/test-setup.ts uses the reference libraries' setup (zoneless: imports from
  jest-preset-angular/setup-env/zoneless and calls setupZonelessTestEnv, not the
  Zone.js variant)
- eslint.config.mjs: both selector rules have prefix: '<prefix>' (not 'lib')

For the design-library library:
- project.json carries the @nx/angular:component generators block

For every library made by @nx/js:library:
- project.json has a lint target

(only when frameworkFreeLib is given) For each library in <frameworkFreeLib.libs>:
- eslint.config.mjs spreads <frameworkFreeLib.export> after the base config

(only when the Storybook worker ran) In <storybook.app>:
- .storybook/main.ts lists the design library's stories glob
- project.json's build options includePaths name the domain's theme folder
- src/styles.scss @uses <prefix>-themes and calls its mixin, in the file's order
- .storybook/tsconfig.json includes the stories and component globs and excludes the spec glob

Fix minor issues. Report structural issues without fixing.
```

---

## Validation

```
Run validation for the new domain <domain>. Execute these commands in sequence with
Bash. Stop at the first failure and report the error with its file path and line
number where available.

1. Reset the Nx graph FIRST. The Phase 2 edits to nx.json and .nxignore while the
   generators ran can leave the daemon's project graph stale — symptoms are a spurious
   "Could not find project <domain>-<type>" and a build that cannot find the
   '<prefix>-themes' stylesheet. A reset clears it:
   npx nx reset

2. Lint every domain project WITH --fix. Generated stub code can break the repo's
   stricter ESLint rules (import and key sorting, type-only imports); --fix resolves
   those. Remaining warnings do not fail the run.
   npx nx run-many --target=lint --fix --projects=<every project, the app included>

3. Test every domain project that has tests:
   npx nx run-many --target=test --projects=<every project except those with tests: false>

4. Build the app:
   npx nx run <domain>-app:build

Report each project as pass or fail. On a failure, include the error output, file and
line. If all pass, confirm the domain is ready for feature development.
```
