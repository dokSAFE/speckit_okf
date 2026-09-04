# speckit-okf (OpenWiki engine)

A [Spec Kit](https://github.com/github/spec-kit) extension that generates and
maintains an [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
(OKF) knowledge bundle for a repository. It's a fork of
[alexcpn/speckit_okf](https://github.com/alexcpn/speckit_okf), which
generated OKF v0.1 bundles with a hand-rolled bash inventory scan, git-history
mining, and a single-shot agent prompt doing all the writing and validation
itself.

This fork replaces that generation engine with
[**OpenWiki**](https://github.com/langchain-ai/openwiki), run in-session
through its Claude Code MCP integration. OpenWiki:

- owns run state, a durable resumable page queue, and Claims (fact → cited
  source-evidence) tracking instead of a single free-form pass;
- deterministically enforces OKF v0.2 frontmatter/provenance conformance,
  index synchronization, and Mermaid diagram validity as part of every run —
  regardless of what the authoring agent wrote;
- designs its own repository-specific documentation taxonomy per run instead
  of a fixed layout;
- needs **no separate LLM API key** when run this way: the Claude Code
  integration uses the calling agent's own authenticated model session.
  (OpenWiki also has a standalone CLI mode with its own provider/API-key
  setup — this extension deliberately does not use that mode.)

## Why fork instead of extend the original

The original extension's whole generation/validation logic is bash + a
single agent prompt per run; there's no pluggable "engine" seam to swap in a
different generator. This fork keeps the same four command names
(`/speckit.okf.generate`, `/speckit.okf.update`, `/speckit.okf.clarify`,
`/speckit.okf.validate`) as a drop-in replacement, but the command bodies and
supporting scripts are rewritten to orchestrate OpenWiki's MCP tools instead
of doing the research/inventory/history-mining themselves.

**Scope note:** this fork covers the Spec Kit extension surface only. The
upstream repo also ships a `plugins/okf` Claude Code plugin/skill bundle with
a sync script (`scripts/sync-skill.sh`) that mirrors the extension into a
separate skill package; that packaging layer was not ported here.

## Setup

1. Install the OpenWiki CLI (Node.js ≥ 22):

   ```sh
   npm install -g openwiki
   ```

2. Install the Claude Code integration (registers OpenWiki as an MCP server
   and installs its skill — no API key needed for this path):

   ```sh
   openwiki integrations install claude
   ```

   Use `--project` instead of the default user-level install if you want the
   MCP registration checked into this repo's `.mcp.json` for teammates.

3. Restart Claude Code (or this coding agent) so it picks up the new MCP
   server.

4. Install this extension into your Spec Kit project:

   ```sh
   specify extension add --dev /path/to/speckit-okf
   ```

   (Use whatever install path/flag your Spec Kit version expects for a local
   extension; see the [Spec Kit extension docs](https://github.com/github/spec-kit/blob/main/extensions/EXTENSION-DEVELOPMENT-GUIDE.md)
   if `--dev` isn't right for your version.)

Every command below runs `okf-preflight.sh` first and tells you exactly
what's missing (with the fix command) if any of the above isn't done yet.

## Commands

- **`/speckit.okf.generate`** — bootstraps the bundle under `openwiki/` by
  driving OpenWiki's `init` lifecycle (`openwiki_begin` → plan → per-page
  research/write loop → `openwiki_finish`). Refuses to blindly clobber an
  existing bundle; suggests `/speckit.okf.update` instead unless you
  explicitly ask for a rebuild.
- **`/speckit.okf.update`** — refreshes the bundle for repository changes
  since the last run and reconciles any Claims whose cited evidence went
  stale, via OpenWiki's `update` lifecycle. No-ops cleanly if nothing
  changed.
- **`/speckit.okf.clarify`** — **redesigned** for OpenWiki's model (see
  below): scans page bodies for uncertainty language, asks you concrete
  questions about it, and records your answers in
  `openwiki/INSTRUCTIONS.md` for the next `/speckit.okf.update` to pick up.
- **`/speckit.okf.validate`** — a structural second opinion on the bundle
  (frontmatter parses, links resolve, indexes present, no dupes). OpenWiki's
  own finalizer is the authoritative validator and runs on every
  generate/update regardless.

### Why `/speckit.okf.clarify` had to change

The original extension parked unresolved questions in an `open_questions`
frontmatter field it invented and wrote by hand. OpenWiki has no such field —
it only writes what it can back with cited source evidence (a Claim), and
otherwise just doesn't assert the fact. There's nothing to "collect" from
frontmatter. This fork's `/speckit.okf.clarify` instead treats
`openwiki/INSTRUCTIONS.md` — the one file OpenWiki reads on every run but
never overwrites — as the injection point for facts only a human can supply,
and greps existing pages for uncertainty phrasing ("unclear", "TODO",
"unable to verify", …) as the starting point for what to ask about. Configure
the marker list in `okf-config.yml`.

## Configuration

Copy `okf-config.template.yml` to `.specify/extensions/okf/okf-config.yml` to
override defaults (bundle location is fixed by OpenWiki to `openwiki/`; the
main things actually worth changing here are the Spec Kit agent `host` id and
the `/speckit.okf.clarify` uncertainty-marker list). See the comments in that
file — most of the original's config surface (bundle layout, granularity,
type taxonomy, exclude globs) no longer applies, since OpenWiki owns those
decisions itself now.

## Credits

- Original extension: [alexcpn/speckit_okf](https://github.com/alexcpn/speckit_okf)
  by Alex Punnen.
- Generation engine: [langchain-ai/openwiki](https://github.com/langchain-ai/openwiki).
- OKF spec: [GoogleCloudPlatform/knowledge-catalog](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md).
