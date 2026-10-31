# Explicit expected outcomes

These are synthetic assumptions, not policies supplied by a real customer. The original sample files and expected normalized values predated the original processor. Following review of the release policy, these expectations now specify record-level release and whole-input blocking separately. Tests compare outputs against these values and independently generated counts.

## Rules

Preserve the received bytes and original source. Recognise headings through the approved alias CSV; allow reordering and report unused extra columns. Missing or ambiguous required headings, malformed CSV, invalid encoding, or an empty input block approval. A partial parse never releases its apparently valid prefix.

For fully parsed input, release valid records and report required-value failures or conflicting records for the same customer ID as correction cases. Remove identical normalized duplicates once, with a warning. Preserve leading zeroes, real ISO dates, optional empty purchase dates, and YES/NO/UNKNOWN permission meanings. No error-rate threshold overrides identity or permission rules.

| Fixture | Expected result |
| --- | --- |
| `valid.csv` | READY: three approved records, exactly matching `expected/cleaned_valid.csv`. |
| `renamed_report.csv` | READY: the same three approved records despite aliases, order and whitespace. |
| `extra_column.csv` | READY: one approved record; unused `loyalty_points` warning. |
| `bad_values.csv` | READY_WITH_EXCEPTIONS: four parsed, two approved (F001 and F004), two correction cases (missing ID and invalid date). F004 retains UNKNOWN permission. |
| `duplicates.csv` | READY_WITH_EXCEPTIONS: four parsed, one approved F001, one identical duplicate ignored, two conflicting F002 records requiring correction. |
| `breaking_change.csv` | BLOCKED: no approved output; `supporter_number` lacks an approved alias for the required customer ID heading. |
| `unknown_permission.csv` | READY: two approved records with UNKNOWN permission and warnings. |
| `malformed.csv` | BLOCKED: no approved output; received bytes and diagnostics remain. Complete record totals cannot be asserted. |

Each completed run has received.csv, diagnostic reports, record_status.csv and its final completion marker. cleaned.csv exists only for READY or READY_WITH_EXCEPTIONS. No completion marker means no completed result.

The 10,000-record test generates 800 missing-ID rows and 9,200 valid unique IDs. Expected result: exact received-byte preservation; 9,200 approved IDs matching the independent expected set; 800 NEEDS_CORRECTION statuses; 10,000 status rows; READY_WITH_EXCEPTIONS. It does not assume duplicates or overlapping error categories.

A separate test renames the heading to customerdata_id. It is BLOCKED before source-approved configuration is supplied and READY after the explicit alias is added. Tests also verify NO/UNKNOWN remain distinct and a late structure error prevents release of earlier valid rows.

Passing ingestion does not verify the truth of every source attribute or authorise marketing. Campaign checks are outside the processor.
