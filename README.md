# Reliable CRM CSV ingestion

[Code and files](https://github.com/swihpi/Assesment) · [Automated validation](https://github.com/swihpi/Assesment/actions/workflows/validate.yml)

A standalone Python program reads a CRM export, normalizes approved equivalents, reports bad records, and releases a cleaned file only when the selected checks pass.

The main script is **160 lines**, uses Python's standard library, and is intended to be easy to review. The hypothetical customer is a sports organisation preparing profile data for later analytics. [Customer note](docs/customer_note.md). [Assessment narrative](docs/assessment.md).

## Run in Development or Test

I direct Codex to execute these checks in the local Development/Test workspace and review the results. The commands below also support direct reproduction by another engineer.

Use Python 3.12 or 3.14; both have been verified in clean local environments. No third-party packages, credentials, database, or cloud connection are required to run the processor. Git is needed only for the clone step; downloading and extracting the repository ZIP is an alternative.

Clone the repository, enter its folder, and check that Python is available:

```sh
git clone https://github.com/swihpi/Assesment.git
cd Assesment
python3 --version
```

From the repository root, run the examples and tests:

```sh
python3 process_export.py --input samples/valid.csv --output runs/dev-valid
python3 process_export.py --input samples/renamed_report.csv --output runs/dev-renamed
python3 process_export.py --input samples/bad_values.csv --output runs/dev-held
python3 -m unittest discover -s tests -v
```

The first two runs produce the same three normalized records. The bad-value example deliberately returns HELD and **exit code 2**; no cleaned file is released. This is the expected rejection outcome, not a crash. Run the commands on separate lines as shown: chaining them with `&&` stops at that expected non-zero result, so the test command would not run. Every example needs a fresh output folder. Existing output is never overwritten.

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

**Demonstration choice:** standalone Python makes the selected validation behavior locally reproducible without Oracle platform access.

**Production recommendation:** first assess whether native Oracle Integration Cloud mappings and controls meet the validation, duplicate-handling, and diagnostic requirements. Use a separately hosted Python function where those requirements justify it.

The scenario assumes no usable CRM API or supported application-specific connector is available, including through Oracle Integration Cloud. The CRM supports a scheduled daily CSV report and native delivery to a customer-controlled SFTP location. Oracle Integration Cloud retrieves the completed export using its FTP Adapter configured for SFTP.

The diagram shows the proposed Python option: Oracle Integration Cloud invokes a separately hosted Python function through its OCI Function action and routes approved data to Autonomous Database/ADW. The database receives approved data; it does not pull the export from the CRM. The command-line script is not an embedded Oracle Integration Cloud Python library. Its rules could be reused, but a handler, cloud input/output interface, access configuration, and deployed integration still need implementation and testing. The cloud flow remains a proposal.

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

I originated and championed the sports sentiment initiative within Oracle, helped bring colleagues together, contributed to the Oracle Integration Cloud / Autonomous Data Warehouse / Oracle Analytics Cloud architecture, created dashboards, and developed the broader idea of combining customer sources for useful audience information. I supplied this experience, directed the assessment iterations, challenged unnecessary complexity, and reviewed Codex results.

Codex assisted with the hypothetical CRM incident, detailed rules, fixtures and expected outcomes created before implementation, code/tests, documentation, research, and execution. A supplied Claude critique informed my review. I chose Codex to work with files, code, and actual execution results in one workspace. I deliberately kept an LLM out of the running processor: explicit rules make known transformations repeatable, while unfamiliar meanings require human confirmation.

The implementation is available in the public [Assesment repository](https://github.com/swihpi/Assesment).

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
| Repository URL | [Assesment](https://github.com/swihpi/Assesment) (public). |
| Safe delivery | Development/Test first, then reviewed Production promotion. |
