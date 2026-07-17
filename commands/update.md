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
   `<bundle_dir>/log.md` and find the newest (first) `## YYYY-MM-DD`
   block; its `Commit: \`<sha>\`` line (the first line under the heading)
   is the last recorded state. If no bundle, no `log.md`, or no `Commit:`
   line exists, stop and tell the user to run `/speckit.okf.generate`
   first (or, if the log predates this convention, ask the user to
   confirm the last-known commit manually).

2. **No-op check.** Compare the recorded SHA to `git rev-parse HEAD`. If
   they match, stop here and report "bundle is already up to date with
   `<sha>` — nothing to do." Do not touch `log.md` or any concept file.

3. **Ancestor check.** Before diffing, confirm the recorded SHA is still
   reachable from HEAD:

   ```bash
   git merge-base --is-ancestor <last-sha> HEAD
   ```

   If this fails (non-zero exit), the branch's history was rewritten
   (rebase/squash/force-push) and a range diff against `<last-sha>` is
   meaningless. Warn the user that the last recorded commit is no longer
   part of this branch's history, then fall back to a **full re-scan**:
   run the inventory script (as in `/speckit.okf.generate` Phase 0) and
   treat every existing concept's `source_files` as needing a staleness
   re-check against current disk state, rather than relying on a commit
   range. Skip to step 5 using that broader work set. Otherwise, proceed
   to step 4.

4. **Diff.** Compute what changed:

   ```bash
   git diff --name-status <last-sha>..HEAD
   git log --oneline <last-sha>..HEAD
   ```

   `git diff --name-status` reports renames as `R<score>\t<old>\t<new>`.
   Handle these explicitly — do not treat a rename as delete+add.

5. **Map changes to concepts.** For every concept file in the bundle,
   read its `source_files` frontmatter list. Build four work sets:
   - **Renamed sources**: for each `R` status line, any concept whose
     `source_files` contains the *old* path. Update that entry's
     `source_files` to the *new* path and classify the concept as
     **stale** (re-check facts) — never orphan or duplicate it.
   - **Stale concepts**: any concept whose `source_files` intersect the
     changed (`M`) paths, or the new paths from a rename already handled
     above.
   - **Orphaned concepts**: concepts ALL of whose `source_files` were
     deleted (`D`) and not accounted for by a rename.
   - **Uncovered changes**: changed/added (`A`) paths not claimed by any
     concept's `source_files` — candidates for new concepts (apply the
     same significance rules as generate; don't create a concept for a
     trivial change).

6. **Update surgically.**
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

7. **Maintain reserved files.**
   - Update affected `index.md` entries (add new, mark deprecated).
   - Prepend a dated entry to `log.md`, newest first (OKF §7), with the
     required `Commit:` line as the first line under the heading, using
     the `**Update**` / `**Creation**` / `**Deprecation**` conventions:

     ```markdown
     ## <YYYY-MM-DD>
     Commit: `<new-head-sha>`
     * **Update**: Refreshed [Checkout Service](/services/checkout.md) for payment-provider change (commit `<sha>`).
     * **Creation**: Added [Refunds API](/apis/refunds.md).
     ```

8. **Validate and report.** Run

   ```bash
   python3 .specify/extensions/okf/scripts/python/validate_okf.py <bundle_dir> --config .specify/extensions/okf/okf-config.yml
   ```

   fix ERRORs, then summarize: N updated, N created, N deprecated,
   validation status.

## Hard rules

- Preserve unknown frontmatter keys on round-trip (OKF §4.1).
- Never delete concept files or human-authored prose.
- Never modify source code; writes stay inside `bundle_dir`.
- No secrets/credentials in any output.
