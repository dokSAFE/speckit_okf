---
description: "Check OKF structural conformance of the OpenWiki-generated bundle and report OpenWiki setup/run status"
scripts:
  sh: ../../scripts/bash/okf-preflight.sh
---

# /speckit.okf.validate — Conformance check

OpenWiki's own finalizer already enforces OKF v0.2 frontmatter conformance,
index synchronization, and Mermaid validity **deterministically** as part of
every `openwiki_finish` — it is the authoritative validator, and it runs
whether or not you invoke this command. This command is a convenience
second opinion: it re-checks the bundle structurally (useful after an
interrupted run, a manual edit, or before committing), and reports whether
OpenWiki/its Claude Code integration are even set up correctly.

User input (optional: a subdirectory of the bundle to scope the check to):

$ARGUMENTS

## Phase 0 — Preflight

Run:

```bash
.specify/extensions/okf/scripts/bash/okf-preflight.sh --config .specify/extensions/okf/okf-config.yml
```

Report its output to the user regardless of pass/fail (unlike generate/update,
don't hard-stop here — validation of an existing bundle is still useful even
if, say, the MCP integration got unregistered since the bundle was last
generated).

## Phase 1 — Structural check

If `openwiki/` (or the bundle dir from
`.specify/extensions/okf/okf-config.yml`) doesn't exist, tell the user to run
`/speckit.okf.generate` first and stop.

Run:

```bash
python3 .specify/extensions/okf/scripts/python/validate_okf_bundle.py openwiki ${ARGUMENTS:+--scope "$ARGUMENTS"}
```

This checks, per file: parseable YAML frontmatter with a non-empty `type`;
recommended `title`/`description` present; no obviously secret-looking
strings; internal links resolve; every directory with concept files has an
`index.md`; no two concepts share the same `type`+`title`; and, when present,
that `generated`/`verified`/`sources`/`status`/`stale_after` have roughly the
right shape (this is advisory only — OpenWiki's own frontmatter validator in
`src/okf/frontmatter.ts` is authoritative, this script does not replicate its
exact YAML-schema rules).

**What this script deliberately does not do:** determine whether a Claim's
cited evidence is stale (that requires OpenWiki's internal evidence-hash
comparison, which is not something to reimplement here) — trust
`openwiki_inspect_page_claims` / a fresh `/speckit.okf.update` run for that.

## Phase 2 — Report

Summarize: page count, error count (frontmatter unparseable / missing `type`
/ malformed reserved files), warning count and the categories they fall into,
and overall CONFORMANT / NON-CONFORMANT result. If there are errors, list
them and suggest fixes (usually: re-run `/speckit.okf.update` and let
OpenWiki repair the page, since `migrateWikiToOkf` normalizes non-conformant
frontmatter automatically on its next run). If everything is clean, say so
plainly.
