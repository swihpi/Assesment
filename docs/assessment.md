# From CRM exports to usable customer data

Stefan Willems — Senior Forward Deployed Engineer assessment

## The customer problem and the thinking behind it

A sports organisation wants to bring customer information from its CRM into an analytics environment. For the customer, a successfully delivered file is only part of the problem: they need to know which information they can use, what still needs attention, and whether correcting one problem will delay everything else. The available interface is a daily CSV export, but changing headings, incomplete values and conflicting records make that input difficult to trust. I built a small flow that preserves received data, releases valid records and reports correction cases; unreliable input prevents approval. The customer and incident are hypothetical, informed by my Oracle experience.

### The working result

In the tested 10,000-record example, all received records are preserved, 9,200 pass the selected checks and are released, and 800 are reported for correction. Independent record errors do not block usable records; an input-wide failure, such as an unrecognised required heading or broken CSV structure, blocks the whole release. All 60 automated tests pass. These are local file-processing results; using partial updates in a database requires an agreed destination policy.

### Why a batch example?

For this exercise, I deliberately assumed a legacy CRM whose available interface is a scheduled CSV export. This keeps the demonstration focused on a practical source constraint and on making inconsistent data usable. Where the business needs customer changes reflected within seconds or minutes—and the source supports it—a streaming integration would be a stronger fit. The validation, identity and permission principles demonstrated here would still apply, while continuous processing would require additional handling for repeated updates, event ordering and recovery. The current implementation demonstrates batch processing only.

### Why this scope?

I chose to demonstrate the uncertain part of the handoff: interpreting changing headings, separating usable records from correction cases, and explaining failures. Cloud connectivity and database updates remain outside the working implementation so the selected behaviour can be reproduced and inspected. The repository contains the runnable code, assumptions and evidence.

### Technology key

| Service | Abbreviation | Role in this proposal |
| --- | --- | --- |
| Oracle Integration Cloud | OIC | Retrieve files and coordinate processing. |
| Autonomous Data Warehouse | ADW | Store classified customer records. |
| Oracle Analytics Cloud | OAC | Present information through dashboards. |

### Key decisions

| Decision | Why |
| --- | --- |
| Use the existing CSV/SFTP export | No usable CRM API or supported application connector is available in the assumed environment. |
| Match confirmed headings by name | Labels and column positions can change without the underlying information changing. |
| Preserve uncertainty and withhold conflicting records for the same customer ID | Missing information or conflicting records should not be resolved by guessing. |
| Release valid records; block unreliable input | Independent row errors should not block valid records; uncertain headings or broken structure prevent safe approval of the input. |
| Demonstrate the rules in standalone Python | Reviewers can reproduce the behavior without access to Oracle services. |

### The experience that informed the case

This assignment reminded me of a Social Media Sentiment Analysis initiative I championed through what we informally called the OCI Think Tank. It began with two people: Mark, an Oracle US sales representative, and me. We shared an enthusiasm for experimenting with customer solutions that could generate Oracle revenue while helping customers create their own commercial advantage and revenue opportunities. We then brought in like-minded colleagues from EMEA and the US, assembling the integration, analytics, product-management and database expertise needed to explore the use case. My contribution included architectural direction and evaluating which Oracle services could support the use case, including OIC, ADW and OAC. I understood OIC’s role in connecting systems and orchestrating data flows, but did not configure or implement integrations myself. I created several OAC dashboards; a colleague configured the database sentiment analysis.

The wider ambition was to combine aggregated social-media audience signals with other customer-held information, including individual profiles, ticket purchases, and merchandise transactions. This could help a company decide where to invest its advertising, promotion, and communication budget, and which audiences or customers to approach through email, push notifications, WhatsApp, or SMS. The intended outcome was more relevant engagement and increased revenue, while customers retained their source data in their own database. For this assessment, we make one foundational input dependable before it supports those decisions.

## The source and the missing handoff

We first establish what the CRM can provide, who owns its export and which constraints are genuine. Here, no usable API or supported application connector is available, including through OIC. The CRM can deliver a scheduled CSV to customer-controlled SFTP. At 02:00 UTC it exports ID, name, region, joining date, last-purchase date and marketing permission; OIC retrieves the completed file.

