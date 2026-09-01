# Security Policy

## Supported Versions

Only the latest released version is supported with security fixes.

| Version | Supported |
| ------- | --------- |
| 0.2.x   | ✅        |
| 0.1.x   | ❌        |

## Reporting a Vulnerability

Please report suspected vulnerabilities privately via
[GitHub Security Advisories](https://github.com/alexcpn/speckit_okf/security/advisories/new)
rather than opening a public issue.

Include:
- A description of the issue and its potential impact
- Steps to reproduce, or a minimal example
- The version/commit affected

You should get an initial response within a few days. If confirmed, a fix
will be released and credited in the [CHANGELOG](CHANGELOG.md) unless you
prefer to stay anonymous.

## What's in Scope

This extension is a prompt-driven Spec Kit extension: two supporting
scripts (`scripts/bash/okf-inventory.sh`, `scripts/python/validate_okf.py`)
and three agent command prompts. Both scripts are automatically checked
on every push:

- [ShellCheck](.github/workflows/shellcheck.yml) — static analysis of the
  bash inventory script
- [CodeQL](.github/workflows/codeql.yml) — static security analysis of
  the Python validator
- GitHub secret scanning (with push protection) is enabled on this
  repository

Note that both scripts read arbitrary repository content (file paths,
config values) and are designed to run inside a developer's own
environment via their coding agent — they are not intended to process
untrusted input from third parties.
