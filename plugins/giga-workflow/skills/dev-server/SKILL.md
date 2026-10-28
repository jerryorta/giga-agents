---
name: dev-server
description: Launch and supervise a local dev server or Storybook for any app in this workspace, so browser work runs against a live, compiling build. Owns the per-app launch command + port + log-file lookup (from `devServers` in `.claude/giga/config.json`), the mandatory stdout→log redirect, the compile-error Monitor contract, and the measured Storybook diagnostics gotchas (its log reports TypeScript source errors but is SILENT on Angular template errors, and a healthy build emits no success line at all). Use whenever a task runs an app in the browser — cross-actor testing, manual verification, screenshotting, driving any `localhost:<port>` URL, or adding/editing a Storybook story — and before concluding a change works, a build is green, or a bug is absent.
---

# Local dev servers for actor / browser testing

Whenever a task involves running an app in the browser — cross-actor testing, manual verification, screenshotting, or any session driving a `localhost:<port>` URL — Claude is responsible for the dev server's runtime state. Same contract for every app; only the launch command and port change. Look up the app in `devServers`, then follow the same four steps.

## Project config

Repo-specific values come from `.claude/giga/config.json` at the repository root, under `workflow`. Read it once at the start. A missing file or field takes the fallback below, never a guess.

| Field | Used for | When absent |
| --- | --- | --- |
| `devServers` | the per-app launch `command`, `port`, `logFile` and `kind` (`app` or `storybook`); the entry with `kind: "storybook"` is Storybook | ask the user for the launch command, port and log file |
| `devServerPrelude` | shell lines run before every launch (for example selecting the right runtime version) | run the launch command as is |
| `storybook.ports` | every port a Storybook for this repo may hold, including the extra ones | only the `kind: "storybook"` entry's port is checked |

## App → command + port lookup

Pick the `devServers` entry for whichever app the task targets (match on `app`); its `command`, `port` and `logFile` fill the placeholders below (`<launch-command>`, `<port>`, `<log-file>`). A `<repo>` in a `logFile` is this checkout's directory name.

⚠️ **Run every `devServerPrelude` line before each launch.** A *running* Claude Code keeps the PATH it started with, so its shell can resolve a different runtime version than the repo needs, and a wrong version fails loudly on install and quietly at runtime. For example, with a prelude of `nvm use`:

```sh
export NVM_DIR="$HOME/.nvm"; [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
<devServerPrelude lines>
<launch-command> > <log-file> 2>&1 &
```

## Storybook specifics

Storybook is a **different builder** (webpack) from the `kind: "app"` entries (Angular CLI/esbuild), so step 3's monitor command does not work against it unchanged.

⚠️ **What its log does and does not report — measured, because the intuitive reading is wrong in the dangerous direction.** The dev-server log reports **TypeScript source diagnostics** and is **silent on Angular template diagnostics**. Falsifiability-tested both ways on a library story:

| Injected error | Reported? |
| --- | --- |
| `.ts` source — `const x: number = 's'` (TS2322) in a story component | **Yes, in ~4s** — `ERROR in <file>:<line> - error TS2322: …` then `preview compiled with 1 error` |
| Template — a `strictTemplates` violation on a `let-` binding | **No.** Silent across **482** incremental rebuild cycles, a cache reset + cold boot, and an explicit `iframe.html` request returning 200 |

Two consequences, and the second is the one that bites:

- **It emits no success verdict at all** — only error verdicts. A prior log carrying 31 verdicts had every one of them an error naming a `.ts` file. So **silence is the normal state of a healthy build**, and any wait-loop keyed to a success line hangs forever.
- **A story template is checked by nothing automated.** A library with no `build` target never runs `ngtsc`: `tsc -p tsconfig.lib.json` checks TypeScript but not templates, lint and Jest do not type-check templates, and the dev server does not report them. A broken binding — a projected template missing its type carrier, a field that does not exist — surfaces only when a human loads the story and reads it and its console. Treat that as the check, and consider a `build-storybook` run when a template change matters.

