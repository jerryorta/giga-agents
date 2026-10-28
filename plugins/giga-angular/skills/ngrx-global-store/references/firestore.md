# Firestore section

Read this when `angular.globalStore.firestore` is set. It adds Firestore + NgRx invariants to the slice's standard, replaces Phase 4 steps 5 and 6 with a listener service and a write service, and adds three patterns. Read the docs in `globalStore.firestore.standards` with it; where they differ, they win.

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
- **Writes go through dedicated `create` / `update` / `delete` actions** → an effect built with `writeEffect` → a write service → the `firestoreService` write method the standards name as the default.
- **No optimistic updates; the snapshot echo is the source of truth.** A write never patches the stored entity in the reducer: the listener echoes the written document and the reducer applies that. A pending-merged view belongs in the facade or a component-scoped SignalStore, not the reducer.
- **A snapshot replaces the stored entity.** The snapshot arm (and any whole-document read) uses `setOne` / `setMany`, or replaces the whole record for a single-record slice — never `upsert*` / `update*`, so a field the server deleted leaves state. Merges touch only local, non-snapshot state.
- **Atomic multi-document writes are one batch.** A write that must land on several documents together goes through the `firestoreService` batch API in one write-service method; its success action carries the generated ids, so later effects can chain.
- **Per-write `inFlight`.** Every write-enabled slice composes `writeState`. The caller mints a write id; the trigger, the success and the failure each carry it, so a page settles its own write (`isWriteInFlight(writeId)`), not the slice's. The next trigger clears the error.
- **Cross-slice dispatches go in effects**, never in reducers.

## Files (in place of Phase 4 steps 5 and 6)

1. **Actions** add the snapshot events the reference uses — for a single record `Loaded From Snapshot` and `Snapshot Missing`, for a collection the added / modified (both whole documents, replaced with `setMany`) and removed events.
2. **Reducer** starts from the write-state initial state and reduces every write triple with its started / succeeded / failed handlers, and nothing else.
3. **Selectors** add the write-state selectors: the slice's error, any write in flight, and this write in flight.
4. **`<slice>-write.service.ts`** (when the slice writes) — `@Injectable({ providedIn: 'root' })`, injects `firestoreService` and `Store` (for the signed-in uid), and exposes one `…$(…): Observable<void>` method per write over the default write method. Name it as the reference does.
5. **`<slice>-firestore-watch.service.ts`** (when the slice listens) — implements `listenerContract`; its connection key is the slice's feature key; `onConnect(user)` opens the listener and dispatches the snapshot events; `onDisconnect()` closes it. A collection under a parent uses `queryCache` instead of one listener.
6. **Effects** wrap each write in `writeEffect`. Side effects of a write (navigation, a clear in another slice) are separate effects on its success action.
7. **Registration** also constructs each listener service at boot, as `registrationNote` says, so it joins the registry before sign-in resolves. A listener nothing constructs yields a slice that never hydrates.

## Patterns

- **A single record under the signed-in user** — the listener opens `onSnapshot` on the user's document path and dispatches `Loaded From Snapshot` or `Snapshot Missing`; the write service writes through the default write method, which stamps its own timestamps (a create may need the create-stamp option the standards name).
- **A collection under a parent entity** — `queryCache` watches the parent slice's entities and adds or drops one child listener per parent; each change reaches the slice's added / modified / removed events, and the reducer replaces with `setMany`. No one-shot reads anywhere.
- **A write-only slice** — no listener. Actions → effect → a write service that writes several documents in one batch; the success carries the generated ids so later effects chain.
