---
description: "Validate the OKF knowledge bundle against the OKF v0.1 conformance rules and report issues"
---

# /speckit.okf.validate — Conformance check

Run the OKF conformance checker against the bundle and interpret the
results for the user.

User input (optional path override):

$ARGUMENTS

## Steps

1. Determine `bundle_dir` from `$ARGUMENTS`, else from
   `.specify/extensions/okf/okf-config.yml`, else default `knowledge/`.
2. Run:

   ```bash
   python3 .specify/extensions/okf/scripts/python/validate_okf.py <bundle_dir>
   ```

3. Interpret the output using OKF §9 semantics:
   - **ERRORs** make the bundle non-conformant (unparseable frontmatter,
     missing/empty `type`, malformed `index.md`/`log.md`). Offer to fix
     them, and fix on confirmation.
   - **WARNINGs** are soft guidance a consumer must tolerate (broken
     cross-links, missing `title`/`description`, missing indexes). Report
     them grouped by kind; broken links may legitimately represent
     not-yet-written knowledge.
4. Additionally spot-check quality beyond mechanical conformance: flag
   concepts with empty bodies, indexes whose entries lack descriptions,
   stale `timestamp`s older than the last log entry, and any file content
   that looks like a credential or secret (report immediately if found).
5. Summarize with a conformant / non-conformant verdict and a short
   prioritized fix list.