![Proposed production flow: OIC retrieves and archives the original CSV, coordinates validation before database loading, then writes approved records and restricted correction cases to ADW. Python in an OCI Function is the illustrated validation option; the cloud deployment remains proposed.](diagrams/deployment.svg)

The assumed incident is a report-template change: headings are renamed, columns reordered, and some values are missing or inconsistent. The database itself need not have changed. The source owner confirms field meanings before we approve mappings. The local demonstration starts with a completed CSV; the cloud handoff shown above remains proposed.

For that deployment, we must also agree how completed files are recognised, how missing exports are reported, and how previously processed files are handled.

## The processing decisions

All six headings must exist. Customer ID, name, region and joining date require valid values; last-purchase date may be empty. CSV mapping files define approved aliases and permission equivalents. We do not infer meaning from spelling or invent missing identity.

| Situation | Processing decision |
| --- | --- |
| Approved renamed or reordered heading | Map by confirmed name; column position is not the contract. |
| Extra unused column | Report a warning and continue. |
| Missing/ambiguous required heading, malformed CSV or invalid encoding | BLOCKED: preserve received bytes and diagnostics; release no approved records. A valid-looking prefix is insufficient. |
| Missing ID, invalid required value or conflicting records for the same customer ID in a fully parsed file | Mark the affected records NEEDS_CORRECTION and release the other valid records. |
| Identical normalized duplicate | Retain one approved copy; report the duplicate as ignored. |
| Unknown permission | Preserve UNKNOWN, report a warning and retain the otherwise valid record. Campaign eligibility is separate. |

![Implemented local flow: preserve the received file, separate record errors from input-wide failures, and publish approved records only after a successful completion marker.](diagrams/validation.svg)

### What happens to 10,000 records with 800 failures?

I questioned why correcting 800 records should prevent the customer from using 9,200 otherwise usable records. The answer depends on the destination: partial release is appropriate only if it can safely accept independent updates. In the tested case, received.csv retains 10,000 records, cleaned.csv contains 9,200, and correction/status reports identify 800 exceptions. READY_WITH_EXCEPTIONS confirms release. A missing required heading, broken structure or input with no valid records produces BLOCKED and no cleaned CSV.

The destination must not treat omitted rows as deleted customers or replace a complete table with a partial file. An all-or-nothing policy can be appropriate for a complete snapshot replacement or a transaction requiring consistency across records. This prototype proves selection, not database reconciliation. Missing-ID rows remain traceable by batch and source-record reference; these references do not manufacture customer identity.

Different attributes under the same customer ID do not prove that two identities conflict. They may be inconsistent records for one customer. The prototype reports CONFLICTING_RECORDS_FOR_ID and withholds the group rather than choosing a winner; authoritative-source or recency-based reconciliation is outside scope.

### Permission is different from data quality

Data quality and marketing eligibility are separate. NO records an explicit opt-out; UNKNOWN preserves missing or unrecognised information. Neither authorises the assumed consent-based campaign. Production activation must check current channel/purpose permission and a valid address or device. Email permission does not authorise push, SMS or WhatsApp.

| Permission | Meaning | Assumed campaign treatment |
| --- | --- | --- |
| YES | Approved source value indicates permission for the specified channel and purpose. | Proceed to other eligibility checks; acceptance alone does not authorise sending. |
| NO | Explicit customer opt-out. | Exclude from the affected marketing action. |
| UNKNOWN | Permission missing or not reliably interpretable. | Exclude where confirmed permission is required; request clarification. |

The script normalizes these values but does not send messages or enforce campaign selection. An otherwise valid UNKNOWN record is marked `ACCEPTED_WITH_WARNING`. In production, approved access and campaign-specific filters must enforce restrictions; a flag that downstream exports can bypass is insufficient. Passing ingestion does not prove every source attribute is true or authorise a campaign.

### If the CRM renames the customer ID column

If `customer_id` becomes `customerdata_id`, the processor initially blocks release because the required ID heading has no approved mapping. The source owner confirms whether this is only a rename, with unchanged values, meaning and uniqueness. The integration owner can then add `customerdata_id → customer_id` to the mapping CSV, validate it in Development/Test and rerun the export. A test checks both outcomes. If identifier values or meaning have changed, a heading alias is insufficient: an approved identity relationship is needed.

