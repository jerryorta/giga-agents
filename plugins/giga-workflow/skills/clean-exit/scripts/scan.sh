#!/bin/bash
# Read-only inventory for /clean-exit. Signals nothing, removes nothing.
#
# PROCESSES — every process group with a member whose cwd is this checkout or one of its linked
# worktrees, classified by where it runs:
#   detached  no controlling tty → launched in the background by this or an earlier agent session
#   terminal  a member holds a tty → running in the user's own terminal
# Excluded outright: descendants of any `claude` process (harness-managed — TaskStop owns them, and
# MCP servers die with the session), IDE-owned trees (VS Code / Cursor / JetBrains extensions) and the
# Nx daemon (shared with the IDE and every terminal; restarts on demand).
# WORKTREES — every linked worktree with its dirty-file count and commits not on any remote.
#
# Always exits 0.

set -u

TOP=$(git rev-parse --show-toplevel 2>/dev/null) || { echo "clean-exit: not inside a git repo"; exit 0; }
COMMON=$(git rev-parse --path-format=absolute --git-common-dir)
MAIN=$(cd "$COMMON/.." && pwd -P)
ROOTS=$(git worktree list --porcelain | sed -n 's/^worktree //p' | tr '\n' '|')

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

ps -axo pid=,ppid=,pgid=,tty=,etime=,command= > "$tmp/ps"
lsof -nP -d cwd -Fpn 2>/dev/null > "$tmp/cwd"
lsof -nP -iTCP -sTCP:LISTEN -Fpn 2>/dev/null > "$tmp/listen"

echo "== PROCESSES rooted in $MAIN (+ worktrees) =="
awk -v roots="$ROOTS" -v self="$$" '
  function secs(e,   d, n, p, s, i) {
    d = 0
    if (index(e, "-")) { split(e, p, "-"); d = p[1]; e = p[2] }
    n = split(e, p, ":"); s = 0
    for (i = 1; i <= n; i++) s = s * 60 + p[i]
    return d * 86400 + s
  }
  function inroots(path,   i) {
    path = tolower(path)
    for (i = 1; i <= nr; i++) if (path == r[i] || index(path, r[i] "/") == 1) return 1
    return 0
  }
  function flagged(pid, re,   p, guard) {
    p = pid; guard = 0
    while (p > 1 && (p in ppid) && guard++ < 64) { if (cmd[p] ~ re) return 1; p = ppid[p] }
    return 0
  }
  BEGIN {
    nr = split(roots, raw, "|"); n = 0
    for (i = 1; i <= nr; i++) if (raw[i] != "") r[++n] = tolower(raw[i])
    nr = n
  }
  FILENAME ~ /\/ps$/ {
    pid = $1; ppid[pid] = $2; pgid[pid] = $3; tty[pid] = $4; et[pid] = $5
    c = $0; sub(/^ *[0-9]+ +[0-9]+ +[0-9]+ +[^ ]+ +[^ ]+ +/, "", c); cmd[pid] = c
    next
  }
  FILENAME ~ /\/cwd$/ {
    if ($0 ~ /^p/) cur = substr($0, 2); else if ($0 ~ /^n/) cwd[cur] = substr($0, 2)
    next
  }
  FILENAME ~ /\/listen$/ {
    if ($0 ~ /^p/) cur = substr($0, 2)
    else if ($0 ~ /^n/) { port = $0; sub(/.*:/, "", port); if (index(" " ports[cur] " ", " " port " ") == 0) ports[cur] = ports[cur] " " port }
    next
  }
  END {
    claude_re = "(^|/)claude( |$)"
    ide_re = "Visual Studio Code|Code Helper|Cursor\\.app|JetBrains|IntelliJ|WebStorm|Zed\\.app|nx/.*daemon/server/start\\.js"
    for (pid in cwd) {
      if (!(pid in ppid) || pid == self || !inroots(cwd[pid])) continue
      if (flagged(pid, claude_re) || flagged(pid, ide_re)) continue
      g = pgid[pid]; hit[g] = 1
    }
    for (pid in pgid) {
      g = pgid[pid]; if (!(g in hit) || pid == self || flagged(pid, claude_re) || flagged(pid, ide_re)) continue
      members[g] = members[g] " " pid
      if (tty[pid] != "??") term[g] = 1
      if (ports[pid] != "") gports[g] = gports[g] ports[pid]
      if (!(g in lead) || secs(et[pid]) > secs(et[lead[g]]) || (secs(et[pid]) == secs(et[lead[g]]) && pid + 0 < lead[g] + 0)) lead[g] = pid
      if (cwd[pid] != "" && inroots(cwd[pid])) gcwd[g] = cwd[pid]
    }
    found = 0
    for (g in hit) {
      found = 1; l = lead[g]
      cls = (g in term) ? "terminal" : "detached"
      printf "  pgid %-6s %-8s up %-12s ports:%s\n", g, cls, et[l], (gports[g] == "" ? " -" : gports[g])
      printf "    cwd  %s\n    cmd  %s\n    pids%s\n", gcwd[g], substr(cmd[l], 1, 140), members[g]
    }
    if (!found) print "  (none)"
  }
' "$tmp/ps" "$tmp/cwd" "$tmp/listen"

echo
echo "== WORKTREES =="
git worktree prune --dry-run -v 2>&1 | sed 's/^/  prunable: /'
git worktree list --porcelain | awk '/^worktree /{p=substr($0,10)} /^branch /{b[p]=substr($0,19)} /^detached/{b[p]="(detached)"} /^locked/{l[p]=1} /^$/{if(p!="")o[++n]=p; p=""} END{if(p!="")o[++n]=p; for(i=1;i<=n;i++) print o[i] "\t" b[o[i]] "\t" (o[i] in l)}' |
while IFS="$(printf '\t')" read -r wt branch locked; do
  [ "$wt" = "$MAIN" ] && continue
  if [ ! -d "$wt" ]; then echo "  $wt  [$branch]  MISSING on disk (prunable)"; continue; fi
  dirty=$(git -C "$wt" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  unpushed=$(git -C "$wt" rev-list --count HEAD --not --remotes 2>/dev/null || echo "?")
  where="external"
  case "$wt" in "$MAIN"/.claude/worktrees/*) where="harness" ;; esac
  here=""
  [ "$wt" = "$TOP" ] && here=" CURRENT"
  lk=""
  [ "$locked" = "1" ] && lk=" LOCKED"
  echo "  $wt  [$branch]  $where  dirty:$dirty  unpushed-commits:$unpushed$lk$here"
done
[ "$(git worktree list | wc -l | tr -d ' ')" = "1" ] && echo "  (no linked worktrees)"

exit 0
