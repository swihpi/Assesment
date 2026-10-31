# Proposed deployment and operating responsibilities

The local processor is implemented. The following cloud deployment is proposed; it has not been provisioned or tested.

1. The CRM generates its completed daily export and delivers it to customer-controlled SFTP. OIC retrieves it on the agreed schedule. Missing files, completion detection and previously processed exports need an explicit delivery contract.
2. OIC archives the exact received bytes in a restricted raw-file location, proposed as OCI Object Storage, with a batch reference. This preserves malformed or unsupported-encoding input without claiming it became readable database rows.
3. OIC coordinates validation and normalisation before database loading. Assess native mappings and controls first; the illustrated option invokes Python hosted separately in an OCI Function. Its handler and cloud I/O still need implementation. The CLI script cannot be deployed unchanged.
4. After classification, OIC loads readable records into ADW: approved records enter the controlled approved selection; correction cases retain source values, status and reason in restricted exception storage. Invalid dates must be representable as source text. A file-level contract failure produces no approved customer rows. Campaign-specific permission and other eligibility checks apply separately; a flag alone does not enforce exclusion.
5. An exception report is securely routed to the responsible CRM/data or consent-record owner. Corrections are made at source, re-exported, validated and reconciled. Integration engineering owns processing and mappings. The report-delivery and work-assignment process is proposed; the script generates reports only.

![Proposed receiving and validation flow](diagrams/deployment.svg)

## Same policy, different storage

The local received.csv corresponds to the raw-file archive; record_status.csv corresponds to per-record status/reason; cleaned.csv corresponds to the approved selection; rejected.csv contains actionable correction diagnostics. The local program implements that selection policy but has no ADW connection. Validation precedes the proposed ADW writes. The cloud deployment must apply partial updates safely: absence must not mean deletion and a partial selection must never replace a complete customer table. Existing-customer updates, source freshness, duplicate replay, corrections and permission changes need reconciliation rules.

Batch and source-record references identify received rows even when a customer ID is missing; they do not invent customer identity. Conflicting IDs remain excluded until resolved. NO and UNKNOWN are distinct; neither authorises sending in the assumed consent-based campaign. Production access, retention and deletion policies need agreement.

## Development/Test before Production

Use synthetic inputs locally, then validate the deployed integration in a dedicated Development/Test environment. Check file completion, missing exports, credentials, timeouts, retries, raw-file archiving, pre-load validation, classified ADW loads, approved selection, partial updates, report delivery, correction replay and campaign exclusion. Only after review and successful validation should the same reviewed artifacts be promoted with separate Production configuration, monitoring and rollback arrangements. Only local processing has been exercised.

## Official capability references

- [Transform records with OIC mappings](https://docs.oracle.com/en/cloud/paas/application-integration/ftp-adapter/configure-data-mapping-transform-data-files.html).
- [Preserve source files in OCI Object Storage](https://docs.oracle.com/en-us/iaas/Content/Object/Concepts/objectstorageoverview.htm).

- [Schedule an integration](https://docs.oracle.com/en/cloud/paas/application-integration/integrations-user/define-integration-schedule.html).
- [SFTP through the FTP Adapter](https://docs.oracle.com/en/cloud/paas/application-integration/ftp-adapter/ftp-adapter-capabilities.html).
- [Invoke an OCI Function](https://docs.oracle.com/en/cloud/paas/application-integration/integrations-user/invoke-oracle-cloud-infrastructure-functions-directly-from-integration-oci-function-action.html).
- [Python function packaging](https://docs.oracle.com/en-us/iaas/Content/Functions/Tasks/functions-codeonly-python.htm).

These document platform capabilities, not an existing deployment.