- ⚠️ **Strip ANSI before grepping.** webpack writes `ERROR` and ` in` with escape codes *between* them, so a literal `grep "ERROR in"` matches **nothing** and the monitor reports silence on a failing build.
- ⚠️ **The log is append-only — read it from a marked position, never with a bare `tail`.** An error written five minutes ago looks identical to one written now, so a `tail | grep ERROR` after an edit reports the *previous* verdict whenever no rebuild has happened yet. This is the single easiest way to chase a fixed bug. Mark, then read past the mark:
  ⚠️ **Wait on the REBUILD, never on a verdict.** A clean build logs no verdict line, so `until … grep -qE "compiled (successfully|with)"` never terminates on success — it reads as "still compiling" forever on exactly the builds that are fine. Webpack's progress ticker is the only signal that a rebuild happened at all:
  ```bash
  mark=$(wc -l < <log-file>)
  # …make the edit, then wait for a rebuild cycle logged after the mark…
  until tail -n +$((mark+1)) <log-file> | grep -q "webpack.Progress"; do sleep 2; done
  sleep 5   # let the cycle finish; an error lands a beat after the progress lines
  tail -n +$((mark+1)) <log-file> | perl -pe 's/\e\[[0-9;]*[a-zA-Z]//g' \
    | grep -E "ERROR in|TS[0-9]{4}|NG[0-9]{4}|preview compiled with"
  ```
  No output means no **source** error. It says nothing about the templates — see the table above.
