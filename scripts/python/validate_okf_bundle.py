#!/usr/bin/env python3
"""validate_okf_bundle.py — structural conformance checker for OpenWiki-
generated OKF v0.2 bundles.

This is a *second opinion*, not the authoritative validator: OpenWiki's own
`src/okf/frontmatter.ts` deterministically enforces OKF conformance on every
`openwiki_finish`. This script re-checks structure for cases where that's
useful anyway (an interrupted run, a manual edit before commit, CI) without
reimplementing OpenWiki's internal evidence-staleness logic.

Adapted from alexcpn/speckit_okf's validate_okf.py (OKF v0.1 checker). The
`log.md` / `Commit: <sha>` requirement (E3/E4 there) is dropped: OpenWiki
does not use log.md for its own incremental-update bookkeeping (it uses
openwiki/.run.json and openwiki/.last-update.json instead), so requiring a
commit-stamped log entry no longer reflects how staleness is actually
tracked. If a log.md is present it's still checked for readability and
sane date headings, but never required.

ERRORS (bundle is structurally broken):
  E1  Non-reserved .md file has no parseable YAML frontmatter block, or
      could not be read.
  E2  Frontmatter lacks a non-empty `type` field.
  E3  index.md carries frontmatter outside the bundle root, or the root
      index.md's frontmatter declares more than just `okf_version`.

WARNINGS (advisory; OpenWiki tolerates/produces some of these by design):
  W0  PyYAML not installed — using the lenient fallback parser.
  W1  Missing recommended frontmatter (title, description).
  W2  Broken bundle-internal links (may be not-yet-written knowledge).
  W3  Directory containing concepts but no index.md.
  W4  Concept body is empty.
  W5  Possible secret-looking string in a file.
  W6  A `sources[].resource` entry does not point at a file that exists on
      disk (best-effort; only checked for `repo://<path>[#...]` forms).
  W7  Possible duplicate concept: another file shares the same
      `type` + `title`.
  W8  `generated`/`verified`/`sources`/`status`/`stale_after` present but
      not shaped the way OKF v0.2 expects (advisory only — see module
      docstring; OpenWiki's own validator is authoritative).
  W9  log.md date heading not ISO 8601 YYYY-MM-DD (only checked if log.md
      exists; OpenWiki does not require this file).

Usage: validate_okf_bundle.py <bundle_dir> [--scope SUBDIR] [--json]
Exit code 0 if conformant (warnings allowed), 1 if non-conformant, 2 on bad
usage.

Only stdlib is required; PyYAML is used if available for stricter YAML
parsing, with a lenient fallback otherwise.
"""

import argparse
import json
import os
import re
import sys

try:
    import yaml  # type: ignore
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False

