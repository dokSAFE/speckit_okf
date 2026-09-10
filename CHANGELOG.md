# Changelog

## 1.1.2 — revert the `--host` example back to `junie`

1.1.1 (below) changed the suggested Junie MCP `args` from `--host junie` to
`--host claude`, reasoning that `junie` was an "unrecognized" value.
That reasoning didn't hold up on a closer look at OpenWiki's source:
`HostSessionManager` sets the producer-actor provenance metadata directly
from whatever `--host` string is passed — no lookup table, no restriction
to the `integrations install` registry (codex/claude/opencode/cursor), no
different behavior for an "unknown" value. There is no functional or
correctness reason to mislabel a Junie run as `claude`; `junie` is accepted
just as freely and is the accurate one. Reverted README,
`okf-config.template.yml`'s comment, and `okf-preflight.sh`'s fix-it message
back to suggesting `--host junie`. `okf.host` in `okf-config.yml` was never
affected by any of this — it only drives which MCP-config *file*
`okf-preflight.sh` checks, a separate concern from the `--host` value
inside that file.

## 1.1.1 — fix the Junie MCP `--host` example (superseded by 1.1.2 above)

The 1.1.0 README/config examples suggested registering OpenWiki's MCP server
under Junie with `args: ["mcp", "--host", "junie"]`. That's not what's
actually deployed: since OpenWiki has no real Junie awareness to key off of,
this deployment's `~/.junie/mcp/mcp.json` uses `--host claude` instead (a
recognized label; purely cosmetic provenance metadata either way — it does
not affect functionality or gate any behavior). Corrected in README,
`okf-config.template.yml`'s comment, and `okf-preflight.sh`'s fix-it message
(which now suggests `claude` when it has to tell a Junie user what to add).
`okf.host` in `okf-config.yml` is unaffected and stays `"junie"` — it drives
which MCP-config *file* okf-preflight.sh checks
(`.junie/mcp/mcp.json`/`~/.junie/mcp/mcp.json`), which is a separate concern
from the `--host` value inside that file.

## 1.1.0 — Junie (JetBrains) support

Added support for running this extension under Junie, not just Claude Code:

- `scripts/bash/okf-preflight.sh` now branches on `okf.host` (`claude` |
  `junie`) and checks the right MCP-config file for each: `.mcp.json` /
  `~/.claude.json` for Claude Code, `.junie/mcp/mcp.json` /
  `~/.junie/mcp/mcp.json` for Junie. Junie has no entry in OpenWiki's
  `integrations install` registry, so its fix-it message gives the exact
  JSON to add by hand instead of an install command.
- All four command files now reference each other via Spec Kit's
  `__SPECKIT_COMMAND_<NAME>__` placeholders instead of hardcoded
  `/speckit.okf.*` text, so the invocation Spec Kit tells the user to type
  is correct for either host (`/speckit.okf.update` under Claude's dotted
  convention, `/speckit-okf-update` under Junie's hyphenated one — Junie
  doesn't allow dots in slash-command names).
- `okf-config.template.yml`'s `host` default changed to `"junie"` for this
  deployment (was `"claude"`); switch it back if you run this under Claude
  Code instead.
- README gained a Junie-specific setup section (manual MCP registration,
  since there's no `openwiki integrations install junie`).

No change to the generation/update/clarify/validate logic itself — this is
purely making the same behavior reachable from a second host.

## 1.0.0 — fork from alexcpn/speckit_okf 0.5.0

Replaced the generation engine: `/speckit.okf.generate` and
`/speckit.okf.update` now orchestrate [OpenWiki](https://github.com/langchain-ai/openwiki)
via its Claude Code MCP integration (`openwiki_begin` / `openwiki_submit_plan`
/ `openwiki_next_page` / `openwiki_submit_page` / `openwiki_finish`) instead
of driving a hand-rolled bash inventory scan and a single-shot agent prompt.

Consequences of the swap:

- Bundle format moves from OKF v0.1 to OKF v0.2 (OpenWiki's own output
  format), written to the fixed `openwiki/` directory instead of the
  configurable `knowledge/` default.
- Frontmatter/provenance/index/Mermaid conformance is now enforced
  deterministically by OpenWiki's own finalizer on every run, not by a
  bundled Python validator alone.
- `scripts/bash/okf-inventory.sh` and `scripts/bash/okf-history.sh` were
  removed — OpenWiki's page-job research loop replaces both.
- `scripts/python/validate_okf.py` was replaced with
  `scripts/python/validate_okf_bundle.py`: an OKF v0.2–aware structural
  second opinion (no longer requires a `log.md` `Commit:` line, since
  OpenWiki tracks incremental state in `openwiki/.run.json` /
  `.last-update.json`, not a bundle log).
- `/speckit.okf.clarify` was redesigned: OpenWiki has no `open_questions`
  frontmatter field to collect from, so this command now greps page bodies
  for uncertainty language and records confirmed answers in
  `openwiki/INSTRUCTIONS.md` instead.
- No separate LLM provider API key is required for normal use (the Claude
  Code integration uses the calling agent's own model session).
- Added `scripts/bash/okf-preflight.sh` and a Phase 0 preflight step on every
  command, since the extension now depends on an external CLI + registered
  MCP server being present.
- Did not port the upstream `plugins/okf` Claude Code plugin/skill packaging
  layer (`.claude-plugin/`, `scripts/sync-skill.sh`) — out of scope for this
  fork; only the Spec Kit extension surface was rebuilt.
