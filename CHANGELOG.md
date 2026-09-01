# Changelog

## [0.4.0](https://github.com/alexcpn/speckit_okf/releases/tag/v0.4.0) — 2026-09-01
* **Packaged as an Agent Skill.** The four workflows are now also available as
  a portable `SKILL.md` skill at
  `plugins/okf/skills/okf-knowledge-bundle/`, usable by Claude Code, Claude.ai,
  the Claude Agent SDK, and any agent that reads the Agent Skills format —
  invoked in plain language instead of by slash command. `SKILL.md` is a small
  router (config/path resolution, script reference, and the rules that hold
  across every workflow); the workflow detail lives in `references/{generate,
  update,clarify,validate}.md` and is loaded only when that workflow runs.
* **Installable as a Claude Code plugin.** Added `.claude-plugin/marketplace.json`
  and `plugins/okf/.claude-plugin/plugin.json`, so
  `/plugin marketplace add alexcpn/speckit_okf` + `/plugin install okf@speckit-okf`
  installs the skill. The plugin deliberately contains only the skill — the
  Spec Kit `commands/` at the repo root hardcode `.specify/` paths and would
  not work outside a Spec Kit project.
* The skill is self-contained: it carries its own copies of the three scripts
  and the config template so the directory works wherever it is copied. The
  repo-root copies stay canonical; **`scripts/sync-skill.sh`** resyncs them and
  `scripts/sync-skill.sh --check` fails CI on drift.
* **New `scripts/python/validate_skill.py`** — lints a skill directory's
  `SKILL.md` frontmatter (name shape and directory match, description length,
  unknown keys, body size) and verifies every skill-relative path it references
  exists. Wired into a new `Skill` workflow alongside the sync and
  manifest-JSON checks; ShellCheck now scans all of `scripts/`.
* The skill also reads `.okf-config.yml` from the repo root, so it can be
  configured without a `.specify/` directory.
* Fixed: the generate workflow's Phase 0 steps were numbered `1,2,5,3,4`, and
  the "bundle already exists" guard ran *after* the inventory scan. The guard
  is now step 2, before any scanning.
* Fixed: every `speckit_ofk` URL (a typo for `speckit_okf`) in the README,
  `SECURITY.md`, `extension.yml`, and CHANGELOG.
* `generated_by` bumped to `speckit-okf/0.4.0`.

## [0.3.0](https://github.com/alexcpn/speckit_okf/releases/tag/v0.3.0) — 2026-07-20
* **Git history as a first-class signal.** `okf-inventory.sh` now emits a
  `git.history` object: `churn` (per-file commit counts over the last
  `OKF_HISTORY_COMMITS` non-merge commits, capped at `OKF_CHURN_TOP`) as a
  significance signal, plus `recent_commits`. Added an `adr_docs` category
  (ADR/RFC/decision files) for seeding Design Decision concepts. All scans
  are bounded and skip cleanly on non-git repos.
* **New `okf-history.sh` script** — bounded, per-path git history for the
  agent to mine the "why" of a concept: creation commit, commit count,
  recent subjects, and revert/hotfix/risk-flagged commits (deadlock, race,
  regression, security). Diff-free by default (`--patch` opt-in) to avoid
  leaking secrets from history; `--json` and `--limit` supported.
* **New `/speckit.okf.clarify` command.** Generate/update now *park*
  uncertainty in an `open_questions` frontmatter list instead of guessing;
  clarify collects those, asks the user in prioritized batches (capped by
  `clarify.max_questions`, default 20), and folds answers back into concept
  bodies marked with `<!-- clarified: ... -->` sentinels. `/speckit.okf.update`
  preserves those sentinels as human curation and never overwrites them.
* `/speckit.okf.generate`: uses churn for Phase 1 significance, runs
  `okf-history.sh` per concept for the "why", and emits `open_questions`
  where code + history are inconclusive. `generated_by` bumped to
  `speckit-okf/0.3.0`.
* `validate_okf.py`: added **W8** (concept has unresolved `open_questions`).
* `validate.md`/`README`/`extension.yml`/config template updated for the new
  command, script, and config knob.

## [0.2.0](https://github.com/alexcpn/speckit_okf/releases/tag/v0.2.0) — 2026-07-17
* `okf-config.yml`'s `exclude` list is now actually honored by both
  `okf-inventory.sh` and `validate_okf.py` (via `--config`/`--exclude`),
  not just interpreted as prompt guidance. Fallback exclude defaults in
  the inventory script's non-git branch now match the config template.
* `validate_okf.py`: added `argparse` (`--config`, `--exclude`,
  `--repo-root`, `--json`, `--help`), graceful error handling instead of
  crashing on unreadable files, and three new checks — **W6** (dangling
  `source_files` entries), **W7** (possible duplicate concept by
  type+title), **E4** (missing/malformed `Commit:` line in `log.md`).
  Extended the W5 secret heuristic to catch unquoted values, AWS-style
  access keys, and PEM private-key blocks. Warns (W0) when PyYAML isn't
  installed and the lenient fallback parser is in use.
* **Breaking (bundle format):** `log.md` date blocks now require a
  `Commit: \`<sha>\`` line as the first line under the heading — this is
  what `/speckit.okf.update` reads to resume incrementally, replacing
  free-form SHA parsing from prose. Bundles generated before 0.2.0 will
  need this line added manually (or regenerated) before `/speckit.okf.update`
  or `/speckit.okf.validate` will treat them as conformant.
* `okf-inventory.sh`: removed dead `json_escape()` helper, applied a
  consistent cap (`OKF_INVENTORY_CAP`, default 150) across all inventory
  categories with a `truncated` flag per category, and switched the
  default output path from the fixed `/tmp/okf-inventory.json` to a
  per-repo, per-PID path to avoid collisions between concurrent runs.
* `/speckit.okf.update`: added an explicit no-op check (stops cleanly if
  `HEAD` already matches the logged commit), explicit handling of renamed
  source files (updates `source_files` in place instead of
  orphaning+duplicating), and a fallback full re-scan when the logged
  commit is no longer reachable (rebase/squash/force-push).
* `/speckit.okf.generate`: the "bundle already exists" guard now checks
  for any `.md` file in `bundle_dir`, not just `log.md`, so hand-seeded
  or partial bundles aren't clobbered.
* `/speckit.okf.validate`: no longer re-derives W4/W5 in prose (relies on
  the validator's own output); the "stale timestamp" spot-check now has a
  concrete algorithm (compare `timestamp` against each `source_files`
  entry's last commit time).

## [0.1.0](https://github.com/alexcpn/speckit_okf/releases/tag/v0.1.0) — 2026-07-17
* Initial release: `/speckit.okf.generate`, `/speckit.okf.update`, `/speckit.okf.validate`.
* Deterministic inventory script and OKF v0.1 conformance validator.
