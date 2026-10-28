#!/usr/bin/env python3
"""Validate the coding-discipline skill against the Agent Skills spec."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

SKILL_DIR = Path(__file__).resolve().parents[1]
SKILL_PATH = SKILL_DIR / "SKILL.md"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    text = SKILL_PATH.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        fail("SKILL.md must start with YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        fail("SKILL.md frontmatter is not closed")
    front = yaml.safe_load(text[4:end])
    body = text[end + 5 :]

    if not isinstance(front, dict):
        fail("frontmatter must be a mapping")
    name = front.get("name", "")
    description = front.get("description", "")
    if not name:
        fail("missing required field: name")
    if len(name) > 64 or not NAME_RE.match(name):
        fail(f"invalid name: {name!r}")
    if name != SKILL_DIR.name:
        fail(f"name {name!r} must match directory {SKILL_DIR.name!r}")
    if not description:
        fail("missing required field: description")
    if len(description) > 1024:
        fail(f"description is {len(description)} characters; max is 1024")
    if not front.get("license"):
        print("WARNING: recommended field missing: license")
    if "allowed-tools" in front and not isinstance(front["allowed-tools"], str):
        fail("allowed-tools must be a string, not an array")
    metadata = front.get("metadata") or {}
    if not isinstance(metadata, dict):
        fail("metadata must be a mapping")
    for key, value in metadata.items():
        if not isinstance(value, str):
            fail(f"metadata.{key} must be a string, got {type(value).__name__}")

    line_count = len(body.splitlines())
    if line_count > 500:
        fail(f"SKILL.md body has {line_count} lines; keep it under 500")
    approx_tokens = len(body) // 4
    if approx_tokens > 5000:
        fail(f"SKILL.md body is about {approx_tokens} tokens; keep it under 5000")

    for match in re.finditer(r"`(references/[^`]+)`", body):
        ref = SKILL_DIR / match.group(1)
        if not ref.exists():
            fail(f"referenced file does not exist: {match.group(1)}")

    for marker in ("<<<<<<<", ">>>>>>>", "TODO", "FIXME"):
        if marker in body:
            fail(f"unresolved marker in SKILL.md: {marker}")

    coverage_path = SKILL_DIR / "tests" / "coverage.json"
    if coverage_path.exists():
        coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
        total = coverage.get("total_source_bullets", 0)
        accounted = (
            coverage.get("matched", 0)
            + coverage.get("duplicates", 0)
            + coverage.get("new", 0)
        )
        if total != accounted:
            fail(f"coverage mismatch: {accounted} accounted of {total} source bullets")
        if coverage.get("possible_duplicates"):
            fail("possible duplicate rules need review before release")
        if coverage.get("unmapped_headings"):
            fail("unmapped upstream headings need review before release")
    else:
        print("WARNING: tests/coverage.json missing; run sync.py --apply")

    print(f"OK: {name}")
    print(f"  description: {len(description)} characters")
    print(f"  body: {line_count} lines, about {approx_tokens} tokens")
    print(f"  metadata.version: {metadata.get('version', 'missing')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
