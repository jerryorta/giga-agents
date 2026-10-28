#!/usr/bin/env bash
# PreToolUse hook: when a file is written (Write/Edit/MultiEdit, or a Bash command that writes a
# source file), inject the standards that govern it, routed by the `standards` table in
# .claude/giga/config.json and pulled live from their docs. Never blocks: any error exits 0.

input=$(cat)
command -v jq >/dev/null 2>&1 || exit 0

tool=$(printf '%s' "$input" | jq -r '.tool_name // empty'               2>/dev/null)
fp=$(printf '%s' "$input"   | jq -r '.tool_input.file_path // empty'    2>/dev/null)
sid=$(printf '%s' "$input"  | jq -r '.session_id // "nosession"'        2>/dev/null)
cwd=$(printf '%s' "$input"  | jq -r '.cwd // empty'                     2>/dev/null)
# Agent scope: a subagent's own id when the harness sends one, else the transcript file that
# agent is writing (unique per agent — subagents live under <session>/subagents/), else "main".
agent=$(printf '%s' "$input" | jq -r '
  (.agent_id // "") as $a
  | if ($a | length) > 0 then $a
    elif ((.transcript_path // "") | length) > 0 then (.transcript_path | split("/") | last | sub("\\.jsonl$"; ""))
    else "main" end' 2>/dev/null)
[ -n "$agent" ] || agent="main"
agent=$(printf '%s' "$agent" | tr -c 'A-Za-z0-9_.-' '_')
cmd=""
[ "$tool" = "Bash" ] && cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null)
[ -n "$fp$cmd" ] || exit 0

root=$(git -C "${cwd:-.}" rev-parse --show-toplevel 2>/dev/null || printf '%s' "${cwd:-.}")
std=$(jq -c '.standards | objects' "$root/.claude/giga/config.json" 2>/dev/null)
[ -n "$std" ] || exit 0
# cfg [jq options] <filter> -> the filter applied to the standards table, raw output.
cfg() { printf '%s' "$std" | jq -r "$@" 2>/dev/null; }

# Bash branch: only a command that WRITES a source file (standards.sourceFilePattern) is a
# standards event. The target is the path in the WRITING position of the command — after a
# redirect, tee, or cp/mv, inside a scripted open(…, 'w'|'a'), or anywhere for an in-place
# sed/perl — so a redirect to /tmp beside a source path that is merely read stays silent.
bash_write=0
if [ "$tool" = "Bash" ]; then
  pattern=$(cfg '.sourceFilePattern // empty')
  [ -n "$pattern" ] && [ -n "$cmd" ] || exit 0
  SRC="(/[A-Za-z0-9_./-]+/)?(${pattern})"
  printf '' | grep -qE "$SRC" 2>/dev/null; [ $? -lt 2 ] || exit 0   # an invalid pattern disables this branch
  fp=""
  if printf '%s' "$cmd" | grep -qE '(sed[[:space:]]+-[A-Za-z]*i|perl[[:space:]]+-[A-Za-z]*i)'; then
    fp=$(printf '%s' "$cmd" | grep -oE "$SRC" | head -1)
  fi
  [ -z "$fp" ] && fp=$(printf '%s' "$cmd" | grep -oE "(^|[^0-9&<>])>>?[[:space:]]*['\"]?$SRC" | grep -oE "$SRC" | head -1)
  [ -z "$fp" ] && fp=$(printf '%s' "$cmd" | grep -oE "(^|[[:space:]|;])tee[[:space:]]+(-a[[:space:]]+)?['\"]?$SRC" | grep -oE "$SRC" | head -1)
  [ -z "$fp" ] && fp=$(printf '%s' "$cmd" | grep -oE "(^|[[:space:]|;&(])(cp|mv)[[:space:]]+(-[A-Za-z]+[[:space:]]+)*[^[:space:]]+[[:space:]]+['\"]?$SRC" | grep -oE "$SRC" | tail -1)
  [ -z "$fp" ] && fp=$(printf '%s' "$cmd" | grep -oE "open\(['\"]$SRC['\"][[:space:]]*,[[:space:]]*['\"][wa]" | grep -oE "$SRC" | head -1)
  [ -n "$fp" ] || exit 0
  bash_write=1
fi
[ -n "$fp" ] || exit 0

case "$fp" in /*) ;; *) fp="$root/$fp" ;; esac
rel="${fp#$root/}"
# doc_path <field> -> the root joined to that repo-relative standards path, or empty when absent.
doc_path() { local p; p=$(cfg --arg k "$1" '.[$k] // empty'); [ -n "$p" ] && printf '%s/%s' "$root" "$p"; }
CONSTRAINTS=$(doc_path constraintsFile)
ANTIPATTERNS=$(doc_path antiPatternsFile)
STANDARDS=$(doc_path fragmentsDir)
LIBTYPES=$(doc_path libTypesDir)
INSTRUCTIONS=$(doc_path guidesDir)
# The harness shows a hook's additionalContext inline only up to ~10 KB; a larger payload goes to
# a file behind a 2 KB preview that is rarely opened. So the payload is assembled in priority
# order under this budget, and what does not fit becomes a pointer.
BUDGET_BYTES=$(cfg '.budgetBytes // 9800')
case "$BUDGET_BYTES" in ''|*[!0-9]*) BUDGET_BYTES=9800 ;; esac

# read_applyto <file> -> raw applyTo frontmatter value (unquoted), or empty.
read_applyto() {
  grep -m1 '^applyTo:' "$1" 2>/dev/null | sed -E "s/^applyTo:[[:space:]]*//; s/^['\"]//; s/['\"][[:space:]]*$//"
}
# path_matches <applyTo-spec> -> 0 if $rel matches (precise globs only; '**' never matches).
path_matches() {
  local spec="$1" g pat rc=1
  { [ -z "$spec" ] || [ "$spec" = '**' ]; } && return 1
  local IFS=,
  set -f                       # disable pathname expansion — a glob like libs/*/ui/** must
  for g in $spec; do           # stay literal here, NOT expand against the filesystem
    g="${g//[[:space:]]/}"
    { [ -z "$g" ] || [ "$g" = '**' ]; } && continue
    pat="${g//\*\*\//}"
    case "$rel" in $pat) rc=0; break ;; esac
  done
  set +f
  return $rc
}
# first_match <list> -> index of the first entry of standards.<list> with a `match` glob fitting $rel.
first_match() {
  local i g hit=""
  set -f
  while IFS=$'\t' read -r i g; do
    case "$rel" in $g) hit="$i"; break ;; esac
  done < <(cfg --arg k "$1" '.[$k] // [] | to_entries[] | "\(.key)\t\(.value.match // [] | .[])"')
  set +f
  printf '%s' "$hit"
}
# strip_frontmatter <file> -> file body with a leading --- YAML block removed.
strip_frontmatter() {
  awk 'NR==1 && $0=="---" { fm=1; next } fm && $0=="---" { fm=0; next } !fm { print }' "$1" 2>/dev/null
}
# nbytes <string> -> byte length (the harness threshold is measured in bytes, not characters).
nbytes() { printf '%s' "$1" | wc -c | tr -d ' '; }

# ---- Artifact detection: the first matching artifacts entry, plus the first everyArtifact entry ----
artifact=""; headings=""; ids="[]"; refguide=""
a=$(first_match artifacts)
if [ -n "$a" ]; then
  e=$(first_match everyArtifact)
  # art <filter> -> the filter with $a (the artifacts index) and $e (everyArtifact index or null).
  art() { cfg --argjson a "$a" --argjson e "${e:-null}" "$1"; }
  artifact=$(art '.artifacts[$a].artifact // empty')
  refguide=$(art '.artifacts[$a].guide // empty')
  headings=$(art '[.artifacts[$a], .everyArtifact[$e // empty]] | map(.sections // []) | add | join("\n")')
  ids=$(art '[.artifacts[$a], .everyArtifact[$e // empty]] | map(.antiPatterns // []) | add | tojson')
fi

# Keyed by session AND agent: a subagent shares its parent's session_id but has its own context,
# so a session-only key would let the first writer silence every later agent. Compaction clears
# the compacted agent's markers (reset-standards-markers.sh) so its next write re-injects.
mark_dir="${TMPDIR:-/tmp}/claude-standards-injected/$sid/$agent"
mkdir -p "$mark_dir" 2>/dev/null

# ---- GLOBAL scope (invariants + anti-patterns + artifact fragments + guides) — once per artifact ----
sections=""; patterns=""; guides=""
frag_paths=(); frag_bodies=()
if [ -n "$artifact" ] && [ ! -e "$mark_dir/art-$artifact" ]; then
  : > "$mark_dir/art-$artifact" 2>/dev/null
  if [ -f "$CONSTRAINTS" ]; then
    while IFS= read -r h; do
      [ -n "$h" ] || continue
      sec=$(awk -v h="$h" '
        /^## / { cur = substr($0, 4); if (substr(cur, 1, length(h)) == h) { cap = 1; print; next } else if (cap) { cap = 0 } }
        cap { print }' "$CONSTRAINTS" 2>/dev/null)
      [ -n "$sec" ] && sections="$sections$sec"$'\n\n'
    done <<< "$headings"
  fi
  if [ -f "$ANTIPATTERNS" ] && [ "$ids" != "[]" ]; then
    patterns=$(jq -r --argjson ids "$ids" '
      .patterns[] | select(.id as $x | $ids | any(. == $x))
      | "- [\(.severity)] \(.description)" + (if .fix then " → " + .fix else "" end)' "$ANTIPATTERNS" 2>/dev/null)
  fi
  if [ -d "$STANDARDS" ]; then
    while IFS= read -r frag; do
      path_matches "$(read_applyto "$frag")" || continue
      body=$(strip_frontmatter "$frag")
      [ -n "$body" ] || continue
      frag_paths+=("${frag#$root/}"); frag_bodies+=("$body")
    done < <(find "$STANDARDS" -maxdepth 1 -name '*.md' 2>/dev/null | sort)
  fi
  if [ -d "$INSTRUCTIONS" ]; then
    while IFS= read -r doc; do
      path_matches "$(read_applyto "$doc")" || continue
      title=$(grep -m1 '^# ' "$doc" 2>/dev/null | sed 's/^#[[:space:]]*//')
      guides="${guides}- ${doc#$root/}${title:+ — $title}"$'\n'
    done < <(find "$INSTRUCTIONS" -name '*.instructions.md' 2>/dev/null | sort)
  fi
  [ -n "$refguide" ] && guides="- ${refguide}"$'\n'"${guides}"
fi

# ---- LIBRARY-TYPE scope (one fragment per lib-type) — once per lib-type ----
libstd=""
if [ -d "$LIBTYPES" ]; then
  while IFS= read -r frag; do
    path_matches "$(read_applyto "$frag")" || continue
    key="libtype-$(basename "$frag" .md)"
    [ -e "$mark_dir/$key" ] && continue
    : > "$mark_dir/$key" 2>/dev/null
    body=$(strip_frontmatter "$frag"); [ -n "$body" ] && libstd="${libstd}${body}"$'\n\n'
  done < <(find "$LIBTYPES" -name '*.md' 2>/dev/null | sort)
fi

# ---- LIBRARY-INSTANCE scope (nearest AGENTS.md above the file) — once per library ----
notes_file=""; libpath=""
d=$(dirname "$fp")
while [ -n "$d" ] && [ "$d" != "/" ] && [ "$d" != "$root" ]; do
  if [ -f "$d/AGENTS.md" ]; then
    key="lib-$(printf '%s' "${d#$root/}" | tr '/.' '__')"
    if [ ! -e "$mark_dir/$key" ]; then
      : > "$mark_dir/$key" 2>/dev/null
      notes_file="$d/AGENTS.md"; libpath="${d#$root/}/AGENTS.md"
    fi
    break
  fi
  nd=$(dirname "$d"); [ "$nd" = "$d" ] && break; d="$nd"
done

# ---- Nothing new this session? stay silent. ----
[ -z "$sections$patterns$guides$libstd$notes_file" ] && [ "${#frag_paths[@]}" -eq 0 ] && exit 0

# ---- Assemble additionalContext under the byte budget, in priority order ----
ctx="📐 Standards for this ${artifact:-source} file ($(basename "$fp")) — apply these BEFORE writing."
if [ "$bash_write" -eq 1 ]; then
  ctx="⚠️ This Bash command writes a source file (${rel}). Source edits belong in the Edit / Write tools — they are what the standards hook, the IDE and review tooling key on; a shell rewrite bypasses all of it. If you continue in Bash, the standards below still apply.

${ctx}"
fi
ctx="${ctx}"$'\n\n'
# The guide / pointer list is appended last but must always fit: reserve its worst case
# (every fragment demoted to a pointer) before sizing the notes and fragment blocks.
reserve=$(( $(nbytes "$guides") + 110 * ${#frag_paths[@]} + 100 ))

[ -n "$sections" ] && ctx="${ctx}── Constraints (authoritative · ${CONSTRAINTS#$root/}) ──
${sections}"
[ -n "$patterns" ] && ctx="${ctx}── Anti-patterns to avoid (${ANTIPATTERNS#$root/}) ──
${patterns}

"
[ -n "$libstd" ] && ctx="${ctx}── Library-type standard (${LIBTYPES#$root/}) ──
${libstd}"
remaining=$(( BUDGET_BYTES - reserve - $(nbytes "$ctx") ))

# Library notes: whole file when it fits; otherwise intro + first section (if it fits) + the
# full heading index, so the writer knows which sections to open before touching the library.
if [ -n "$notes_file" ]; then
  notes_body=$(strip_frontmatter "$notes_file")
  hdr="── Library notes (${libpath}) ──"$'\n'
  if [ $(( $(nbytes "$notes_body") + ${#hdr} + 8 )) -le "$remaining" ]; then
    ctx="${ctx}${hdr}${notes_body}"$'\n\n'
  else
    kb=$(( ($(wc -c < "$notes_file") + 1023) / 1024 ))
    intro=$(printf '%s\n' "$notes_body" | awk '/^## /{exit} {print}')
    first=$(printf '%s\n' "$notes_body" | awk '/^## /{n++} n==1{print} n==2{exit}')
    toc=$(printf '%s\n' "$notes_body" | grep -E '^##+ ')
    toc_total=$(printf '%s\n' "$toc" | grep -c .)
    idx_hdr=$'\n'"── Section index of ${libpath} (${kb} KB — only the intro is inline; open the sections that touch your change before writing) ──"$'\n'
    # fit_toc <bytes> -> as many heading lines as fit, then a count of the rest with the grep to list them.
    fit_toc() {
      local budget=$1 out="" n=0 line
      while IFS= read -r line; do
        [ $(( $(nbytes "$out") + $(nbytes "$line") + 1 )) -gt "$budget" ] && break
        out="${out}${line}"$'\n'; n=$((n+1))
      done <<< "$toc"
      printf '%s' "$out"
      [ "$n" -lt "$toc_total" ] && printf '… %d more sections — `grep -n '"'"'^##'"'"' %s`\n' "$((toc_total - n))" "$libpath"
      return 0
    }
    block="${hdr}${intro}"$'\n'"${first}"$'\n'"${idx_hdr}${toc}"$'\n\n'
    if [ "$(nbytes "$block")" -gt "$remaining" ]; then
      head_part="${hdr}${intro}"$'\n'"${idx_hdr}"
      toc_budget=$(( remaining - $(nbytes "$head_part") - 120 ))
      if [ "$toc_budget" -gt 80 ]; then
        block="${head_part}$(fit_toc "$toc_budget")"$'\n\n'
      else
        block="${hdr}(${kb} KB — read ${libpath} before writing here; nothing of it fits inline: \`grep -n '^##' ${libpath}\`)"$'\n\n'
      fi
    fi
    ctx="${ctx}${block}"
  fi
  remaining=$(( BUDGET_BYTES - reserve - $(nbytes "$ctx") ))
fi

# Pattern fragments: each whole when it fits, else a pointer under the guides list.
frags=""; frag_pointers=""
i=0
while [ "$i" -lt "${#frag_paths[@]}" ]; do
  body="${frag_bodies[$i]}"; path="${frag_paths[$i]}"
  if [ $(( $(nbytes "$frags") + $(nbytes "$body") + 80 )) -le "$remaining" ]; then
    frags="${frags}${body}"$'\n\n'
  else
    frag_pointers="${frag_pointers}- ${path} — pattern fragment (did not fit inline; open it)"$'\n'
  fi
  i=$((i+1))
done
[ -n "$frags" ] && ctx="${ctx}── Patterns & shapes (${STANDARDS#$root/}) ──
${frags}"
guides="${frag_pointers}${guides}"
[ -n "$guides" ] && ctx="${ctx}── Deep guides — open if relevant (routed by applyTo) ──
${guides}"

jq -n --arg ctx "$ctx" '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "allow",
    additionalContext: $ctx
  }
}' 2>/dev/null

exit 0
