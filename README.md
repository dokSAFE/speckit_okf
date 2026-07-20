# speckit-okf — OKF Knowledge Bundle Generator for Spec Kit

[![CodeQL](https://github.com/alexcpn/speckit_ofk/actions/workflows/codeql.yml/badge.svg)](https://github.com/alexcpn/speckit_ofk/actions/workflows/codeql.yml)
[![ShellCheck](https://github.com/alexcpn/speckit_ofk/actions/workflows/shellcheck.yml/badge.svg)](https://github.com/alexcpn/speckit_ofk/actions/workflows/shellcheck.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A [Spec Kit](https://github.com/github/spec-kit) extension that turns your AI coding agent into an **OKF enrichment agent**: it analyzes a source-code repository and generates a conformant [Open Knowledge Format (OKF v0.1)](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) knowledge bundle — a directory of cross-linked markdown concepts with YAML frontmatter describing your services, modules, APIs, data models, and operations.

Because OKF bundles are plain markdown in git, the generated bundle is readable by humans, diffable in PRs, and consumable by other agents without any bespoke tooling.

## Commands

| Command | What it does |
| ------- | ------------ |
| `/speckit.okf.generate` | Bootstrap a full bundle from the repo: inventory scan, git-history mining (churn + rationale), concept plan, concept documents, `index.md` files, `log.md`, validation. |
| `/speckit.okf.update` | Incremental refresh: diffs git history since the last logged commit, surgically updates only stale concepts, deprecates orphans, creates concepts for new code, preserves human curation. |
| `/speckit.okf.clarify` | Resolves the `open_questions` that generate/update parked (instead of guessing) by asking the user, then folds the answers back into concepts as cited, curation-protected knowledge. |
| `/speckit.okf.validate` | Runs the OKF §9 conformance checker and a quality spot-check; reports ERRORs/WARNINGs with fixes. |

## Install

```bash
# Option 1: install from a released archive (no catalog needed)
specify extension add okf --from https://github.com/alexcpn/speckit_ofk/archive/refs/tags/v0.3.0.zip

# Option 2: install from a local clone (dev mode)
git clone https://github.com/alexcpn/speckit_ofk.git
specify extension add --dev speckit_ofk/

# Option 3: once listed in the community catalog
specify extension add okf
```

## Usage

From your coding agent (Claude Code, Copilot, etc.) in the project:

```bash
# 1. Generate the initial knowledge bundle
/speckit.okf.generate

# 2. Resolve anything the agent couldn't infer from code + git history
/speckit.okf.clarify

# 3. After making code changes, refresh incrementally
/speckit.okf.update

# 4. Validate conformance before committing
/speckit.okf.validate
```

Output lands in `knowledge/` (configurable) as a set of cross-linked markdown concept files ready to commit alongside your code.

## Configuration

Copy `okf-config.template.yml` to `.specify/extensions/okf/okf-config.yml` to control the bundle directory (default `knowledge/`), resource URI base, excludes, type mappings, layout, and granularity (`coarse` / `medium` / `fine`). Defaults work without any config.

## How it works

1. `scripts/bash/okf-inventory.sh` deterministically scans the repo (entry points, dependency manifests, API definitions, migrations/models, CI/CD, docs, ADRs) into JSON — including **git-history signals** (`churn` = per-file commit counts for significance, `recent_commits`) — so the agent plans from facts, not guesses.
2. `scripts/bash/okf-history.sh <path>` gives the agent bounded, per-concept git history — creation commit, recent subjects, and revert/hotfix/risk-flagged commits — so concepts capture the **"why"** (invariants, gotchas) with commit citations, not just the "what".
3. The command prompt instructs the agent to draft a concept plan, then write OKF-conformant documents: required `type` frontmatter, recommended `title`/`description`/`resource`/`tags`/`timestamp`, producer extension fields `source_files` (maps each concept back to code — what makes incremental updates possible) and `open_questions` (parks uncertainty for `/speckit.okf.clarify` instead of guessing), bundle-relative cross-links, `index.md` progressive-disclosure files, and an ISO-dated `log.md`.
4. `scripts/python/validate_okf.py` enforces OKF §9: parseable frontmatter everywhere, non-empty `type`, reserved-file structure — and warns on broken links, missing indexes, empty bodies, secret-looking strings, dangling `source_files`, duplicate concepts, and unresolved `open_questions`.

## Generated bundle shape (example)

```
knowledge/
├── index.md            # okf_version: "0.1" + directory of everything
├── log.md              # dated history, records source commit SHA
├── architecture/
│   ├── index.md
│   └── overview.md     # type: Reference — the "start here" concept
├── services/…          # type: Service
├── modules/…           # type: Module
├── apis/…              # type: API Endpoint / API Resource
├── data/…              # type: Data Model / Database Table
└── operations/…        # type: Pipeline / Configuration / Playbook
```

## Notes

- The updater never deletes concepts or human-written prose; removed code yields `status: deprecated`, not deletion.
- The agent parks what it can't verify in `open_questions` rather than guessing; `/speckit.okf.clarify` turns those into human-confirmed, curation-protected facts (marked with `<!-- clarified -->` sentinels the updater won't overwrite).
- Secrets found in configs — or surfaced by git-history mining — are described by shape, never by value; the validator flags anything that slips through.
- OKF's permissive consumption model (unknown types OK, broken links OK) is relied on deliberately — generation is safe to run early and often.
- Both scripts are checked on every push via CodeQL and ShellCheck; see [SECURITY.md](SECURITY.md) to report a vulnerability.

## License

MIT
