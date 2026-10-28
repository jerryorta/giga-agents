---
description: Drive a cross-actor scenario for any epic board with a `crossActor` config across two browser profiles — act in one persona, verify the realtime Firestore propagation in another. Board-parameterized — `/giga-workflow:epic-cross-actor-test <board> <scenario> [flags]` reads the board's `crossActor` config from `epic.<board>.json` plus its scenario-catalog + browser-profiles memories; every app-specific value (dev server, port, Firestore paths, personas, bracket commands, e2e hook) comes from that config. Every run is BRACKETED — Phase 0.5 prompts the before-bracket; Phase 7 prompts the after-bracket (per the scenario's catalog). Pass `--auto-confirm-bracket` to skip both Y/Enter prompts and auto-run the brackets (use only when the caller owns the test fixture exclusively). Optional mobile viewport via `--mobile-actor` / `--mobile-verifier` / `--mobile-both`. $ARGUMENTS = `<board> <scenario>` where board is an epic board with a `crossActor` block and scenario is a catalog title or freeform description. If scenario is empty, list the catalog and ask the user to pick.
---

Drive a cross-actor test for a configured epic board: one persona acts, another persona verifies the realtime Firestore propagation. It is board-parameterized — it runs the same **act → wait → switch → verify** playbook for any board, with every app-specific value read from that board's `crossActor` config block in `epic.<board>.json` (mirroring how `/giga-workflow:epic-next <board>` resolves a board config).

## Project config

Repo-specific values come from `.claude/giga/config.json` at the repository root, under `workflow`. Read it once at the start. A missing file or field takes the fallback below, never a guess. Per-board values come from the board's `crossActor` block (see Config contract).

| Field | Used for | When absent |
| --- | --- | --- |
| `memoryDir` | the personal memory directory holding each board's scenario catalog, scenario files and browser-profiles memory (Step 0, Phase 1, Profile switching) | skip those reads, say the scenario catalog and persona-to-profile map are unavailable, and fall back to a freeform scenario where the user names the actor, verifier, action and check |
| `devServerPrelude` | shell lines run before every dev-server launch (Phase 0) | run the serve command with no prelude |
| `browser.chromeBinary` | the Chrome binary used to launch a persona's profile (Profile switching, step 1b) | do not relaunch Chrome; ask the user to open that profile |

**Stack.** This skill tests realtime propagation in an Angular app on Firebase: the signed-in identity check reads Firebase Auth's `firebaseLocalStorageDb` IndexedDB, and the diagnostic ladder reads the NgRx `Store` and Firestore's `onSnapshot` traffic. On another stack, skip those checks and say so in the report; the rest of the method applies unchanged.

## What it does

Orchestrates the **act → wait → switch → verify** flow:
1. Resolve the board config + its scenario catalog and browser-profiles memories (from `<memoryDir>`)
2. Confirm preconditions (dev server up + monitor armed, required profiles connected)
3. Resolve the scenario from `$ARGUMENTS` against the catalog
4. Apply mobile viewport flags if requested
5. Switch to actor profile, drive the action
6. Wait for Firestore snapshot propagation, switch to verifier
7. Verify via UI → NgRx store → [Firestore-direct, if the board exposes an e2e hook] → console → network
8. Report what happened, including any gaps

## When to use

- Smoke testing a feature that crosses persona boundaries (one persona writes, another must see the realtime update)
- Verifying realtime propagation works end-to-end for a watch service
- QA'ing the mobile shell against a desktop-driven action
- Catching regressions where one persona's UI doesn't reflect another persona's writes

## When NOT to use

- Single-persona flows — use direct browser MCP calls
- Component-isolation tests — use Storybook, launched through the `giga-workflow:dev-server` skill
- Backend-only verification — only when the board's config exposes an `e2eHook` is there a Firestore-direct rung to call (see Phase 5)

---

## Config contract — the `crossActor` block

Everything app-specific lives in `config.crossActor` on `epic.<board>.json`. This skill reads it; it hardcodes nothing about any one app. The schema:

