# Expected outcomes established before implementation

These are proposed demonstration rules, not incidents or policies supplied by a real customer. The synthetic fixtures were written before the processor. Their expected values are explicit so the code can be checked against something other than itself.

## Small set of rules

- Recognise column names through the readable alias table in `config/column_aliases.csv`.
- Allow reordered columns. Warn about extra unused columns. Hold a file if an expected column is absent or two columns mean the same output field.
- Trim surrounding whitespace. Collapse repeated spaces in names and region labels. Preserve identifiers, including leading zeroes, and preserve region meaning rather than invent a geographical mapping.
- Require customer ID, name, region, and customer-since date. Last-purchase date may be empty.
- Accept real calendar dates in the documented `YYYY-MM-DD` format. Reject ambiguous alternatives rather than guess.
- Map recognised permission values through `config/permission_values.csv`. Missing or unfamiliar permission becomes `UNKNOWN` with a warning; it never becomes `YES`.
- Treat identical normalized records for one customer ID as duplicates: retain one and warn.
- If records for one ID disagree, reject all records for that ID and hold the batch. An ID on an otherwise invalid row still participates in conflict detection.
- Any rejected record holds the batch. This deliberately simple snapshot policy has no adjustable rejection threshold. Identical duplicates are counted separately; conflicting IDs and broken file structure hold the batch.
- A held batch has no `cleaned.csv`. Review diagnostics are still written. The source remains unchanged.

## Hand-specified expectations

| Fixture | Expected result under the default policy |
| --- | --- |
| `valid.csv` | READY: 3 records accepted; 0 rejected; values match `expected/cleaned_valid.csv`. |
| `renamed_report.csv` | READY: same cleaned records as `valid.csv`, despite aliases, order, whitespace, and value forms. |
| `extra_column.csv` | READY: 1 accepted, warning about `loyalty_points`; no such column in output. |
| `bad_values.csv` | HELD: 4 parsed; 2 accepted candidates; 2 rejected. Missing customer ID and impossible date explain the rejections. F004 has `UNKNOWN` permission and a warning. No cleaned output is released. |
| `duplicates.csv` | HELD: 4 parsed; 1 accepted candidate; 1 identical duplicate removed; 2 conflicting rows rejected. No cleaned output is released. |
| `breaking_change.csv` | HELD before processing records: `supporter_number` is not an approved alias and `customer_id` is missing. |
| `unknown_permission.csv` | READY: 2 accepted records, both with `UNKNOWN` permission and a warning each. |
| `malformed.csv` | HELD: malformed quoted CSV; complete record totals cannot be asserted. |

`READY` means the file passed this normalization contract and release policy. It does not mean the customers are eligible for marketing, identity has been independently verified, or a campaign is authorised.