## Demonstration and evidence

The standalone Python processor uses only the standard library. It runs without cloud credentials, a database or additional packages. I direct Codex to execute the examples and tests, then review the results; the README contains exact setup and reproduction commands. Local files represent the raw-file archive, per-record status and approved selection, so the implementation demonstrates the policy illustrated in the cloud diagram.

### Python preview: checking real dates

This excerpt from the normalize function checks the joining and last-purchase dates. It requires the agreed YYYY-MM-DD format and a real calendar date, so a value such as 2024-02-30 is reported as INVALID_DATE. The complete processor also handles heading mappings, same-ID record conflicts, record status and approved output.

process_export.py · lines 91–100 · version 1.1.0

[View the matching Python source on GitHub ↗](https://github.com/swihpi/Assesment/blob/6f125de7ae323d9f72fea7d9a3f7c0d006fc5521/process_export.py#L91-L100)

```python
    for field in ("member_since", "last_purchase_date"):
        if row[field]:
            try:
                valid_format = re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", row[field])
                if valid_format:
                    date.fromisoformat(row[field])
                else:
                    problems.append((field, "INVALID_DATE"))
            except ValueError:
                problems.append((field, "INVALID_DATE"))
```

### How I execute and review the demonstration

I use Codex to run and verify the demonstration by providing the commands or describing the checks in natural language, then reviewing the reported outcomes against the expected results. In this run, the valid and renamed exports each released three records; the bad-value example released F001 and F004 and reported two correction cases; the missing required heading blocked release. All 60 tests passed. This approach lets me repeat the checks without manually entering each command in a terminal, while the README retains the commands for independent reproduction.

The private presentation retains a clearly labelled historical execution capture from the earlier 24-test version. The current version 1.1.0 passes 60 tests. Earlier artifacts remain in Git history; the current execution log is linked below.

[Historical 24-test log](https://github.com/swihpi/Assesment/blob/f4d042730f67bca0e334ad5ef359e2ba33115384/docs/evidence/codex-run-24-tests-20261031.txt) · [Current 60-test log](evidence/codex-run-current.txt)

[Read the full execution log](evidence/codex-run-current.txt)

### One successful record

| Field | Received | Normalized |
| --- | --- | --- |
| Customer ID | F001 with surrounding spaces | F001 |
| Full Name | Alex, repeated spaces, Morgan | Alex Morgan |
| Home Region | NY with surrounding spaces | NY |
| Email Opt In | `y` with surrounding spaces | YES |
| Customer Since | `2022-04-15` | `2022-04-15` |

The dates retain their meaning. Another record has no last-purchase date and remains valid.

### One actionable failure

The bad-value sample contains the impossible joining date 2024-02-30. The row below shows selected columns from actual rejected.csv output from a fresh run. The full report also includes physical source-line ranges. Record 3 is the third nonblank source record. Messages and actions identify the particular problem; several problems remain combined into one report row per rejected record. The source owner confirms and corrects the date in the CRM and re-exports; the processor does not guess a replacement.

| Record | Customer ID | Field | Code | Message | Next action |
| --- | --- | --- | --- | --- | --- |
| 3 | F003 | member_since | INVALID_DATE | Joining date is not a valid YYYY-MM-DD calendar date. | Confirm joining date in the authoritative CRM record, correct it and re-export. |

[Inspect the full generated correction report on GitHub →](https://github.com/swihpi/Assesment/blob/main/examples/with-exceptions/rejected.csv)

| Example | Recorded outcome |
| --- | --- |
| Valid export | READY: three normalized records. |
| Renamed/reordered report | READY: the same three expected records. |
| Bad-value export | READY_WITH_EXCEPTIONS: F001 and F004 released; two correction cases. |

The current reproduction results and test output are available in the [execution log](evidence/codex-run-current.txt) and the public repository’s automated checks.

Each completed run contains the original received bytes, record statuses, correction and warning reports, a summary and a log. Approved records appear in cleaned.csv. A READY or READY_WITH_EXCEPTIONS marker is written last and must be present before consumption. BLOCKED or no marker means no approved release. Existing run folders cannot be overwritten.

### Correctness and operability

Sixty automated tests cover predefined output, heading changes, required fields, dates, NO versus UNKNOWN, duplicate handling, malformed input, encoding, reruns and failed report/completion-marker writes. They also verify received-byte preservation, the 10,000/800 case, an explicitly approved customerdata_id alias, and a structure error encountered after valid records. Expected outcomes specify approved IDs and independent counts, rather than relying only on the processor’s summary. The summary exposes parsing completeness, candidates, released records, warnings, duration, processor version, UTC start time and the received-input SHA-256. Reports include physical source-line ranges; locations remain blank where decoding cannot identify them reliably. BLOCKED exits 3, operational/configuration errors exit 1, invalid command syntax exits 2 and both successful outcomes exit 0. Use --debug for tracebacks. For fully parsed input:

Parsed records = Valid records + Rejected records + Identical duplicates removed

An incomplete parse releases nothing; earlier candidates receive NOT_RELEASED. A write failure before the final marker also prevents consumption. Batch and source-record references keep diagnostics traceable.

### Performance and scaling

| Synthetic input | Verified output | Recorded wall time |
| --- | --- | --- |
| 1,000 records | 1,000 records | 0.051 seconds |
| 100,000 records | 100,000 records | 0.595 seconds |

These single local measurements use processor version 1.1.0 on Python 3.14.4 and macOS 26.6.2 ARM64. They include startup, received-file copying, processing and report writing; input generation and independent output counting are outside the timer. The raw results record the processor SHA-256 and UTC timestamp. They do not establish Production or cloud capacity. Memory retained for identity comparisons and record statuses is the main scaling limit. We would measure peak memory and acceptable batch size before considering partitioning or database-backed checks, preserving duplicate detection across partitions. [Raw benchmark results](benchmark.csv).

## Production direction and boundaries

**Demonstration choice:** standalone Python makes the selected behavior locally reproducible. **Production recommendation:** first assess whether native OIC mappings and controls meet the validation, duplicate-handling, and diagnostic requirements; use a separate function where those requirements justify it. If custom Python is selected, OIC can invoke a separately hosted OCI Function. The rules could be reused, but a function handler, cloud input/output interface, and destination loading still require implementation. The command-line script is not an embedded Python library inside OIC.

### Retain received data; control approved use

OIC retrieves the completed export and archives the original in restricted OCI Object Storage. It coordinates validation before ADW loading, using native controls where sufficient or a separately hosted Python function where justified. ADW would retain validation status, reason and batch/source-record references, with correction cases excluded from approved access. Cloud interfaces, loading and access enforcement remain proposed.

| Example | Proposed ADW status | Available use |
| --- | --- | --- |
| Required fields pass the checks | ACCEPTED | Available for downstream eligibility checks, not automatic campaign activation. |
| Customer ID missing, required date invalid, or records for the same customer ID conflict | NEEDS_CORRECTION | Retained for investigation; excluded from approved downstream use. |
| Required checks pass, permission is unknown | ACCEPTED_WITH_WARNING | Retained in the trusted dataset; excluded from campaigns requiring confirmed permission. |

The local files correspond to the raw archive, classification report, approved selection and correction diagnostics shown in section 3. In the proposed deployment, ADW receives classified results only after validation. Correction storage must safely retain invalid source values, such as a date as text. An unreadable file remains an archived file-level failure, not a set of successfully parsed customer rows.

### Who corrects the data?

When an import fails, the customer needs to know what remains usable, who is investigating and when to expect the next update. Distinguish source-data problems from processing failures; do not promise a resolution time before understanding the cause.

The source owner corrects data; integration engineering maintains mappings and processing. An exception CSV supplies file, row, available customer reference, problem and action through an agreed secure channel. Assign, correct at source, re-export, revalidate and reconcile. Track unresolved counts and age. Delivery and recovery tracking remain proposed operating capabilities.

| Issue | Proposed responsible team |
| --- | --- |
| Missing ID or incorrect customer information | CRM/data owner, supported by the CRM administrator or data steward. |
| Missing or ambiguous permission | Owner of the authoritative consent records; UNKNOWN remains until reliable evidence resolves it. |
| Changed heading or incorrect mapping | Source owner confirms meaning; integration owner maintains and validates the approved mapping. |
| Transfer, processing or delivery failure | Integration engineering team. |

After source correction, revalidation and reconciliation can move a row into the approved selection. A correction must not overwrite newer customer information or permission changes. The destination also needs an explicit rule for yesterday’s approved version when today’s update fails: a stale approval must not be assumed safe for marketing. These update and suspension controls are not implemented in the local processor.

![Validate locally, then in Development/Test, before reviewed Production promotion.](diagrams/promotion.svg)

We never test a new script, mapping, or integration in Production first. Use synthetic files locally, then a dedicated Development/Test environment to validate completed-file detection, missing exports, permissions, connectivity, retries, raw-file retention, pre-load validation, classified ADW loads, partial updates, exception recovery and downstream exclusion. Only after review and successful validation should the flow be promoted to Production with separate configuration and monitoring. Only the local file-processing stage has been exercised here; no live customer dataset or Production system was used.

Outside the working slice are live extraction, transfer, scheduling, database updates, exception delivery, exactly-once processing, sentiment scoring and campaign enforcement. A daily snapshot cannot establish immediate permission changes; activation needs a suitable current-permission check.

If source failures recur, we review reporting, change ownership, supported interfaces, and operating cost. Stabilising the report may suffice. CRM modernisation or replacement becomes a separate recommendation where justified, weighed against migration cost and disruption.

## Codex assistance and my judgement

### How I approached this implementation

My strongest experience is in cloud architecture, analytics and bringing technical disciplines together around a business problem. The NHL proposition, internal advocacy, architectural direction and dashboard work came from my Oracle experience. For this assessment, I developed the hypothetical scenario with Codex and directed changes to its processing policy. Codex generated the Python and executed checks at my direction. I reviewed functional outcomes and consistency across the code, diagrams and explanation.

### Questions that changed the design

| My review question | Decision and consequence |
| --- | --- |
| How does the CRM export actually reach the integration? | We made the scheduled CSV export, CRM-to-SFTP delivery and OIC retrieval explicit. |
| Why introduce unfamiliar database programming or a long script? | We chose a compact, independently runnable Python example I could inspect and discuss. |
| Why should 800 bad records prevent use of 9,200 valid ones? | I challenged blanket rejection, then made partial release conditional on a destination that supports independent updates. An all-or-nothing policy remains valid where completeness is required. |
| Why do the production diagram and local demonstration describe different release rules? | Codex’s diagram and explanation described a different release policy from the code. I rejected that inconsistency and required alignment across code, tests, diagrams and documentation, then checked the revised outputs. |
| Who fixes missing data, and should missing permission mean NO? | We assigned source ownership and separated data-quality status from channel-specific marketing eligibility; missing permission remains UNKNOWN. |
| Could the AI-generated code still contain gaps after the initial tests? | I requested a code review in Codex, which found silently skipped empty records, inconsistent permission whitespace matching and duplicate reports that hid field errors. I had the fixes applied and regression tests added; all 39 tests then passed locally and in GitHub Actions on Python 3.12 and 3.14. [Fixes](https://github.com/swihpi/Assesment/commit/f027e5aeb5353d222ae3311a33cc7cee570eb7be) · [Checks](https://github.com/swihpi/Assesment/actions/runs/41202300627). |

In a second review, I asked Codex to assess Claude’s feedback point by point. I accepted changes to configuration validation, Unicode matching, diagnostics and traceability, while retaining the agreed release policy. The revised version passed 60 tests in a fresh local clone on Python 3.14 and in GitHub Actions on Python 3.12 and 3.14. [Version 1.1.0 changes](https://github.com/swihpi/Assesment/commit/6f125de7ae323d9f72fea7d9a3f7c0d006fc5521) · [Checks](https://github.com/swihpi/Assesment/actions/runs/41203284886).

I requested a fresh-copy test on my Mac rather than accepting a claim that the code worked. Passing checks support the tested behaviour; they do not establish cloud readiness or exhaustive correctness.

### A small, reproducible change

In an additional Codex-executed check, customerdata_id first produced BLOCKED. Assuming source-owner confirmation, a temporary mapping-only change then released the same three normalized records as the baseline. The processor and repository mappings were unchanged.

[Open the code walkthrough and reproduction instructions →](https://github.com/swihpi/Assesment/blob/main/docs/walkthrough.md)

### How Codex helped and where judgement remains necessary

I chose Codex to work with documents, code and execution results in one workspace. It assisted with the scenario, research, fixtures, code, tests, documentation and execution; a Claude critique also informed review. My responsibility was to define intended behaviour, question consequences and check outcomes. The walkthrough explains the mapping, normalisation, same-ID comparison, file-level failures and completion marker that underpin those decisions.

The running processor has no LLM dependency. Known mappings, dates and duplicate handling need repeatable, explainable outcomes. AI could help investigate an unfamiliar field, but a person must confirm its meaning before approving a mapping. Neither AI nor the integration should invent missing identity or permission. Adding an agent to daily processing would need a specific customer benefit and a reliable way to validate its output.

## Wider context and historical examples

The broader idea combined different sources to support audience decisions:

![The broader audience-data concept. CRM quality checks are the implemented local slice.](diagrams/architecture.svg)

Social post text is unstructured; derived sentiment scores and summaries are structured outputs. CRM, ticketing, and purchase records have their own definitions and checks. Aggregate sentiment may inform campaign timing. It does not identify a known customer’s sentiment. Combining individual records requires a reliable linking identifier and confirmation that the information may be used for that purpose.

### Original initiative

The account of the original initiative and individual responsibilities is my personal account, checked against internal presentation material. That presentation and its historical screenshots are not included in this public repository. The CRM incident and processing rules are hypothetical extensions.

The idea was inspired by existing subscription-based social-listening and sentiment-analysis solutions. We wanted to explore whether a PaaS approach could give customers more control over their data environment and more flexibility to customise the analysis. Rather than relying primarily on a packaged application, the proposed solution would bring data and analysis together within the customer’s own OCI environment, with scope to connect additional sources and adapt the dashboards to their business needs. This offered a potential commercial benefit for the customer while generating consumption of Oracle cloud services. The trade-off was greater responsibility for building and maintaining the solution.

The initiative focused on NHL hockey. The original presentation includes Nashville Predators versus LA Kings. The initiative was internal and intended for exploration as an OCI Sports Unit pilot. It was discontinued because of other priorities within OCI OAC Product Management. Bringing engineers, product management, and DBAs together was a useful learning experience around an idea intended to increase OCI usage and help customers derive commercial value.

The NHL example used the OIC Twitter adapter to bring in Twitter activity, alongside game information obtained through the public NHL API. The data was brought together in ADW and presented through OAC dashboards, combining aggregate sentiment with match-day events.

### Original slide 6: aggregate sentiment

The original screenshot illustrates aggregate sentiment categories and trends. The source slide identifies Oracle Text in Autonomous.

*Historical screenshot is available in the private presentation; original images are not included in this repository.*

### Original slide 7: match-day context

The original screenshot places social information alongside game events. Correlating timelines is different from identifying an individual fan or establishing campaign impact.

*Historical screenshot is available in the private presentation; original images are not included in this repository.*

## Assignment coverage

| Assignment requirement | Evidence |
| --- | --- |
| Customer context, assumptions, and value | Sections 1–2 and the accompanying customer note. |
| Runnable ingestion and normalization | Processor, mappings, sample files, and README. |
| Schema drift, bad data, actionable errors | Sections 3–4 and executed examples. |
| Setup and run instructions | README prerequisites, commands, outputs, and exit statuses. |
| Architecture, trade-offs, and limitations | Sections 2–5. |
| Meaningful tests and reliability | Sixty passing tests, explicit expected output, and fresh-copy checks. |
| Logging and observability | Counts, parsing completeness, reports, log, duration, and completion markers. |
| Performance and scalability thinking | Recorded measurements, their limits, and the memory bottleneck. |
| AI disclosure and deliberate non-reliance | Section 6 and the README. |
