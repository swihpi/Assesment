# Validation evidence

The automated checks use dummy data in local Development/Test environments. They verify the local file processor, not the proposed cloud connections or campaign controls.

## Run the checks

```sh
python3 -m unittest discover -s tests -v
```

The suite checks expected customer IDs and counts, approved heading changes, required fields and dates, permission values, repeated records, malformed files, configuration errors and output-write failures. It also checks that the input is preserved and that incomplete processing does not release usable output. The GitHub workflow runs on Python 3.12 and 3.14.

## Expected results

| Input | Expected outcome |
| --- | --- |
| `samples/valid.csv` | Three approved records. |
| `samples/renamed_report.csv` | The same three approved records. |
| `samples/bad_values.csv` | F001 and F004 approved; two records reported for correction. |
| `samples/breaking_change.csv` | BLOCKED; no cleaned CSV. |

For field-level expectations, see [expected outcomes](../samples/expected_outcomes.md). Recorded execution is available in the [test log](evidence/codex-run-current.txt).

## Larger case

```sh
python3 tools/large_case_demo.py --output runs/demo-10000
```

This generates 10,000 records, deliberately including 800 missing IDs, and runs the same processor. Independent checks verify the exact 9,200 approved IDs, 800 correction cases and unchanged received file. The command retains its input and outputs; use a new output folder for each run. See the [recorded execution](evidence/large-case-current.txt).

These checks establish behaviour for the supplied scenarios. They do not prove that source facts are correct or that an OIC/ADW deployment works. Benchmark methodology and capacity limits are described in the README.

## Inventory of the 60 tests

This inventory explains the intended purpose of the current automated tests. It was prepared with AI assistance from the test code. It is a guide to the suite, not an independent verification of its completeness or correctness. Some tests overlap because they were added during successive reviews. A test method may check several related cases; the count refers to methods, not individual assertions.

### test_processor.py — 24 tests

| Test | Purpose |
| --- | --- |
| `test_valid_output_matches_predefined_expected_records` | Compares the complete valid output with predefined expected records; checks three approvals, completion and unchanged input. |
| `test_confirmed_aliases_reordering_whitespace_and_permission_forms` | Checks that approved heading aliases, reordered columns, whitespace and permission equivalents produce the same expected customer output. |
| `test_additive_drift_warns_and_continues` | Checks that an unused extra column produces a warning while valid records continue, without adding that column to cleaned output. |
| `test_breaking_drift_holds_before_processing` | Checks that an unfamiliar required heading blocks release, reports the missing field and produces no cleaned CSV. |
| `test_bad_values_release_valid_records_with_correction_reports` | Checks partial release of the four-record example, field-specific corrective messages and combined diagnostics for several problems on one record. |
| `test_unknown_permission_never_becomes_yes` | Checks that missing or unrecognised permission stays UNKNOWN with warnings, rather than becoming YES. |
| `test_identical_duplicates_are_removed_and_conflicts_excluded` | Checks that identical valid copies are removed while conflicting records under one ID are reported and excluded. |
| `test_only_identical_duplicates_can_release` | Checks that two identical valid copies release one record and preserve leading zeroes in its ID. |
| `test_invalid_record_cannot_hide_a_conflict_for_a_known_id` | Checks that an invalid same-ID record still causes the apparently valid counterpart to be excluded as conflicting information. |
| `test_no_usable_records_never_releases` | Checks that a file with no valid records is BLOCKED and produces no cleaned output. |
| `test_broken_quoting_and_wrong_record_width_hold` | Checks that broken quoting and rows with too few fields block release. |
| `test_utf8_bom_and_quoted_multiline_names_are_read_as_records` | Checks support for a UTF-8 file marker and a quoted multiline name, counted as one record and tidied correctly. |
| `test_bad_encoding_is_reported_without_guessing` | Checks that invalid UTF-8 blocks processing without guessing another encoding. |
| `test_ambiguous_alias_columns_hold` | Checks that two headings mapping to the same output field are rejected as ambiguous. |
| `test_empty_source_and_empty_snapshot_hold` | Checks that an empty file and a headings-only file both block approval. |
| `test_same_file_reruns_are_deterministic_and_never_overwrite` | Checks identical cleaned output across fresh runs and refusal to overwrite an existing run folder. |
| `test_configuration_can_add_a_confirmed_alias_without_code_changes` | Checks that adding an approved heading alias in temporary configuration enables processing without changing Python. |
| `test_report_write_failure_never_creates_a_ready_marker` | Simulates report-writing failure and checks that no completion marker is created. |
| `test_cli_exit_status_and_missing_input` | Checks command-line return codes for valid, partial, blocked and missing-input cases; missing input must not create a run folder. |
| `test_ten_thousand_records_preserve_800_exceptions_and_release_9200` | Generates 10,000 records with 800 missing IDs; checks exact approved IDs, all statuses, correction counts and preserved input. |
| `test_no_and_unknown_remain_distinct` | Checks that explicit opt-out becomes NO while blank permission remains UNKNOWN with a warning status. |
| `test_customerdata_id_needs_an_explicitly_approved_mapping` | Checks that customerdata_id blocks before an explicit alias is supplied and succeeds afterward, preserving the identifier. |
| `test_structure_error_after_valid_rows_prevents_any_release` | Checks that a structural error after a valid record blocks all release and marks the earlier candidate NOT_RELEASED. |
| `test_completion_marker_failure_cannot_look_like_success` | Simulates failure writing the final success marker and checks that the interrupted run has no completion marker. |

