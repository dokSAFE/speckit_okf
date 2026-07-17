#!/usr/bin/env bash
# okf-inventory.sh — deterministic repository inventory for the OKF
# enrichment agent. Emits JSON (default: a per-repo temp path, printed to
# stdout) and a short human-readable summary to stdout.
#
# The agent uses this as the factual substrate for concept planning so it
# doesn't have to guess the repo layout.
#
# Usage: okf-inventory.sh [output_path] [--config <okf-config.yml>]

set -euo pipefail

OUT=""
CONFIG=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --config)
      CONFIG="${2:-}"
      shift 2
      ;;
    *)
      OUT="$1"
      shift
      ;;
  esac
done

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

OUT="${OUT:-${TMPDIR:-/tmp}/okf-inventory-$(basename "$ROOT")-$$.json}"
CAP="${OKF_INVENTORY_CAP:-150}"

# Default excludes, aligned with okf-config.template.yml's `exclude:` list.
DEFAULT_EXCLUDE='^(node_modules|\.git|dist|build|vendor|\.specify|specs)/|(^|/)[^/]*\.min\.js$'

# --- helpers ---------------------------------------------------------------

# Reads `okf.exclude` glob list from a config YAML (best-effort, no PyYAML
# dependency) and prints one alternation-ready regex fragment per line.
# Silent no-op (empty output) if $CONFIG is unset or unreadable.
config_exclude_regex() {
  if [[ -z "$CONFIG" || ! -f "$CONFIG" ]]; then
    return 0
  fi
  python3 - "$CONFIG" <<'PYEOF'
import re, sys

path = sys.argv[1]
try:
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
except OSError:
    sys.exit(0)

in_exclude = False
globs = []
for line in lines:
    stripped = line.strip()
    if re.match(r"^exclude\s*:\s*$", stripped):
        in_exclude = True
        continue
    if in_exclude:
        m = re.match(r"^-\s*[\"']?([^\"'#]+)[\"']?\s*(#.*)?$", stripped)
        if m:
            globs.append(m.group(1).strip())
            continue
        if stripped and not stripped.startswith("#"):
            # A non-list, non-comment line ends the exclude block.
            in_exclude = False

def glob_to_regex(g):
    # Minimal glob->regex: ** -> .*, * -> [^/]*, escape the rest.
    out = []
    i = 0
    while i < len(g):
        if g[i:i+2] == "**":
            out.append(".*")
            i += 2
        elif g[i] == "*":
            out.append("[^/]*")
            i += 1
        else:
            out.append(re.escape(g[i]))
            i += 1
    return "^" + "".join(out) + "$"

for g in globs:
    print(glob_to_regex(g))
PYEOF
}

EXCLUDE_FRAGMENTS="$(config_exclude_regex || true)"
if [[ -n "$EXCLUDE_FRAGMENTS" ]]; then
  CONFIG_EXCLUDE_RE="$(printf '%s\n' "$EXCLUDE_FRAGMENTS" | paste -sd '|' -)"
else
  CONFIG_EXCLUDE_RE=""
fi

list_matching() {
  # $1 = regex on path; respects .gitignore via git ls-files when available.
  # Always applies the default exclude list, plus config excludes if present.
  local raw
  if git rev-parse --git-dir >/dev/null 2>&1; then
    raw="$(git ls-files || true)"
  else
    raw="$(find . -type f | sed 's|^\./||' || true)"
  fi
  printf '%s\n' "$raw" \
    | grep -vE "$DEFAULT_EXCLUDE" \
    | { if [[ -n "$CONFIG_EXCLUDE_RE" ]]; then grep -vE "$CONFIG_EXCLUDE_RE"; else cat; fi; } \
    | grep -E "$1" || true
}

to_json_array() { python3 -c '
import json, sys
print(json.dumps([l for l in sys.stdin.read().splitlines() if l.strip()]))'; }

# --- collect ---------------------------------------------------------------
REMOTE="$(git remote get-url origin 2>/dev/null || echo "")"
BRANCH="$(git symbolic-ref --short HEAD 2>/dev/null || echo "main")"
HEAD_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo "")"

ALL_FILES="$(list_matching '.')"
FILE_COUNT="$(printf '%s\n' "$ALL_FILES" | sed '/^$/d' | wc -l | tr -d ' ')"

# Language histogram by extension (top 15)
LANG_HIST="$(printf '%s\n' "$ALL_FILES" | sed '/^$/d' \
  | awk -F. 'NF>1 {print $NF}' | sort | uniq -c | sort -rn | head -15 \
  | awk '{printf "%s:%s\n", $2, $1}')"

# Each category: raw match count vs capped count, so the caller can detect
# truncation. head -"$CAP" applied uniformly across every category.
raw_count() { list_matching "$1" | sed '/^$/d' | wc -l | tr -d ' '; }

