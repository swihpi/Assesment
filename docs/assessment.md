# Making a daily CRM export dependable

**Stefan Willems — Senior Forward Deployed Engineer assessment**
**Repository: [https://github.com/swihpi/Assesment](https://github.com/swihpi/Assesment)**

## 1. The customer problem and the thinking behind it

A sports organisation wants to bring customer information from its CRM into an analytics environment. Its available interface is a daily CSV export. Changes to report headings, incomplete values, and conflicting customer records make that input difficult to use reliably.

We build a small working flow that reads a completed CSV, normalizes approved equivalents, and identifies information that cannot safely be accepted. The result is either a cleaned dataset with reports or a held batch with actionable errors.

The customer and incident are hypothetical, informed by my Oracle experience.

### Key decisions

| Decision | Why |
|---|---|
| Use the existing CSV/SFTP export | No usable CRM API or supported application connector is available in the assumed environment. |
| Match confirmed headings by name | Labels and column positions can change without the underlying information changing. |
| Preserve uncertainty and reject conflicting identities | Missing information or conflicting records should not be resolved by guessing. |
| Initially hold snapshots containing rejected records | The receiving system expects a complete snapshot; partial data needs a separate agreement. |
| Demonstrate the rules in standalone Python | Reviewers can reproduce the behavior without access to Oracle services. |

### The experience that informed the case

This assignment reminded me of an internal Social Media Sentiment Analysis initiative I championed within Oracle’s OCI Think Tank, bringing together colleagues from EMEA and the US. I proposed the use case and helped assemble the integration, analytics, product-management, and database expertise needed to explore it.

My contribution included architectural direction and tool choices around Oracle Integration Cloud, Data Integration, Autonomous Data Warehouse, and Oracle Analytics Cloud. Oracle Integration Cloud connects applications and data sources and orchestrates integration workflows. I also created several dashboards; a colleague configured the database sentiment analysis.

The wider ambition was to combine aggregated social-media audience signals with other customer-held information, including individual profiles, ticket purchases, and merchandise transactions. This could help a company decide where to invest its advertising, promotion, and communication budget, and which audiences or customers to approach through email, push notifications, WhatsApp, or SMS.

The intended outcome was more relevant engagement and increased revenue, while customers retained their source data in their own database. For this assessment, we make one foundational input dependable before it supports those decisions.

## 2. The source and the missing handoff

For this hypothetical customer, the CRM version has no usable API or supported application-specific connector available for the integration, including through Oracle Integration Cloud.

It does support scheduled CSV reports and delivery to a customer-controlled SFTP location. Each night at 02:00 UTC, it exports selected customer fields: ID, name, region, joining date, last-purchase date, and marketing permission. Oracle Integration Cloud retrieves the completed file from SFTP.

![Deployment diagram](diagrams/deployment.svg)

The assumed incident is a report-template change: headings are renamed, columns are reordered, and some records contain missing or inconsistent values. The database itself need not have changed.

We agree field meanings with the source owner and make those rules executable. Automated delivery alone does not establish that a renamed field has the intended meaning.

The **implemented demonstration starts with an available, completed CSV** and ends with local output. The CRM export, SFTP collection, cloud integration, and database loading remain proposed deployment work.

For that deployment, we must also agree how completed files are recognised, how missing exports are reported, and how previously processed files are handled.

## 3. The processing decisions

All six selected headings must exist. Customer ID, name, region, and joining date require values. Last-purchase date may be empty; missing or unfamiliar permission remains UNKNOWN.

Approved heading aliases and permission forms are recorded in two readable CSV mapping files.

| Situation | Response and reason |
|---|---|
| Approved renamed or reordered heading | Map by name; position is not a reliable contract. |
| Additional unused column | Warn and continue because required information may remain usable. |
| Missing or ambiguous required heading | Hold the file because its interpretation is uncertain. |
| Invalid required value or date | Reject the record and identify the required correction. |
| Unknown permission | Retain UNKNOWN with a warning; do not infer YES. |
| Repeated customer ID | Remove identical normalized copies; reject conflicting copies rather than guess. |

For example, `Customer ID` can be an approved alias for `customer_id`. In the synthetic fixture, `Email Opt In` is approved as the selected permission field. A real customer must confirm its channel and meaning before that mapping is accepted.

We tidy whitespace, preserve IDs as text—including leading zeroes—and require real dates in `YYYY-MM-DD` form. An empty purchase date can be legitimate. A missing ID prevents us from using the record under this contract.

![Validation diagram](diagrams/validation.svg)

### Why hold the complete snapshot?

Suppose two different profiles share the same customer ID. Choosing whichever appears last would introduce a rule the customer never agreed to. We reject the conflicting copies for source clarification.

The initial downstream agreement expects a complete daily snapshot. Simply omitting rejected records could cause the receiving system to interpret missing customers as removed or inactive.

Holding the batch delays the update, but provides one complete unit to correct and rerun.

We reconsider this policy when timely partial data becomes more valuable than waiting, and the receiving system can safely distinguish an incomplete dataset from a complete snapshot. That requires agreement on eligible error types, any rejection threshold, a qualified release status, and later reconciliation.

A percentage alone is insufficient: a few conflicting identities may matter more than many optional-field warnings. **The current processor implements the fixed hold policy; partial release is an extension.**

READY confirms the implemented processing checks and completed output writing. It does not prove every source attribute is true or authorise a campaign.

## 4. Demonstration and evidence

The Python processor is 160 lines, including comments and blank lines, and uses the standard library. It runs without cloud credentials, a database, or additional packages.

I direct Codex to execute the examples and tests, then review the results. The README contains the exact commands for direct reproduction.

### One successful record

| Field | Received | Normalized |
|---|---|---|
| Customer ID | F001 with surrounding spaces | F001 |
| Full Name | Alex, repeated spaces, Morgan | Alex Morgan |
| Home Region | NY with surrounding spaces | NY |
| Email Opt In | `y` with surrounding spaces | YES |
| Customer Since | `2022-04-15` | `2022-04-15` |

The dates retain their meaning. Another record has no last-purchase date and remains valid.

### One actionable failure

A record with joining date `2024-02-30` is rejected. The report identifies customer F003, the `member_since` field, `INVALID_DATE`, and the action to confirm and supply a real date.

The same sample also contains a missing customer ID and an unknown permission. The missing ID is rejected; unknown permission remains a warning. Two records are valid, but the snapshot policy holds the batch.

| Example | Recorded outcome |
|---|---|
| Valid export | READY: three normalized records. |
| Renamed/reordered report | READY: the same three expected records. |
| Bad-value export | HELD: diagnostics, with no cleaned file. |

**Codex execution results reviewed during preparation:**

*The corresponding screenshot is included in the private presentation.*

Each run writes rejection and warning reports, a summary, and a log. A cleaned CSV is released only for READY. The completion marker is written last, and consumers must require it.

Source files remain unchanged. Previous run folders cannot be overwritten. After source correction, we obtain a new export and use a fresh output folder.

### Correctness and operability

Nineteen automated tests passed across heading changes, required fields, dates, permission uncertainty, duplicates, malformed CSV, encoding, repeat runs, command-line outcomes, and report-write failure.

Expected outcomes were created before the processor, with Codex assistance. Tests compare actual values with those expectations. A clean Git export reproduced the expected outcomes and passed all 19 tests.

The summary and log expose parsing completeness, counts, warnings, status, processing stages, and duration. For fully parsed input:

Parsed records = valid records + rejected records + identical duplicates removed.

Malformed input is marked incomplete. If output writing fails before completion, no READY marker is available.

### Performance and scaling

| Synthetic input | Verified output | Recorded wall time |
|---|---|---|
| 1,000 records | 1,000 records | 0.037 seconds |
| 100,000 records | 100,000 records | 0.393 seconds |

These single local measurements include startup, processing, and report writing. Input generation and output counting are outside the timer. They do not establish cloud or Production capacity.

The measurements used Python 3.14.4 on macOS 26.6.2 ARM64; clean-export checks used Python 3.12.14.

Memory retained for duplicate comparison is the main scaling limit. We would measure peak memory and acceptable batch size before assessing partitioning or database-backed checks, ensuring conflicts are still detected across partitions.

## 5. Production direction and boundaries

**Demonstration choice:** standalone Python makes the selected behavior locally reproducible.

**Production recommendation:** first assess whether native Oracle Integration Cloud mappings and controls meet the validation, duplicate-handling, and diagnostic requirements; use a separate function where those requirements justify it.

If custom Python is selected, Oracle Integration Cloud can invoke a separately hosted OCI Function. The rules could be reused, but a function handler, cloud input/output interface, and destination loading still require implementation.

The command-line script is not an embedded Python library inside Oracle Integration Cloud.

![Promotion diagram](diagrams/promotion.svg)

We never test a new script, mapping, or integration in Production first. Deployment validation includes file completion, missing exports, permissions, connectivity, payload size, timeouts, retries, held batches, and downstream loading.

Only the local stage has been exercised here. No live customer dataset or Production system was used.

The implementation assumes a completed, stable source file. Live extraction, secure transfer, scheduling, freshness checks, database loading, exactly-once delivery, sentiment scoring, and campaign execution are outside its scope.

A daily snapshot is also insufficient for immediate permission changes; marketing use requires a suitable current-permission check.

If source failures recur, we review reporting, change ownership, supported interfaces, and operating cost. Stabilising the report may suffice. CRM modernisation or replacement becomes a separate recommendation where justified, weighed against migration cost and disruption.

## 6. Codex assistance and my judgement

The original sports sentiment proposition, internal advocacy, architectural direction, dashboard work, and broader customer-data ambition came from my Oracle experience.

The specific CRM incident and detailed processing rules were developed with Codex assistance.

### A concrete review decision

An earlier proposal said Oracle Integration Cloud would collect a CRM export without adequately explaining why CSV was necessary or how the file reached it.

I challenged that explanation: what data was in the file, where did it originate, how frequently did it arrive, why could acquisition not simply be automated, and what did Oracle Integration Cloud actually connect to?

That exposed a missing architectural handoff. We then made the constraint and delivery path explicit: no usable CRM application connection, but an existing scheduled CSV/SFTP export.

I also asked for a smaller implementation and challenged unfamiliar database programming and unnecessary complexity. My aim was a working example I could inspect and discuss credibly.

### How Codex helped

I chose Codex to work with documents, code, and execution results in one workspace. It assisted with structure, tooling research, detailed rules, fixtures, expected outcomes, Python, tests, documentation, and execution at my direction. A supplied Claude critique also informed the review.

### Where we use explicit rules

The running processor has no LLM dependency. Known mappings, dates, and duplicate handling need repeatable, explainable outcomes.

AI could help investigate an unfamiliar field, but a person must confirm its meaning before changing the mapping. AI cannot establish missing permission or resolve conflicting identities by assumption.

Codex supports preparation and development. Adding an AI agent to daily processing would require a specific customer benefit and a way to validate its output.

## Appendix A. Wider context and historical examples

The broader idea combined different sources to support audience decisions:

![Architecture diagram](diagrams/architecture.svg)

Social post text is unstructured; derived sentiment scores and summaries are structured outputs. CRM, ticketing, and purchase records have their own definitions and checks.

Aggregate sentiment may inform campaign timing. It does not identify a known customer’s sentiment. Combining individual records requires a reliable linking identifier and confirmation that the information may be used for that purpose.

### Original initiative

The initiative focused on NHL hockey. The original presentation includes Nashville Predators versus LA Kings.

The initiative was internal and intended for exploration as an OCI Sports Unit pilot. It was discontinued because of other priorities within OCI OAC Product Management.

Bringing engineers, product management, and DBAs together was a useful learning experience around an idea intended to increase OCI usage and help customers derive commercial value.

### Original slide 6: aggregate sentiment

The original screenshot illustrates aggregate sentiment categories and trends. The source slide identifies Oracle Text in Autonomous.

*The corresponding screenshot is included in the private presentation.*

### Original slide 7: match-day context

The original screenshot places social information alongside game events. Correlating timelines is different from identifying an individual fan or establishing campaign impact.

*The corresponding screenshot is included in the private presentation.*

## Appendix B. Assignment coverage

| Assignment requirement | Evidence |
|---|---|
| Customer context, assumptions, and value | Sections 1–2 and the accompanying customer note. |
| Runnable ingestion and normalization | Processor, mappings, sample files, and README. |
| Schema drift, bad data, actionable errors | Sections 3–4 and executed examples. |
| Setup and run instructions | README prerequisites, commands, outputs, and exit statuses. |
| Architecture, trade-offs, and limitations | Sections 2–5. |
| Meaningful tests and reliability | Nineteen passing tests, explicit expected output, and clean-export checks. |
| Logging and observability | Counts, parsing completeness, reports, log, duration, and completion markers. |
| Performance and scalability thinking | Recorded measurements, their limits, and the memory bottleneck. |
| AI disclosure and deliberate non-reliance | Section 6 and the README. |

## Appendix C. Sources

1. *Integrating a Messy External Data Source — Forward Deployed Engineer Home Assignment*, and the supplied Candidate Guide.
2. [Oracle: Define the integration schedule](https://docs.oracle.com/en/cloud/paas/application-integration/integrations-user/define-integration-schedule.html).
3. [Oracle: Invoke OCI Functions from an Oracle Integration Cloud integration](https://docs.oracle.com/en/cloud/paas/application-integration/integrations-user/invoke-oracle-cloud-infrastructure-functions-directly-from-integration-oci-function-action.html).
4. [Oracle: Python function packaging](https://docs.oracle.com/en-us/iaas/Content/Functions/Tasks/functions-codeonly-python.htm).
5. [Oracle: FTP Adapter capabilities, including SFTP](https://docs.oracle.com/en/cloud/paas/application-integration/ftp-adapter/ftp-adapter-capabilities.html).
