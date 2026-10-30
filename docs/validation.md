# Validation evidence

30 October 2026. Checks executed by the assistant in the local development workspace with synthetic data. No Production system or live customer dataset was used. Candidate review and independent rehearsal remain outstanding.

## Behavior checks

```sh
python3 -m unittest discover -s tests -v
```

**19 tests passed** for the 160-line processor. Tests cover approved mappings/reordering, additional/missing columns, invalid values, permission uncertainty, duplicate handling, malformed CSV, encoding/BOM, multiline records, reruns, configuration changes, CLI outcomes, and report-write failure without a completed marker.

Examples in `examples/ready` and `examples/held` show the recorded outputs. The held case has no cleaned CSV. Predefined expected output remains in `samples/expected`.

## Measured local runs

```sh
python3 tools/benchmark.py --sizes 1000 100000 --output runs/benchmark.csv
```

| Input records | Verified output | Wall seconds |
| ---: | ---: | ---: |
| 1,000 | 1,000 | 0.037468 |
| 100,000 | 100,000 | 0.393321 |

Raw results are in `benchmark.csv`. The timer covers process startup and the processor, including reports. Generation and independent output counting are outside it. Environment: Python 3.14.4, macOS 26.6.2 ARM64. Single runs, with no memory profiling or cold-cache control. Memory grows with retained records. No production or cloud capacity claim is made.

## Reproducibility and environment limits

A clean Git export was verified with Python 3.12.14, independently of the working folder. The valid and renamed samples returned READY (exit 0), matched the predefined three-record output, and wrote READY markers. The bad-value sample returned HELD (exit 2) with no cleaned CSV. All 19 tests also passed in that clean export. No cloud OIC flow, OCI Function handler, connector, database load, or Production configuration has been deployed or tested.

The documented promotion policy is Development/Test validation first, followed by reviewed promotion to Production. The standalone local checks establish only the implemented file-processing behavior.