- **Transient errors during rapid edits and branch switches are real, not noise.** Adding a usage before its import, or checking out another branch, genuinely breaks the build for that rebuild — the compiler is right and the error clears on the next one. Do not train yourself to dismiss them; just confirm against a verdict logged *after* your change. Cross-check with `npx tsc -p libs/<lib>/tsconfig.lib.json --noEmit` when the two disagree, remembering `tsc` does **not** check Angular templates.
- ⚠️ **`pgrep -f storybook` matches the monitor's own `tail -f /tmp/…storybook.log`**, so killing the server that way kills the watcher too. Target the port holder (`lsof -nP -iTCP:<port> -sTCP:LISTEN -t`) — and only after the cwd check in the next bullet. `pkill -f "nx storybook storybook-app"` is cwd-blind: a sibling clone runs the identical command, so it takes that clone's server down too.
- ⚠️ **The Storybook port (the `kind: "storybook"` entry's `port`, plus any in `storybook.ports`) is fixed and may be held by a SIBLING clone.** The story tree looks identical, so a check can silently exercise the wrong repo. Confirm the serving cwd: `lsof -a -p <pid> -d cwd -Fn`. **A holder whose cwd is not this clone is the user's server — never kill it** (CLAUDE.md: never kill a dev server the user is relying on); the port being free at session start proves nothing, since the user can launch the other clone's Storybook at any point mid-session. Report the holder's cwd and pid, and let the user decide. The restart block below encodes this guard — use it verbatim rather than a bare `xargs kill`.

### ⚠️ HMR is best-effort — a clean restart is the only verification

Storybook is configured for hot module reload, and **it is not reliably good at it.** The fault is shared between Storybook and the Angular compiler layers (webpack, and vite where it applies); neither is perfect. A rebuild can silently fail to pick up a change, or report on a tree that no longer matches disk.

**There is no signal that tells you this has happened.** That is the whole problem — the log looks entirely normal either way. So deciding when to restart is an **intuitive judgement call, not a rule**, and no benchmark or indicator exists to make it one. Do not expect one.

⚠️ **The dangerous direction is a false CLEAN, not a false error.** A spurious error makes you look at the code; a spurious clean makes you ship. And a clean here is **silence** — the log prints nothing on success — so the false-clean and the true-clean are byte-identical, which is as thin a signal as it sounds. The instinct to double-check only when something looks broken is therefore backwards: that is precisely the case HMR handles fine. **Restart before you trust a verdict you intend to act on**, not after you start doubting one:

- declaring a story or a feature done
- quoting a number or a green build as evidence
- concluding a bug is *not* present

```sh
# the Storybook port is shared with sibling clones: kill ONLY a holder whose cwd is THIS clone (never a bare `xargs kill`)
pid=$(lsof -nP -iTCP:<port> -sTCP:LISTEN -t | head -1)
cwd=$([ -n "$pid" ] && lsof -a -p "$pid" -d cwd -Fn | sed -n 's/^n//p')
if [ -n "$pid" ] && [ "$cwd" != "$(git rev-parse --show-toplevel)" ]; then
  echo "<port> is held by $cwd (pid $pid) — another clone's Storybook. STOP: do not kill, do not launch; tell the user."
else
  [ -n "$pid" ] && kill "$pid"                        # ours — never `pgrep -f storybook`, see above
  # the workspace's cache reset (Nx: `npx nx reset`) clears the cache + stops the daemon
  # run the devServerPrelude lines
  <storybook-command> > <storybook-log-file> 2>&1 &
fi
```

Prompts to *consider* it — deliberately not an exhaustive trigger list, because the failure gives no warning: switching branches, a `git pull` that moves many files, a dependency install, a rename or a move, or any result you find yourself arguing with. Expect a slower first boot (the cache is gone), and rotate or re-mark the log, since a fresh run appends to whatever was already there.

Monitor command for Storybook (use in place of step 3's):

```
tail -f <log-file> | perl -pe 'BEGIN { $| = 1 } s/\e\[[0-9;]*[a-zA-Z]//g' | grep -E --line-buffered "ERROR in|TS[0-9]{4}|NG[0-9]{4}|Module not found|preview compiled with"
```

⚠️ The `BEGIN { $| = 1 }` is load-bearing: `perl` writing to a pipe is block-buffered, so without it every stripped line sits in perl's buffer and the monitor emits nothing across a whole rebuild (measured — two clean rebuilds, zero events). Prove any monitor with a deliberate event before trusting its silence.

⚠️ **This monitor fires on source errors and stays silent on everything else, including a broken template.** It is worth arming — it catches a missing import or a bad type within seconds, which is exactly the class that masquerades as a propagation bug. But its silence is not a passing build, so never quote it as one.

## The four steps (same for every app)

1. **Launch with stdout redirected to a log file.** The log redirect is REQUIRED — the in-session compile-error monitor reads from it.
   ```
   <launch-command> > <log-file> 2>&1 &
   ```
   If the user already has the server running in their terminal (stdout not redirected to the log file), kill it and relaunch with the redirect so the monitor can read it — for Storybook, only after confirming the holder's cwd is this clone (§ Storybook specifics): a sibling clone's server on the Storybook port is not yours to kill. Without the log file, the monitor is blind and compile errors masquerade as runtime / propagation bugs.

2. **Health-check before starting any browser work.**
   ```
   curl -sS -o /dev/null -w "%{http_code}\n" http://localhost:<port>
   ```
   Must print `200`. If not, launch the dev server with step 1's command.

3. **Arm the compile-error monitor (MANDATORY for any session that writes new TS/HTML/SCSS files Claude will then test in the browser).** Use the `Monitor` tool with `persistent: true`:
   ```
   tail -f <log-file> | grep -E --line-buffered "ERROR|TS[0-9]+|✘|Application bundle generation complete"
   ```
   Every compile cycle emits a notification — `Application bundle generation complete` confirms the latest impl change is live; any `✘` / `ERROR TS####` line is a blocker the current session must fix BEFORE driving the next browser action. Without this monitor, a TS error in a freshly-added file masquerades as a propagation / data bug and burns 5–10 minutes of investigation.

4. **Cleanup.** Stop the monitor with `TaskStop` when the browser-driving phase of the session ends. Leave the dev server running (the user typically wants to keep it alive across sessions).

Codified in `/giga-workflow:epic-cross-actor-test` (Phase 0). Other apps inherit the same pattern through this section.

**This applies to story work too, not just app/actor testing.** Any story that adds or edits a Storybook story should arm the monitor — it catches a source error in seconds, which is the difference between "the import is missing" and half an hour of debugging a story that renders blank. ⚠️ **But it does not type-check the template, and nothing else does either** (see § Storybook specifics). So a story that projects an `ng-template` is only actually verified by loading it and reading it — and its console — by eye.
