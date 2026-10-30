# Programmatic deployment and environment promotion

The working assessment program is standalone. The customer deployment below is proposed and has not been provisioned or tested.

1. Assume no usable API or supported application-specific CRM connector is available, including through OIC. The CRM supports scheduled CSV reports and native SFTP delivery. It generates a full daily snapshot at 02:00 UTC and publishes the completed file to customer-controlled SFTP. OIC retrieves it with its FTP Adapter configured for SFTP. The collection schedule follows the expected handoff. File completion, missing exports, and previously processed files need an agreed delivery policy.
2. OIC invokes a Python function hosted in OCI Functions through the OCI Function action. The rules validate and normalize the data and return an outcome or output references.
3. OIC routes READY output to a designated staging destination, such as Autonomous Database/ADW. The database receives approved data; it does not pull the CRM export. HELD output follows the error path and is not loaded as an approved dataset.

The function needs a handler and cloud input/output interface; the local command-line/folder interface cannot be deployed unchanged. Access, connectivity, payload size, timeout, and retry behavior must be verified in the selected environment. Local tests do not verify these cloud concerns.

## Development or Test before Production

We never use Production as the first place to try a new script, mapping, or integration change.

- **Local development:** use synthetic fixtures, inspect expected results, and run tests.
- **Dedicated Development/Test integration environment:** deploy the function and OIC flow with test connections and destinations. Validate scheduling, transfer, checks, held batches, logs, and downstream loading. Fix and repeat there.
- **Production promotion:** after review and successful validation, promote the same reviewed artifacts with separate Production configuration. Use controlled deployment verification and monitoring, retaining the last approved artifacts for rollback.

The local stage has been exercised. The cloud Development/Test and Production stages remain a plan. No Production system or real customer data was used.

## Official documentation

- [Define the OIC integration schedule](https://docs.oracle.com/en/cloud/paas/application-integration/integrations-user/define-integration-schedule.html).
- [Invoke OCI Functions through an OIC action](https://docs.oracle.com/en/cloud/paas/application-integration/integrations-user/invoke-oracle-cloud-infrastructure-functions-directly-from-integration-oci-function-action.html).
- [Package a Python function](https://docs.oracle.com/en-us/iaas/Content/Functions/Tasks/functions-codeonly-python.htm).

- [FTP Adapter capabilities, including SFTP](https://docs.oracle.com/en/cloud/paas/application-integration/ftp-adapter/ftp-adapter-capabilities.html).

These sources confirm capabilities, not an existing assessment deployment.
