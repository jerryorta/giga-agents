# Firestore section

Read this when `angular.globalStore.firestore` is set. It adds Firestore + NgRx invariants to the slice's standard, adds files to Phase 4 (its listener service and write service replace steps 5 and 6), adds three patterns, and adds a verify list to Phase 5. Read the docs in `globalStore.firestore.standards` with it, the repo's Firestore data-access standard among them; where they differ, they win.

## Helpers, by key

The repo's own Firestore plumbing is named in config, never by path in this skill. Each key maps to `{ symbol, module, note }`; the target store's `helpers` key wins over the same key in `globalStore.firestore.helpers`. Read each helper's `module` before using it: its exports name the companion functions (initial state, reducer handlers, selectors) that go with the symbol. A `module` that is a path inside the target library is imported relatively, as the reference slices import it.

| Key | What it is |
| --- | --- |
| `firestoreService` | the injectable that wraps the Firestore SDK: document and collection writes, batches, the signed-in user |
| `listenerContract` | the interface a listener service implements so a registry opens it on sign-in and closes it on sign-out (`note` names its connector) |
| `writeEffect` | the effect factory that wraps one write: trigger → work → success or failure, keeping the write state |
| `writeState` | the state fragment every write-enabled slice composes: `error` plus `inFlight` keyed by write id |
| `queryCache` | the cache that opens one child-collection listener per parent entity and closes it when the parent leaves state |

A key that is absent: find the pattern in the reference slice whose note shows it and copy that. With no reference either, write the shape by hand: a listener service with `onConnect` / `onDisconnect`, an effect with `catchError` inside the inner observable, and `error` / `inFlight` fields on the state. Never invent a helper's name or module.

## Invariants

- **Reads that feed state are `onSnapshot` listeners, never a one-shot get.** A listener service implements `listenerContract`: opening the listener when the user connects and closing it on disconnect. A one-shot read is an exception the store's standards name, never the default.
- **Every listener-backed slice carries two read signals: loaded and confirmed.** The loaded flag turns true on the first result in hand, cached or not: rows paint and chained watches open on it. `isConfirmedByServer` turns true only once the server has answered, on the first snapshot whose `metadata.fromCache` is `false`, reported by a settle hook: the listener helper's `onSettled`, or for a raw listener a settle probe (a second listener on the same ref with `includeMetadataChanges: true`, opened after the data listener, closed with it, dispatching only the settle). Each signal is a state field, a reducer arm, a selector and a facade member. Confirmed settles once per connect and resets when the listener closes; offline it never turns true. A removed-only batch (a parent leaving, a refused listen retracting its rows) is never a first snapshot: it removes rows and marks neither signal.
- **Every absence decision binds to the confirmed signal; cached rows never wait.** An empty state, a zero or "(0)" count, "not found", "no … match", a missing-document terminal, create-vs-open, "not covered": each reads `isConfirmedByServer`, never the loaded flag or `length === 0` alone, because a query that synced before can raise an empty cached snapshot. Held rows render as soon as they land. Until the slice confirms, an empty region shows its loading state, and only that region: offline never confirms, so nothing gates a page on it.
- **An aggregate over parents confirms only once the parent set does.** For a collection under a parent, "every parent confirmed" is the parent slice's own `isConfirmedByServer` AND every held parent's settle. `[].every(…)` is `true`, so without the parent term an empty parent set reads as confirmed before the server has said the set is empty. The loaded aggregate takes the parent slice's loaded flag the same way.
- **An existence decision never comes from a one-shot get.** With a persistent multi-tab cache, a `getDoc` can report a document missing without the server having answered. A seed or create-if-missing is create-only: one transaction that reads from the server and creates only while the document is still absent (the `firestoreService` method the standards name for once-only initialization; with none, `runTransaction`), and writes nothing offline or on a read error.
- **Turning an app's persistent cache on includes the sweep of that app's absence decisions, in the same story.** A persistent cache makes a cached first snapshot, an empty one included, the normal start. The story that turns it on finds every absence decision in the app (templates, component stores, selectors, guards, effects), rebinds each to its slice's confirmed signal, and adds the signal to any slice that lacks it.
- **Writes go through dedicated `create` / `update` / `delete` actions** → an effect built with `writeEffect` → a write service → the `firestoreService` write method the standards name as the default.
- **No optimistic updates; the snapshot echo is the source of truth.** A write never patches the stored entity in the reducer: the listener echoes the written document and the reducer applies that. A pending-merged view belongs in the facade or a component-scoped SignalStore, not the reducer.
- **A snapshot replaces the stored entity.** The snapshot arm (and any whole-document read) uses `setOne` / `setMany`, or replaces the whole record for a single-record slice — never `upsert*` / `update*`, so a field the server deleted leaves state. Merges touch only local, non-snapshot state.
- **Atomic multi-document writes are one batch.** A write that must land on several documents together goes through the `firestoreService` batch API in one write-service method; its success action carries the generated ids, so later effects can chain.
- **Per-write `inFlight`.** Every write-enabled slice composes `writeState`. The caller mints a write id; the trigger, the success and the failure each carry it, so a page settles its own write (`isWriteInFlight(writeId)`), not the slice's. The next trigger clears the error.
- **Cross-slice dispatches go in effects**, never in reducers.

