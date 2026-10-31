# Execution evidence

- [Current execution log](codex-run-current.txt): genuine local version 1.1.0 execution, 60 passing tests and four sample runs; identifies the code commit and runtime.
- [Retained 10,000-record execution](large-case-current.txt): actual processor run plus independently checked counts; generated files can be retained locally with `tools/large_case_demo.py`.
- [Full correction report](../../examples/with-exceptions/rejected.csv): actual current bad-value sample output, including physical source-line ranges.
- [Validation summary](../validation.md): test coverage, reproduction instructions and limits.

The three complete output sets are in [examples](../../examples/). Earlier logs and screenshots remain in Git history. The narrative preserves the review milestones without duplicating superseded artifacts in the current branch. Python 3.12 and 3.14 checks are also recorded in GitHub Actions.
