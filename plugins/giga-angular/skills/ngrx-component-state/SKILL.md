---
name: ngrx-component-state
description: Place a component's reactive state and property/method logic in its correct home so the component class keeps only `input()`/`output()`, the injected store/facade, and template glue. Decides per concern — a colocated component-scoped `@ngrx/signals` SignalStore (local UI/interaction state), consumption of the global `@ngrx/store` via its domain facade (app/domain-wide persistent data), or pure functions (algorithms); a component often needs more than one. Applies to NEW components (born thin) and EXISTING ones (extract + thin). Hybrid skill — authoritative signalStore API guidance comes from a local NgRx clone (kept current via `git pull`); layout conventions come from the repo's own reference stores. Use when a component (new or existing) has internal reactive state, computed getters, or method logic that needs a home; to scaffold a signalStore or a `with-*` feature; to convert an `@Injectable`/`@ngrx/component-store` to a signalStore; or to thin a fat component. Does NOT author a global slice (actions/reducer/effects/selectors/facade) — that goes to the repo's global-store skill.
---

# NgRx Component State

Get a component's state and logic **out of the component** and into its correct home, so the class keeps only `input()`/`output()`, the injected store/facade, and template glue. The home is decided per concern (see **Routing** below): a colocated component-scoped SignalStore for local UI/interaction state, the domain **facade** for global/persistent data, or pure functions for algorithms — a component system often needs more than one. This skill owns the **component side** (the decision, the local SignalStore, the facade wiring); it hands global-slice authoring to the skill named in `globalStoreSkill`.

Hybrid skill: authoritative signalStore API docs live in a local NgRx clone (kept current via `git pull`). Layout + composition conventions come from the repo's reference stores (`componentState.references`).

## Project config

Repo-specific values come from `.claude/giga/config.json` at the repository root, under `angular`. Read it once at the start. A missing file or field takes the fallback below, never a guess.

| Field | Used for | When absent |
| --- | --- | --- |
| `componentState.references` | the stores Phase 3 teaches from: `{ path, note }` entries, each note saying what that store shows | teach from the NgRx docs (Phase 2) and the generic layout in Phase 3 |
| `componentState.standards` | the repo's state standards: every store this skill creates or refactors toward satisfies them, and they win over this skill's text | the invariants under **Standard** below are the standard |
| `ngrxDocs` | the local clone of NgRx `platform` the API guidance comes from; `$NGRX_DOCS` wins when set | with `$NGRX_DOCS` unset too, ask the user for the clone and stop until they answer |
| `globalStoreSkill` | the skill that authors a global `@ngrx/store` slice (actions, reducer, effects, selectors, facade) | hand off to `/giga-angular:ngrx-global-store`, the sibling skill in this plugin |

---

## Standard (read first)

Read every doc in `componentState.standards` before writing. Every store this skill creates or refactors toward MUST satisfy them and the invariants below; where they differ, the configured standards win.

- **No size or line-count threshold.** ALL of a component's internal reactive state — writable `signal()`s, stateful `computed()`/`linkedSignal()`s, `effect()`s, `toSignal` bridges, RxJS subscriptions, and the orchestration around them — moves into ONE component-scoped SignalStore. A component with a single internal signal still extracts. The component class keeps ONLY `input()` / `output()` (its public boundary), the injected store, and template-only glue.
- **Component-scoped, NEVER `providedIn: 'root'` for component/feature state.** Provide the store on the component via `providers: [Store]` (for a system, its root component) — one instance per component instance, correct lifecycle + isolation. Reserve `providedIn: 'root'` for genuinely app-global *signal* state; app-/domain-wide *persistent* data is not that — it belongs in the global classic `@ngrx/store`, consumed via facades.
- **Colocated.** The store lives in its own folder next to the component / system root it serves — never a shared / central store directory; it ships and is tested with its component.
- **Multi-component systems** (a root orchestrating a tree of children that share state / interaction): ONE store provided at the root; children `inject()` it. `input()` / `output()` stay ONLY at the root's public boundary — NEVER prop-drill shared state as `input()` nor bubble interactions as `output()` between internal components.
- **State, not logic.** The store holds reactive UI state; derived view-models are `withComputed`; algorithms stay in **pure functions** the store calls.
- **Supplements, never replaces, the global store.** The component SignalStore holds ephemeral local UI / interaction state; the global `@ngrx/store` (via facades/selectors) stays the system of record for app-/domain-wide persistent data, `@ngrx/entity`, and realtime / websocket subscriptions. A system typically runs BOTH. Never migrate a global slice into a component store, nor promote local UI state into the global store.
- **Exemption is by KIND, not size.** Design-library presentational primitives keep their intrinsic widget mechanics (CVA internals — a reveal/open toggle, hover/focus state) as plain component signals; zero-state components need no store. Don't force these into a SignalStore.

