# Walkthrough in ordinary language

Start with `samples/valid.csv` and its expected cleaned version. The file describes three fictional people, using familiar customer fields. There is no database to administer.

## The five questions the program answers

1. **Do these headings mean what we expect?** The alias CSV lists approved equivalents. Reordering is fine. A harmless extra column is reported. A missing ID column stops the batch.
2. **Can the values be represented consistently?** Names have whitespace tidied, dates must be real ISO dates, and approved permission values become YES or NO. Unknown permission stays UNKNOWN.
3. **Does one ID describe more than one profile?** Identical normalized copies become one record. Conflicting copies are all rejected; the program cannot decide which is true.
4. **Can this batch be released under the chosen rule?** Any rejected record holds the batch. This conservative snapshot policy is deliberately fixed and simple to explain.
5. **Can someone explain the outcome?** The summary, rejected records, warnings, and log show what happened. A READY marker is written only after output writing finishes.

## Follow one successful record

In `renamed_report.csv`, F001 has an ID with surrounding whitespace, the name `Alex   Morgan`, and permission `y`. The configured headings identify the right fields. The result is F001, `Alex Morgan`, and `YES`. Its dates keep their meaning. Compare the actual result with `samples/expected/cleaned_valid.csv`.

## Follow one problem

In `bad_values.csv`, a record has no customer ID and another says the customer joined on 30 February. The rejection report identifies each issue. Two other records are valid, but the fixed policy holds the whole batch, so no cleaned file is released. The source can be corrected and exported again into a new run folder.

F004 has blank permission. That is represented as UNKNOWN and reported as a warning. Retaining the profile for analysis does not authorise marketing to it.

## Explain the code structure

| Function | Responsibility |
| --- | --- |
| `load_mapping` | Read an approved CSV mapping for headings or permission values. |
| `normalize` | Apply the small set of per-record rules. |
| `process_file` | Check headings, coordinate reading, compare duplicate IDs, and decide release. |
| `write_csv` | Write a consistent CSV report. |

Duplicate comparison and final reporting are short sections inside `process_file`. The implementation has a fixed hold policy and assumes a completed, stable export.

The underlying code needs review, but the choices above are the reasons it exists. We do not need to justify SQL queries or database indexes because this implementation uses neither.

## Questions to answer independently before submission

- Why can an extra column be ignored while a missing customer ID column cannot?
- Why is an empty last-purchase date allowed?
- Why is unknown permission different from YES and NO?
- Why not simply choose a winner for conflicting IDs?
- What happens if half the rows fail validation?
- What does READY prove, and what does it leave unproven?
- How do we know the test expectations were not merely copied from the implementation?
- What do the measured timings say, and what do they not establish?

These are prompts for understanding. They are not a script to memorise or evidence that Stefan has already completed the rehearsal.

## Development, Test, then Production

The supplied examples and tests use synthetic files in a local development environment. We never use Production as the first place to try a script or mapping change. A future OIC/OCI Functions deployment would first be exercised in a dedicated Development or Test environment, including its connectors, held batches, and destination behavior. Only the reviewed, validated artifacts would then be promoted to Production with separate environment configuration and monitoring.