MANIFESTS_RE='(^|/)(package\.json|pyproject\.toml|setup\.py|requirements[^/]*\.txt|go\.mod|Cargo\.toml|pom\.xml|build\.gradle(\.kts)?|Gemfile|composer\.json|\.csproj)$'
ENTRYPOINTS_RE='(^|/)(main|app|index|server|cli|manage|__main__)\.(py|js|ts|go|rs|rb|java|cs)$'
API_DEFS_RE='\.(proto|avsc|graphql|gql)$|(^|/)(openapi|swagger)[^/]*\.(ya?ml|json)$'
ROUTES_RE='(rout|controller|endpoint|handler|view|resource)s?[^/]*\.(py|js|ts|go|rb|java|cs|php)$'
DB_FILES_RE='(^|/)(migrations?|alembic|db/migrate)/|(model|schema|entit)[^/]*\.(py|js|ts|go|rb|java|cs|sql|prisma)$'
OPS_FILES_RE='(^|/)(Dockerfile[^/]*|docker-compose[^/]*\.ya?ml|Makefile|Procfile|[^/]*\.tf|helm/.*|k8s/.*\.ya?ml|\.github/workflows/.*\.ya?ml|\.gitlab-ci\.yml|Jenkinsfile|cloudbuild\.ya?ml)$'
DOCS_RE='(^|/)(README[^/]*|CONTRIBUTING[^/]*|CHANGELOG[^/]*|ARCHITECTURE[^/]*|docs?/.*)\.(md|rst|txt)$'
CONFIGS_RE='(^|/)(config|settings|conf)[^/]*\.(py|js|ts|ya?ml|json|toml|ini|env\.example)$'

MANIFESTS="$(list_matching "$MANIFESTS_RE" | head -"$CAP")"
ENTRYPOINTS="$(list_matching "$ENTRYPOINTS_RE" | head -"$CAP")"
API_DEFS="$(list_matching "$API_DEFS_RE" | head -"$CAP")"
ROUTES="$(list_matching "$ROUTES_RE" | head -"$CAP")"
DB_FILES="$(list_matching "$DB_FILES_RE" | head -"$CAP")"
OPS_FILES="$(list_matching "$OPS_FILES_RE" | head -"$CAP")"
DOCS="$(list_matching "$DOCS_RE" | head -"$CAP")"
CONFIGS="$(list_matching "$CONFIGS_RE" | head -"$CAP")"

MANIFESTS_RAW="$(raw_count "$MANIFESTS_RE")"
ENTRYPOINTS_RAW="$(raw_count "$ENTRYPOINTS_RE")"
API_DEFS_RAW="$(raw_count "$API_DEFS_RE")"
ROUTES_RAW="$(raw_count "$ROUTES_RE")"
DB_FILES_RAW="$(raw_count "$DB_FILES_RE")"
OPS_FILES_RAW="$(raw_count "$OPS_FILES_RE")"
DOCS_RAW="$(raw_count "$DOCS_RE")"
CONFIGS_RAW="$(raw_count "$CONFIGS_RE")"

# Top-level directory sizes (proxy for module significance)
TOPDIRS="$(printf '%s\n' "$ALL_FILES" | sed '/^$/d' | awk -F/ 'NF>1 {print $1}' | sort | uniq -c | sort -rn | head -20 | awk '{printf "%s:%s\n", $2, $1}')"

# --- emit ------------------------------------------------------------------
python3 - "$OUT" "$CAP" <<PYEOF
import json, sys, os

def lines(s): return [l for l in s.splitlines() if l.strip()]

cap = int(sys.argv[2])

def category(name_lines, raw_count):
    items = lines(name_lines)
    return {"items": items, "truncated": raw_count > len(items)}

categories = {
  "dependency_manifests": category("""$MANIFESTS""", int("$MANIFESTS_RAW" or 0)),
  "entrypoints": category("""$ENTRYPOINTS""", int("$ENTRYPOINTS_RAW" or 0)),
  "api_definitions": category("""$API_DEFS""", int("$API_DEFS_RAW" or 0)),
  "route_like_files": category("""$ROUTES""", int("$ROUTES_RAW" or 0)),
  "data_layer_files": category("""$DB_FILES""", int("$DB_FILES_RAW" or 0)),
  "ops_files": category("""$OPS_FILES""", int("$OPS_FILES_RAW" or 0)),
  "docs": category("""$DOCS""", int("$DOCS_RAW" or 0)),
  "config_files": category("""$CONFIGS""", int("$CONFIGS_RAW" or 0)),
}

inv = {
  "root": os.getcwd(),
  "git": {"remote": """$REMOTE""", "branch": """$BRANCH""", "head": """$HEAD_SHA"""},
  "file_count": int("$FILE_COUNT" or 0),
  "cap": cap,
  "language_histogram": dict(x.split(":") for x in lines("""$LANG_HIST""")),
  "top_level_dirs": dict(x.split(":") for x in lines("""$TOPDIRS""")),
  **{k: v["items"] for k, v in categories.items()},
  "truncated": {k: v["truncated"] for k, v in categories.items() if v["truncated"]},
}
with open(sys.argv[1], "w") as f:
    json.dump(inv, f, indent=2)

print(f"Inventory written to {sys.argv[1]}")
print(f"  files: {inv['file_count']}  head: {inv['git']['head']}  branch: {inv['git']['branch']}")
for k in ("dependency_manifests","entrypoints","api_definitions","route_like_files",
          "data_layer_files","ops_files","docs","config_files"):
    flag = " (truncated)" if k in inv["truncated"] else ""
    print(f"  {k}: {len(inv[k])}{flag}")
PYEOF