---

## Routing — decide the home(s) first

Before scaffolding anything, route **each** piece of state / logic the component holds (or, for a new component, will hold). A component system commonly needs more than one home — route each concern independently; don't force a single bucket.

| The concern is… | Home | What to do |
|---|---|---|
| Ephemeral, local UI / interaction state (toggles, wizard step, selection, debounced input) | **Component-scoped SignalStore** | Scaffold it — Phases 0–5 below |
| App-/domain-wide persistent data (server or realtime data, `@ngrx/entity`, shared across unrelated consumers) | **Global `@ngrx/store` via its domain facade** | Wire the facade — see **Global path**. If the slice doesn't exist yet, hand off to the skill named in `globalStoreSkill`, then return |
| A derived getter / property | `withComputed` (signal path) or a facade **selector** (global path) | Move it off the component |
| An algorithm / method body | A **pure function** the store or selector calls | Move it off the component |
| Intrinsic widget mechanics in a design-library presentational primitive (CVA internals, open/hover/focus) | **Plain component `signal()`** — by-kind exemption | Leave it; no store |
| Nothing reactive (zero-state / pure presentational leaf) | — | Stop; no store, no facade |

Outcomes:

- **Local state present** → continue to Phase 0 and scaffold the SignalStore.
- **Only global data** → skip the phases below; do **Global path** and you're done.
- **Both** → do both (the common multi-component-system case).
- **Neither** → nothing to do; the component is already correctly thin.

For a **new** component, scaffold the `.ts/.html/.scss/.spec` shell with the repo's Angular component generator (`@nx/angular:component` in an Nx workspace); this skill only places the state home on top.

---

## Phase 0 — Resolve and refresh the local NgRx docs

### 0a — Resolve the path

1. `$NGRX_DOCS`, when the env var is set.
2. Otherwise `ngrxDocs` from the config, with a leading `~` expanded to `$HOME`.
3. Otherwise ask the user where their clone of `ngrx/platform` is (or to clone `https://github.com/ngrx/platform`) and stop until they answer.

Verify: `<path>/projects/www/src/app/pages/guide/signals/signal-store/index.md` must exist. If it doesn't, ask the user for the clone's location and stop until they answer.

Substitute `$NGRX_DOCS` throughout the rest of this skill with the resolved path.

### 0b — Refresh the clone (best-effort, non-blocking)

Run the following with a 10-second timeout on the fetch; never block the skill on a slow network:

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
- **`REMOTE` ahead and `DIRTY` non-empty** → skip the pull. Warn the user: "NgRx docs clone at `$NGRX_DOCS` has uncommitted changes; proceeding with current checkout. Pull manually if you want newer docs."
- **Fast-forward fails (diverged history)** → skip. Warn: "NgRx docs clone has diverged from upstream; proceeding with current checkout."

Whatever happens, continue to Phase 1. A stale-but-working clone is always better than stopping.

---

## Phase 1 — Clarify scope

Ask the user one at a time when answers shape later questions:

1. **Store name** (e.g. `CheckoutStore`) and target directory, colocated with the component it serves (e.g. `libs/<domain>/ui/src/lib/checkout/`).
2. **`providedIn` scope** — default **component-scoped**: omit `providedIn`, provide via `providers: [Store]` on the component (or, for a system, its root component). NEVER `providedIn: 'root'` for component/feature state. Reserve `'root'` for genuinely app-global *signal* state — and note that app-/domain-wide *persistent* data is not that; it belongs in the global `@ngrx/store` (recommend the skill named in `globalStoreSkill`).
3. **State shape** — list the fields and their types. Distinguish persistent state (computed from a classic-store source) from transient UI state (owned here).
4. **Features** — the cohesive concerns. If the user doesn't know, propose a split based on state groupings (form fields vs async channel vs submit orchestration); whether they become `with-*` files is decided in Phase 3.
5. **Reactive dependencies** — does the store need to observe another store (facade, selector, signalStore)? If yes, its `withProps` will inject the source.
6. **Existing code to refactor** — path(s) to component/class being migrated.

If converting an existing `@Injectable` class, read the source file completely before Phase 2.

If the feature needs app-global persistence, multiple unrelated consumers, devtools time-travel, or websocket subscriptions — **stop and recommend the skill named in `globalStoreSkill` instead** (absent: `/giga-angular:ngrx-global-store`). SignalStore is the wrong tool for those.

---

## Phase 2 — Load relevant docs

Read only the guide pages that map to what you're building. Don't preload all 4000 lines.

All paths under `$NGRX_DOCS/projects/www/src/app/pages/guide/signals/`:

