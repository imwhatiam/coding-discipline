# Quality Gates

These gates are mandatory. Run them from the project root after the tests pass and before the work is called done. The three tools support Clojure, Java, Go, TypeScript/JavaScript, Rust, and Python.

## One-time install

Keep the three checkouts side by side. `mutator` expects `crapper` at `../crapper`.

```bash
mkdir -p ~/tools
git clone https://github.com/unclebob/crapper.git ~/tools/crapper
git clone https://github.com/unclebob/dryer.git ~/tools/dryer
git clone https://github.com/unclebob/mutator.git ~/tools/mutator
```

The first run of each launcher creates its own `.venv` and installs its dependencies. Python 3.11 or later is required.

## 1. Crapper — complexity, coverage, CRAP

```bash
cd /path/to/project
~/tools/crapper/crapper --threshold 10
```

- CRAP = cyclomatic complexity squared times the uncovered fraction, plus complexity.
- Keep every function under **CRAP 10**. Split it, test it, or both.
- Exit code `2` means the worst score is above the threshold: the gate failed.
- Output is also written to `.metrics/crap.edn` for inspection.
- Use `--changed` to check only additions and edits.

## 2. Dryer — structural duplication

```bash
cd /path/to/project
~/tools/dryer/dryer --threshold 0.8
```

- Reports pairs of forms whose normalized structures score at or above the threshold.
- Review every reported pair. Refactor real duplication; record why a reported pair is intentionally similar.
- Output is also written to `.metrics/dry.edn`.
- Use `--changed` to scan only changed files.

## 3. Mutator — mutation testing

```bash
cd /path/to/project
~/tools/mutator/mutator --changed
```

- A mutant is killed when the tests fail. A surviving mutant means the tests do not constrain that behavior.
- Exit code `0`: every executed mutant was killed. Gate passed.
- Exit code `2`: the baseline tests failed. Fix the tests first.
- Exit code `3`: a mutant survived. Add or strengthen a test, then rerun.
- Use `--test-command "pytest -q"` or the project's own test command when auto-detection is wrong.
- Output is written under `.metrics/mutate/`.

## Unsupported projects

If a project's language is not supported by these tools, do not skip the gate silently. Record the reason in the final report and run the nearest project-native equivalents:

- complexity: lint or cyclomatic-complexity tool;
- coverage: the project's coverage command;
- duplication: the project's duplicate-code detector;
- mutation: the project's mutation-testing tool, or a written explanation of why mutation testing is not feasible.

`uml-viewer` (https://github.com/unclebob/uml-viewer) can visualize the `.metrics` snapshots, but it is optional.