## Files (added to Phase 4)

1. **State** adds the two read signals, both `false` at start, named as the reference slices name them (a loaded flag, `isConfirmedByServer`); a collection under a parent keeps one of each per parent key.
2. **Actions** add the snapshot events the reference uses — for a single record `Loaded From Snapshot` and `Snapshot Missing`, for a collection the added / modified (both whole documents, replaced with `setMany`) and removed events — and the settle event (`Confirmed By Server`, carrying the parent key under a parent).
3. **Reducer** starts from the write-state initial state and reduces every write triple with its started / succeeded / failed handlers, and nothing else. Its snapshot arms set the loaded flag, except on a removed-only batch; the settle arm is the only writer of `isConfirmedByServer`; a disconnect or a released parent resets it.
4. **Selectors** add the write-state selectors (the slice's error, any write in flight, and this write in flight) and one selector per read signal. A slice under a parent adds the two aggregates, each ANDed with the parent slice's own signal, in the aggregate-selectors file the Standard names.
5. **Facade** exposes the loaded and confirmed signals, and any aggregate, as members named and typed like the reference facade's reads (e.g. `isConfirmedByServer$`).
6. **`<slice>-write.service.ts`** (when the slice writes) — `@Injectable({ providedIn: 'root' })`, injects `firestoreService` and `Store` (for the signed-in uid), and exposes one `…$(…): Observable<void>` method per write over the default write method. Name it as the reference does.
7. **`<slice>-firestore-watch.service.ts`** (when the slice listens) — implements `listenerContract`; its connection key is the slice's feature key; `onConnect(user)` opens the listener and dispatches the snapshot events; its settle hook dispatches the settle event; `onDisconnect()` closes both. A collection under a parent uses `queryCache` instead of one listener, with the settle per parent. A missing document's terminal (an error, a redirect, a seed) runs only on a server-confirmed miss; a cached miss paints and decides nothing.
8. **Effects** wrap each write in `writeEffect`. Side effects of a write (navigation, a clear in another slice) are separate effects on its success action.
9. **Registration** also constructs each listener service at boot, as `registrationNote` says, so it joins the registry before sign-in resolves. A listener nothing constructs yields a slice that never hydrates.

## Patterns

- **A single record under the signed-in user** — the listener opens `onSnapshot` on the user's document path and dispatches `Loaded From Snapshot` or `Snapshot Missing`, then the settle event once the server answers; create-vs-open waits for it. The write service writes through the default write method, which stamps its own timestamps (a create may need the create-stamp option the standards name).
- **A collection under a parent entity** — `queryCache` watches the parent slice's entities and adds or drops one child listener per parent; each change reaches the slice's added / modified / removed events, and the reducer replaces with `setMany`. Each parent settles on its own; the slice's confirmed aggregate also waits on the parent slice's. No one-shot reads anywhere.
- **A write-only slice** — no listener and no read signals. Actions → effect → a write service that writes several documents in one batch; the success carries the generated ids so later effects chain.

## Verify (added to Phase 5)

1. **Both read signals, end to end** — state field, reducer arm, selector and facade member for each, and the watch service dispatching the settle event from its settle hook.
2. **Specs** — a cached first snapshot sets the loaded flag and leaves confirmed `false`; the settle sets confirmed; a removed-only batch marks neither; a disconnect resets confirmed; an aggregate over an empty parent set stays `false` until the parent slice confirms.
3. **Absence decisions** — search the slice's consumers (templates, component stores, selectors, guards, effects) for empty states, `length === 0`, zero counts, "not found", "no … match" and create-vs-open branches: each reads the confirmed signal, and none gates a page on it. When the story turns an app's persistent cache on, the search covers the whole app.
4. **Existence** — no create-or-skip decision reads a one-shot get; a create-if-missing is the transactional create-only write.
