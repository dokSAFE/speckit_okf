# Changelog

## 0.2.0 — 2026-07-17
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

## 0.1.0 — 2026-07-17
* Initial release: `/speckit.okf.generate`, `/speckit.okf.update`, `/speckit.okf.validate`.
* Deterministic inventory script and OKF v0.1 conformance validator.
