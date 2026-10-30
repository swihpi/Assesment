# Proposed deployment and operating responsibilities

The local processor is implemented. The following cloud deployment is proposed; it has not been provisioned or tested.

1. The CRM generates its completed daily export and delivers it to customer-controlled SFTP. Oracle Integration Cloud retrieves it on the agreed schedule. Missing files, completion detection and previously processed exports need an explicit delivery contract.
2. The integration retains readable received records in a restricted ADW receiving area, with import-batch and source-record references. Uncertain or malformed inputs are not approved merely because their bytes were received.
3. Validation assigns status and reason. Native Oracle Integration Cloud mappings and controls should be assessed first; the illustrated option invokes Python hosted separately in an OCI Function. A handler, cloud I/O, permissions and ADW status updates remain to be implemented. The CLI script cannot be deployed unchanged.
4. A controlled approved selection exposes valid records and excludes NEEDS_CORRECTION cases. Campaign-specific permission and other eligibility checks apply separately. A flag alone does not enforce exclusion.
5. An exception report is securely routed to the responsible CRM/data or consent-record owner. Corrections are made at source, re-exported, validated and reconciled. Integration engineering owns processing and mappings. The report-delivery and work-assignment process is proposed; the script generates reports only.

![Proposed receiving and validation flow](diagrams/deployment.svg)

## Same policy, different storage

The local received.csv corresponds to the receiving area; record_status.csv corresponds to per-record status/reason; cleaned.csv corresponds to the approved selection; rejected.csv contains actionable correction diagnostics. The local program implements that selection policy but has no ADW connection. The cloud deployment must apply partial updates safely: absence must not mean deletion and a partial selection must never replace a complete customer table. Existing-customer updates, source freshness, duplicate replay, corrections and permission changes need reconciliation rules.

Batch and source-record references identify received rows even when a customer ID is missing; they do not invent customer identity. Conflicting IDs remain excluded until resolved. NO and UNKNOWN are distinct; neither authorises sending in the assumed consent-based campaign. Production access, retention and deletion policies need agreement.

## Development/Test before Production

Use synthetic inputs locally, then validate the deployed integration in a dedicated Development/Test environment. Check file completion, missing exports, credentials, timeouts, retries, receiving-area loads, state assignment, approved selection, partial updates, report delivery, correction replay and campaign exclusion. Only after review and successful validation should the same reviewed artifacts be promoted with separate Production configuration, monitoring and rollback arrangements. Only local processing has been exercised.

## Official capability references

- [Schedule an integration](https://docs.oracle.com/en/cloud/paas/application-integration/integrations-user/define-integration-schedule.html).
- [SFTP through the FTP Adapter](https://docs.oracle.com/en/cloud/paas/application-integration/ftp-adapter/ftp-adapter-capabilities.html).
- [Invoke an OCI Function](https://docs.oracle.com/en/cloud/paas/application-integration/integrations-user/invoke-oracle-cloud-infrastructure-functions-directly-from-integration-oci-function-action.html).
- [Python function packaging](https://docs.oracle.com/en-us/iaas/Content/Functions/Tasks/functions-codeonly-python.htm).

These document platform capabilities, not an existing deployment.
