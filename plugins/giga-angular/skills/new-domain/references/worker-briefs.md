# Worker briefs

The orchestrator substitutes every placeholder (`<domain>`, `<prefix>`, `<port>`, `<appsRoot>`, `<libsRoot>`, `<guide>`, `<ref>` for `newDomain.referenceDomain`, and the config values each brief names) before launching. A line marked *(only when …)* is dropped from the prompt when that value is absent. Where `<guide>` is absent, drop its "read first" lines; where `<ref>` is absent, drop the reference lines.

---

## Root wiring

Launched in Phase 2, in parallel with the generators. Target directories are outside the Nx project graph; the files it edits are root files the generators leave alone.

```
Working directory: the repository root.

Domain: <domain> | Reference domain: <ref>

Do only the tasks whose values are given below.

1. Placeholder directories (stubs.dirs: <list>): for each, run mkdir -p <dir> and
   touch <dir>/.gitkeep. A directory that is not also listed in step 2 or 3 (a docs
   folder, for example) is markdown only, not an Nx project, and needs no ignore entry.

2. .nxignore (stubs.nxignore: <list>): add each line alongside the other per-domain
   app entries. Skip a line an existing wildcard already covers, and say so.

3. ESLint plugin exclude (stubs.eslintExclude: <list>): in nx.json, add each entry to
   the "exclude" array of the @nx/eslint/plugin entry, alongside the other per-domain
   app entries and before the generic wildcard entries.

4. Module boundaries (moduleBoundaries: <file>): in <file>, find every constraint whose
   sourceTag is scope:<ref>. Add the same constraint for scope:<domain> beside it, with
   scope:<ref> replaced by scope:<domain> in its tag lists. Change no other constraint.

Report each change with its file and line.
```

---

## Worker 1 — App

```
You are configuring the Angular app post-generation for a new Nx domain.

Domain: <domain> | Prefix: <prefix> | Port: <port>
App: <appsRoot>/<domain>/app | Reference app: <appsRoot>/<ref>/app

FIRST — read the app sections of <guide> (its post-generation steps for styles, the
app config, index.html and package.json scripts, and its workspace notes) before
touching any file. Where the guide gives a template, follow it. Where it is silent,
copy the shape of the reference app's file. The guide wins over this list.

Complete these tasks:

1. Tailwind: set up the app's Tailwind entry the way the guide and the reference app
   do (a tailwind.config.js built on createGlobPatternsForDependencies from
   @nx/angular/tailwind, or a CSS entry file), so the app and every library it
   depends on are scanned.

2. src/styles.scss: load the domain theme (@use '<prefix>-themes'), Tailwind, and the
   theme mixin call (@include <prefix>-themes.<prefix>-theme-mixin()), in the order and
   form the reference app uses.

3. src/index.html, per the guide: the theme class on <html>, an inline body background
   so the page never flashes white before the CSS loads (a placeholder color), font
   preconnect and font links (placeholders), the icon font the reference app loads, a
   theme-color meta (placeholder), and <<prefix>-root></<prefix>-root> in the body.

4. src/app/app.config.ts: match the reference app's change detection. For a zoneless
   reference, provideZonelessChangeDetection() and no Zone.js provider or polyfill.

5. (only when release is given) Release updates, per <release.doc>: add the version
   file and the served version JSON the doc names, and call <release.symbol>({ ... })
   from <release.module> in app.config.ts. Never write a domain-specific release
   watcher. List these as follow-ups in your report: <release.followUps>.

6. (only when scripts are given) Add to the root package.json scripts:
   "<scripts.serve.name>": "<scripts.serve.command>",
   "<scripts.build.name>": "<scripts.build.command>"

Do not edit <appsRoot>/<domain>/app/project.json: the Themes worker owns it.
Report every file changed.
```

---

## Worker 2 — Themes

```
You are scaffolding the SCSS theme library for a new Nx domain.

Domain: <domain> | Prefix: <prefix>
Themes library: <libsRoot>/<domain>/themes | App: <appsRoot>/<domain>/app

FIRST — read these before touching any file:
- the themes section of <guide>: its SCSS structure, mixin pattern and
  stylePreprocessorOptions wiring
- <agentsMd.typeStandards>/themes.md, the themes-library standard (only when given)
- every file under <themeExample>, the structural example (only when given)

Complete these tasks:

1. Create the theme's SCSS files under <libsRoot>/<domain>/themes/src/lib/styles/ in
   the structure the guide gives. With none in the guide, use:

   <prefix>-themes.scss      ← entry point: @use every partial, expose <prefix>-theme-mixin()
   _<prefix>-tokens.scss     ← documents every --<prefix>-* variable name (comments only, no values)
   _<prefix>-base.scss       ← reset, body styles, global layout, in a <prefix>-base() mixin
   <prefix>/
     _<prefix>-dark.scss     ← every --<prefix>-* token under html.<prefix>-dark, in a <prefix>-dark-theme() mixin
     _<prefix>-light.scss    ← light theme placeholder, in a <prefix>-light-theme() mixin

   Every partial wraps all its rules in a mixin: nothing emits CSS at @use time, only
   when <prefix>-themes.scss calls the mixin. Tokens are own-namespace --<prefix>-*
   custom properties with literal values.

2. When the guide says the themes library is style-only, or the reference domain's
   themes library has no src/index.ts, delete the generated stub component and barrel:
   rm -rf <libsRoot>/<domain>/themes/src/lib/<domain>-themes/
   rm <libsRoot>/<domain>/themes/src/index.ts

3. In <appsRoot>/<domain>/app/project.json, add the theme folder to
   stylePreprocessorOptions.includePaths in the build target's top-level options block
   (NOT inside any configuration), beside any shared theme paths the reference app lists:
   "stylePreprocessorOptions": {
     "includePaths": ["<libsRoot>/<domain>/themes/src/lib/styles"]
   }

4. (only when scripts are given) If <scripts.serve.command> names a configuration
   (serve:<config>) the generated app lacks, add <config> to BOTH the build and the
   serve targets in the same project.json, mirroring the reference app:
     build → configurations.<config>: { "optimization": false, "extractLicenses": false, "sourceMap": true }
     serve → configurations.<config>: { "buildTarget": "<domain>-app:build:<config>" }
   Without it the serve script fails.

Report every file changed.
```

