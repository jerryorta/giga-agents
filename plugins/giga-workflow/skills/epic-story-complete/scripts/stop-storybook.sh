#!/bin/sh
# Stop THIS checkout's Storybook servers. Sibling clones are left running.
#
# Two traps this exists to encode, each of which has already cost a session:
#
#   - `pgrep -f storybook` also matches a compile monitor's own `tail -f /tmp/sb-*.log`.
#     Killing by that pattern takes out the watcher and can leave the server up. Only
#     `nx storybook` / `npm run storybook` supervisors are matched here.
#
#   - A sibling clone of the same repo may hold a Storybook port, and two clones look
#     identical from the process table. Every candidate is filtered on its cwd before
#     it is signalled, so a still-occupied port is a correct outcome rather than a
#     failed kill.
#
# Ports come from `workflow.storybook.ports` in .claude/giga/config.json at the repo
# root. No config file or no ports configured: nothing is done. Scope is Storybook
# only — app dev servers are never touched.
#
# `--print-ports` prints the configured ports and exits without signalling anything.
#
# Always exits 0. A failure here must not fail a story wrap-up.

set -u

REPO=$(git rev-parse --show-toplevel 2>/dev/null) || REPO=""
if [ -z "$REPO" ]; then
  echo "storybook: not inside a git repo — nothing stopped"
  exit 0
fi

CONFIG="$REPO/.claude/giga/config.json"
PORTS=""
if [ -f "$CONFIG" ]; then
  PORTS=$(python3 -c '
import json, sys
try:
    ports = json.load(open(sys.argv[1])).get("workflow", {}).get("storybook", {}).get("ports", [])
    print(" ".join(str(p) for p in ports if isinstance(p, int)))
except Exception:
    pass
' "$CONFIG" 2>/dev/null)
fi

if [ "${1:-}" = "--print-ports" ]; then
  echo "$PORTS"
  exit 0
fi

if [ -z "$PORTS" ]; then
  echo "storybook: no ports configured — nothing stopped"
  exit 0
fi

PORT_ARGS=""
for port in $PORTS; do PORT_ARGS="$PORT_ARGS -iTCP:$port"; done

seen=""
stopped=""
skipped=""

consider() {
  pid=$1
  case " $seen " in *" $pid "*) return ;; esac
  seen="$seen $pid"
  cwd=$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')
  case "$cwd" in
    "$REPO" | "$REPO"/*) kill "$pid" 2>/dev/null && stopped="$stopped $pid" ;;
    *) skipped="$skipped $pid($cwd)" ;;
  esac
}

for pid in $(lsof -nP $PORT_ARGS -sTCP:LISTEN -t 2>/dev/null); do
  consider "$pid"
done

# Supervisors that outlived their socket: `npm run storybook` → `npm exec nx storybook …` → node
for pid in $(pgrep -f "nx storybook|npm run storybook" 2>/dev/null); do
  consider "$pid"
done

if [ -n "$stopped" ]; then
  echo "storybook: stopped$stopped"
else
  echo "storybook: none of ours were running"
fi
[ -n "$skipped" ] && echo "storybook: skipped, other checkout —$skipped"

survivors=$(lsof -nP $PORT_ARGS -sTCP:LISTEN -t 2>/dev/null | sort -u | tr '\n' ' ')
[ -n "$survivors" ] && echo "storybook: still listening: ${survivors}(correct iff another clone owns them)"

exit 0
