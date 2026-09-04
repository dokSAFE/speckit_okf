#!/usr/bin/env bash
# okf-preflight.sh — checks that OpenWiki is ready to act as the OKF
# generation engine for this repository, before any speckit.okf.* command
# tries to drive it.
#
# Exit 0 and print "PREFLIGHT: OK" plus a few facts when everything needed is
# present. Exit 1 and print the missing pieces (with exact fix commands) when
# something is missing — the calling command should stop and show that
# output to the user rather than trying to work around it.
#
# Usage: okf-preflight.sh [--host <host>] [--config <okf-config.yml>]

set -euo pipefail

HOST="claude"
CONFIG=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST="${2:-claude}"; shift 2 ;;
    --config) CONFIG="${2:-}"; shift 2 ;;
    *) shift ;;
  esac
done

# Prefer host from config if given and --host wasn't explicitly overridden.
if [[ -n "$CONFIG" && -f "$CONFIG" ]]; then
  cfg_host="$(python3 -c "
import re,sys
try:
    text = open('$CONFIG', encoding='utf-8').read()
except OSError:
    sys.exit(0)
m = re.search(r'^\s*host:\s*[\"\']?([a-z]+)[\"\']?\s*\$', text, re.M)
if m:
    print(m.group(1))
" 2>/dev/null || true)"
  if [[ -n "${cfg_host:-}" ]]; then
    HOST="$cfg_host"
  fi
fi

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

MISSING=0
NOTES=()

# 1. openwiki CLI on PATH (Claude Code launches `openwiki mcp --host <host>`
#    as the MCP server process, so the binary must resolve even though this
#    script never calls it directly).
if ! command -v openwiki >/dev/null 2>&1; then
  MISSING=1
  NOTES+=("openwiki CLI not found on PATH. Install it with:  npm install -g openwiki  (Node.js >= 22 required)")
else
  OW_VERSION="$(openwiki --version 2>/dev/null || echo "unknown")"
  NOTES+=("openwiki CLI found: version ${OW_VERSION}")
fi

# 2. Host integration installed for this project or user.
#    Project scope: .mcp.json (Claude Code) with an "openwiki" server entry.
#    User scope:    ~/.claude.json with an "openwiki" server entry.
#    Either is sufficient.
PROJECT_MCP=".mcp.json"
USER_MCP="${HOME}/.claude.json"
INTEGRATION_FOUND=0

if [[ "$HOST" == "claude" ]]; then
  if [[ -f "$PROJECT_MCP" ]] && grep -q '"openwiki"' "$PROJECT_MCP" 2>/dev/null; then
    INTEGRATION_FOUND=1
    NOTES+=("OpenWiki MCP integration found in project .mcp.json")
  elif [[ -f "$USER_MCP" ]] && grep -q '"openwiki"' "$USER_MCP" 2>/dev/null; then
    INTEGRATION_FOUND=1
    NOTES+=("OpenWiki MCP integration found in user-level .claude.json")
  fi
  if [[ -d ".claude/skills/openwiki" ]] || [[ -d "${HOME}/.claude/skills/openwiki" ]]; then
    NOTES+=("OpenWiki skill installed (project or user scope)")
  fi
else
  NOTES+=("Host '$HOST' is not 'claude' — this preflight only checks the Claude Code integration; verify '$HOST' manually.")
  INTEGRATION_FOUND=1  # don't block on a host we can't check
fi

if [[ "$INTEGRATION_FOUND" -eq 0 ]]; then
  MISSING=1
  NOTES+=("OpenWiki is not registered as an MCP server for this host yet. Install it with:  openwiki integrations install ${HOST}   (then restart this coding agent so it picks up the new MCP server)")
fi

# 3. Git repository (OpenWiki's resumable run/Claims model assumes one).
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  MISSING=1
  NOTES+=("This directory is not a git repository. OpenWiki's code mode requires git.")
fi

echo "OKF/OpenWiki preflight for: $ROOT"
for n in "${NOTES[@]}"; do
  echo "  - $n"
done

if [[ "$MISSING" -eq 1 ]]; then
  echo
  echo "PREFLIGHT: BLOCKED — fix the item(s) above, then re-run this command."
  exit 1
fi

echo
echo "PREFLIGHT: OK"
exit 0
