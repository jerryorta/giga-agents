---
description: Drive a cross-actor scenario for an epic board with a `crossActor` config — one persona acts, another verifies the realtime Firestore propagation. `/giga-workflow:epic-cross-actor-test <board> <scenario> [flags]`. The session resolves the scenario and confirms the before/after brackets once; a foreground Sonnet subagent drives the browsers, so screenshots never enter this context. Flags `--auto-confirm-bracket`, `--mobile-actor` / `--mobile-verifier` / `--mobile-both`. Empty scenario lists the catalog.
---

Drive a cross-actor test for a configured epic board: one persona acts, another persona verifies the realtime Firestore propagation. It runs the same **act → wait → switch → verify** playbook for any board, with every app-specific value read from that board's `crossActor` config block in `epic.<board>.json` (the way `/giga-workflow:epic-next <board>` resolves a board config).

The browser driving runs in a foreground Sonnet subagent, so screenshots and page reads never enter this session's context (every turn here re-reads all of it). The session keeps every decision: scenario match, bracket gate, compile-error Monitor, clean-up choice, fixes.

## Project config

Repo-specific values come from `.claude/giga/config.json` at the repository root, under `workflow`. Read it once at the start. A missing file or field takes the fallback below, never a guess. Per-board values come from the board's `crossActor` block.

| Field | Used for | When absent |
| --- | --- | --- |
| `memoryDir` | the personal memory directory holding each board's scenario files and browser-profiles memory (Step 0, Phase 1, dispatch) | skip the scenario reads, say the scenario catalog and persona-to-profile map are unavailable, and fall back to a freeform scenario where the user names the actor, verifier, action and check |
| `devServerPrelude` | shell lines run before every dev-server launch (Phase 0) | run the serve command with no prelude |

The agent reads `browser.chromeBinary` itself; this session does not use it.

## When to use

- Smoke testing a feature that crosses persona boundaries (one persona writes, another must see the realtime update)
- Verifying realtime propagation works end-to-end for a watch service
- QA'ing the mobile shell against a desktop-driven action
- Catching regressions where one persona's UI doesn't reflect another persona's writes

## When NOT to use

- Single-persona flows — use direct browser MCP calls
- Component-isolation tests — use Storybook, launched through the `giga-workflow:dev-server` skill
- Backend-only verification — only when the board's config exposes an `e2eHook` is there a Firestore-direct rung (see `drive.md`)

---

## Config the session reads — the `crossActor` block

Everything app-specific lives in `config.crossActor` on `epic.<board>.json`. The session uses these fields; the agent reads the whole block (schema in `drive.md`).

```
"crossActor": {
  "devServer": { "serveCommand", "port", "logFile", "healthCheckUrl" },
  "firebaseEnvNote": <string|null>,        // shown in Phase 0 (which Firebase target the dev server serves)
  "personas": [ { "displayName", "email", ... } ],
  "scenarioDir": <dir>,                    // beside the memory directory, one scenario per file with `title:` / `status:` / `actors:` frontmatter
  "browserProfilesMemory": <slug>          // memory slug holding persona ↔ Chrome-profile detail, deviceIds, auth notes
}
```

### Constants (NOT config — identical for every board)

- The compile-error monitor grep pattern: `ERROR|TS[0-9]+|✘|Application bundle generation complete|Compilation complete|Watch mode enabled` (the success/status alternations cover dev-server output variation across apps/CLI versions; the error markers `✘`/`ERROR`/`TS####` are the load-bearing ones).

---

## Step 0 — Load board config

Read `$ARGUMENTS`. The **first token** is the board name — exactly as `/giga-workflow:epic-next <board>` resolves it.

1. Read `.claude/giga/epic.<board>.json` and bind its fields as `config.*`. If no board token is provided, or the config file does not exist, list the available `.claude/giga/epic.*.json` files and stop helpfully.
2. If `config.hybridMode` is not `"conditional"`, OR `config.crossActor` is absent, STOP and report: this board is not configured for cross-actor testing (no `crossActor` block / not in hybrid mode). Point the user at `/giga-workflow:epic-config <board>` to add one. Do not fall back to another board's config.
3. Bind `config.crossActor.*`. Do NOT read the scenario-catalog memory, the browser-profiles memory or the scenario body: the agent reads them. The session needs only the matched scenario's frontmatter and its `Bracket:` line, read with a `grep` (Phase 1). With no `memoryDir`, skip those reads and say the catalog is unavailable.

