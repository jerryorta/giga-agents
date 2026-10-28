---
name: ngrx-global-store
description: Create or refactor a classic global `@ngrx/store` slice (actions, reducer, effects, selectors, facade) laid out like the repo's own store slices and registered where the repo registers them. Hybrid skill — authoritative API guidance comes from a local NgRx clone (kept current via `git pull`); layout, registration and backend conventions come from the repo's reference slices, with an optional Firestore section (realtime listeners, snapshot-authoritative writes, per-write state) for repos whose slices are fed by Firestore. Use when the user wants to add a global store slice, wire effects, introduce `@ngrx/entity`, integrate `@ngrx/router-store`, connect a realtime Firestore listener to state, or refactor an existing slice. Does NOT handle component-scoped SignalStore work or decide where a component's state belongs — `/giga-angular:ngrx-component-state` does.
---

# NgRx Global Store

Build or refactor one slice of the global `@ngrx/store`: actions, reducer, effects, selectors and the facade components inject. This skill owns the **slice**; deciding which of a component's concerns belong in the global store, and wiring the facade into the component, belong to `/giga-angular:ngrx-component-state`.

Hybrid skill: authoritative `@ngrx/store`, `@ngrx/effects`, `@ngrx/entity` and `@ngrx/router-store` API docs live in a local NgRx clone (kept current via `git pull`). Layout, registration and backend wiring come from the repo's reference slices (`globalStore.stores`).

## Project config

Repo-specific values come from `.claude/giga/config.json` at the repository root, under `angular`. Read it once at the start. A missing file or field takes the fallback below, never a guess.

