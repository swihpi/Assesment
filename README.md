# Reliable CRM CSV ingestion

[Code and files](https://github.com/swihpi/Assesment) · [Automated validation](https://github.com/swihpi/Assesment/actions/workflows/validate.yml)

A standalone Python program reads a CRM export, normalizes approved equivalents, reports bad records, and releases a cleaned file only when the selected checks pass.

The main script is **160 lines**, uses Python's standard library, and is intended to be easy to review. The hypothetical customer is a sports organisation preparing profile data for later analytics. [Customer note](docs/customer_note.md). [Assessment narrative](docs/assessment.md).

## Run in Development or Test

Stefan directs Codex to execute these checks in the local Development/Test workspace and reviews the results. The commands below also support direct reproduction by another engineer.

Use Python 3; the verified runtime is Python 3.14.4. No packages, credentials, database, or cloud connection are required. From this folder:

```sh
python3 process_export.py --input samples/valid.csv --output runs/dev-valid
python3 process_export.py --input samples/renamed_report.csv --output runs/dev-renamed
python3 process_export.py --input samples/bad_values.csv --output runs/dev-held
python3 -m unittest discover -s tests -v
```

The first two runs produce the same three normalized records. The bad-value report returns HELD and exit code 2; no cleaned file is released. Every run needs a fresh folder. Existing output is never overwritten.

**Never test a new script or mapping in Production first.** Use synthetic examples locally, then validate the deployed integration in a dedicated Development or Test environment. Promote the reviewed artifacts to Production only after that validation. [Deployment and promotion approach](docs/deployment.md).

## Input and rules

All six headings must exist:

| Field | Rule |
| --- | --- |
| `customer_id` | Required ID; preserve leading zeroes. |
| `name` | Required; tidy whitespace. |
| `region` | Required; tidy whitespace without inventing geography. |
| `member_since` | Required real date in `YYYY-MM-DD`. |
| `last_purchase_date` | Same date format or empty. |
| `marketing_permission` | Approved values become YES/NO; missing or unfamiliar values stay UNKNOWN with a warning. |

The two readable CSV files under `config/` contain heading aliases and permission values.

- Approved renamed/reordered headings work; an extra unused column warns.
- Missing or ambiguous required headings hold the file.
- Invalid required values or dates reject the record.
- Identical normalized duplicates become one, with a warning.
- Conflicting records for one ID are rejected; no winner is guessed.
- Any rejection holds the batch. There is no adjustable rejection threshold.

Unknown permission remains UNKNOWN. READY does not establish marketing eligibility or the truth of source attributes.

![Validation and release](docs/diagrams/validation.svg)

## Outputs and errors

`cleaned.csv` exists only for READY. `rejected.csv` identifies the record, field, problem, and next action. `warnings.csv` reports unused columns, unknown permission, and removed duplicates. `summary.txt` and `run.log` provide counts, duration, and status.

A READY or HELD marker is written last. Consumers must require READY. No marker means incomplete output. The source remains unchanged.

For fully parsed input:

```text
parsed records = valid records + rejected records + identical duplicates removed
```

Malformed CSV or invalid encoding holds the batch and marks parsing incomplete. Partial counts are not represented as complete source counts.

Exit codes: 0 = READY; 2 = HELD; 1 = operational/configuration failure. Invalid command syntax also uses the parser's exit code 2; read the message and run marker.

## Programmatic customer deployment

![Proposed CRM-to-staging handoff](docs/diagrams/deployment.svg)

The scenario assumes no usable CRM API or supported application-specific connector is available, including through OIC. The CRM does support a scheduled daily CSV report and native delivery to a customer-controlled SFTP location. OIC retrieves the completed export with its FTP Adapter configured for SFTP, then invokes a separately hosted Python function through its OCI Function action. Autonomous Database/ADW receives approved data; it does not pull the export from the CRM. The command-line script is not an embedded OIC Python library. Its rules could be reused, but a handler, request/response interface, access configuration, and deployed integration still need implementation and testing.

Basic transformations can also be configured in OIC. Python makes this selected slice locally reproducible without platform access. The cloud path is a documented architecture proposal, not a claimed deployment.

## Verification

**19 tests passed** after simplification. Cases cover predefined output, additive/breaking changes, aliases/reordering, dates, unknown permission, duplicates, malformed files, encoding, reruns, and incomplete publication. [Expected outcomes](samples/expected_outcomes.md). [Validation evidence](docs/validation.md).

```sh
python3 tools/benchmark.py --sizes 1000 100000 --output runs/benchmark.csv
```

Single local measurements: 1,000 records in 0.037 seconds; 100,000 in 0.393 seconds, with output counts verified. Python 3.14.4 on macOS 26.6.2 ARM64. The timer includes process startup and report writing. Input generation and independent output counting are outside it.

Records are retained for duplicate checks, so memory grows with the file. No production/cloud throughput or constant-memory claim is made.

## Trade-offs, AI use, and remaining work

This is the local file-to-file slice. It has no live extraction, schedule, database load, freshness check, source-change lock, exactly-once delivery, sentiment model, or campaign action. The caller supplies a completed, stable export. Repeated processing uses a new folder rather than appending to previous results.

Explicit dates avoid ambiguous guessing. Standard CSV parsing handles quoting and UTF-8 BOM; unsupported encoding holds the file. Mappings are reviewed data rather than inferred meanings.

Stefan originated and championed the sports sentiment initiative within Oracle, helped bring colleagues together, contributed to the OIC/ADW/OAC architecture, created dashboards, and developed the broader idea of combining customer sources for useful audience information. He supplied this experience, directed the assessment iterations, challenged unnecessary complexity, and reviewed Codex results. Codex assisted with the hypothetical CRM incident, detailed rules, fixtures and expected outcomes created before implementation, code/tests, documentation, research, and execution. A supplied Claude critique informed the review. Codex was chosen to work with files, code, and actual execution results in one workspace. No runtime LLM is used: explicit rules make known transformations repeatable; unfamiliar meanings require human confirmation.

The implementation is available in the private [Assesment repository](https://github.com/swihpi/Assesment). Reviewers need repository access.

The accompanying presentation provides historical screenshots. This repository contains the runnable implementation and vector flow diagrams; the original slide images are not included.

## Assignment coverage

| Matter | Evidence / status |
| --- | --- |
| Customer context and assumptions | Customer note and assessment narrative. |
| Runnable ingestion/normalization | Standalone processor and synthetic fixtures. |
| Drift, bad data, actionable errors | Explicit mappings, warnings, rejections, READY/HELD. |
| Setup/run instructions | Commands above and fresh-export check. |
| Architecture, trade-offs, limits | README and deployment note. |
| Tests and reliability | 19 passing checks and predefined expected output. |
| Logging and scalability mindset | Counts, status, markers, measured runs, memory limitation. |
| AI disclosure | Candidate and Codex contributions, with explicit runtime rules. |
| Repository URL | [Assesment](https://github.com/swihpi/Assesment) (private; reviewer access required). |
| Safe delivery | Development/Test first, then reviewed Production promotion. |