| Concern | File |
|---|---|
| `signalStore` basics — `withState`, `withComputed`, `withMethods` | `signal-store/index.md` |
| Reusable `with*` features via `withFeature` composition | `signal-store/custom-store-features.md` |
| Injecting services — `withProps` | `signal-store/custom-store-properties.md` |
| Collections inside a signalStore — `withEntities` | `signal-store/entity-management.md` |
| Event-driven patterns (dispatch-like workflow) | `signal-store/events.md` |
| Lifecycle hooks — `onInit` / `onDestroy` | `signal-store/lifecycle-hooks.md` |
| `linkedSignal` — writable signal derived from a source | `signal-store/linked-state.md` |
| Private members (underscore-prefix convention) | `signal-store/private-store-members.md` |
| Devtools / change tracking | `signal-store/state-tracking.md` |
| Unit testing a signalStore | `signal-store/testing.md` |
| `rxMethod` — RxJS → signal bridge for async effects | `rxjs-integration.md` |
| `signalMethod` — synchronous signal-driven method | `signal-method.md` |
| Plain `signalState` primitive (when a full store is overkill) | `signal-state.md` |
| `deepComputed` helper | `deep-computed.md` |
| FAQ / edge cases | `faq.md` |

API reference (structured metadata): `$NGRX_DOCS/projects/www/src/app/reference/signals/` — e.g. `signalStore.json`, `withComputed.json`, `withEntities/*.json`.

Typical read sets:

- **New store from scratch**: `signal-store/index.md` + `signal-store/custom-store-features.md` + `signal-store/custom-store-properties.md` + `signal-store/lifecycle-hooks.md`.
- **Uses async / HTTP / backend writes**: add `rxjs-integration.md`.
- **Collection of items**: add `signal-store/entity-management.md`.
- **Needs writable derived signals**: add `signal-store/linked-state.md`.
- **Migrating from component-store**: `signal-store/index.md` + `signal-store/custom-store-features.md`.

When unsure which primitive fits (`rxMethod` vs `signalMethod`, `linkedSignal` vs `computed`, etc.), read the relevant page before deciding — don't guess.

---

## Phase 3 — Read the reference stores

Layout comes from the repo's own stores, listed in `componentState.references`. Each entry is a `{ path, note }`; the note says what the store shows (a multi-file root composing `features/`, a single-file store, a page store over facades, a shared building block) and may name the feature file to read for a given concern.

1. **Pick the reference that matches the case**: a multi-component system or a store with several concerns → a multi-file root composing `features/`; one cohesive concern → a single-file store; a store that mediates the global store → a page store over facades. With no clear match, read the first entry.
2. **Read it before scaffolding**: its composition root (the shape, the JSDoc on feature order, how it is provided and injected), its state file if it has one, and the one feature file whose concern matches yours.
3. **Follow that reference's OWN file naming.** Repos differ — `<name>.store.ts` + `features/with-<concern>.feature.ts` in one, `<name>-store.ts` + `features/with-<concern>.ts` in another — so never impose one on the other; inside an existing library, the names its stores use win.
4. **A shared building block** (an entry whose note says so): check whether it applies before reinventing its features.

With no `references`, Glob `**/*.store.ts` and `**/*-store.ts` for the repo's own stores and follow the one nearest the target component; with none, use the generic layout below and the NgRx docs.

### Generic layout

Two shapes are equally canonical:

- **Single-file store** — `withState` + `withProps` + `withComputed` + `withMethods` (+ `withHooks`) in one `<name>.store.ts`, right while its concerns read well together.
- **Multi-file root composing `features/`** — a thin composition root plus one file per cohesive concern:

```
<name>.store.ts               ← composition root: shared identity + one withFeature line per concern
<name>.store.state.ts         ← state shape + initial state
<name>.store.spec-setup.ts    ← stubs and createStore the feature specs share
features/
  with-<concern>.feature.ts        ← one cohesive concern per file
  with-<concern>.feature.spec.ts   ← its spec, beside it
```

**The `features/` split is decided by concern count and cohesion, never by line count alone.** Split when the concerns stop reading well together: a root holding two concerns, each with its own state + methods + cleanup, splits whatever its size, and a store with one concern stays one file.

Conventions, whatever the file names:

