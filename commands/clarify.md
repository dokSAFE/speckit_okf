---
description: "Surface uncertainty OpenWiki parked in the OKF bundle, ask the user about it, and feed confirmed answers back via openwiki/INSTRUCTIONS.md"
scripts:
  sh: ../../scripts/bash/okf-preflight.sh
---

# /speckit.okf.clarify — Resolve parked uncertainty

**This command works differently from the original speckit_okf
`/speckit.okf.clarify`.** The original relied on an `open_questions`
frontmatter field the agent wrote by hand. OpenWiki has no equivalent
concept — it deliberately prefers to write only what it can verify from
source and cite as a Claim, rather than parking a question in frontmatter.
So instead of reading a structured field, this command **greps page bodies
for uncertainty language**, asks you about what it finds, and writes your
confirmed answers into `openwiki/INSTRUCTIONS.md` — the one file in the
bundle OpenWiki reads on every run but never overwrites — so the next
`/speckit.okf.update` incorporates them as grounding context.

User input (optional scope hints — e.g. a subdirectory of the bundle to
focus on):

$ARGUMENTS

## Phase 0 — Preflight

Run:

```bash
.specify/extensions/okf/scripts/bash/okf-preflight.sh --config .specify/extensions/okf/okf-config.yml
```

If it reports `PREFLIGHT: BLOCKED`, stop and show the user its output. If
`openwiki/` doesn't exist yet, tell the user to run `/speckit.okf.generate`
first and stop.

## Phase 1 — Find parked uncertainty

1. Load `okf.clarify.uncertainty_markers` and `okf.clarify.max_questions`
   from `.specify/extensions/okf/okf-config.yml` if present, else use the
   defaults in `okf-config.template.yml` (markers: "unclear", "not clear
   from", "unable to verify", "unverified", "TODO", "not documented",
   "unknown whether"; max_questions: 20).
2. Grep the bundle (respecting any $ARGUMENTS scope) for those markers,
   case-insensitively, across `openwiki/**/*.md` excluding `index.md` and
   `INSTRUCTIONS.md`:

   ```bash
   grep -rniE '(unclear|not clear from|unable to verify|unverified|TODO|not documented|unknown whether)' openwiki --include='*.md' | grep -v '/index.md:'
   ```

   (Substitute the actual configured marker list if it differs from the
   default shown above.)
3. For each hit, read enough surrounding context in that page to turn it
   into one concrete, answerable question — never an open-ended one. Group
   hits from the same page into a single question when they're about the
   same fact. Cap the list at `max_questions`; if there are more, ask about
   the highest-value ones (pages describing services/APIs/data models over
   peripheral ones) and tell the user how many were deferred to a later run.
4. If nothing is found, tell the user the bundle currently has no parked
   uncertainty worth asking about, and stop here.

## Phase 2 — Ask the user

Present the questions to the user (concrete, one fact at a time — e.g. "In
`services/checkout.md` it's unclear whether the 30s payment-provider timeout
is a hard SLA or a tunable default — which is it, and who owns that
decision?"). Wait for their answers. Do not guess or fabricate an answer on
their behalf; if they don't know either, say so and move on rather than
inventing something.

## Phase 3 — Record confirmed answers

For each answered question:

1. Open `openwiki/INSTRUCTIONS.md` (create it with a short header comment if
   it doesn't exist yet — OpenWiki reads this file but never writes it, so
   it's always safe for you to edit).
2. Append a dated entry under a `## Clarifications` section, in this form:

   ```markdown
   ## Clarifications

   - (2026-09-04) services/checkout.md — payment-provider timeout: hard SLA,
     30s, owned by the Payments team. Confirmed by Didier.
   ```

   Keep each entry to the confirmed fact plus enough pointer (page path) for
   OpenWiki to find and ground it next run. Do not editorialize or add
   anything the user did not actually confirm.
3. Do **not** edit the OKF pages themselves in this command — leave that to
   `/speckit.okf.update`, which will read the refreshed
   `openwiki/INSTRUCTIONS.md` and can then write the confirmed fact into the
   page as a properly evidenced Claim (citing the source that best supports
   it, or citing the instructions file itself if the fact is genuinely
   only known to a human).

## Phase 4 — Report

Tell the user how many questions were asked/answered/deferred, that the
answers are recorded in `openwiki/INSTRUCTIONS.md`, and that running
`/speckit.okf.update` next will fold them into the bundle.
