# How the processor works

Read this alongside `process_export.py`. Setup, commands and expected outputs are in the README.

## Code structure

| Function | Responsibility |
| --- | --- |
| load_mapping | Validate the mapping header, row shape, keys and allowed target values before accepting equivalents. |
| normalize | Apply required-value, date, whitespace and permission rules. |
| process_file | Establish run provenance and log operational failures when possible. |
| _process_file | Preserve input, check the contract, compare records grouped by customer ID, assign statuses and coordinate output. |
| write_csv | Write consistent CSV files. |

## Main processing steps

1. **Approved headings:** `load_mapping()` reads the CSV configuration. `_process_file()` matches normalized header names rather than column positions. Missing required fields or multiple headings mapped to one field block release. An unfamiliar extra field warns.
2. **Normalization:** `normalize()` trims whitespace, checks required values and real ISO dates, and maps approved permission equivalents. An empty purchase date is allowed. Unknown permission remains UNKNOWN; this does not authorize marketing.
3. **Same-ID grouping:** records sharing a customer ID in the delivered CSV are compared after normalization. Identical valid copies are retained once. Different normalized attributes withhold the group as a conflict. Identical invalid copies are each rejected for their field errors. Conflict reports also retain any field errors. This signals inconsistent export rows, not two customers in the CRM. The source owner must check what went wrong and confirm the correct values; the processor does not choose a row from the information supplied.
4. **Input-wide failure:** parsing must finish reliably before release. A late structural error blocks even valid-looking earlier candidates because the file cannot be interpreted completely.
5. **Completion marker:** reports and any approved CSV are written before the final marker. Consumers must require READY or READY_WITH_EXCEPTIONS. Finding cleaned.csv is insufficient if writing failed before completion. The marker does not establish database transaction success.
