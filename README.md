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
through its coding-agent MCP integration — **Claude Code** or **Junie**
(JetBrains) are both supported by this extension; see Setup below. OpenWiki:

- owns run state, a durable resumable page queue, and Claims (fact → cited
  source-evidence) tracking instead of a single free-form pass;
- deterministically enforces OKF v0.2 frontmatter/provenance conformance,
  index synchronization, and Mermaid diagram validity as part of every run —
  regardless of what the authoring agent wrote;
- designs its own repository-specific documentation taxonomy per run instead
  of a fixed layout;
- needs **no separate LLM API key** when run this way: the host integration
  uses the calling agent's own authenticated model session. (OpenWiki also
  has a standalone CLI mode with its own provider/API-key setup — this
  extension deliberately does not use that mode.)

Commands are written host-agnostically using Spec Kit's
`__SPECKIT_COMMAND_<NAME>__` placeholders, so the invocation syntax the agent
tells you to type is always correct for whichever host installed them:
`/speckit.okf.update` under Claude Code (Spec Kit's dotted convention) vs.
`/speckit-okf-update` under Junie (Junie doesn't allow dots in slash-command
names, so Spec Kit's Junie integration installs hyphenated names instead —
this happens automatically, nothing to configure). This README uses the
dotted form throughout for readability; mentally substitute hyphens if
you're on Junie.

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

1. Install the OpenWiki CLI (Node.js ≥ 22), same for every host:

   ```sh
   npm install -g openwiki
   ```

2. Register OpenWiki as an MCP server for your coding agent — pick one:

   ### Setup for Claude Code

   OpenWiki has a built-in installer for this host:

   ```sh
   openwiki integrations install claude
   ```

   This registers the MCP server (in `.mcp.json` for `--project`, or
   `~/.claude.json` for the default user-level install) **and** installs its
   skill file. No API key needed.

   ### Setup for Junie (JetBrains)

   Junie is not in OpenWiki's `integrations install` registry (that only
   covers Codex, Claude Code, OpenCode, Cursor), so there's no one-line
   installer — register the MCP server by hand instead, in
   `~/.junie/mcp/mcp.json` (user-level) or `.junie/mcp/mcp.json`
   (project-level, if you want it checked in for teammates):

   ```json
   {
     "mcpServers": {
       "openwiki": {
         "command": "openwiki",
         "args": ["mcp", "--host", "junie"]
       }
     }
   }
   ```

   Merge the `"openwiki"` entry into `mcpServers` if the file already has
   other servers configured. `--host junie` is accepted freely — OpenWiki
   only validates it's a lowercase id, it isn't restricted to the
   `integrations install` registry — it just stamps `junie` as the producer
   in generated-page provenance instead of, say, `claude-code`. There is no
   separately installed Junie skill file for OpenWiki (unlike the Claude
   path); that's fine, this extension's command files are self-contained and
   don't depend on it. See [Junie's MCP docs](https://junie.jetbrains.com/docs/junie-cli-mcp-configuration.html)
   for the general format.

3. Restart your coding agent (Claude Code / the Junie CLI or plugin) so it
   picks up the new MCP server.

4. Install this extension into your Spec Kit project:

   ```sh
   specify extension add --dev /path/to/speckit-okf
   ```

   (Use whatever install path/flag your Spec Kit version expects for a local
   extension; see the [Spec Kit extension docs](https://github.com/github/spec-kit/blob/main/extensions/EXTENSION-DEVELOPMENT-GUIDE.md)
   if `--dev` isn't right for your version.) Spec Kit's Junie integration
   installs the commands to `.junie/commands/` with hyphenated names
   (`speckit-okf-generate.md`, etc.) automatically — nothing extra to do for
   that part.

5. Copy `okf-config.template.yml` to
   `.specify/extensions/okf/okf-config.yml` and set `okf.host` to match
   whichever agent you set up above (`"junie"` or `"claude"`) — the
   preflight check in every command reads it to know which MCP-config file
   to look for.

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
