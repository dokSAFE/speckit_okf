#!/usr/bin/env bash
# okf-inventory.sh — deterministic repository inventory for the OKF
# enrichment agent. Emits JSON to /tmp/okf-inventory.json and a short
# human-readable summary to stdout.
#
# The agent uses this as the factual substrate for concept planning so it
# doesn't have to guess the repo layout.

set -euo pipefail

OUT="${1:-/tmp/okf-inventory.json}"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

# --- helpers ---------------------------------------------------------------
json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

list_matching() {
  # $1 = regex on path; respects .gitignore via git ls-files when available
  if git rev-parse --git-dir >/dev/null 2>&1; then
    git ls-files | grep -E "$1" || true
  else
    find . -type f | sed 's|^\./||' \
      | grep -vE '^(node_modules|\.git|dist|build|vendor)/' \
      | grep -E "$1" || true
  fi
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

MANIFESTS="$(list_matching '(^|/)(package\.json|pyproject\.toml|setup\.py|requirements[^/]*\.txt|go\.mod|Cargo\.toml|pom\.xml|build\.gradle(\.kts)?|Gemfile|composer\.json|\.csproj)$')"
ENTRYPOINTS="$(list_matching '(^|/)(main|app|index|server|cli|manage|__main__)\.(py|js|ts|go|rs|rb|java|cs)$')"
API_DEFS="$(list_matching '\.(proto|avsc|graphql|gql)$|(^|/)(openapi|swagger)[^/]*\.(ya?ml|json)$')"
ROUTES="$(list_matching '(rout|controller|endpoint|handler|view|resource)s?[^/]*\.(py|js|ts|go|rb|java|cs|php)$' | head -100)"
DB_FILES="$(list_matching '(^|/)(migrations?|alembic|db/migrate)/|(model|schema|entit)[^/]*\.(py|js|ts|go|rb|java|cs|sql|prisma)$' | head -150)"
OPS_FILES="$(list_matching '(^|/)(Dockerfile[^/]*|docker-compose[^/]*\.ya?ml|Makefile|Procfile|[^/]*\.tf|helm/.*|k8s/.*\.ya?ml|\.github/workflows/.*\.ya?ml|\.gitlab-ci\.yml|Jenkinsfile|cloudbuild\.ya?ml)$')"
DOCS="$(list_matching '(^|/)(README[^/]*|CONTRIBUTING[^/]*|CHANGELOG[^/]*|ARCHITECTURE[^/]*|docs?/.*)\.(md|rst|txt)$' | head -100)"
CONFIGS="$(list_matching '(^|/)(config|settings|conf)[^/]*\.(py|js|ts|ya?ml|json|toml|ini|env\.example)$' | head -60)"

# Top-level directory sizes (proxy for module significance)
TOPDIRS="$(printf '%s\n' "$ALL_FILES" | sed '/^$/d' | awk -F/ 'NF>1 {print $1}' | sort | uniq -c | sort -rn | head -20 | awk '{printf "%s:%s\n", $2, $1}')"

# --- emit ------------------------------------------------------------------
python3 - "$OUT" <<PYEOF
import json, sys, os

def lines(s): return [l for l in s.splitlines() if l.strip()]

inv = {
  "root": os.getcwd(),
  "git": {"remote": """$REMOTE""", "branch": """$BRANCH""", "head": """$HEAD_SHA"""},
  "file_count": int("$FILE_COUNT" or 0),
  "language_histogram": dict(x.split(":") for x in lines("""$LANG_HIST""")),
  "top_level_dirs": dict(x.split(":") for x in lines("""$TOPDIRS""")),
  "dependency_manifests": lines("""$MANIFESTS"""),
  "entrypoints": lines("""$ENTRYPOINTS"""),
  "api_definitions": lines("""$API_DEFS"""),
  "route_like_files": lines("""$ROUTES"""),
  "data_layer_files": lines("""$DB_FILES"""),
  "ops_files": lines("""$OPS_FILES"""),
  "docs": lines("""$DOCS"""),
  "config_files": lines("""$CONFIGS"""),
}
with open(sys.argv[1], "w") as f:
    json.dump(inv, f, indent=2)

print(f"Inventory written to {sys.argv[1]}")
print(f"  files: {inv['file_count']}  head: {inv['git']['head']}  branch: {inv['git']['branch']}")
for k in ("dependency_manifests","entrypoints","api_definitions","route_like_files",
          "data_layer_files","ops_files","docs","config_files"):
    print(f"  {k}: {len(inv[k])}")
PYEOF
