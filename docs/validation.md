# Validation evidence

31 October 2026. Local Development/Test execution uses synthetic inputs; no customer or Production system is involved. Candidate-independent rehearsal remains separate from automated checks.

## Correctness and recovery boundaries

The 60-test suite verifies exact normalized output, heading drift, missing/invalid values, explicit NO versus UNKNOWN, duplicates, input preservation, source-record status, malformed CSV, encoding, reruns, CLI exit codes and report/completion-marker failures. It includes a generated 10,000-record case with 800 missing IDs: all received bytes are retained, exactly the 9,200 expected valid IDs are released, and exactly 800 statuses require correction. A late structural error blocks every approval, even after a valid record was parsed. The customerdata_id example is blocked until its explicit alias is provided.

Version 1.1.0 adds tests for mapping headers and malformed configuration, Unicode equivalents and exact customer IDs, physical line ranges, provenance hashes and UTC timestamps, distinct exit codes, debug tracebacks, best-effort operational error logs, semicolon delimiters and a decode failure after a valid prefix. All 60 tests passed locally on Python 3.14.4 before publication. GitHub Actions separately verifies Python 3.12 and 3.14.

The original fixture values predated the original processor. The reviewed release expectations explicitly state approved IDs and independent counts. Tests and sample outputs check the documented current policy.

```sh
python3 -m unittest discover -s tests -v
```

## Reproduction examples

- valid.csv: READY; three approved records matching the predefined CSV.
- renamed_report.csv: READY; the same three approved records.
- bad_values.csv: READY_WITH_EXCEPTIONS; F001 and F004 approved, two correction cases, source copy unchanged.
- breaking_change.csv: BLOCKED; no approved output, diagnostics and received copy retained.

Python 3.12 and 3.14 are the verification targets, locally and in GitHub's Linux workflow. The full outputs in examples/ show a successful run, a run with exceptions and a blocked run. Consumers require the corresponding success marker before using cleaned.csv.

## Measurements and limitations

Single local runs of processor version 1.1.0 measured 1,000 records in 0.051 seconds and 100,000 in 0.595 seconds, with output counts independently verified. Python 3.14.4 on macOS 26.6.2 ARM64. The timer includes startup, snapshot copying, processing and report writing; generation and independent output counting are outside it. The raw measurements record the processor SHA-256 and UTC timestamp. Memory grows with retained records; these measurements do not establish Production/cloud capacity or a supported memory ceiling. [Raw results](benchmark.csv).

The current execution is recorded in [the 60-test log](evidence/codex-run-current.txt). Earlier logs and screenshots remain available in Git history rather than being duplicated in the current source tree.

No OIC/OCI Function handler, ADW connection, approved-view access control, campaign filter, exception delivery or correction workflow has been deployed. Automated checks establish only the local processor's behavior. New cloud work must be validated in Development/Test before reviewed Production promotion.
