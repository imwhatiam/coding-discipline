---
name: coding-discipline
description: 'Lightweight coding discipline for AI coding agents: surface assumptions before coding, keep changes small and surgical, write failing tests first, verify outcomes, and run the mandatory quality gates. Use when writing, reviewing, refactoring, or debugging non-trivial code. Do not use for trivial one-line edits, formatting-only changes, or pure explanation.'
license: MIT
metadata:
  version: 1.0.0
  repository: https://github.com/imwhatiam/coding-discipline
---

# Coding Discipline

A lightweight discipline for any code change. It biases toward caution over speed; use judgment for trivial tasks.

**Priority:** the user's request and the project's own instructions override this skill. If they conflict, follow the project and say so.

## Before You Code

### Surface assumptions

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### Get the foundation right

- Get the data shape right before you write the logic.
- Do first whatever helps every later phase.
- If a concurrent writer would matter, do not share state.
- Do not bolt a new requirement onto the old design.
- Ask what you would have built if it had been there from the start, think that through, and deliver it in pieces.

### Attack the premise

- When two fixes that share one premise fail the same gate, write that premise in one sentence and count which actors hold the imbalance.
- Remove the assignment.
- Do not start another fix until you have done that.

## While You Code

### Keep it small

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.
- One decision lives in one place.
- Ship the smallest edit that solves the problem.
- Take complexity out before you add anything.

### Make surgical changes

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

### Write the test first

- Write the failing test before you change the code.
- See it fail for the reason you expect.
- Make the smallest change that makes it pass.
- If an honest test is impractical, do not write a bad one.

### Test behavior, not implementation

- The test calls the code the way its user does and checks the result that user would see.
- If the test would still pass when every function returned nothing, throw it out.

### Architecture

- Put the domain in a structure that makes the illegal states impossible.
- Maintain a glossary of domain terms.
- If the code is already clear and local, leave it.
- Check the data where it enters.
- Inside, trust it.
- Keep the business logic in a pure function.
- Make the illegal value impossible to write.
- Parse outside data once, where it comes in.
- Do not silence the compiler.
- Running it twice, or running it after a crash halfway through, ends in the same state.
- If they do not need the same mutable thing, give each its own.
- If they do, allow one writer, and enforce that in the structure.

### Build the lever

- If the work is not obvious at a glance, build the tool that does it.
- Do one unit by hand, then make the tool match that unit.

## Before You Finish

### Fix the root cause

- Reproduce it.
- Fix the cause.
- A guard that only hides the crash is not a fix.

### Sequence the work

- Finish one small unit and check it.
- Then start the next.

### Refactor without changing behavior

- Pin what the code does.
- Change the structure.
- Prove the behavior did not change.

### Define done

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"
- Aim at the end state you can check.
- A break in the middle is allowed when you planned it and can undo it.

For multi-step work, state a brief plan in this form:

```text
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

## Quality Gates (Mandatory)

Run these gates before calling the work done. If a gate tool does not support the project's language, record the reason and run the nearest project-native equivalent for complexity, coverage, duplication, and mutation; never skip silently.

See `references/quality-gates.md` for installation and command details.

### Crapper — complexity and coverage

- Use the crapper tool
- Reduce each function under  CRAP 10 by splitting it, by testing it, or both.
- Consider whether case statements are worth reducing.
- Keep every function under CRAP 10; use `--threshold 10` for supported projects.

### Dryer — duplication

- Use the dryer tool to eliminate duplication that rank 0.8 or above.
- Use `--threshold 0.8` so the tool matches the 0.8 rule below.

### Mutator — mutation testing

- Use the mutator tool
- Cover the uncovered.
- Kill the survivors.
- Delete dead code.
- A run must exit 0: every executed mutant killed. Exit 2 means the baseline tests failed; exit 3 means a mutant survived.

## Practice

### Keep a log

- Keep a log of every action you take and the reason you took it.
- Report that log upon completion.

### Guard the context window

- Keep the main thread small.
- Send the bulk elsewhere, and keep the summary.

### Clean up the worktree

- Find what is safe to remove, confirm nothing still in use needs it, then reclaim the disk.
- Uncommitted work waits for a decision.

### Commit and push

- Commit or push only when the user explicitly asks; a change request is not authorization.
- When asked, use small ordered commits; each says why, what changed, and how you proved it; push only if asked.
- Otherwise leave the changes in the working tree and report them.

**These guidelines are working if:** diffs contain fewer unnecessary changes, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