- Store exported as `ConstCase` type-and-value (`export const CheckoutStore = signalStore(…)`). `providedIn` is omitted for component-scoped stores (provided via `providers: [Store]`); use `providedIn: 'root'` only for genuinely app-global signal state — never for component/feature state.
- Provided on the component, or for a system on its root component; descendants `inject()` it with no provider of their own.
- `withProps(() => ({ _service: inject(X), ... }))` for injected dependencies. Private members prefixed with `_` (per `private-store-members.md`).
- Features are factory functions, each file named for its function (`with-cart-items` ↔ `withCartItems`, with the reference's suffix). Each owns its `withState` slice, injects the services/facades only it uses, runs its own effects and `onDestroy`, and declares what it reads off the root as a typed `Deps` interface. Compose via `withFeature((store) => withXxx(store))`; a feature that reads nothing off the root composes as `withXxx()`.
- Feature order is dependency order; the root's JSDoc states it.
- `signalStore()` takes at most 15 features; past that, group related features into one composite feature. The overflow error is an overload dump that names neither the cap nor the cause.
- A store over the global store injects facades in `withProps`, projects reads into `withComputed`, delegates writes from `withMethods`, and cleans up in `withHooks`.
- `withHooks` last for lifecycle cleanup.
- Composition root stays thin: imports + service props + feature composition + hooks. Heavy logic lives in the feature files.

---

## Phase 4 — Scaffold

Write files in dependency order, named as the reference names them:

1. Multi-file shape: one feature file per cohesive concern, each with its own state slice (start with the most independent).
2. The store — for the multi-file shape, the composition root: shared identity + one `withFeature` line per concern, in dependency order. Split by the Phase 3 rule (concerns that each own state, methods and cleanup), or when a file passes the size limit the repo's standards set.
3. Specs — one beside each feature and one for the root, per `testing.md`. Stubs the specs share go in `<name>.store.spec-setup.ts`; exclude `src/**/*.spec-setup.ts` in the lib's `tsconfig.lib.json` and include it in `tsconfig.spec.json`.

Rules while writing:

- Form fields — bind templates to computed-from-store signals + method setters. Don't duplicate state in component-local `signal()` instances.
- Async / debounced flows — use `rxMethod` inside the feature file (read `rxjs-integration.md` first if in doubt).
- Cleanup — `withHooks({ onDestroy })`. Don't rely on GC.
- Dependencies on other stores — inject via `withProps`, not in the component.

---

## Phase 5 — Verify

1. `npx nx run <project>:lint` — clean on the touched files.
2. `npx nx run <project>:test` — new specs pass.
3. Type-check consumer sites: `inject(StoreName)` resolves cleanly.
4. Component-scoped stores — confirm the component has `providers: [StoreName]` (DI fails at runtime with no compile error otherwise).

If refactoring, delete the dead local signals / effects after the store takes over.

---

## Global path — wire the facade, delegate the slice

When **Routing** sends a concern to the global store:

1. **Slice + facade already exist** → inject the facade (in the component, or for a system in its container/root), read via its exposed signals, dispatch via its methods. Delete the component's duplicated or hand-hydrated copy of that global state. Children of a system `inject()` the facade — don't prop-drill it.
2. **Slice does not exist** → this is global-slice work. Stop and run the skill named in `globalStoreSkill` to author the slice (actions/reducer/effects/selectors/facade), then return here to wire the facade. With no `globalStoreSkill`, run `/giga-angular:ngrx-global-store`, then wire it.
3. **Never** author actions / reducers / effects / selectors in this skill while `globalStoreSkill` names a skill — that boundary belongs to it.

Clean split: this skill = component side (decision + local SignalStore + facade wiring); the `globalStoreSkill` skill = the global slice itself.

---

## Common conversions

### `@Injectable` class with signals → `signalStore`

Extract fields into `withState`, getters into `withComputed`, methods into `withMethods`. Injected services move into `withProps`. Constructor `effect()` blocks become `withHooks({ onInit })` or `rxMethod` pipelines. The exported class name stays the same so consumers' `inject()` calls don't change.

### Component-local `signal(store.value)` + hydrate-effect anti-pattern → reactive computed-from-store

Source-of-truth is the store. Form fields become `computed(() => store.field())`. User input handlers call `store.setField(value)`. Delete the local signals and `hasHydratedFromX` effects entirely. Requires the store to expose a pending-merged view if it debounces writes.

### `effect(() => ...)` orchestration with multiple source signals → `rxMethod`

If the effect reads multiple signals and dispatches side-effects on derived state, it's almost always cleaner as an `rxMethod` pipeline triggered by a source signal. Gives automatic cleanup, cancellation, RxJS operator composition.

### `@ngrx/component-store` → `signalStore`

Component-store is the signalStore predecessor. When touching one for any reason, migrate it.

---

## What this skill deliberately does NOT do

- **Scaffold without reading docs first.** Always read the relevant guide page(s) before writing code.
- **Author the global slice itself** while `globalStoreSkill` names a skill. Deciding the global path and wiring its facade into the component is in scope; building the slice (actions/reducer/effects/selectors/facade) is that skill's job — hand off to it (see **Global path**).
- **Default to `providedIn: 'root'`.** Component/feature state is always component-scoped (`providers: [Store]`); reserve `'root'` for genuinely app-global signal state, never for persistent domain data.
- **Use `@ngrx/component-store` or `@ngrx/data` for new code.** Both are superseded by signalStore.
- **Block on a slow / offline `git fetch`.** Phase 0b times out cleanly; a stale-but-working clone is always better than stopping.
