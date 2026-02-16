#!/usr/bin/env python3
"""Minimal PII scan: fail if likely personal email addresses are committed.

This is intentionally lightweight and conservative. It is designed to prevent
accidental publication of volunteer contact info in a public repo.

Allowlist:
- example.com / example.org / example.net (documentation examples)
- agentvillage.org (org contact addresses, e.g. Code of Conduct reporting)

Usage:
- Scan whole repo:      python3 scripts/pii_scan.py
- Scan specific files:  python3 scripts/pii_scan.py path/to/file.md ...
- Scan from file list:  python3 scripts/pii_scan.py --files-from changed.txt
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
ALLOW_DOMAINS = {"example.com", "example.org", "example.net", "agentvillage.org"}

EXCLUDE_DIRS = {".git", ".venv", "node_modules"}
BINARY_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".ico", ".zip"}


def iter_repo_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for p in root.rglob("*"):
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        if p.is_file():
            files.append(p)
    return files


def scan_files(paths: list[Path]) -> list[tuple[str, int, str]]:
    hits: list[tuple[str, int, str]] = []

    for path in paths:
        if not path.exists() or not path.is_file():
            continue

        if path.suffix.lower() in BINARY_EXTS:
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for i, line in enumerate(text.splitlines(), start=1):
            m = EMAIL_RE.search(line)
            if not m:
                continue
            domain = m.group(1).lower()
            if domain in ALLOW_DOMAINS:
                continue
            hits.append((str(path), i, line.strip()))

    return hits


def load_paths_from_filelist(filelist_path: Path) -> list[Path]:
    raw = filelist_path.read_text(encoding="utf-8", errors="ignore")
    paths: list[Path] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        # Ignore deleted paths in diffs, just in case
        if line.startswith("/dev/null"):
            continue
        paths.append(Path(line))
    return paths


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", help="Files to scan (default: whole repo)")
    ap.add_argument("--files-from", dest="files_from", help="Read newline-delimited file paths from a file")
    args = ap.parse_args()

    if args.files_from:
        paths = load_paths_from_filelist(Path(args.files_from))
    elif args.paths:
        paths = [Path(p) for p in args.paths]
    else:
        paths = iter_repo_files(Path("."))

    hits = scan_files(paths)

    if hits:
        print(
            "PII scan failed: found likely email address(es). "
            "Do not commit volunteer contact info to public repos."
        )
        for path, i, line in hits[:200]:
            print(f"{path}:{i}: {line}")
        if len(hits) > 200:
            print(f"... plus {len(hits) - 200} more")
        return 2

    print("PII scan OK: no disallowed email addresses found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