Strip the board token from `$ARGUMENTS`; the remainder is the scenario string + flags, parsed in Phase 1.

## Phase 0 — Dev server (session)

1. **Dev server up + monitoring armed** (from `config.crossActor.devServer`):
   - Run each `devServerPrelude` line first when launching. Then health-check: `curl -sS -o /dev/null -w "%{http_code}\n" <config.crossActor.devServer.healthCheckUrl>` should print `200`. If not, instruct the user to run `<config.crossActor.devServer.serveCommand>` and stop. If `config.crossActor.firebaseEnvNote` is set, surface it here so the user knows which Firebase target the dev server serves.
   - **Then arm a compile-error monitor** via the Monitor tool so any TypeScript / template compile errors that surface mid-scenario (typically because Claude wrote a new file on the impl branch during a fix-in-place loop) reach THIS session, the one that fixes code. Use the **constant** grep pattern against the board's log file:
     ```bash
     tail -f <config.crossActor.devServer.logFile> | grep -E --line-buffered "ERROR|TS[0-9]+|✘|Application bundle generation complete|Compilation complete|Watch mode enabled"
     ```
     Set `persistent: true` so the monitor lives for the whole scenario (and any fix-in-place re-runs that follow). If the user is running their own dev server with stdout in their terminal (no log file), ask them to redirect or — preferred — kill it and let Claude re-launch via `<config.crossActor.devServer.serveCommand> > <config.crossActor.devServer.logFile> 2>&1 &` so the monitor has a readable file. Without the monitor, a TS error in a freshly-added file looks identical to "watch service didn't subscribe" in the verifier UI. (This is the `giga-workflow:dev-server` skill's log-redirect and compile-error-monitor contract.)
   - If the dev-server log already shows `✘` / `ERROR TS####` entries before you dispatch, surface them and STOP — fix the compile error first, do not enter Phase 1.

Profiles connected and per-persona auth are checked by the agent (`drive.md`); a problem there comes back as `BLOCKED`.

## Phase 1 — Resolve scenario

The scenario files (`config.crossActor.scenarioDir`) are the source of truth for scenario bodies; do NOT hardcode them here. Resolve by frontmatter, not by reading: `grep -il '^title: .*<distinctive words>' <memoryDir>/<scenarioDir>/*.md`.

Parse the post-board remainder of `$ARGUMENTS`:
- **Empty scenario**: list the catalog with `grep -h '^title:\|^status:' <memoryDir>/<scenarioDir>/*.md | paste - -` (number = the file's `NN-` prefix; status runnable / partial / BLOCKED), and ask the user to pick by number or short name.
- **Catalog match** (substring or fuzzy match on the `title:` frontmatter, `grep -il` over the directory): read only its frontmatter and `Bracket:` line — `grep -E '^(title|status|actors):|Bracket:' <file>` — never the whole file. Confirm with the user which scenario you matched ("Running scenario: <title>. Confirm? y/n.").
- **No match (freeform)**: treat as ad-hoc. Ask the user explicitly: which actor profile, which verifier profile, what action, what to verify. Don't guess persona pairs — getting the actor wrong wastes a full setup cycle.

Persona names come from `config.crossActor.personas` (`displayName` is the identity throughout). A scenario marked BLOCKED in the catalog: surface its blocker and unblocking criteria from the frontmatter, then exit cleanly.

Extract mobile flags from `$ARGUMENTS` (the agent applies 390 × 844):
- `--mobile-actor`, `--mobile-verifier`, `--mobile-both`
- Default: no resize.

## Phase 0.5 — ONE bracket gate before dispatch

The scenario's `Bracket: before=<token> after=<token>` line holds the two tokens. The agent runs them; this session only collects the decisions, once.

- **If `$ARGUMENTS` contains `--auto-confirm-bracket`**: skip the prompt. Log a single line — `auto-confirm-bracket: before=<before-token>, after=<after-token(s)>` — and record both as yes. Caller asserts exclusive ownership of the test fixture; no human gate.
- **Otherwise**, surface the bracket:

  ```
  Scenario bracket (per catalog):
    before: <before-token>
    after:  <after-token(s)>

  Run `before` now? [Y/n/skip]
  Run `after` once the test passes? [Y/n]
  ```

  - `before` **Y / Enter** — the agent runs it first. **n** — abort the whole test (ask why before falling back to "run anyway"). **skip** — the agent runs no before; the report notes the test ran against ad-hoc state, not a clean baseline. (Only valid when the catalog marks the scenario's before as `(optional)`, e.g. pure-additive scenarios.)
  - `after` **Y / Enter** — the agent runs it only on PASS. **n** — leave residual data; the report notes cleanup was skipped so the next session expects stale data.
- Without `--auto-confirm-bracket`, never pre-approve either token: bracket commands touch the board's Firestore (the env in `config.crossActor.firebaseEnvNote`) and a stray run can disrupt parallel sessions or manual QA work. The flag is the explicit opt-in for orchestrator contexts where the caller owns the test fixture exclusively.

## Dispatch

One `Agent` call, `subagent_type: "general-purpose"`, `model: "sonnet"`, foreground. Keep the prompt small:

```
Read `${CLAUDE_SKILL_DIR}/drive.md` in full and follow it.

Inputs:
- board: <board>
- board config: .claude/giga/epic.<board>.json
- scenario file: <path, or "freeform">
- freeform scenario (only if freeform): actor, verifier, action, check
- actor persona: <displayName>
- verifier persona(s): <displayName(s)>
- mobile flags: <--mobile-actor | --mobile-verifier | --mobile-both | none>
- before bracket: <run | skip> (token: <before-token>)
- after bracket: <run on PASS | do not run> (token(s): <after-token(s)>)
- memoryDir: <memoryDir>
- dev-server log: <config.crossActor.devServer.logFile>
- deviceIds / profile map: <memoryDir>/<browserProfilesMemory>.md
```

The agent cannot ask the user anything: every decision above is already made.

## After the agent returns

Print its report. Then by status:

- **PASS** — offer a follow-up scenario or a GIF (`mcp__claude-in-chrome__gif_creator`) for documentation.
- **PARTIAL** — show the gaps with their category and recommend the next step per category.
- **FAIL** — the agent has preserved the state (no after bracket ran). Distinguish (a) write didn't fire (actor-side bug), (b) write fired but didn't propagate (Firestore / listener bug), (c) propagated but UI didn't render (selector / component bug); recommend the right next step. Ask the user "clean up or preserve for inspection?" and, if they say clean, run the `after` token(s) yourself, sequentially and awaited, per the board's `bracketMode`: `"skill"` runs each as a Skill invocation, `"npm"` as backgrounded Bash (`run_in_background: true`). If they preserve, note that cleanup is pending.
- **BLOCKED** — relay exactly what the user must do (a signed-out profile to sign in, an access code to enter, a missing profile to connect, a human sign-in step), then re-dispatch once they confirm. For `BLOCKED — compile error`, fix the code; the Monitor shows when the bundle rebuilds.

In a fix-in-place loop the session fixes the code and re-dispatches (the before bracket already ran: re-dispatch with `before: skip` unless the fix needs a clean baseline). The dev-server Monitor stays armed across re-dispatches.

## Notes

- Why a subagent, and why foreground: the agent runs in the foreground, so the user still watches the Chrome windows it drives, and every decision point (scenario, brackets, clean-up, fixes) stays in this session. Only the screenshots and page reads stay out of it. Backgrounded bash is only for `npm`-mode bracket commands, which produce no browser activity.
- Firestore anchors and the test fixture ids live in the board's catalog and browser-profiles memories; the agent reads them.
- Default scenario latency: 1–3 s end-to-end. Anything over 5 s is a red flag — likely the verifier's watch service didn't subscribe (persona gate, missing membership, wrong active group/org).
- This is the single cross-actor entry point for every hybrid board.
