#!/usr/bin/env bash
# SessionStart hook (matcher: compact): clear the standards-injection markers of the agent whose
# context was just compacted, so its next write injects again. Keyed exactly like
# inject-standards.sh. Never blocks: any error exits 0.

input=$(cat)
command -v jq >/dev/null 2>&1 || exit 0
sid=$(printf '%s' "$input" | jq -r '.session_id // "nosession"' 2>/dev/null)
agent=$(printf '%s' "$input" | jq -r '
  (.agent_id // "") as $a
  | if ($a | length) > 0 then $a
    elif ((.transcript_path // "") | length) > 0 then (.transcript_path | split("/") | last | sub("\\.jsonl$"; ""))
    else "main" end' 2>/dev/null)
[ -n "$agent" ] || agent="main"
agent=$(printf '%s' "$agent" | tr -c 'A-Za-z0-9_.-' '_')
[ -n "$sid" ] && [ "$sid" != "nosession" ] || exit 0
rm -rf "${TMPDIR:-/tmp}/claude-standards-injected/$sid/$agent" 2>/dev/null
exit 0
