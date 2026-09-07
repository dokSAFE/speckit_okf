#!/usr/bin/env bash
# sync-skill.sh — keep the Agent Skill's bundled copies of the shared assets
# in step with the canonical ones at the repo root.
#
# The Spec Kit extension consumes scripts/ and okf-config.template.yml from
# the repo root; the Agent Skill must be self-contained (it gets copied to
# ~/.claude/skills/ or installed as a plugin), so it carries its own copies.
# Root is canonical — edit there, then run this.
#
# Usage:
#   scripts/sync-skill.sh          # copy root -> skill
#   scripts/sync-skill.sh --check  # exit 1 if they differ (used by CI)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL="$ROOT/plugins/okf/skills/okf-knowledge-bundle"

ASSETS=(
  "scripts/bash/okf-inventory.sh"
  "scripts/bash/okf-history.sh"
  "scripts/python/okf-cochange.py"
  "scripts/python/validate_okf.py"
  "scripts/python/verify_okf.py"
)

CHECK=0
[[ "${1:-}" == "--check" ]] && CHECK=1

status=0
for rel in "${ASSETS[@]}"; do
  src="$ROOT/$rel"
  dst="$SKILL/$rel"
  if [[ $CHECK -eq 1 ]]; then
    if ! diff -u "$src" "$dst"; then
      echo "drift: $rel differs between repo root and the skill" >&2
      status=1
    fi
  else
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
  fi
done

# okf-config.template.yml lives at the root of both trees.
if [[ $CHECK -eq 1 ]]; then
  if ! diff -u "$ROOT/okf-config.template.yml" "$SKILL/okf-config.template.yml"; then
    echo "drift: okf-config.template.yml differs between repo root and the skill" >&2
    status=1
  fi
else
  cp "$ROOT/okf-config.template.yml" "$SKILL/okf-config.template.yml"
  chmod +x "$SKILL"/scripts/bash/*.sh
fi

if [[ $CHECK -eq 1 ]]; then
  if [[ $status -eq 0 ]]; then
    echo "skill assets are in sync"
  else
    echo "run scripts/sync-skill.sh to resync" >&2
  fi
  exit $status
fi

echo "synced skill assets into $SKILL"