---

## Worker 3 — Libs

```
You are applying post-generation corrections to a new domain's libraries.

Domain: <domain> | Prefix: <prefix>
Libraries (type → generator): <each newDomain.libs entry>
Reference libraries: <libsRoot>/<ref>/<type>

FIRST — read the post-generation corrections in <guide> and the section for each
library type before touching any file.

FOR EVERY LIBRARY MADE BY AN @nx/angular:* GENERATOR THAT HAS TESTS:

1. Replace src/test-setup.ts with the test setup the reference libraries use. For a
   zoneless reference:
   import { setupZonelessTestEnv } from 'jest-preset-angular/setup-env/zoneless';
   setupZonelessTestEnv({ errorOnUnknownElements: true, errorOnUnknownProperties: true });

2. In eslint.config.mjs, both selector rules use prefix '<prefix>'. The generator may
   have defaulted to 'lib' — correct it:
   '@angular-eslint/directive-selector': ['error', { type: 'attribute', prefix: '<prefix>', style: 'camelCase' }],
   '@angular-eslint/component-selector': ['error', { type: 'element', prefix: '<prefix>', style: 'kebab-case' }],

FOR THE design-library LIBRARY:

3. Add the generators block the guide or the reference design library's project.json
   carries, so every component generated in it defaults to the repo's conventions:
   "generators": {
     "@nx/angular:component": {
       "style": "scss",
       "changeDetection": "OnPush",
       "viewEncapsulation": "None",
       "displayBlock": true,
       "skipTests": false,
       "inlineStyle": false,
       "inlineTemplate": false
     }
   }

FOR EVERY LIBRARY MADE BY @nx/js:library:

4. If its project.json has no lint target, add one under "targets", as the reference
   domain's library of the same type has. Without it, inference runs a broken
   eslint command:
   "lint": { "executor": "@nx/eslint:lint" }

5. (only when frameworkFreeLib is given) In the eslint.config.mjs of each library in
   <frameworkFreeLib.libs>, import <frameworkFreeLib.export> from the root
   <frameworkFreeLib.config> beside the base config, and spread it after the base
   config, as <frameworkFreeLib.example> does. It makes a framework import a lint
   error, because a backend compiles that library from source.

Report every file changed.
```

---

## Worker 4 — Storybook registration

The domain's `design-library` is what Storybook registers. Its `ui` library is not registered by default (stories for its smart components can be added later), and the app never is.

```
You are registering a new domain's design library with the repo's Storybook app.

Domain: <domain> | Prefix: <prefix> | Storybook app: <storybook.app>

FIRST — read these before touching any file:
- the Storybook registration section of <guide>
- <storybook.app>/.storybook/main.ts (the existing stories entries)
- <storybook.app>/project.json (the existing stylePreprocessorOptions block)
- <storybook.app>/src/styles.scss (the existing theme @use / @include lines)
- <storybook.app>/.storybook/tsconfig.json (the existing include / exclude entries)

Complete these tasks, matching the relative depth and form of the existing entries:

1. In .storybook/main.ts, add to the stories array:
   '<relative path>/<libsRoot>/<domain>/design-library/src/**/*.@(mdx|stories.@(js|jsx|ts|tsx))'

2. In project.json, add to stylePreprocessorOptions.includePaths in the build target's
   top-level options block (not inside a configuration):
   "<libsRoot>/<domain>/themes/src/lib/styles"

3. In src/styles.scss, add @use '<prefix>-themes'; beside the other theme @use lines,
   and @include <prefix>-themes.<prefix>-theme-mixin(); beside the other theme mixin
   calls, keeping the file's existing order.

4. In .storybook/tsconfig.json, add to "include" the design library's *.stories.ts and
   *.component.ts globs, and to "exclude" its *.spec.ts glob.

The stories glob in main.ts controls discovery; the tsconfig entries are needed
separately for compilation. Both are needed, or the build fails.
Report every file changed.
```