```
"crossActor": {
  "devServer": { "serveCommand", "port", "logFile", "healthCheckUrl" },
  "firebaseEnvNote": <string|null>,        // human note shown in Phase 0 (e.g. which Firebase target the dev server serves)
  "firestorePathPrefix": <string>,         // root path under which this board's docs live (e.g. "/organizations/{orgId}" or "/groups/{groupId}")
  "testAnchorPath": <string>,              // repo path to the seed test-anchors file (for reference in reports)
  "bracketMode": "skill" | "npm",          // BRANCH 1: how each scenario's before=/after= token is executed
  "e2eHook": <string|null>,                // BRANCH 3: Firestore-direct verify hook expression, or null if the app has none
  "personas": [ { "displayName", "email", "seedAnchorKey": <"users.x"|null>, "authModel", "role" } ],
  "scenarioCatalogMemory": <slug>,         // memory slug holding the cross-actor PATTERN + policies (bracket policy, edge cases, verification primitives)
  "scenarioDir": <dir>,                    // directory beside that memory file, one scenario per file with `title:` / `status:` / `actors:` frontmatter
  "browserProfilesMemory": <slug>          // memory slug holding persona ↔ Chrome-profile detail + auth/cold-auth notes
}
```

Three config-driven BRANCHES are the ONLY app-specific control flow in this skill. Everything else is identical for every board:

- **BRANCH 1 — `bracketMode`** (Phase 0.5 + Phase 7): how a scenario's `before=` / `after=` token is run.
  - `"skill"` → run each token as a **Skill invocation** (e.g. `/seed-reset`). A multi-token `after` joined by `+` (e.g. `/seed-clear + /clear-analytics-data`) runs each Skill sequentially, never in parallel.
  - `"npm"` → run each token as **backgrounded bash** (e.g. `npm run seed.reset`), via Bash with `run_in_background: true`, awaited to completion. Multiple commands run one at a time, never in parallel.
  - **Non-runnable tokens** — a `before=`/`after=` token that is prose rather than a command (e.g. `manual delete of the created docs`, `manually delete a doc through the e2e hook`, `none needed`, or an `(optional)` marker) is NOT auto-executed in either mode: surface it to the user as a manual step (or simply skip a `none needed` token), and note it in the Phase 6 report. Only execute tokens that are an actual `/skill` name (`skill` mode) or a shell command (`npm` mode).
- **BRANCH 2 — persona `authModel`** (Phase 0): how each persona's session is established.
  - `"workspace-sso"`, `"email-password"`, or `"access-code-gate"` → the skill MAY drive the documented login for that persona in Phase 0 (prefill email + password; for an access-code gate also let the user supply the access code — follow the cold-auth steps in `config.crossActor.browserProfilesMemory`).
  - `"google-oauth-pre-authed"` or `"pre-authed"` → the skill ONLY checks the profile is connected and signed in as the persona's `email`; it NEVER drives a login (no email/password entry, no OAuth consent click). A connected-but-signed-out profile is surfaced and the run stops, asking the user to sign that profile in. Use `"pre-authed"` for an email/password account whose password the owner keeps.
- **BRANCH 3 — `e2eHook`** (Phase 5): whether a Firestore-direct verify rung exists.
  - a hook expression (e.g. `window.__cgE2E`) → Phase 5 escalation includes a Firestore-direct read between the store rung and the console rung.
  - `null` → that rung is skipped; escalation is one rung shorter (UI → store → console → network).

### Constants (NOT config — identical for every board)

These are hardcoded in this skill and must NOT be read from config:
- Mobile viewport: **390 × 844** (iPhone 14).
- The mobile-shell verification: after a resize, `read_page` must reference mobile-shell markup (bottom tab bar / mobile-shell element) — never deep-link a route to force the mobile shell; resize and let the app route.
- The compile-error monitor grep pattern: `ERROR|TS[0-9]+|✘|Application bundle generation complete|Compilation complete|Watch mode enabled` (the success/status alternations cover dev-server output variation across apps/CLI versions; the error markers `✘`/`ERROR`/`TS####` are the load-bearing ones).

---

## Step 0 — Load board config

Read `$ARGUMENTS`. The **first token** is the board name — exactly as `/giga-workflow:epic-next <board>` resolves it.

