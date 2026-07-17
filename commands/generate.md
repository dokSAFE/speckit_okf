---
description: "Generate an Open Knowledge Format (OKF v0.1) knowledge bundle from this repository's source code"
---

# /speckit.okf.generate — Bootstrap an OKF knowledge bundle

You are acting as an **OKF enrichment agent**. Your job is to analyze this
repository and produce a conformant **Open Knowledge Format (OKF v0.1)**
knowledge bundle: a directory of markdown files with YAML frontmatter that
captures the metadata, context, and curated insight surrounding this codebase.

Spec: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md

User input (optional focus/scope hints):

$ARGUMENTS

## Phase 0 — Configuration and inventory

1. Load configuration from `.specify/extensions/okf/okf-config.yml` if it
   exists; otherwise use the defaults in `okf-config.template.yml`
   (bundle_dir=`knowledge/`, granularity=`medium`).
2. Run the inventory script, passing the config path if it exists, and
   read the path it prints (do not assume a fixed location — the script
   picks a per-run temp file to avoid collisions with concurrent runs):

   ```bash
   .specify/extensions/okf/scripts/bash/okf-inventory.sh --config .specify/extensions/okf/okf-config.yml
   ```

   The script prints `Inventory written to <path>` — read the JSON from
   that path. It contains the file tree, languages, entry points,
   dependency manifests, schema/migration files, API definition files,
   CI/CD configs, and existing docs, honoring the config's `exclude` list.
   Each category also carries a `truncated` flag (see the top-level
   `truncated` object) — if a category you need was truncated, either
   widen `--exclude` in config or ask the user before concluding you've
   seen the full picture for that category.
3. Determine `resource_base`: from config, else from
   `git remote get-url origin` + default branch (convert SSH form to an
   `https://.../blob/<branch>/{path}` form). If the repo has no remote,
   omit `resource:` fields entirely rather than inventing URIs.
4. If `bundle_dir` already exists and contains one or more `.md` files
   (whether or not `log.md` is present — a hand-seeded or partial bundle
   is still real curation), STOP and tell the user to run
   `/speckit.okf.update` instead (regenerating from scratch would destroy
   curation). Only proceed if the user explicitly asked for a full
   rebuild in $ARGUMENTS. If `bundle_dir` doesn't exist or is empty,
   proceed.

## Phase 1 — Concept planning (do this BEFORE writing files)

Read the inventory plus key files (READMEs, entry points, route
definitions, schema files, docker/CI configs) and draft a **concept plan**:
a table of `concept_id | type | title | one-line description | source files`.

Selection rules by granularity (default: medium):

- Always: one `architecture/overview.md` concept (type: `Reference`)
  describing the system's purpose, high-level structure, and how the
  pieces fit together — with links to every other top-level concept.
- One concept per **deployable unit / service / app** (type: `Service`).
- One concept per **significant module or package** — significant means it
  has a coherent responsibility a new engineer would need explained, not
  merely that a directory exists (type: `Module`).
- One concept per **API surface**: group endpoints by resource or router
  file, not one file per endpoint unless granularity=fine
  (type: `API Endpoint` or `API Resource`).
- One concept per **data model / database table / event schema** found in
  migrations, ORM models, .proto/.avsc/OpenAPI schemas (type:
  `Data Model` / `Database Table`).
- One concept per **operational artifact** worth explaining: CI pipeline,
  deployment config, cron/scheduled jobs (type: `Pipeline`,
  `Configuration`).
- Optionally: `operations/` playbooks if the repo contains runbook-like
  docs; mirror external references into `references/` when the code links
  to essential external documents.

Present this plan to the user briefly (the table), then proceed — do not
wait for approval unless the plan exceeds ~40 concepts, in which case ask
whether to coarsen granularity.

## Phase 2 — Write the bundle

Create the bundle under `bundle_dir` following OKF §3–§8 exactly:

### Frontmatter (every concept file)

