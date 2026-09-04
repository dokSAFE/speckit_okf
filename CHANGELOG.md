# Changelog

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