1. Read `.claude/giga/epic.<board>.json` and bind its fields as `config.*`. If no board token is provided, or the config file does not exist, list the available `.claude/giga/epic.*.json` files and stop helpfully.
2. If `config.hybridMode` is not `"conditional"`, OR `config.crossActor` is absent, STOP and report: this board is not configured for cross-actor testing (no `crossActor` block / not in hybrid mode). Point the user at `/giga-workflow:epic-config <board>` to add one. Do not fall back to another board's config.
3. Bind `config.crossActor.*` (the block above). Then **read the two memory files by slug** (`<memoryDir>/<slug>.md`; with no `memoryDir`, skip both reads and the scenario-body reads below, and say the catalog is unavailable): `config.crossActor.scenarioCatalogMemory` (the pattern, the bracket policy, the edge cases — NOT the scenario bodies) and `config.crossActor.browserProfilesMemory` (persona ↔ Chrome-profile mapping, auth/cold-auth detail, anchors). If either is already loaded, reuse it; otherwise read it now. Scenario bodies live one per file in `<memoryDir>/<config.crossActor.scenarioDir>/`, beside the catalog memory; **read only the one file the matched scenario names (Phase 1) — never the directory whole.** A scenario file can hold a long run history on its own. These files are the source of truth for scenario bodies and persona detail — do NOT hardcode either here.

Strip the board token from `$ARGUMENTS`; the remainder is the scenario string + flags, parsed in Phase 1.

## Phase 0 — Preconditions

Run these in order; abort + report on first failure.

