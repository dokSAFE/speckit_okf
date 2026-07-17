---
description: "Incrementally update the OKF knowledge bundle from changes in git history since the last run"
---

# /speckit.okf.update — Incremental bundle refresh

You are acting as an **OKF enrichment agent** performing an incremental
update. Never rewrite the whole bundle — the bundle contains human
curation you must preserve.

User input (optional scope hints):

$ARGUMENTS

## Steps

1. **Locate state.** Read `bundle_dir` from
   `.specify/extensions/okf/okf-config.yml` (default `knowledge/`). Read
   `<bundle_dir>/log.md` and extract the most recent commit SHA recorded
   in an entry. If no bundle or no SHA exists, stop and tell the user to
   run `/speckit.okf.generate` first.

2. **Diff.** Compute what changed:

   ```bash
   git diff --name-status <last-sha>..HEAD
   git log --oneline <last-sha>..HEAD
   ```

3. **Map changes to concepts.** For every concept file in the bundle,
   read its `source_files` frontmatter list. Build three work sets:
   - **Stale concepts**: any concept whose `source_files` intersect the
     changed/deleted paths.
   - **Orphaned concepts**: concepts ALL of whose `source_files` were
     deleted.
   - **Uncovered changes**: changed/added paths not claimed by any
     concept's `source_files` — candidates for new concepts (apply the
     same significance rules as generate; don't create a concept for a
     trivial change).

4. **Update surgically.**
   - For stale concepts: re-read the current source, then edit ONLY the
     sections whose facts changed (schema tables, interface lists,
     dependency links). Preserve prose, tips, and any content not
     traceable to `source_files` — that is human curation. Update
     `timestamp` and `source_files` frontmatter.
   - For orphaned concepts: do not delete. Add `status: deprecated` to
     frontmatter, prepend a one-line deprecation note to the body, and
     keep inbound links working.
   - For uncovered changes: create new concept files per the generate
     command's frontmatter/body rules, and add them to the relevant
     `index.md` files.

5. **Maintain reserved files.**
   - Update affected `index.md` entries (add new, mark deprecated).
   - Prepend a dated entry to `log.md`, newest first (OKF §7), using the
     `**Update**` / `**Creation**` / `**Deprecation**` conventions, and
     record the new HEAD SHA:

     ```markdown
     ## <YYYY-MM-DD>
     * **Update**: Refreshed [Checkout Service](/services/checkout.md) for payment-provider change (commit `<sha>`).
     * **Creation**: Added [Refunds API](/apis/refunds.md).
     ```

6. **Validate and report.** Run
   `python3 .specify/extensions/okf/scripts/python/validate_okf.py <bundle_dir>`,
   fix ERRORs, then summarize: N updated, N created, N deprecated,
   validation status.

## Hard rules

- Preserve unknown frontmatter keys on round-trip (OKF §4.1).
- Never delete concept files or human-authored prose.
- Never modify source code; writes stay inside `bundle_dir`.
- No secrets/credentials in any output.
