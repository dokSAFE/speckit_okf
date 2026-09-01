# okf — OKF knowledge bundle plugin

Ships the [`okf-knowledge-bundle`](skills/okf-knowledge-bundle/SKILL.md) Agent
Skill: it analyzes a source-code repository and generates or maintains a
conformant [Open Knowledge Format (OKF v0.1)](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
knowledge bundle — cross-linked markdown concepts describing the repo's
services, modules, APIs, data models, and operations, with git history mined
for the *why* behind the code.

## Install

```
/plugin marketplace add alexcpn/speckit_okf
/plugin install okf@speckit-okf
```

Then just ask: *"generate an OKF knowledge bundle for this repo"*,
*"refresh the knowledge bundle"*, *"validate the OKF bundle"*.

## Four workflows

| Workflow | What it does |
| -------- | ------------ |
| generate | Inventory scan + git-history mining, concept plan, concept documents, `index.md` files, `log.md`, validation. |
| update | Diffs since the last logged commit; surgically refreshes stale concepts, deprecates orphans, adds new ones, preserves human curation. |
| clarify | Asks the user about the `open_questions` the other workflows parked rather than guessing, then folds the answers in as cited, curation-protected knowledge. |
| validate | OKF §9 conformance check plus a quality spot-check. |

The skill never guesses (uncertainty is parked as `open_questions`), never
deletes curation (removed code becomes `status: deprecated`), never emits
secret values, and never writes outside the bundle directory.

Full documentation: <https://github.com/alexcpn/speckit_okf>

MIT licensed.