1. **Dev server up + monitoring armed** (from `config.crossActor.devServer`):
   - Run each `devServerPrelude` line first when launching. Then health-check: `curl -sS -o /dev/null -w "%{http_code}\n" <config.crossActor.devServer.healthCheckUrl>` should print `200`. If not, instruct the user to run `<config.crossActor.devServer.serveCommand>` and stop. If `config.crossActor.firebaseEnvNote` is set, surface it here so the user knows which Firebase target the dev server serves.
   - **Then arm a compile-error monitor** via the Monitor tool so any TypeScript / template compile errors that surface mid-scenario (typically because Claude wrote a new file on the impl branch during a fix-in-place loop) are detected within seconds rather than misdiagnosed as "the realtime didn't propagate". Use the **constant** grep pattern against the board's log file:
     ```bash
     tail -f <config.crossActor.devServer.logFile> | grep -E --line-buffered "ERROR|TS[0-9]+|✘|Application bundle generation complete|Compilation complete|Watch mode enabled"
     ```
     Set `persistent: true` so the monitor lives for the whole scenario (and any fix-in-place re-runs that follow). If the user is running their own dev server with stdout in their terminal (no log file), ask them to redirect or — preferred — kill it and let Claude re-launch via `<config.crossActor.devServer.serveCommand> > <config.crossActor.devServer.logFile> 2>&1 &` so the monitor has a readable file. Without the monitor, a TS error in a freshly-added file looks identical to "watch service didn't subscribe" in the verifier UI — wasting an entire investigation loop. (This is the `giga-workflow:dev-server` skill's log-redirect and compile-error-monitor contract.)
   - If the dev-server log already shows `✘` / `ERROR TS####` entries before you start driving the scenario, surface them and STOP — fix the compile error first, do not enter Phase 1.
2. **Required profiles connected**: call `mcp__claude-in-chrome__tabs_context_mcp`. The set of profiles a scenario needs comes from the catalog (the scenario's actor + verifier(s)); the persona ↔ canonical-profile-name mapping is in `config.crossActor.browserProfilesMemory`. If a required profile is missing, instruct the user to connect a Chrome window with that byte-exact canonical name and stop. Do NOT proceed with a missing verifier — silent failure is the worst outcome.
3. **Establish / verify each required persona's session — BRANCH 2 (per persona `authModel`):**
   - `"google-oauth-pre-authed"` / `"pre-authed"` — only *check* the profile is connected (step 2) and signed in as the persona's `email`. NEVER attempt to enter a Google email/password or click through the OAuth consent screen. If the profile is connected but signed out (cold-auth), surface that and stop — ask the user to sign that profile in via Google, citing the cold-auth notes in `config.crossActor.browserProfilesMemory`.
   - `"access-code-gate"` — the persona may hit a beta access-code gate on first cold load this session. The skill MAY drive the documented login: prefill the persona's `email`, but let the **user** enter the access code + password (per the cold-auth notes in `config.crossActor.browserProfilesMemory`). After first sign-in, cookies persist and later runs are auto-authed.
   - `"email-password"` — the persona signs in with email + password, **no** access-code gate. The skill MAY drive the login: prefill the persona's `email` and password (per the cold-auth notes in `config.crossActor.browserProfilesMemory`). After first sign-in, cookies persist and later runs are auto-authed.
   - `"workspace-sso"` — the persona signs in via the workspace SSO path documented in `config.crossActor.browserProfilesMemory`; the skill MAY drive that documented login. If the documented path requires a human step, surface it and wait.
   - If a scenario in the catalog is marked BLOCKED on a missing/unavailable persona, surface the blocker and the unblocking criteria from the catalog, then exit cleanly.

### Why the dev-server monitor matters (don't skip)

The cross-actor flow is "act → wait → switch → verify". When verification fails, the diagnosis tree branches three ways: (a) actor write didn't fire, (b) write fired but didn't propagate, (c) propagated but UI didn't render. **A fourth, much subtler branch is: (d) the impl branch has a TypeScript error and the dev server is serving stale code from the last successful compile.** Symptoms look identical to (c): the new store slice / facade method / watch service appears absent from the running app, but the spec passes and the file is on disk. The monitor catches this in seconds — `Application bundle generation complete` confirms the latest impl change is live; any `✘` / `ERROR TS####` line is a blocker the current session must fix BEFORE driving the next browser action. Without it, Claude wastes 5–10 minutes investigating a propagation bug that doesn't exist.

## Phase 0.5 — Resolve + run the BEFORE bracket (REQUIRED)

Every scenario carries a `Bracket: before=<token> after=<token>` line in its scenario file (`config.crossActor.scenarioDir`). Resolve the bracket, then either prompt the user OR auto-run it depending on `--auto-confirm-bracket`.

1. Look up the scenario's `before=` / `after=` tokens in its scenario file. How a token is executed is **BRANCH 1 — `config.crossActor.bracketMode`**:
   - `"skill"` → each token is a Skill name (e.g. `/seed-reset`); run it via the Skill tool.
   - `"npm"` → each token is a shell command (e.g. `npm run seed.reset`); run it via Bash with `run_in_background: true`.
2. **Run brackets SEQUENTIAL, awaited, never in parallel.** For `skill` mode, await each Skill to completion before the next. For `npm` mode, launch via Bash `run_in_background: true` and await completion before the next step. If a bracket lists more than one token (e.g. a `+`-joined `after`), run them one at a time — a later clear can depend on an earlier write/clear having settled.
3. **If `$ARGUMENTS` contains `--auto-confirm-bracket`**: skip the prompt. Log a single line — `auto-confirm-bracket: running <before-token>` — then run the before token and proceed to Phase 1. Caller asserts exclusive ownership of the test fixture; no human gate.
4. **Otherwise**, surface the bracket to the user (the example below shows the tokens resolved from the catalog for the matched scenario):

   ```
   Scenario bracket (per catalog):
     before: <before-token>
     after:  <after-token>

   Run `before` now? [Y/n/skip]
   ```

   - **Y / Enter** — run the before token (per BRANCH 1), wait for completion, then proceed to Phase 1.
   - **n** — abort the whole test (user opted out of bracket; ask them why before falling back to "run anyway").
   - **skip** — proceed to Phase 1 without running before. Note in the final report that the test ran against ad-hoc state, not a clean baseline. (Only valid when the catalog marks the scenario's before as `(optional)`, e.g. pure-additive scenarios.)
5. Without `--auto-confirm-bracket`: do NOT auto-run the before token — confirm with the user. Bracket commands/skills touch the board's Firestore (the env in `config.crossActor.firebaseEnvNote`) and a stray run can disrupt parallel sessions or manual QA work. The flag is the explicit opt-in for orchestrator contexts where the caller owns the test fixture exclusively.

## Phase 1 — Resolve scenario

The scenario files (`config.crossActor.scenarioDir`) are the source of truth for scenario bodies; do NOT hardcode them here. Resolve by frontmatter, not by reading: `grep -il '^title: .*<distinctive words>' <memoryDir>/<scenarioDir>/*.md`, then read the one match.

Parse the post-board remainder of `$ARGUMENTS`:
- **Empty scenario**: list the catalog with `grep -h '^title:\|^status:' <memoryDir>/<scenarioDir>/*.md | paste - -` (number = the file's `NN-` prefix; status runnable / partial / BLOCKED), and ask the user to pick by number or short name.
- **Catalog match** (substring or fuzzy match on the `title:` frontmatter, `grep -il` over the directory): read that file only and use it directly. Confirm with the user which scenario you matched ("Running scenario: <title>. Confirm? y/n.").
- **No match (freeform)**: treat as ad-hoc. Ask the user explicitly: which actor profile, which verifier profile, what action, what to verify. Don't guess persona pairs — getting the actor wrong wastes a full setup cycle.

Persona reference comes from `config.crossActor.personas` (each entry: `displayName`, `email`, `seedAnchorKey`, `authModel`, `role`) cross-checked against `config.crossActor.browserProfilesMemory` for the canonical Chrome-profile name and any cold-auth detail. Use `displayName` as the actor/verifier identity throughout.

Extract mobile flags from `$ARGUMENTS` (constants — 390×844):
- `--mobile-actor` → resize actor profile to 390×844 before switching
- `--mobile-verifier` → resize verifier profile to 390×844 before switching
- `--mobile-both` → resize both
- Default viewport: iPhone 14 (390 × 844).

## Profile switching — `select_browser` first, assert always

Wherever a phase below says "switch to the actor / verifier profile", it means THIS procedure — not a
bare `switch_browser`.

**Why:** `switch_browser` broadcasts a Connect prompt to every installed extension and blocks until the
user clicks it. That is one user click per switch (an act → verify → act → verify run costs 3–4), and it
times out after ~2 min for two indistinguishable reasons: nobody clicked, or the extension is signed out.
`select_browser` takes a `deviceId` and switches silently. deviceIds are **stable** — they survive Chrome
restarts and extension reconnects — whereas the extension *name* cannot be recovered at all:
`list_connected_browsers` routinely reports every window as a generic `Browser N` no matter what it was
named (a `switch_browser` can return `Connected to browser "<name>"` and the very next list show every
window as `Browser N`).

**Procedure:**

1. **Resolve the deviceId** for the persona from the board's `config.crossActor.browserProfilesMemory`.
   If that memory carries a deviceId map, use it. If it does NOT (board not yet mapped), fall back to
   `mcp__claude-in-chrome__switch_browser` and tell the user which window to click Connect in.
1b. **If that deviceId is not in `list_connected_browsers`, LAUNCH it** — do not block and do not ask the
   user to open a window. When the board's memory records a Chrome profile directory for the persona:

   ```sh
   "<browser.chromeBinary>" --profile-directory="<dir>" &
   ```

   With no `browser.chromeBinary`, do not relaunch Chrome — ask the user to open that profile.

   Wait ~10 s, then re-list; the extension auto-connects and the id appears. ⚠️ Use the binary directly —
   `open -na "Google Chrome" --args …` silently does nothing while Chrome is already running. A persona
   whose profile dir is unknown is the only case that still needs the user.
2. **`mcp__claude-in-chrome__select_browser`** with that deviceId.
3. **Assert the identity BEFORE driving anything.** The silent switch is only safe because of this step —
   a stale map would otherwise drive the WRONG PERSONA, and the run would look successful while proving
   nothing. Navigate to the board's `devServer.healthCheckUrl` origin and read the signed-in account:

   ```js
   const db = await new Promise((res, rej) => { const r = indexedDB.open('firebaseLocalStorageDb');
     r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); });
   const recs = await new Promise((res, rej) => { const rq = db
     .transaction('firebaseLocalStorage', 'readonly').objectStore('firebaseLocalStorage').getAll();
     rq.onsuccess = () => res(rq.result); rq.onerror = () => rej(rq.error); });
   (recs.map(r => r && r.value).find(v => v && v.email) ?? {}).email;
   ```

   Compare against the persona's `email` in `config.crossActor.personas`. **Mismatch or empty → STOP.**
   Do not proceed, and do not "fix" it by guessing another deviceId: report which persona was expected
   and what was found. An empty result means that window is signed out — signing it in needs the user.
4. Only once the assertion passes, continue with the phase's own steps.

⚠️ A deviceId map goes stale when the Claude in Chrome extension is reinstalled — every id is re-minted.
Step 3 is what turns that from a silent wrong-persona run into a clean stop. Re-derivation instructions
live in the board's `browserProfilesMemory`; the cheapest route is **launch-diff** — snapshot the
connected list, launch one profile, re-list, and the id that appeared belongs to it.

⚠️ **A window reporting `Browser N` is not "unnamed" and needs no user action.** A freshly-launched
connection reports its real extension name while older ones degrade to `Browser N`, so absence of a name
says nothing. Never gate a run on it.

## Phase 2 — Mobile prep (skip if no mobile flag)

For each profile that needs mobile viewport:
1. Switch to that profile per § Profile switching (`select_browser` + assert) — briefly, just to set context
2. `mcp__claude-in-chrome__resize_window` to `width: 390, height: 844`
3. Brief settle (~500ms) so the app's breakpoint listener picks up the change
4. Verify the mobile shell rendered: a `read_page` snippet should reference mobile-shell-specific markup (bottom tab bar / mobile-shell element). If the desktop shell is still rendered, that's an app bug — surface and stop. Do NOT navigate to a route to force the mobile shell; resize and let the app route.

## Phase 3 — Act

1. Switch to the actor profile per § Profile switching (`select_browser` + assert)
2. Navigate to the action surface (the URL or the click-path — prefer click-path through the dashboard since it exercises the real user flow)
3. Drive the action via `find` (locate element) → `form_input` (fill fields) → click (via `computer`, or by triggering the right button via `find` + `javascript_tool`)
4. Capture a `read_network_requests` snapshot — look for the Firestore write (a path under `firestore.googleapis.com/...:commit` or similar, e.g. a write under `<config.crossActor.firestorePathPrefix>/...`). If no write fired, the actor-side action didn't actually mutate state; abort the verify phase and report the failure.

## Phase 4 — Wait + switch

1. Wait ~2 seconds (use `setTimeout` via `javascript_tool` or just proceed — the network round-trip after `read_network_requests` typically gives you ~1s of natural delay).
2. Switch to the verifier profile per § Profile switching (`select_browser` + assert)
3. Navigate to (or refresh) the verification surface — but try NOT to refresh; the snapshot should propagate without a reload. A forced reload masks listener bugs.

## Phase 5 — Verify

Try in order, escalating only if the prior step fails. The Firestore-direct rung is **BRANCH 3 — `config.crossActor.e2eHook`**:

1. **UI**: `read_page` for the expected element / text. Repeat with brief retry up to 5 s total. If found, capture a screenshot via `computer` for evidence and proceed to Phase 6 success.
2. **NgRx store**: if the UI didn't update, `javascript_tool` to access the store via the Angular `ng` debug helper — try `ng.getInjector(document.querySelector('app-root')).get(Store).pipe(take(1))` patterns to read the relevant slice. If the store has the data but the UI didn't render, the bug is in the selector / component — report that distinction.
3. **Firestore-direct (ONLY if `config.crossActor.e2eHook` is set)**: call the hook expression (e.g. `<config.crossActor.e2eHook>`) via `javascript_tool` — e.g. `getDoc(doc(db, '<path under config.crossActor.firestorePathPrefix>'))` — to read the doc you expect. If the doc is there but neither the store nor the UI reflects it, the bug is in the listener / selector / component — report that distinction. **If `config.crossActor.e2eHook` is `null`, SKIP this rung** (the app has no Firestore debug hook) and go straight to console.
4. **Console**: `read_console_messages` filtered by `[Snapshot]` / `[NgRx]` / the feature name. If the listener fired but state didn't update, the action dispatch was likely missing.
5. **Network**: `read_network_requests` on the verifier — was an `onSnapshot` long-poll connection even open? If no listener connection exists, the verifier's watch service never subscribed (persona gate, missing membership, wrong active group/org).

## Phase 6 — Report

One concise report (under 200 words):
- Scenario title + status (success / partial / failed / blocked)
- Actor: profile, action surface, write detected (yes/no, latency from action click to network confirm)
- Verifier: profile, viewport (desktop / mobile), where verification happened (UI / store / Firestore-direct / console / network), latency from write to verifier-side observation
- Screenshots saved (if any)
- Gaps: e.g. "slot claimed but recipient's view didn't reflect the claimed slot — known gap"
- Suggested next steps: another scenario, mobile retry, file Jira for an app bug, etc.

## Phase 7 — Run the AFTER bracket (REQUIRED)

After the report is surfaced, run the after-side of the scenario's bracket. Execution follows **BRANCH 1 — `config.crossActor.bracketMode`** (same as Phase 0.5), and the prompt is gated by `--auto-confirm-bracket`:

- **If `$ARGUMENTS` contains `--auto-confirm-bracket`**: skip the prompt. Log `auto-confirm-bracket: running <after-token(s)>` and run each after token in sequence (sequential, awaited, never parallel — for `skill` mode each Skill in turn; for `npm` mode each backgrounded bash command in turn). A `+`-joined multi-token `after` runs left-to-right (e.g. a Firestore clear before an external-store clear, so the later step sees settled state).

- **Otherwise**, prompt the user. Same shape as Phase 0.5, but at the end:

  ```
  Cleanup bracket (per catalog):
    after: <after-token(s)>

  Run cleanup now? [Y/n]
  ```

  - **Y / Enter** — run each after token in sequence (same sequencing rule as above, per BRANCH 1).
  - **n** — leave residual data. Note in the final report that cleanup was skipped so the next session knows to expect stale data in the test fixture.

Do NOT auto-run cleanup if Phase 5 reported a FAILURE — the user may want to inspect the residual state in the Firebase console or the app to diagnose. Ask whether to clean up or preserve for inspection. If they ask to preserve, also note in the final report that cleanup is pending.

> **Bracket scope is whatever the catalog lists.** Some boards' after-brackets include an external cleanup step (e.g. an analytics-store clear chained with `+`); others clear Firestore only. Run exactly the tokens the catalog specifies for the matched scenario — do not add or assume a cleanup step that isn't in the bracket, and if a catalog notes a documented NO-OP (e.g. an external store with no clear script), respect that note and don't attempt it.

## After it completes

1. Surface the report to the user.
2. If success: offer to run a follow-up scenario or capture a GIF (`mcp__claude-in-chrome__gif_creator`) for documentation.
3. If failure: distinguish (a) write didn't fire (actor-side bug), (b) write fired but didn't propagate (Firestore / listener bug), (c) propagated but UI didn't render (selector / component bug). Recommend the right next step per category.
4. If BLOCKED: confirm the unblocking criteria from the catalog and offer to file a Jira / open a PR.

## Notes

- Persona auth comes from each persona's `authModel` (BRANCH 2) + the cold-auth detail in `config.crossActor.browserProfilesMemory`. For `google-oauth-pre-authed` and `pre-authed` personas Claude never drives a login; for `email-password` personas Claude drives email + password sign-in (no gate); for `access-code-gate` personas Claude prefills email and the user supplies the access code + password; a profile may need cold-auth on first use of the session.
- Firestore anchors + the test fixture ids live in `config.crossActor.scenarioCatalogMemory` / `config.crossActor.browserProfilesMemory`; the seed test-anchors file is at `config.crossActor.testAnchorPath`. Board docs live under `config.crossActor.firestorePathPrefix`.
- Default scenario latency: 1–3 s end-to-end. Anything over 5 s is a red flag — likely the verifier's watch service didn't subscribe (persona gate, missing membership, wrong active group/org).
- Mobile viewport rules: never deep-link a route to force the mobile shell; resize to 390×844 and let the app route.
- This skill is intentionally a playbook, not a black-box automation — Claude orchestrates each phase using MCP tools, with the user available to intervene at any step. Do not background-spawn a sub-agent for the orchestration itself; the user needs to see what's happening in their browser. (Backgrounded bash is only for `npm`-mode bracket commands, which produce no browser activity.)
- This is the single cross-actor entry point for every hybrid board.
