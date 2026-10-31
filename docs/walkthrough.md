# Walkthrough in ordinary language

The program answers four questions: can the file be interpreted reliably, which records pass the agreed checks, which need correction, and can someone explain the result? It first copies the source bytes, then checks headings and reads records, normalizes approved equivalents, resolves identical duplicates, and writes approved output plus correction/status reports. Only after writing completes does it create a final marker.

In valid.csv and renamed_report.csv, all three records pass and the normalized outputs match the predefined expected CSV. In bad_values.csv, F001 and F004 pass and are released; the missing-ID record and invalid-date record need correction. F004 retains UNKNOWN permission and an ACCEPTED_WITH_WARNING status. Ingestion acceptance is not marketing eligibility.

A missing required heading or malformed CSV blocks the entire input, because its meaning or completeness is uncertain. Even records parsed successfully before a late structural failure are not released. A valid file with independent row errors produces READY_WITH_EXCEPTIONS and the valid selection. If no valid records remain, the outcome is BLOCKED and no cleaned CSV exists. Source bytes and diagnostics remain available.

## Code structure

| Function | Responsibility |
| --- | --- |
| load_mapping | Read approved heading or permission equivalents from CSV. |
| normalize | Apply required-value, date, whitespace and permission rules. |
| process_file | Preserve input, check the contract, compare records grouped by customer ID, assign statuses and coordinate output. |
| write_csv | Write consistent CSV files. |

The receiving/approved/correction decisions are the same locally and in the proposed cloud architecture: preserve raw bytes, validate, then load classified results into ADW. Local files simulate storage boundaries; cloud loading, access enforcement, source correction and campaigns remain proposed. Partial updates must not cause missing records to be deleted from the destination.

## Five mechanisms to explain

1. **Approved headings:** `load_mapping()` reads the CSV configuration. `process_file()` matches normalized header names rather than column positions. Missing required fields or multiple headings mapped to one field block release. An unfamiliar extra field warns.
2. **Normalization:** `normalize()` trims whitespace, checks required values and real ISO dates, and maps approved permission equivalents. An empty purchase date is allowed. Unknown permission remains UNKNOWN; this does not authorize marketing.
3. **Same-ID grouping:** records sharing a customer ID are compared after normalization. Identical valid copies are retained once. Different attributes, or an invalid record within a repeated-ID group, withhold the group. This signals inconsistent records, not proven conflicting identities. There is no authoritative-source or recency resolver.
4. **Input-wide failure:** parsing must finish reliably before release. A late structural error blocks even valid-looking earlier candidates because the file cannot be interpreted completely.
5. **Completion marker:** reports and any approved CSV are written before the final marker. Consumers must require READY or READY_WITH_EXCEPTIONS. Finding cleaned.csv is insufficient if writing failed before completion. The marker does not establish database transaction success.

## A mapping-only change executed through Codex

Run from the repository root:

```sh
python3 tools/mapping_walkthrough.py
```

The script uses a temporary workspace and changes only the first heading in the valid sample to `customerdata_id`. Expected and verified outcomes:

- Before an approved mapping: BLOCKED, with no cleaned.csv.
- After assumed source-owner confirmation and a temporary alias: READY, with three released records.
- The released CSV exactly matches the original valid export. The processor and repository mappings remain unchanged.

The exercise was executed through Codex and its assertions passed. Source-owner confirmation is an exercise assumption. A real change requires confirmation of the identifier’s meaning, values and uniqueness; spelling similarity is insufficient.

## One actual AI correction

The production diagram and narrative previously described a different release policy from the local code. Stefan challenged the inconsistency and directed alignment across code, diagrams, tests and documentation. Revised outcomes were checked. The lesson is to compare artifacts against one agreed policy rather than accept individually plausible AI outputs.

## Production questions this does not solve

Partial release is conditional: complete snapshot replacement or a consistency-sensitive transaction may require all-or-nothing processing. The destination must define what happens to yesterday's approved record if today's update fails, and prevent an older correction from overwriting a newer update. Stale permission must not automatically remain usable for marketing. The file processor does not implement these controls.

## Questions to rehearse

- Why can an unused extra column be ignored while an unfamiliar required ID heading blocks release?
- Why do bad dates affect individual records, while a broken CSV structure blocks all approval?
- What do READY, READY_WITH_EXCEPTIONS and BLOCKED mean?
- How do received.csv, record_status.csv and cleaned.csv correspond to the raw archive and proposed ADW selections?
- Why do NO and UNKNOWN remain distinct, and what further checks does a campaign require?
- Who corrects source facts, who maintains mappings, and how is a corrected export reconciled?
- Why does the destination need an agreed partial-update contract?
- What happens if a file exists but its completion marker does not?

Use these questions to prepare a walkthrough of the decisions and observed outputs. Validate new integration changes in Development/Test before reviewed Production promotion.
