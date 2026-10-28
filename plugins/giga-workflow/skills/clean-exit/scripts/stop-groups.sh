#!/bin/bash
# Stop whole process groups by pgid — the `npm run` supervisor, `nx`, and the node server beneath it
# go down together, so no orphan keeps the port.
#
# Each pgid is re-checked immediately before it is signalled: a member must still have its cwd inside
# this checkout or one of its worktrees. A pgid recycled since /clean-exit's scan, or one belonging to
# a sibling clone, is skipped rather than killed. SIGTERM first, SIGKILL after 10 s.
#
# Usage: stop-groups.sh <pgid> [<pgid> …]    Always exits 0.

set -u

git rev-parse --show-toplevel >/dev/null 2>&1 || { echo "clean-exit: not inside a git repo — nothing stopped"; exit 0; }
ROOTS=$(git worktree list --porcelain | sed -n 's/^worktree //p' | tr 'A-Z' 'a-z')
own_pgid=$(ps -o pgid= -p $$ | tr -d ' ')

ours() {
  for pid in $(pgrep -g "$1" 2>/dev/null); do
    cwd=$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | tr 'A-Z' 'a-z')
    [ -z "$cwd" ] && continue
    for root in $ROOTS; do
      case "$cwd" in "$root" | "$root"/*) return 0 ;; esac
    done
  done
  return 1
}

for g in "$@"; do
  case "$g" in '' | *[!0-9]*) echo "  $g: not a pgid — skipped"; continue ;; esac
  if [ "$g" = "$own_pgid" ]; then echo "  pgid $g: this shell's own group — skipped"; continue; fi
  if ! pgrep -g "$g" >/dev/null 2>&1; then echo "  pgid $g: already gone"; continue; fi
  if ! ours "$g"; then echo "  pgid $g: no member rooted in this checkout any more — skipped"; continue; fi

  ports=$(for pid in $(pgrep -g "$g"); do lsof -nP -a -p "$pid" -iTCP -sTCP:LISTEN -Fn 2>/dev/null | sed -n 's/^n.*://p'; done | sort -u | tr '\n' ' ')
  kill -TERM -- "-$g" 2>/dev/null
  i=0
  while pgrep -g "$g" >/dev/null 2>&1 && [ $i -lt 20 ]; do sleep 0.5; i=$((i + 1)); done
  how="TERM"
  if pgrep -g "$g" >/dev/null 2>&1; then kill -KILL -- "-$g" 2>/dev/null; how="KILL"; sleep 0.5; fi

  if pgrep -g "$g" >/dev/null 2>&1; then
    echo "  pgid $g: STILL RUNNING after SIGKILL — pids $(pgrep -g "$g" | tr '\n' ' ')"
  else
    echo "  pgid $g: stopped ($how)${ports:+ — freed ports $ports}"
  fi
done

exit 0
