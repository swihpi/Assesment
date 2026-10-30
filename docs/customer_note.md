# Customer note: why this CSV, and why might it change?

Assume a sports organisation uses a CRM report to supply customer profiles to its analytics workflow. The source database remains the system of record. The integration receives a selected export of ID, name, region, customer-since date, last-purchase date, and a marketing-permission field.

For this hypothetical case, no usable CRM API or supported application-specific connector is available for the chosen CRM version and integration environment, including through OIC. The CRM does have a scheduled report/export facility and native delivery to a customer-controlled SFTP location. The customer configures it to deliver a full snapshot daily at 02:00 UTC. Its delivery job publishes the completed CSV to SFTP; OIC retrieves it using the FTP Adapter configured for SFTP. Autonomous Database is the proposed destination for approved data. This is a proposed operating context, not an export or transfer job implemented in this package. If current permissions are needed immediately, a daily report is insufficient; the source interface and downstream permission checks would need review.

The plausible change occurs in the **report interface**: an administrator updates a report template or an upgrade changes its displayed headings. The database need not rename its columns. `Customer ID` might arrive as `fan_id`, fields can be reordered, or a new loyalty column can appear. These are explicit synthetic assumptions, not claims about any actual CRM product.

Values can be incomplete because an older import lacked a field, a form made it optional, or a merge included profiles from another source. An empty last-purchase date may be legitimate. A blank permission should remain unknown. Repeated rows can arise from a repeated export or a report including more than one source row per customer. The program's contract expects one consistent profile per ID, so conflicting copies need source clarification.

Automating file delivery does not settle these meanings. The processor turns approved equivalents into consistent values, preserves uncertainty, and reports information that cannot safely be released. It produces a dependable input to later analysis rather than assuming that a successfully transferred file is correct.

The sports context comes from Stefan's supplied experience of the OCI Think Tank. Aggregate sentiment could inform a future review of campaign timing, while customer profiles could inform audience selection. This program implements neither sentiment analysis nor campaign targeting. Aggregate sentiment does not establish an individual customer's sentiment.

The demonstrated customer outcome is a consistent profile export with visible exceptions and an explainable READY/HELD decision. No marketing activity or commercial uplift is claimed.

For deployment, OIC could run collection daily and call a separately hosted Python function before routing approved data to a staging destination. This cloud path remains proposed. New code and mappings are validated in Development or Test first; only a reviewed artifacts is promoted to Production. The assessment has used synthetic local data only.
