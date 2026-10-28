#!/usr/bin/env python3
"""Fetch upstream skills, merge them into rules.yaml, and render SKILL.md.

The merge is deterministic. It only appends upstream bullets that are not
already represented; it never rewrites curated rules. A possible duplicate
(0.75 <= similarity < 0.90) is reported and withheld for review instead of
being silently appended.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import quote

import yaml

SKILL_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = SKILL_DIR / "rules.yaml"
SOURCES_PATH = SKILL_DIR / "sources.yaml"
SKILL_PATH = SKILL_DIR / "SKILL.md"
LOCK_PATH = SKILL_DIR / "sources.lock.json"
COVERAGE_PATH = SKILL_DIR / "tests" / "coverage.json"
REPORT_PATH = SKILL_DIR / "reports" / "last-sync.md"

FUZZY_MATCH = 0.90
POSSIBLE_DUPLICATE = 0.75
MAX_NEW_RULES = 20
NEGATION_WORDS = {"not", "never", "only", "always", "must", "cannot", "can't", "without", "no"}


def log(message: str) -> None:
    print(message, flush=True)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    text = re.sub(r"[`*_\"'“”‘’]", "", text)
    text = re.sub(r"[^\w\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def has_negation(text: str) -> bool:
    return bool(set(re.findall(r"[a-z']+", text.casefold())) & NEGATION_WORDS)


def split_sections(text: str) -> dict[str, list[str]]:
    """Return level-2 heading -> bullets, including bullets under level 3+."""
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                lines = lines[i + 1 :]
                break
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            if level == 1:
                current = None
            elif level == 2:
                current = title
                sections.setdefault(current, [])
            # level 3+ remains inside the current level-2 heading
        elif current is not None:
            b = re.match(r"^\s*[-*]\s+(.*)$", line)
            if b and b.group(1).strip():
                sections[current].append(b.group(1).strip())
    return sections


def run(cmd: list[str], *, cwd: Path | None = None, strip: bool = True) -> str:
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd) if cwd else None, text=True,
            capture_output=True, check=True, timeout=60,
        )
        return proc.stdout.strip() if strip else proc.stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise RuntimeError(f"command failed: {' '.join(cmd)}\n{detail.strip()}") from exc


def latest_commit(repo: str, path: str, ref: str) -> str:
    """Return the last commit that touched path, falling back to the branch head."""
    api = (
        f"https://api.github.com/repos/{repo}/commits?"
        f"path={quote(path, safe='')}&sha={quote(ref, safe='')}&per_page=1"
    )
    try:
        data = json.loads(fetch_text(api))
        if isinstance(data, list) and data and data[0].get("sha"):
            return data[0]["sha"]
    except Exception:
        pass
    out = run(["git", "ls-remote", f"https://github.com/{repo}.git", f"refs/heads/{ref}"])
    if not out:
        raise RuntimeError(f"could not resolve {repo} refs/heads/{ref}")
    return out.split()[0]


def fetch_text(url: str) -> str:
    # curl understands HTTPS_PROXY/ALL_PROXY, which keeps this script usable
    # behind the local SOCKS tunnel without adding a Python proxy dependency.
    return run(["curl", "-fsSL", "--retry", "3", "--retry-delay", "1", url], strip=False)


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def dump_yaml(path: Path, data: Any) -> None:
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=110),
        encoding="utf-8",
    )


def render(config: dict[str, Any]) -> str:
    skill = config["skill"]
    front = {
        "name": skill["name"],
        "description": skill["description"],
        "license": skill["license"],
        "metadata": skill.get("metadata", {}),
    }
    lines: list[str] = ["---"]
    lines.append(yaml.safe_dump(front, sort_keys=False, allow_unicode=True, width=1000).rstrip())
    lines.append("---")
    lines.append("")
    lines.append("# Coding Discipline")
    lines.append("")

    for paragraph in config.get("intro", []):
        lines.append(paragraph.strip())
        lines.append("")

    for section in config.get("sections", []):
        lines.append(f"## {section['title']}")
        lines.append("")
        for note in section.get("notes", []):
            lines.append(note.strip())
            lines.append("")
        for group in section.get("groups", []):
            rules = group.get("rules", [])
            if not rules:
                continue
            lines.append(f"### {group['title']}")
            lines.append("")
            for rule in rules:
                lines.append(f"- {rule['text'].strip()}")
            lines.append("")
            for note in group.get("notes", []):
                lines.append(note.strip())
                lines.append("")

    for paragraph in config.get("outro", []):
        lines.append(paragraph.strip())
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def choose_match(text: str, rules: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, float, str]:
    """Return (rule, score, kind). kind is exact, fuzzy, possible, or new."""
    norm = normalize(text)
    for rule in rules:
        if normalize(rule["text"]) == norm:
            return rule, 1.0, "exact"

    best: tuple[dict[str, Any] | None, float] = (None, 0.0)
    for rule in rules:
        score = difflib.SequenceMatcher(None, norm, normalize(rule["text"])).ratio()
        if score > best[1]:
            best = (rule, score)

    rule, score = best
    if rule is not None and score >= FUZZY_MATCH and has_negation(text) == has_negation(rule["text"]):
        return rule, score, "fuzzy"
    if rule is not None and score >= POSSIBLE_DUPLICATE:
        return rule, score, "possible"
    return None, score, "new"


def sync_sources(
    config: dict[str, Any],
    sources: list[dict[str, Any]],
    *,
    prune: bool = False,
    allow_many: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Return (updated config, lock, coverage)."""
    source_index: dict[str, dict[str, Any]] = {}
    all_headings: dict[str, set[str]] = {}
    lock_sources = []
    for source in sources:
        commit = latest_commit(source["repo"], source["path"], source["ref"])
        url = f"https://raw.githubusercontent.com/{source['repo']}/{commit}/{source['path']}"
        text = fetch_text(url)
        headings = split_sections(text)
        source_index[source["id"]] = {
            "source": source, "commit": commit, "text": text, "headings": headings,
        }
        all_headings[source["id"]] = set(headings)
        lock_sources.append({
            "id": source["id"],
            "repo": source["repo"],
            "path": source["path"],
            "ref": source["ref"],
            "commit": commit,
            "content_sha256": sha256(text),
            "license": source.get("license", "unknown"),
        })
        log(f"fetched {source['id']} @ {commit[:10]} ({len(text.splitlines())} lines)")

    # Map every group to the bullets of its declared source headings.
    group_lookup: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for section in config["sections"]:
        for group in section["groups"]:
            group_lookup[group["id"]] = (section, group)

    mapped_headings: set[tuple[str, str]] = set()
    for source in sources:
        for heading, group_id in (source.get("headings") or {}).items():
            mapped_headings.add((source["id"], heading))
            if heading not in all_headings[source["id"]]:
                raise RuntimeError(f"mapped heading missing from {source['id']}: {heading}")
            if group_id not in group_lookup:
                raise RuntimeError(f"mapped group missing: {group_id}")

    seen_global: set[str] = set()
    coverage_rules: list[dict[str, Any]] = []
    new_rules = 0
    matched = 0
    duplicates = 0
    possible: list[dict[str, Any]] = []

    for source in sources:
        sid = source["id"]
        headings = source_index[sid]["headings"]
        for heading, group_id in (source.get("headings") or {}).items():
            section, group = group_lookup[group_id]
            for index, text in enumerate(headings[heading], 1):
                norm_hash = sha256(normalize(text))
                if norm_hash in seen_global:
                    duplicates += 1
                    coverage_rules.append({
                        "source": sid, "heading": heading, "index": index,
                        "text": text, "sha256": norm_hash,
                        "rule_id": None, "status": "duplicate",
                    })
                    continue
                rule, score, kind = choose_match(text, group["rules"])
                if kind == "exact":
                    matched += 1
                    rule_id = rule["id"]
                    status = "matched"
                elif kind == "fuzzy":
                    matched += 1
                    rule_id = rule["id"]
                    status = f"matched-fuzzy:{score:.2f}"
                elif kind == "possible":
                    possible.append({
                        "source": sid, "heading": heading, "text": text,
                        "rule_id": rule["id"] if rule else None, "score": round(score, 3),
                    })
                    coverage_rules.append({
                        "source": sid, "heading": heading, "index": index,
                        "text": text, "sha256": norm_hash,
                        "rule_id": rule["id"] if rule else None,
                        "status": f"possible-duplicate:{score:.2f}",
                    })
                    continue
                else:
                    rule_id = f"auto-{sid}-{norm_hash[:8]}"
                    group["rules"].append({
                        "id": rule_id,
                        "text": text,
                        "origin": sid,
                        "auto": True,
                    })
                    new_rules += 1
                    status = "new"
                seen_global.add(norm_hash)
                coverage_rules.append({
                    "source": sid, "heading": heading, "index": index,
                    "text": text, "sha256": norm_hash,
                    "rule_id": rule_id, "status": status,
                })

    if new_rules > MAX_NEW_RULES and not allow_many:
        raise RuntimeError(
            f"refusing to add {new_rules} new rules in one run (limit {MAX_NEW_RULES}). "
            "Review the upstream change, then rerun with --allow-many if intended."
        )

    if prune:
        keep_hashes = set()
        for source in sources:
            for heading in (source.get("headings") or {}):
                for text in source_index[source["id"]]["headings"][heading]:
                    keep_hashes.add(sha256(normalize(text)))
        for section in config["sections"]:
            for group in section["groups"]:
                kept = []
                for rule in group["rules"]:
                    if rule.get("auto") and sha256(normalize(rule["text"])) not in keep_hashes:
                        continue
                    kept.append(rule)
                group["rules"] = kept

    unmapped = []
    for source in sources:
        for heading in all_headings[source["id"]]:
            if (source["id"], heading) not in mapped_headings:
                unmapped.append({"source": source["id"], "heading": heading})

    total_bullets = sum(
        len(source_index[sid]["headings"][heading])
        for sid in source_index
        for heading in source_index[sid]["headings"]
    )
    coverage = {
        "total_source_bullets": total_bullets,
        "matched": matched,
        "duplicates": duplicates,
        "new": new_rules,
        "possible_duplicates": len(possible),
        "unmapped_headings": unmapped,
        "possible_duplicate_details": possible,
        "rules": coverage_rules,
    }
    lock = {
        "version": 1,
        "skill_sha256": sha256(render(config)),
        "sources": lock_sources,
        "stats": {
            "total_source_bullets": total_bullets,
            "matched": matched,
            "duplicates": duplicates,
            "new": new_rules,
            "possible_duplicates": len(possible),
        },
    }
    return config, lock, coverage


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def report_text(lock: dict[str, Any], coverage: dict[str, Any]) -> str:
    lines = [
        "# Sync report",
        "",
        "## Sources",
        "",
    ]
    for source in lock["sources"]:
        lines.append(
            f"- `{source['id']}`: `{source['repo']}` `{source['path']}` @ `{source['commit']}` "
            f"(license: {source['license']})"
        )
    lines += [
        "",
        "## Counts",
        "",
        f"- Source bullets: {coverage['total_source_bullets']}",
        f"- Matched to curated rules: {coverage['matched']}",
        f"- Exact duplicates skipped: {coverage['duplicates']}",
        f"- New auto rules appended: {coverage['new']}",
        f"- Possible duplicates withheld: {coverage['possible_duplicates']}",
        f"- Unmapped headings: {len(coverage['unmapped_headings'])}",
        "",
    ]
    if coverage["possible_duplicate_details"]:
        lines += ["## Possible duplicates (review before editing)", ""]
        for item in coverage["possible_duplicate_details"]:
            lines.append(
                f"- `{item['source']}` / `{item['heading']}`: `{item['text']}` "
                f"(rule `{item['rule_id']}`, score {item['score']})"
            )
        lines.append("")
    if coverage["unmapped_headings"]:
        lines += ["## Unmapped headings", ""]
        for item in coverage["unmapped_headings"]:
            lines.append(f"- `{item['source']}`: `{item['heading']}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate without writing")
    parser.add_argument("--apply", action="store_true", help="write SKILL.md and state")
    parser.add_argument("--prune", action="store_true", help="remove auto rules no longer upstream")
    parser.add_argument("--replace-edits", action="store_true", help="overwrite a hand-edited SKILL.md")
    parser.add_argument("--allow-many", action="store_true", help="allow more than the new-rule safety limit")
    args = parser.parse_args()
    if not args.check and not args.apply:
        parser.error("choose --check or --apply")

    config = load_yaml(CONFIG_PATH)
    sources = load_yaml(SOURCES_PATH)["sources"]

    if args.apply and SKILL_PATH.exists() and not args.replace_edits:
        lock = json.loads(LOCK_PATH.read_text(encoding="utf-8")) if LOCK_PATH.exists() else None
        expected = lock.get("skill_sha256") if lock else None
        current = sha256(SKILL_PATH.read_text(encoding="utf-8"))
        if expected and current != expected:
            log("SKILL.md has local edits; refusing to overwrite. Use --replace-edits after review.")
            return 2

    updated, lock, coverage = sync_sources(
        config, sources, prune=args.prune, allow_many=args.allow_many
    )
    rendered = render(updated)

    if args.check:
        current = SKILL_PATH.read_text(encoding="utf-8") if SKILL_PATH.exists() else ""
        if current == rendered:
            log("SKILL.md is up to date.")
            log(
                f"coverage: {coverage['matched']} matched, {coverage['duplicates']} duplicates, "
                f"{coverage['new']} new, {coverage['possible_duplicates']} possible duplicates"
            )
            return 0
        diff = difflib.unified_diff(
            current.splitlines(), rendered.splitlines(),
            fromfile="SKILL.md", tofile="generated/SKILL.md", lineterm="",
        )
        print("\n".join(diff))
        return 1

    dump_yaml(CONFIG_PATH, updated)
    write_atomic(SKILL_PATH, rendered)
    write_atomic(LOCK_PATH, json.dumps(lock, ensure_ascii=False, indent=2) + "\n")
    write_atomic(COVERAGE_PATH, json.dumps(coverage, ensure_ascii=False, indent=2) + "\n")
    write_atomic(REPORT_PATH, report_text(lock, coverage))
    log(f"wrote {SKILL_PATH.relative_to(SKILL_DIR)} ({len(rendered.splitlines())} lines)")
    log(
        f"coverage: {coverage['matched']} matched, {coverage['duplicates']} duplicates, "
        f"{coverage['new']} new, {coverage['possible_duplicates']} possible duplicates"
    )
    if coverage["unmapped_headings"]:
        log(f"WARNING: {len(coverage['unmapped_headings'])} unmapped headings; see report")
    return 0


if __name__ == "__main__":
    sys.exit(main())