RESERVED = {"index.md", "log.md", "INSTRUCTIONS.md"}
DATE_HEADING = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*$")
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
ISO_OFFSET_DT = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][A-Za-z0-9+/_\-]{16,}['\"]"),
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*[A-Za-z0-9+/_\-]{16,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----"),
]

errors: list[str] = []
warnings: list[str] = []
concept_meta: list[tuple[str, str, str]] = []  # (rel, type, title)


def split_frontmatter(text: str):
    if not text.startswith("---"):
        return None, text
    parts = text.split("\n")
    if parts[0].strip() != "---":
        return None, text
    for i in range(1, len(parts)):
        if parts[i].strip() == "---":
            return "\n".join(parts[1:i]), "\n".join(parts[i + 1:])
    return None, text


def parse_yaml(fm: str):
    if HAVE_YAML:
        try:
            data = yaml.safe_load(fm)
            return data if isinstance(data, dict) else None
        except yaml.YAMLError:
            return None
    data = {}
    for line in fm.splitlines():
        if not line.strip() or line.startswith(("#", " ", "\t", "-")):
            continue
        if ":" not in line:
            return None
        k, _, v = line.partition(":")
        data[k.strip()] = v.strip().strip("'\"")
    return data


def read_text(path: str):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read(), None
    except OSError as e:
        return None, str(e)


def check_v02_shape(data: dict, rel: str):
    """Advisory-only shape check for OKF v0.2 provenance/trust/lifecycle
    fields. Not authoritative — see module docstring."""
    issues = []

    def is_actor_event(v):
        return (
            isinstance(v, dict)
            and isinstance(v.get("by"), str) and v.get("by").strip()
            and (v.get("at") is None or (isinstance(v.get("at"), str) and ISO_OFFSET_DT.match(v["at"])))
        )

    if "generated" in data and not is_actor_event(data["generated"]):
        issues.append("`generated` should be a {by, at} mapping with a non-empty `by` and an ISO 8601 `at` with explicit UTC offset")
    if "verified" in data:
        v = data["verified"]
        vs = v if isinstance(v, list) else [v]
        if not all(is_actor_event(x) for x in vs):
            issues.append("`verified` should be a {by, at} mapping or list of them")
    if "sources" in data:
        s = data["sources"]
        if not (isinstance(s, list) and all(isinstance(x, dict) and isinstance(x.get("resource"), str) and x["resource"].strip() for x in s)):
            issues.append("`sources` should be a list of mappings each with a non-empty `resource`")
    if "status" in data and data["status"] not in ("draft", "stable", "deprecated"):
        issues.append("`status` should be one of draft, stable, deprecated")
    if "stale_after" in data:
        sa = data["stale_after"]
        if not (isinstance(sa, str) and ISO_OFFSET_DT.match(sa)):
            issues.append("`stale_after` should be an ISO 8601 datetime with explicit UTC offset")

    if issues:
        warnings.append(f"W8 {rel}: " + "; ".join(issues))


def check_source_refs(data: dict, rel: str, repo_root: str | None):
    """Best-effort existence check for repo:// resources cited in `sources`."""
    if repo_root is None:
        return
    s = data.get("sources")
    if not isinstance(s, list):
        return
    for entry in s:
        if not isinstance(entry, dict):
            continue
        resource = entry.get("resource")
        if not isinstance(resource, str) or not resource.startswith("repo://"):
            continue
        path = resource[len("repo://"):].split("#", 1)[0]
        if path and not os.path.exists(os.path.join(repo_root, path)):
            warnings.append(f"W6 {rel}: sources entry '{resource}' points at a path that does not exist")


def check_concept(path: str, rel: str, bundle: str, repo_root: str | None):
    text, err = read_text(path)
    if text is None:
        errors.append(f"E1 {rel}: could not read file ({err})")
        return
    fm, body = split_frontmatter(text)
    if fm is None:
        errors.append(f"E1 {rel}: missing or unterminated YAML frontmatter block")
        return
    data = parse_yaml(fm)
    if data is None:
        errors.append(f"E1 {rel}: frontmatter is not parseable YAML")
        return
    t = data.get("type")
    if not (isinstance(t, str) and t.strip()):
        errors.append(f"E2 {rel}: frontmatter has no non-empty `type` field")
    for field in ("title", "description"):
        if not data.get(field):
            warnings.append(f"W1 {rel}: missing recommended field `{field}`")
    if not body.strip():
        warnings.append(f"W4 {rel}: concept body is empty")
    check_links(body, rel, os.path.dirname(path), bundle)
    check_v02_shape(data, rel)
    check_source_refs(data, rel, repo_root)
    if isinstance(t, str) and t.strip() and data.get("title"):
        concept_meta.append((rel, t.strip(), str(data["title"]).strip()))
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            warnings.append(f"W5 {rel}: possible secret-looking value — review before sharing")
            break


def check_links(body: str, rel: str, filedir: str, bundle: str):
    for target in LINK.findall(body):
        target = target.split("#")[0].strip()
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        if target.startswith("/"):
            dest = os.path.join(bundle, target.lstrip("/"))
        else:
            dest = os.path.join(filedir, target)
        if not (os.path.exists(dest) or os.path.exists(dest.rstrip("/"))):
            warnings.append(f"W2 {rel}: broken link -> {target}")


def check_index(path: str, rel: str, is_root: bool, bundle: str):
    text, err = read_text(path)
    if text is None:
        errors.append(f"E1 {rel}: could not read file ({err})")
        return
    fm, body = split_frontmatter(text)
    if fm is not None:
        if not is_root:
            errors.append(f"E3 {rel}: index.md must not contain frontmatter (only the bundle root may)")
        else:
            data = parse_yaml(fm) or {}
            extra = set(data) - {"okf_version"}
            if extra:
                errors.append(f"E3 {rel}: root index.md frontmatter may only declare okf_version (found: {sorted(extra)})")
    check_links(body if fm is not None else text, rel, os.path.dirname(path), bundle)


def check_log(path: str, rel: str):
    """log.md is not required by OpenWiki; if present, only sanity-check
    date headings, never require a Commit line."""
    text, err = read_text(path)
    if text is None:
        errors.append(f"E1 {rel}: could not read file ({err})")
        return
    for ln in text.splitlines():
        if ln.startswith("## ") and not DATE_HEADING.match(ln.rstrip()):
            warnings.append(f"W9 {rel}: log heading not ISO 8601 YYYY-MM-DD: '{ln.rstrip()}'")


def find_repo_root(bundle: str) -> str | None:
    p = bundle
    while True:
        if os.path.isdir(os.path.join(p, ".git")):
            return p
        parent = os.path.dirname(p)
        if parent == p:
            return None
        p = parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Structural conformance checker for OpenWiki-generated OKF v0.2 bundles.")
    parser.add_argument("bundle_dir", help="Path to the OpenWiki bundle directory (usually 'openwiki')")
    parser.add_argument("--scope", help="Only check this subdirectory of the bundle")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of text")
    args = parser.parse_args()

    if not os.path.isdir(args.bundle_dir):
        parser.error(f"{args.bundle_dir} is not a directory")

    bundle = os.path.abspath(args.bundle_dir)
    repo_root = find_repo_root(bundle)
    scan_root = os.path.join(bundle, args.scope) if args.scope else bundle
    if not os.path.isdir(scan_root):
        parser.error(f"--scope {args.scope} does not exist under {bundle}")

    if not HAVE_YAML:
        warnings.append("W0 (global): PyYAML not installed — using lenient fallback parser, results may be less strict")

    concepts = 0
    for dirpath, dirnames, filenames in os.walk(scan_root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        rel_dir = os.path.relpath(dirpath, bundle)
        mds = [f for f in filenames if f.endswith(".md")]
        if any(f not in RESERVED for f in mds) and "index.md" not in mds:
            warnings.append(f"W3 {rel_dir or '.'}: directory has concepts but no index.md")
        for f in mds:
            path = os.path.join(dirpath, f)
            rel = os.path.relpath(path, bundle)
            if f == "index.md":
                check_index(path, rel, dirpath == bundle, bundle)
            elif f == "log.md":
                check_log(path, rel)
            elif f == "INSTRUCTIONS.md":
                continue  # user-authored, not a concept — nothing to check
            else:
                concepts += 1
                check_concept(path, rel, bundle, repo_root)

    seen: dict[tuple[str, str], str] = {}
    for rel, t, title in concept_meta:
        key = (t.lower(), title.lower())
        if key in seen:
            warnings.append(f"W7 {rel}: possible duplicate concept — same type+title as {seen[key]}")
        else:
            seen[key] = rel

    if args.json:
        print(json.dumps({
            "concepts": concepts,
            "errors": errors,
            "warnings": warnings,
            "result": "NON-CONFORMANT" if errors else "CONFORMANT",
        }, indent=2))
    else:
        print(f"OKF structural check of {bundle}" + (f" (scope: {args.scope})" if args.scope else ""))
        print(f"  concepts: {concepts}  errors: {len(errors)}  warnings: {len(warnings)}\n")
        for e in errors:
            print(f"  ERROR   {e}")
        for w in warnings:
            print(f"  WARNING {w}")
        print("\nRESULT:", "NON-CONFORMANT" if errors else "CONFORMANT (structural check only — OpenWiki's own validator is authoritative)")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
