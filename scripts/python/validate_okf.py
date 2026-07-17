#!/usr/bin/env python3
"""validate_okf.py — conformance checker for OKF v0.1 bundles.

Implements OKF §9 conformance rules as ERRORs and the spec's soft
guidance as WARNINGs:

ERRORS (bundle is non-conformant):
  E1  Non-reserved .md file has no parseable YAML frontmatter block.
  E2  Frontmatter lacks a non-empty `type` field.
  E3  Reserved file structure violations:
      - index.md with frontmatter anywhere except the bundle root
        (root index.md may carry only okf_version per §11)
      - log.md date headings not in ISO 8601 YYYY-MM-DD form (§7)

WARNINGS (consumers must tolerate; reported for quality):
  W1  Missing recommended frontmatter (title, description).
  W2  Broken bundle-internal links (may be not-yet-written knowledge).
  W3  Directory containing concepts but no index.md.
  W4  Concept body is empty.
  W5  Possible secret-looking string in a file.

Usage: validate_okf.py <bundle_dir>
Exit code 0 if conformant (warnings allowed), 1 otherwise.

Only stdlib is required; PyYAML is used if available for stricter YAML
parsing, with a lenient fallback otherwise.
"""

import os
import re
import sys

try:
    import yaml  # type: ignore
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False

RESERVED = {"index.md", "log.md"}
DATE_HEADING = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*$")
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
SECRET_HINT = re.compile(
    r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][A-Za-z0-9+/_\-]{16,}['\"]"
)

errors: list[str] = []
warnings: list[str] = []


def split_frontmatter(text: str):
    """Return (frontmatter_str or None, body)."""
    if not text.startswith("---"):
        return None, text
    parts = text.split("\n")
    if parts[0].strip() != "---":
        return None, text
    for i in range(1, len(parts)):
        if parts[i].strip() == "---":
            return "\n".join(parts[1:i]), "\n".join(parts[i + 1:])
    return None, text  # unterminated block


def parse_yaml(fm: str):
    """Parse frontmatter; return dict or None on failure."""
    if HAVE_YAML:
        try:
            data = yaml.safe_load(fm)
            return data if isinstance(data, dict) else None
        except yaml.YAMLError:
            return None
    # Lenient fallback: top-level "key: value" lines only.
    data = {}
    for line in fm.splitlines():
        if not line.strip() or line.startswith(("#", " ", "\t", "-")):
            continue
        if ":" not in line:
            return None
        k, _, v = line.partition(":")
        data[k.strip()] = v.strip().strip("'\"")
    return data


def check_concept(path: str, rel: str, bundle: str):
    text = open(path, encoding="utf-8", errors="replace").read()
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
    if SECRET_HINT.search(text):
        warnings.append(f"W5 {rel}: possible secret-looking value — review before sharing")


def check_links(body: str, rel: str, filedir: str, bundle: str):
    for target in LINK.findall(body):
        target = target.split("#")[0].strip()
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        if target.startswith("/"):
            dest = os.path.join(bundle, target.lstrip("/"))
        else:
            dest = os.path.join(filedir, target)
        # Directory links (progressive disclosure) are fine if the dir exists.
        if not (os.path.exists(dest) or os.path.exists(dest.rstrip("/"))):
            warnings.append(f"W2 {rel}: broken link -> {target}")


def check_index(path: str, rel: str, is_root: bool, bundle: str):
    text = open(path, encoding="utf-8", errors="replace").read()
    fm, body = split_frontmatter(text)
    if fm is not None:
        if not is_root:
            errors.append(f"E3 {rel}: index.md must not contain frontmatter (only the bundle root may, per §11)")
        else:
            data = parse_yaml(fm) or {}
            extra = set(data) - {"okf_version"}
            if extra:
                errors.append(f"E3 {rel}: root index.md frontmatter may only declare okf_version (found: {sorted(extra)})")
    check_links(body if fm is not None else text, rel, os.path.dirname(path), bundle)


def check_log(path: str, rel: str):
    bad = [
        ln.strip() for ln in open(path, encoding="utf-8", errors="replace")
        if ln.startswith("## ") and not DATE_HEADING.match(ln.rstrip())
    ]
    for ln in bad:
        errors.append(f"E3 {rel}: log heading not ISO 8601 YYYY-MM-DD: '{ln}'")


def main() -> int:
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        print(__doc__)
        return 2
    bundle = os.path.abspath(sys.argv[1])
    concepts = 0
    for dirpath, dirnames, filenames in os.walk(bundle):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        mds = [f for f in filenames if f.endswith(".md")]
        rel_dir = os.path.relpath(dirpath, bundle)
        if any(f not in RESERVED for f in mds) and "index.md" not in mds:
            warnings.append(f"W3 {rel_dir or '.'}: directory has concepts but no index.md")
        for f in mds:
            path = os.path.join(dirpath, f)
            rel = os.path.relpath(path, bundle)
            if f == "index.md":
                check_index(path, rel, dirpath == bundle, bundle)
            elif f == "log.md":
                check_log(path, rel)
            else:
                concepts += 1
                check_concept(path, rel, bundle)

    print(f"OKF validation of {bundle}")
    print(f"  concepts: {concepts}  errors: {len(errors)}  warnings: {len(warnings)}\n")
    for e in errors:
        print(f"  ERROR   {e}")
    for w in warnings:
        print(f"  WARNING {w}")
    print("\nRESULT:", "NON-CONFORMANT" if errors else "CONFORMANT (OKF v0.1)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
