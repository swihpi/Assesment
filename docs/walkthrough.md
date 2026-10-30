# Walkthrough in ordinary language

The program answers four questions: can the file be interpreted reliably, which records pass the agreed checks, which need correction, and can someone explain the result? It first copies the source bytes, then checks headings and reads records, normalizes approved equivalents, resolves identical duplicates, and writes approved output plus correction/status reports. Only after writing completes does it create a final marker.

In valid.csv and renamed_report.csv, all three records pass and the normalized outputs match the predefined expected CSV. In bad_values.csv, F001 and F004 pass and are released; the missing-ID record and invalid-date record need correction. F004 retains UNKNOWN permission and an ACCEPTED_WITH_WARNING status. Ingestion acceptance is not marketing eligibility.

A missing required heading or malformed CSV blocks the entire input, because its meaning or completeness is uncertain. Even records parsed successfully before a late structural failure are not released. A valid file with independent row errors produces READY_WITH_EXCEPTIONS and the valid selection. If no valid records remain, the outcome is BLOCKED and no cleaned CSV exists. Source bytes and diagnostics remain available.

## Code structure

| Function | Responsibility |
| --- | --- |
| load_mapping | Read approved heading or permission equivalents from CSV. |
| normalize | Apply required-value, date, whitespace and permission rules. |
| process_file | Preserve input, check the contract, compare identities, assign statuses and coordinate output. |
| write_csv | Write consistent CSV files. |

The receiving/approved/correction decisions are the same locally and in the proposed ADW architecture. Local files simulate storage boundaries; cloud loading, access enforcement, source correction and campaigns remain proposed. Partial updates must not cause missing records to be deleted from the destination.

## Questions to rehearse

- Why can an unused extra column be ignored while an unfamiliar required ID heading blocks release?
- Why do bad dates affect individual records, while a broken CSV structure blocks all approval?
- What do READY, READY_WITH_EXCEPTIONS and BLOCKED mean?
- How do received.csv, record_status.csv and cleaned.csv correspond to the proposed ADW areas?
- Why do NO and UNKNOWN remain distinct, and what further checks does a campaign require?
- Who corrects source facts, who maintains mappings, and how is a corrected export reconciled?
- Why does the destination need an agreed partial-update contract?
- What happens if a file exists but its completion marker does not?

These are prompts for understanding, not evidence of completed independent rehearsal. Stefan directs Codex to execute examples and tests and reviews the results. All new integration changes are exercised in Development/Test before reviewed Production promotion.
