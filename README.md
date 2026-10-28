# coding-discipline

A lightweight coding discipline for AI coding agents.

It merges the behavioral rules from Karpathy's LLM coding guidelines with Uncle Bob's three-phase `ub-mode` workflow, then adds the mandatory quality gates that make the result verifiable: CRAP, duplication, and mutation testing.

## What it does

The skill gives an agent a short, ordered checklist for any non-trivial code change:

1. **Before You Code** — surface assumptions, get the data shape right, attack a failed premise before trying another patch, and redesign from first principles when a requirement no longer fits.
2. **While You Code** — keep changes small, stay surgical, write the failing test first, test behavior rather than implementation, model the domain, and build a tool when the task is not obvious.
3. **Before You Finish** — fix root causes, sequence work into verifiable units, refactor without changing behavior, and define done in terms you can check.
4. **Quality Gates (Mandatory)** — keep every function under CRAP 10, eliminate duplication at 0.8 or above, and kill every mutation survivor.
5. **Practice** — keep a log, guard the context window, clean up the worktree, and commit in small ordered commits.

The full skill is [`skills/coding-discipline/SKILL.md`](skills/coding-discipline/SKILL.md). It is intentionally small: about 170 lines and roughly 1,500 tokens.

## Install

With GitHub CLI 2.90 or later:

```bash
gh skill install imwhatiam/coding-discipline coding-discipline
```

With the Vercel skills CLI:

```bash
npx skills add imwhatiam/coding-discipline --skill coding-discipline
```

Or copy `skills/coding-discipline/` into the skills directory of your agent. The skill name and directory name must both be `coding-discipline`.

## Updating

The repository includes a deterministic sync pipeline:

```bash
python skills/coding-discipline/scripts/sync.py --check   # show what would change
python skills/coding-discipline/scripts/sync.py --apply   # update SKILL.md, rules.yaml, lock and coverage
python skills/coding-discipline/scripts/validate.py       # validate the Agent Skills spec and coverage
```

`sync.py` fetches `multica-ai/andrej-karpathy-skills` and `unclebob/ub-mode` at their latest commits, matches upstream bullets against the curated rules, appends genuinely new bullets, and withholds near-duplicates for review. It never rewrites curated rules. The current upstream commits and content hashes are recorded in `sources.lock.json`; the last sync report is in `reports/last-sync.md`.

The GitHub Actions workflow [`.github/workflows/sync.yml`](.github/workflows/sync.yml) runs the same sync every Monday and can be triggered manually. It commits changes only when the generated skill, rules, lock, or coverage changed.

## Repository layout

```text
skills/coding-discipline/
├── SKILL.md                  # the skill agents load
├── rules.yaml                # curated rule ledger: the source of truth
├── sources.yaml              # upstream repositories and heading mapping
├── sources.lock.json         # latest synced commits and content hashes
├── references/
│   ├── upstream-karpathy.md  # pinned upstream snapshot
│   ├── upstream-ub-mode.md   # pinned upstream snapshot
│   └── quality-gates.md      # install and run instructions for the gates
├── scripts/
│   ├── sync.py               # fetch, merge, render, report
│   └── validate.py           # Agent Skills and coverage validation
└── tests/
    ├── test_sync.py          # unit tests for parsing and merging
    └── coverage.json         # every upstream bullet -> merged rule
```

## Quality gates

The three gate tools are mandatory for supported languages:

- [crapper](https://github.com/unclebob/crapper) — complexity, coverage, and CRAP score; keep every function under CRAP 10.
- [dryer](https://github.com/unclebob/dryer) — structural duplication; eliminate pairs at 0.8 or above.
- [mutator](https://github.com/unclebob/mutator) — mutation testing; cover the uncovered, kill the survivors, delete dead code.

See [`references/quality-gates.md`](skills/coding-discipline/references/quality-gates.md) for installation and command details. If a project's language is unsupported, record the reason and use the nearest project-native gate; never skip silently.

## Development

```bash
python -m pip install pyyaml
python -m unittest discover -s skills/coding-discipline/tests -v
python skills/coding-discipline/scripts/validate.py
```

## Sources, attribution, and license

This project is a synthesis, not a fork of either upstream repository.

- [Karpathy Guidelines](https://github.com/multica-ai/andrej-karpathy-skills), derived from Andrej Karpathy's observations on LLM coding pitfalls; the skill file declares MIT.
- [ub-mode](https://github.com/unclebob/ub-mode) by Robert C. Martin (Uncle Bob); no explicit license file is present upstream. The rules are restated with attribution; all rights remain with the original author.
- [crapper](https://github.com/unclebob/crapper), [dryer](https://github.com/unclebob/dryer), and [mutator](https://github.com/unclebob/mutator) are 0BSD-licensed.

See [`NOTICE.md`](NOTICE.md) for details. The original synthesis in this repository is MIT-licensed; see [`LICENSE`](LICENSE).