### test_review_regressions.py — 15 tests

| Test | Purpose |
| --- | --- |
| `test_valid_input_and_snapshot_preserved` | Checks a valid record with temporary configuration, normalised permission and unchanged original and received files. |
| `test_empty_record_is_counted_and_rejected` | Checks that a six-field empty customer record is counted and reported for missing required values, rather than silently skipped. |
| `test_only_empty_record_blocks_release` | Checks that a file containing only an empty customer record is counted, rejected and blocked. |
| `test_physical_blank_lines_are_skipped` | Checks that genuinely blank physical lines do not create extra customer records. |
| `test_empty_wrong_width_records_block_release` | Checks that empty-looking rows with the wrong field count block the entire input, including earlier valid candidates. |
| `test_permission_whitespace_and_case_match_mapping` | Checks that approved permission values match despite repeated spaces, tabs, line breaks or different capitalisation. |
| `test_unknown_permission_stays_unknown` | Checks that an unconfigured permission becomes UNKNOWN with a warning and ACCEPTED_WITH_WARNING status. |
| `test_identical_invalid_duplicates_report_date_error` | Checks that identical invalid copies are both reported for their date error, rather than treated as valid duplicates. |
| `test_conflict_retains_field_errors_and_counts_each_record_once` | Checks that same-ID conflicts retain additional date errors, count each rejected record once and still release an unrelated valid customer. |
| `test_conflicting_valid_rows_are_both_rejected` | Checks that individually valid records with the same ID but different names are both rejected as conflicting. |
| `test_identical_valid_duplicates_still_removed` | Checks that equivalent permission formatting allows otherwise identical valid records to be deduplicated. |
| `test_malformed_csv_blocks_release` | Checks that an unterminated quoted value after valid data blocks release and produces a source-contract error. |
| `test_invalid_utf8_blocks_release` | Checks that invalid UTF-8 appended to the input blocks release. |
| `test_existing_output_is_preserved` | Checks that an existing output folder and its sentinel file remain untouched when reuse is refused. |
| `test_cli_success_exceptions_blocked_and_error_exit_codes` | Checks command-line statuses, return codes, output files and completion markers for success, partial release and blocking; reruns into existing folders must fail. |

### test_diagnostics.py — 21 tests

| Test | Purpose |
| --- | --- |
| `test_bad_mapping_messages_identify_file_and_row` | Exercises multiple malformed mapping configurations and checks that errors identify the configuration file and relevant row or header problem. |
| `test_mapping_invalid_utf8_has_clear_message` | Checks that invalid UTF-8 in a mapping file gives a clear configuration-specific message. |
| `test_mapping_bom_crlf_and_normalized_keys_are_supported` | Checks that mapping files support a UTF-8 marker, Windows line endings and normalised mapping keys. |
| `test_bad_configuration_stops_before_creating_output` | Checks that invalid configuration stops processing before a run folder is created. |
| `test_required_fields_are_independent_of_output_order` | Checks that the required-field rules do not accidentally depend on the general output-field order. |
| `test_nfc_names_and_regions_do_not_create_false_conflicts` | Checks that equivalent Unicode representations of accented names and regions do not create false same-ID conflicts. |
| `test_customer_ids_remain_exact_and_case_sensitive` | Checks that IDs retain exact case and Unicode representation, rather than being silently merged. |
| `test_dates_require_ascii_digits` | Checks that dates using non-ASCII digit characters are rejected under the agreed numeric date format. |
| `test_multiline_record_ranges_survive_blanks_rejections_and_duplicates` | Checks exact physical line ranges for multiline records, rejected records and duplicate or permission warnings, despite blank lines. |
| `test_structure_error_reports_physical_range` | Checks that a wrong-width record is reported with its physical source-line range. |
| `test_provenance_matches_snapshot_and_utc_time` | Checks the input fingerprint, processor version and UTC start timestamp, including their presence in the summary and log. |
| `test_blocked_cli_explains_missing_header_on_stderr` | Checks that a blocked command explains the missing customer-ID heading and zero release on the error output channel. |
| `test_usage_error_and_version_are_distinct` | Checks that missing command arguments return usage error 2, while a version request succeeds and reports the version. |
| `test_debug_controls_traceback_for_operational_error` | Checks concise handling of a missing file normally and a technical traceback when debug mode is enabled. |
| `test_unexpected_programming_error_is_identified_and_debug_reraises` | Simulates an unexpected programming error; checks that normal mode identifies its type and debug mode exposes the original exception. |
| `test_report_failure_logs_error_and_provenance_without_success_marker` | Simulates report failure; checks error logging with the input fingerprint and absence of completion markers. |
| `test_snapshot_failure_after_mkdir_is_logged` | Simulates failure copying the original input after folder creation; checks that it is logged without a success marker. |
| `test_failed_diagnostic_write_preserves_original_exception` | Simulates failure of both report writing and error logging; checks that the original exception is not hidden by the logging failure. |
| `test_existing_output_log_is_not_modified_on_failure` | Checks that refusing an existing output folder does not modify its previous run log. |
| `test_semicolon_delimiter_blocks_release` | Checks that semicolon-separated input is blocked rather than silently interpreted as the agreed comma-separated format. |
| `test_decode_failure_after_valid_prefix_blocks_all_release` | Adds invalid UTF-8 after 2,000 valid records; checks no release and no guessed source-line location for the decoding failure. |
