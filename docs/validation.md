# Validation evidence

The automated checks use dummy data in local Development/Test environments. They verify the local file processor, not the proposed cloud connections or campaign controls.

## Run the checks

```sh
python3 -m unittest discover -s tests -v
```

The suite checks expected customer IDs and counts, approved heading changes, required fields and dates, permission values, repeated records, malformed files, configuration errors and output-write failures. It also checks that the input is preserved and that incomplete processing does not release usable output. The GitHub workflow runs on Python 3.12 and 3.14.

## Expected results

| Input | Expected outcome |
| --- | --- |
| `samples/valid.csv` | Three approved records. |
| `samples/renamed_report.csv` | The same three approved records. |
| `samples/bad_values.csv` | F001 and F004 approved; two records reported for correction. |
| `samples/breaking_change.csv` | BLOCKED; no cleaned CSV. |

For field-level expectations, see [expected outcomes](../samples/expected_outcomes.md). Recorded execution is available in the [test log](evidence/codex-run-current.txt).

## Larger case

```sh
python3 tools/large_case_demo.py --output runs/demo-10000
```

This generates 10,000 records, deliberately including 800 missing IDs, and runs the same processor. Independent checks verify the exact 9,200 approved IDs, 800 correction cases and unchanged received file. The command retains its input and outputs; use a new output folder for each run. See the [recorded execution](evidence/large-case-current.txt).

These checks establish behaviour for the supplied scenarios. They do not prove that source facts are correct or that an OIC/ADW deployment works. Benchmark methodology and capacity limits are described in the README.
