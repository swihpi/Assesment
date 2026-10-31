# Validation evidence

30 October 2026. Local Development/Test execution uses synthetic inputs; no customer or Production system is involved. Candidate-independent rehearsal remains separate from automated checks.

## Correctness and recovery boundaries

The 24-test suite verifies exact normalized output, heading drift, missing/invalid values, explicit NO versus UNKNOWN, duplicates, input preservation, source-record status, malformed CSV, encoding, reruns, CLI exit codes and report/completion-marker failures. It includes a generated 10,000-record case with 800 missing IDs: all received bytes are retained, exactly the 9,200 expected valid IDs are released, and exactly 800 statuses require correction. A late structural error blocks every approval, even after a valid record was parsed. The customerdata_id example is blocked until its explicit alias is provided.

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

Single local Python 3.14.4 measurements on macOS 26.6.2 ARM64: 1,000 records in 0.038596 seconds; 100,000 in 0.517292 seconds. Counts were independently checked. Startup, snapshot copying, processing and reports are timed; input generation and independent output counting are not. Raw results are in benchmark.csv. Memory grows with retained records/statuses; no Production capacity, constant-memory, cloud-performance or peak-memory claim is made.

No OIC/OCI Function handler, ADW connection, approved-view access control, campaign filter, exception delivery or correction workflow has been deployed. Automated checks establish only the local processor's behavior. New cloud work must be validated in Development/Test before reviewed Production promotion.