```yaml
---
type: <Type>                      # REQUIRED, non-empty
title: <Human-readable name>
description: <ONE sentence, used in indexes and previews>
resource: <resource_base with the primary source file path>   # omit for abstract concepts
tags: [<lowercase-tag>, ...]
timestamp: <ISO 8601, use the file's last git commit time: git log -1 --format=%cI -- <path>>
source_files:                     # extension field: repo-relative paths this concept derives from
  - path/to/file.py
---
```

`source_files` is a producer extension field (permitted by OKF §4.1) — it
is what makes incremental updates possible. Always include it, and also
include `generated_by: speckit-okf/0.2.0`.

### Body conventions

- Favor **structural markdown** (headings, tables, fenced code) over prose.
- Use conventional headings where applicable: `# Schema` for
  columns/fields of data concepts, `# Examples` for usage snippets,
  `# Citations` for external sources (numbered, per OKF §8).
- For services/modules also use: `# Responsibilities`, `# Interfaces`
  (public functions/endpoints table), `# Dependencies` (internal links +
  external packages), `# Key files`.
- **Cross-link aggressively** using bundle-relative links beginning with
  `/` (OKF §5.1), e.g. `[orders model](/data/orders.md)`. Express the
  relationship in the surrounding prose ("joins with", "depends on",
  "publishes to"). Links to concepts you haven't written are allowed —
  broken links legitimately represent not-yet-written knowledge (§5.3).
- Write what a **staff engineer would tell a new teammate**, not a
  file-by-file paraphrase: purpose, invariants, gotchas, why it is shaped
  the way it is (cite commit messages or ADRs when they explain a
  decision).
- Do NOT copy large source excerpts. Short illustrative snippets only.
- Do NOT include secrets, tokens, credentials, or internal hostnames
  found in the code. If a config file contains secrets, describe its
  shape, never its values.

### Index files (OKF §6)

- Write `index.md` in the bundle root and in every subdirectory.
- No frontmatter, EXCEPT the bundle root `index.md`, which carries exactly:

  ```yaml
  ---
  okf_version: "0.1"
  ---
  ```

- Body = sections of bulleted links, each entry reusing the concept's
  `description` frontmatter:

  ```markdown
  # Services

  * [Checkout Service](services/checkout.md) - Handles cart-to-order conversion and payment orchestration.

  # Data

  * [data/](data/) - Database tables and event schemas.
  ```

### Log file (OKF §7)

Create `log.md` at the bundle root:

```markdown
# Knowledge Bundle Update Log

## <YYYY-MM-DD>
Commit: `<short-sha>`
* **Initialization**: Generated bundle from commit `<short-sha>` with speckit-okf. <N> concepts across <dirs>.
```

The `Commit:` line is REQUIRED and machine-checked (validator rule E4) —
it is what `/speckit.okf.update` reads to resume incrementally. Always
write it as the first line under the date heading, exactly in that
backtick-quoted form.

## Phase 3 — Validate and report

1. Run the conformance checker:

   ```bash
   python3 .specify/extensions/okf/scripts/python/validate_okf.py <bundle_dir> --config .specify/extensions/okf/okf-config.yml
   ```

2. Fix any ERRORs (unparseable frontmatter, missing/empty `type`,
   malformed reserved files). WARNINGs (broken links, missing optional
   fields) are acceptable but list them.
3. Report to the user: concept count by type, bundle tree, validation
   result, and suggested next steps (review `architecture/overview.md`
   first; run `/speckit.okf.update` after future code changes).

## Hard rules

- Only `type` is required in frontmatter, but always provide `title` and
  `description` — indexes are useless without them.
- Reserved filenames `index.md` and `log.md` must never be used for
  concepts (§3.1).
- Concept IDs are file paths minus `.md`; use lowercase, hyphenated
  filenames.
- Never fabricate facts about the code. If behavior is unclear from the
  source, say so in the concept ("unverified — inferred from X") rather
  than guessing.
- All writes stay inside `bundle_dir`. Never modify source code.