| Field | Used for | When absent |
| --- | --- | --- |
| `globalStore.layout` | the slice folder shape: `folder-per-slice` (one `+<slice>/` folder per slice under `src/lib/`) or `flat` (the slice's files directly in `src/lib/`) | the shape the target library's existing slices use; an empty library takes the generic layout in Phase 3 |
| `globalStore.stores` | one entry per store library: `{ name, lib, alias, registration, registrationNote, references, standards, helpers }`. `lib` is the library root, `alias` its barrel import, `registration` the file where its reducers, effects and listeners are registered, `registrationNote` how that file registers them | ask the user for the target library in Phase 1; find its registration by searching the app roots for `provideStore` / `provideState` / `provideEffects` |
| `globalStore.stores[].references` | the slices Phase 3 teaches from: `{ path, note }` entries, each note saying what that slice shows | the existing slice in the target library nearest the new one; with none, the generic layout in Phase 3 and the NgRx docs |
| `globalStore.standards` · `globalStore.stores[].standards` | the repo's store standards, and the target store's own: every slice this skill creates or refactors satisfies them, and they win over this skill's text | the invariants under **Standard** below are the standard |
| `globalStore.firestore` | its presence turns on the Firestore section (`${CLAUDE_SKILL_DIR}/references/firestore.md`); it holds `helpers` and `standards` | no Firestore section: the slice's backend is whatever its reference slices call, wired as Phase 4 shows |
| `globalStore.firestore.helpers` · `globalStore.stores[].helpers` | the repo's Firestore helpers by key — `firestoreService`, `listenerContract`, `writeEffect`, `writeState`, `queryCache` — each `{ symbol, module, note }`; a store's own key wins over the shared one | a missing key: copy the pattern from the reference slice that uses it; with none, write it by hand as the Firestore section shows, and never invent a helper name |
| `globalStore.firestore.standards` | the repo's Firestore rules, read with the Firestore section | the section's invariants are the standard |
| `ngrxDocs` | the local clone of NgRx `platform` the API guidance comes from; `$NGRX_DOCS` wins when set | with `$NGRX_DOCS` unset too, ask the user for the clone and stop until they answer |

---

## Standard (read first)

Read every doc in `globalStore.standards` and in the target store's `standards` before writing. Every slice this skill creates or refactors toward MUST satisfy them and the invariants below; where they differ, the configured standards win.

- **The facade is the only consumption surface.** Components and pages inject the slice's `*.facade.ts`, never `Store` or a selector. The facade exposes reads as signals (`store.selectSignal(selector)`) for templates and as observables (`store.select(selector)`) where they compose into other streams, plus one intent method per user action.
- **Logic lives in selectors and pure functions, not facades or components.** A facade is API, not logic. Derived values are `createSelector` over pure functions; an aggregation across slices goes in a dedicated aggregate-selectors file, never one slice importing a sibling's selectors.
- **Reducers are pure and local.** A reducer handles its own slice's actions and nothing else; side effects and cross-slice dispatches live in effects.
- **One action group per slice** (`createActionGroup`), one feature per slice (`createFeature` with a kebab-case `name`), `@ngrx/entity` adapters for keyed collections.
- **Registered where the store registers its slices.** The slice's state and effects go in the store's registration file; an effect that is not registered never runs, and a feature that is not registered answers `undefined` from every selector — neither fails a build.
- **No `@ngrx/data` or `@ngrx/component-store` in new code.** Both are superseded: global data goes here, component-local state goes to a component-scoped SignalStore.

---

## Phase 0 — Resolve and refresh the local NgRx docs

### 0a — Resolve the path

1. `$NGRX_DOCS`, when the env var is set.
2. Otherwise `ngrxDocs` from the config, with a leading `~` expanded to `$HOME`.
3. Otherwise ask the user where their clone of `ngrx/platform` is (or to clone `https://github.com/ngrx/platform`) and stop until they answer.

Verify: `<path>/projects/www/src/app/pages/guide/store/` must exist, with `effects/`, `entity/`, `router-store/` and `store-devtools/` beside it. If it doesn't, ask the user for the clone's location and stop until they answer.

Substitute `$NGRX_DOCS` throughout the rest of this skill with the resolved path.

### 0b — Refresh the clone (best-effort, non-blocking)

Run the following with a 10-second timeout on the fetch (through `perl`, since macOS ships no `timeout`); never block the skill on a slow network:

```
cd $NGRX_DOCS
perl -e 'alarm shift; exec @ARGV' 10 git fetch --quiet 2>/dev/null || echo "fetch-failed"
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse @{u} 2>/dev/null || echo "")
DIRTY=$(git status --porcelain)
```

Then branch on the result:

- **`LOCAL == REMOTE`**, or `REMOTE` empty, or `fetch-failed` → skip the pull, proceed silently.
- **`REMOTE` ahead and `DIRTY` empty** → `git pull --ff-only` and report "Refreshed NgRx docs clone to `<REMOTE short sha>`."
- **`REMOTE` ahead and `DIRTY` non-empty** → skip the pull. Warn: "NgRx docs clone at `$NGRX_DOCS` has uncommitted changes; proceeding with current checkout. Pull manually if you want newer docs."
- **Fast-forward fails (diverged history)** → skip. Warn: "NgRx docs clone has diverged from upstream; proceeding with current checkout."

Whatever happens, continue to Phase 1. A stale-but-working clone is always better than stopping.

---

## Phase 1 — Clarify scope

Ask one at a time when answers shape later questions:

1. **Slice name and target store** — the slice (e.g. `notifications`) and which entry of `globalStore.stores` it joins (or which library, when none is configured). Name its folder by `globalStore.layout`: `+notifications/` for `folder-per-slice`; for `flat`, the files sit in `src/lib/` while the library holds one slice, and a second slice moves each slice into its own `src/lib/<slice>/` folder, file names unchanged and without a `+`.
2. **Data shape** — single document or record? Collection? Collection under a parent entity? Write-only?
3. **Source** — where the data comes from (an HTTP API, a seed, a realtime listener). With `globalStore.firestore` set, also: the Firestore path(s), and whether the slice listens, writes, or both.
4. **Writes** — create / update / delete patterns, debounced or not.
5. **Consumers** — who reads this state: app-wide, or one feature?
6. **Side effects** — navigation, toasts, analytics, dispatches to other slices on success?
7. **Entity semantics** — a keyed collection where `@ngrx/entity` adapters fit?
8. **Router coupling** — do route params drive reads?
9. **Existing code to refactor** — the path to the slice being migrated. Read it completely before Phase 2.

If the state is purely component-local and transient (wizard fields, toggles, one component's async channel) — **stop and recommend `/giga-angular:ngrx-component-state` instead**. The global store is the wrong tool for those.

---

## Phase 2 — Load relevant docs

Read only the guide sections that map to what you're building. Paths under `$NGRX_DOCS/projects/www/src/app/pages/guide/`:

### `store/` — core primitives

| Concern | File |
|---|---|
| Actions, `createActionGroup` | `store/actions.md` |
| Reducers, `createReducer`, `on` | `store/reducers.md` |
| Selectors, `createSelector`, `createFeature` | `store/selectors.md` |
| Feature state, `provideState` | `store/feature-creators.md` or `store/providing-store.md` |
| Meta-reducers | `store/metareducers.md` |
| Typed-actions conventions | `store/walkthrough.md` (start here when building a project's first slice) |

### `effects/` — action-driven side effects

| Concern | File |
|---|---|
| `createEffect`, `ofType`, subscribing to actions | `effects/index.md` |
| Lifecycle (`ROOT_EFFECTS_INIT`), dispatch control, filtering | siblings of the above |
| Testing effects with `provideMockActions` + marbles | `effects/testing.md` |

### `entity/` — collection adapters

Read when the slice holds a keyed collection with CRUD. Skip for a single document or a free-form object.

### `router-store/` — URL ↔ state

Read only when route params or navigation events drive reads.

### `store-devtools/` — time-travel

Read when setting up a new app's root store or debugging a specific slice. Adding a slice to an existing app needs nothing here.

### Don't read these for new code

- `component-store/` — the SignalStore predecessor; only when migrating one away.
- `data/` — `@ngrx/data` is legacy.
- `operators/` — niche; only for `ofType` quirks or `concatLatestFrom`.
- `eslint-plugin/` — rule config, not coding guidance.
- `migration/` — only during a version bump.

### API reference (structured metadata)

`$NGRX_DOCS/projects/www/src/app/reference/store/`, `effects/`, `entity/` and so on — JSON with each function's exact signature, for when a guide glosses over a parameter.

### Typical read sets

- **New single-record slice**: `store/actions.md` + `store/reducers.md` + `store/selectors.md` + `effects/index.md`.
- **New collection slice**: add the `entity/` guide.
- **Slice with navigation side effects**: add the navigation-after-success parts of `effects/index.md`.
- **Slice with URL coupling**: add the `router-store/` guide.
- **Effects added to an existing slice**: `effects/index.md` + `effects/testing.md`.

---

## Phase 3 — Read the reference slices

Layout comes from the target store's own slices. With `globalStore.firestore` set, read `${CLAUDE_SKILL_DIR}/references/firestore.md` now: it adds invariants, files and patterns to this phase and the next.

1. **Pick the reference that matches the case.** Each `references` entry is a `{ path, note }`; the note says what the slice shows (a single record with writes, a collection, a collection under a parent, a write-only slice, the sign-out reset). With no clear match, read the first entry.
2. **Read it before scaffolding**: its actions, reducer (or feature), effects and facade, and the spec beside each. Copy its conventions; don't reinvent them.
3. **Follow that reference's OWN file naming and effect style.** Repos differ — `<slice>.reducer.ts` + `<slice>.selectors.ts` in one, a single `<slice>.feature.ts` holding `createFeature` with its reducer and `extraSelectors` in another; functional effects (`createEffect(fn, { functional: true })`) in one, an `@Injectable()` effects class in another. Inside an existing library, its slices win.
4. **Read the registration file** (`registration`) and its `registrationNote`: where a reducer, an effect and any listener service get registered.

With no `references`, Glob the target library for `*.reducer.ts` and `*.feature.ts`, and follow the slice nearest the new one; with none, use the generic layout below and the NgRx docs.

### Generic layout

```
<slice>/                         ← or src/lib/ itself, for a flat store holding one slice
  <slice>.model.ts               ← the entity or record type and the slice's state interface
  <slice>.actions.ts             ← createActionGroup
  <slice>.reducer.ts             ← feature key + initial state + on() handlers (entity adapter for a collection)
  <slice>.selectors.ts           ← createFeature selectors + derived selectors
  <slice>.effects.ts             ← side effects: backend calls, navigation, cross-slice dispatches
  <slice>.facade.ts              ← the surface components inject
  index.ts                       ← barrel
  + a spec beside each
```

A store that combines reducer and selectors in one `<slice>.feature.ts` (`createFeature({ name, reducer, extraSelectors })`) is equally canonical; follow whichever the reference uses.

---

## Phase 4 — Scaffold

Write files in dependency order so each can reference the previous, named as the reference names them. The Firestore section replaces steps 5 and 6 when it is on.

1. **Model** — the record type and the state interface. State carries the load lifecycle the reference uses (e.g. `status: 'idle' | 'loading' | 'loaded' | 'error'` plus `error: string | null`), and an entity state for a collection.
2. **Actions** — `createActionGroup({ source: '<Slice>', events: { ... } })`: the load lifecycle (`Load` / `Load Success` / `Load Failure`) and, per write, a dedicated `Create …` / `Update …` / `Delete …` with its `Success` and `Failure`.
3. **Reducer** — the feature key in kebab-case, the initial state, one `on()` per action; `createEntityAdapter` per keyed collection (`setAll` / `setOne` / `setMany` for loaded data). Handlers move `status` and `error`.
4. **Selectors** — `createFeature` gives the base selectors; add each adapter's `getSelectors()` and derived selectors with `createSelector` over pure functions (in the domain's utils library when it has one).
5. **Backend service** (when the slice reads or writes a backend) — an `@Injectable({ providedIn: 'root' })` service whose methods return `Observable`s, as the reference's service does.
6. **Effects** — `ofType(trigger)` → a flattening operator chosen by intent (`switchMap` for a read that a newer one cancels, `concatMap` for ordered writes, `exhaustMap` to ignore repeats while busy) → `map(success)` with `catchError(error => of(failure({ error: String(error) })))` inside the inner observable, so one failure never kills the effect. Cross-slice dispatches go here, never in a reducer.
7. **Facade** — `@Injectable({ providedIn: 'root' })`; reads per **Standard** above, one method per intent that dispatches the matching action.
8. **Barrel** — the slice's `index.ts` re-exports its public surface.
9. **Register** in the store's `registration` file, as its `registrationNote` says: the reducer or feature, the effects, and any service that must exist from boot. With no `registration`, add a `provide-<slice>-store.ts` returning `makeEnvironmentProviders([provideState(<slice>Feature), provideEffects(<Slice>Effects)])`, called once in the app root's `providers` after the root `provideStore()`.
10. **Library barrel** — export the slice from the library's `src/index.ts`, so consumers import it from the store's `alias`.
11. **Specs** — one beside the reducer (or feature), selectors, effects (`provideMockActions`), facade and each service, in the reference's spec shapes. Async specs follow the reference; in a zoneless repo they never use `fakeAsync` / `tick`.

**Sign-out reset.** When the slice must clear on sign-out, use the store's reset mechanism — the reference whose note names it (a clear-state meta-reducer resets every eagerly registered slice to its initial state with no wiring per slice). With none, give the slice a `reset` action and dispatch it from an effect on the sign-out success action.

---

## Phase 5 — Verify

1. `npx nx run <project>:lint` — clean on the touched files.
2. `npx nx run <project>:test` — the new specs pass.
3. Type-check at consumers: `inject(<Slice>Facade)` and its reads resolve.
4. **Registration** — confirm the feature, the effects and any boot-time service are in the registration file, or that `provide<Slice>Store()` is in the app root's `providers`. An unregistered slice never hydrates and nothing fails.
5. **Feature key** — the key the selectors read is the one the feature registers (`createFeature({ name })` derives it); a wrong key answers `undefined`, it never throws.

If refactoring, delete the dead code once the new slice takes over.

---

## Common patterns — quick reference

### Cross-slice dispatch (clear-on-event)

An effect in the consuming slice listens to the producing slice's success action and dispatches its own action (e.g. a draft slice clears itself when the record it drafted is created). Coupling stays at the effects layer; reducers stay pure and local.

### Data hydration race (a component mounts before the data lands)

Don't solve it in the component with an imperative hydrate effect. If the slice's data drives form fields, either (a) give the component a component-scoped SignalStore that reads the slice reactively (`/giga-angular:ngrx-component-state`), or (b) gate the form with `@if` on an `isLoaded` selector so it renders once the data arrives.

### Router-driven reads

An effect on the router's navigation action (or a selector over route params from `@ngrx/router-store`) dispatches the load; the component never reads the param to fetch.

The Firestore section adds the single-record, collection-under-parent and write-only patterns.

---

## What this skill deliberately does NOT do

- **Scaffold without reading docs first.** Always read the relevant guide page(s) before writing code.
- **Handle component-scoped SignalStore work**, or decide which of a component's concerns are global. Stop and recommend `/giga-angular:ngrx-component-state`.
- **Let a component inject `Store` or a selector.** Components consume the facade.
- **Introduce `@ngrx/data` or `@ngrx/component-store` for new code.** Both are legacy.
- **Name a helper the config and the reference slices don't.** An unconfigured helper is copied from a reference slice or written by hand, never guessed.
- **Block on a slow / offline `git fetch`.** Phase 0b times out cleanly; a stale-but-working clone is always better than stopping.
