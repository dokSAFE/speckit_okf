#!/usr/bin/env python3
"""validate_skill.py — sanity-check an Agent Skill directory.

Checks the SKILL.md frontmatter against the Agent Skills format (name,
description, optional license/allowed-tools/metadata), that the name matches
the directory, and that every skill-relative path the body references
actually exists. Exits non-zero on ERROR.

Usage: validate_skill.py <skill_dir>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
KNOWN_KEYS = {"name", "description", "license", "allowed-tools", "metadata"}
# Skill-relative paths mentioned in the body, e.g. `references/generate.md`
# or `$SKILL_DIR/scripts/bash/okf-inventory.sh`. Requires a file extension so
# bare directory mentions ("push detail into references/") aren't flagged.
PATH_RE = re.compile(
    r"(?:\$SKILL_DIR/)?\b((?:references|scripts|assets)"
    r"(?:/[\w.-]+)*\.(?:md|sh|py|json|ya?ml|txt))"
)

errors: list[str] = []
warnings: list[str] = []


def split_frontmatter(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 3)
    if end == -1:
        return None
    return text[4:end + 1]


def parse_frontmatter(raw: str) -> dict:
    try:
        import yaml  # type: ignore
    except ImportError:
        warnings.append("PyYAML not installed — frontmatter parsed leniently")
        data = {}
        key = None
        for line in raw.splitlines():
            m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
            if m:
                key = m.group(1)
                data[key] = m.group(2).strip().strip("'\"")
            elif key and line.strip():
                data[key] = (str(data.get(key, "")) + " " + line.strip()).strip()
        return data
    loaded = yaml.safe_load(raw)
    if not isinstance(loaded, dict):
        raise ValueError("frontmatter is not a mapping")
    return loaded


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip())
        return 2

    skill_dir = Path(argv[1]).resolve()
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.is_file():
        print(f"ERROR: no SKILL.md in {skill_dir}")
        return 1

    text = skill_md.read_text(encoding="utf-8")
    raw = split_frontmatter(text)
    if raw is None:
        errors.append("SKILL.md must open with a `---` YAML frontmatter block")
        meta: dict = {}
    else:
        try:
            meta = parse_frontmatter(raw)
        except Exception as exc:  # noqa: BLE001 - report, don't crash
            errors.append(f"frontmatter is not parseable YAML: {exc}")
            meta = {}

    name = str(meta.get("name", "") or "")
    if not name:
        errors.append("frontmatter is missing a `name`")
    else:
        if not NAME_RE.match(name):
            errors.append(f"`name: {name}` must be lowercase letters/digits/hyphens")
        if len(name) > 64:
            errors.append(f"`name` is {len(name)} chars (max 64)")
        if name != skill_dir.name:
            errors.append(f"`name: {name}` does not match directory `{skill_dir.name}`")

    desc = " ".join(str(meta.get("description", "") or "").split())
    if not desc:
        errors.append("frontmatter is missing a `description`")
    else:
        if len(desc) > 1024:
            errors.append(f"`description` is {len(desc)} chars (max 1024)")
        if len(desc) < 40:
            warnings.append("`description` is very short — it is the only text an "
                            "agent sees when deciding whether to load the skill")

    for key in set(meta) - KNOWN_KEYS:
        warnings.append(f"unknown frontmatter key `{key}` (ignored by most hosts)")

    body = text[len(raw) + 8:] if raw else text
    words = len(body.split())
    if words > 5000:
        warnings.append(f"SKILL.md body is {words} words — keep it under ~5k and "
                        "push detail into references/")

    referenced = sorted(set(PATH_RE.findall(text)))
    for rel in referenced:
        if not (skill_dir / rel).exists():
            errors.append(f"SKILL.md references `{rel}`, which does not exist")

    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")

    print(f"\n{skill_dir.name}: {len(errors)} error(s), {len(warnings)} warning(s), "
          f"{len(referenced)} referenced path(s) checked, {words} body words")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
