# Execution evidence

- `codex-run-current.txt`: genuine local version 1.1.0 execution, 60 passing tests and four sample runs; identifies the code commit and runtime.
- `../test-run.txt`: the same current execution for the existing reproduction link.
- `codex-run-24-tests-20261031.txt`: preserved earlier 24-test execution, including its original commit and exit codes.
- `test-run-24-tests-20261030.txt`: preserved earlier local 24-test output.
- `codex-validation-current.png`: historical screenshot from the earlier 24-test stage; retained unchanged, not evidence of the current 60-test suite.
- `actionable-errors.csv`: actual correction output from the current bad-value sample, including physical source-line ranges.

Historical evidence is not rewritten to imply it came from a newer version. Current Python 3.12 and 3.14 checks are also recorded in GitHub Actions.
