# speckit-okf — OKF Knowledge Bundle Generator for Spec Kit

A [Spec Kit](https://github.com/github/spec-kit) extension that turns your AI coding agent into an **OKF enrichment agent**: it analyzes a source-code repository and generates a conformant [Open Knowledge Format (OKF v0.1)](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) knowledge bundle — a directory of cross-linked markdown concepts with YAML frontmatter describing your services, modules, APIs, data models, and operations.

Because OKF bundles are plain markdown in git, the generated bundle is readable by humans, diffable in PRs, and consumable by other agents without any bespoke tooling.

## Commands

| Command | What it does |
| ------- | ------------ |
| `/speckit.okf.generate` | Bootstrap a full bundle from the repo: inventory scan, concept plan, concept documents, `index.md` files, `log.md`, validation. |
| `/speckit.okf.update` | Incremental refresh: diffs git history since the last logged commit, surgically updates only stale concepts, deprecates orphans, creates concepts for new code, preserves human curation. |
| `/speckit.okf.validate` | Runs the OKF §9 conformance checker and a quality spot-check; reports ERRORs/WARNINGs with fixes. |

## Install

```bash
# From a spec-kit project (after `specify init`):
specify extension add --dev /path/to/speckit-okf
# or, once published to a catalog:
specify extension add okf
```

Then launch your coding agent (Claude Code, Copilot, etc.) in the project and run `/speckit.okf.generate`.

## Configuration

Copy `okf-config.template.yml` to `.specify/extensions/okf/okf-config.yml` to control the bundle directory (default `knowledge/`), resource URI base, excludes, type mappings, layout, and granularity (`coarse` / `medium` / `fine`). Defaults work without any config.

## How it works

1. `scripts/bash/okf-inventory.sh` deterministically scans the repo (entry points, dependency manifests, API definitions, migrations/models, CI/CD, docs) into JSON — so the agent plans from facts, not guesses.
2. The command prompt instructs the agent to draft a concept plan, then write OKF-conformant documents: required `type` frontmatter, recommended `title`/`description`/`resource`/`tags`/`timestamp`, a producer extension field `source_files` that maps each concept back to code (this is what makes incremental updates possible), bundle-relative cross-links, `index.md` progressive-disclosure files, and an ISO-dated `log.md`.
3. `scripts/python/validate_okf.py` enforces OKF §9: parseable frontmatter everywhere, non-empty `type`, reserved-file structure — and warns on broken links, missing indexes, empty bodies, and secret-looking strings.

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
- Secrets found in configs are described by shape, never by value; the validator flags anything that slips through.
- OKF's permissive consumption model (unknown types OK, broken links OK) is relied on deliberately — generation is safe to run early and often.

## License

MIT
