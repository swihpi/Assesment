import csv
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from process_export import FIELDS, process_file


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class ProcessorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)

    def run_sample(self, name, **options):
        output = self.work / name.removesuffix(".csv")
        summary = process_file(ROOT / "samples" / name, output, **options)
        return summary, output

    def write_source(self, rows, header=FIELDS, encoding="utf-8"):
        path = self.work / "input.csv"
        with path.open("w", encoding=encoding, newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(rows)
        return path

    def test_valid_output_matches_predefined_expected_records(self):
        source = ROOT / "samples/valid.csv"
        before = source.read_bytes()
        result, output = self.run_sample("valid.csv")
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["valid_records"], 3)
        self.assertEqual(read_csv(output / "cleaned.csv"), read_csv(ROOT / "samples/expected/cleaned_valid.csv"))
        self.assertTrue((output / "READY").exists())
        self.assertEqual(source.read_bytes(), before)

    def test_confirmed_aliases_reordering_whitespace_and_permission_forms(self):
        result, output = self.run_sample("renamed_report.csv")
        self.assertEqual(result["status"], "READY")
        self.assertEqual(read_csv(output / "cleaned.csv"), read_csv(ROOT / "samples/expected/cleaned_valid.csv"))

    def test_additive_drift_warns_and_continues(self):
        result, output = self.run_sample("extra_column.csv")
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["valid_records"], 1)
        self.assertIn("EXTRA_COLUMN", {row["code"] for row in read_csv(output / "warnings.csv")})
        self.assertNotIn("loyalty_points", read_csv(output / "cleaned.csv")[0])

    def test_breaking_drift_holds_before_processing(self):
        result, output = self.run_sample("breaking_change.csv")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["source_fully_parsed"], "false")
        self.assertIn("customer_id", read_csv(output / "rejected.csv")[-1]["message"])
        self.assertFalse((output / "cleaned.csv").exists())

    def test_bad_values_release_valid_records_with_correction_reports(self):
        result, output = self.run_sample("bad_values.csv")
        self.assertEqual((result["parsed_records"], result["valid_records"], result["rejected_records"]), (4, 2, 2))
        codes = {row["code"] for row in read_csv(output / "rejected.csv")}
        self.assertEqual(codes, {"MISSING_VALUE", "INVALID_DATE"})
        self.assertEqual(result["status"], "READY_WITH_EXCEPTIONS")
        self.assertTrue((output / "READY_WITH_EXCEPTIONS").exists())
        self.assertEqual([r["customer_id"] for r in read_csv(output / "cleaned.csv")], ["F001", "F004"])
        self.assertEqual(result["released_records"], 2)

        diagnostics = {row["code"]: row for row in read_csv(output / "rejected.csv")}
        self.assertEqual(diagnostics["MISSING_VALUE"]["message"], "Customer ID is missing.")
        self.assertIn("Do not invent an ID.", diagnostics["MISSING_VALUE"]["next_action"])
        self.assertEqual(diagnostics["INVALID_DATE"]["message"], "Joining date is not a valid YYYY-MM-DD calendar date.")
        self.assertIn("authoritative CRM record", diagnostics["INVALID_DATE"]["next_action"])
        source = self.write_source([["", "Alex", "NY", "2024-02-30", "", "Y"]])
        multiple = self.work / "multiple-errors"
        summary = process_file(source, multiple)
        errors = read_csv(multiple / "rejected.csv")
        self.assertEqual((summary["rejected_records"], len(errors)), (1, 1))
        self.assertEqual(errors[0]["code"], "MISSING_VALUE; INVALID_DATE")
        self.assertIn("Customer ID is missing.", errors[0]["message"])
        self.assertIn("Joining date is not a valid", errors[0]["message"])
        self.assertIn("Do not invent an ID.", errors[0]["next_action"])
        self.assertIn("Confirm joining date", errors[0]["next_action"])

    def test_unknown_permission_never_becomes_yes(self):
        result, output = self.run_sample("unknown_permission.csv")
        self.assertEqual(result["status"], "READY")
        self.assertEqual([row["marketing_permission"] for row in read_csv(output / "cleaned.csv")], ["UNKNOWN", "UNKNOWN"])
        self.assertEqual(result["warnings"], 2)

    def test_identical_duplicates_are_removed_and_conflicts_excluded(self):
        result, output = self.run_sample("duplicates.csv")
        self.assertEqual(result["status"], "READY_WITH_EXCEPTIONS")
        self.assertEqual((result["parsed_records"], result["valid_records"], result["rejected_records"], result["identical_duplicates_removed"]), (4, 1, 2, 1))
        self.assertEqual({row["customer_id"] for row in read_csv(output / "rejected.csv")}, {"F002"})
        self.assertEqual({row["code"] for row in read_csv(output / "rejected.csv")}, {"CONFLICTING_RECORDS_FOR_ID"})
        self.assertEqual([r["customer_id"] for r in read_csv(output / "cleaned.csv")], ["F001"])

    def test_only_identical_duplicates_can_release(self):
        row = ["001", "Alex Morgan", "NY", "2022-04-15", "", "Y"]
        source = self.write_source([row, row])
        result = process_file(source, self.work / "run")
        cleaned = read_csv(self.work / "run/cleaned.csv")
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["identical_duplicates_removed"], 1)
        self.assertEqual(cleaned[0]["customer_id"], "001")
        self.assertEqual(len(cleaned), 1)

    def test_invalid_record_cannot_hide_a_conflict_for_a_known_id(self):
        source = self.write_source([
            ["F1", "Alex", "NY", "2022-04-15", "", "Y"],
            ["F1", "Alex", "NY", "not-a-date", "", "N"],
        ])
        result = process_file(source, self.work / "run")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["rejected_records"], 2)

    def test_no_usable_records_never_releases(self):
        source = self.write_source([["", "Alex", "NY", "bad", "", "Y"]])
        result = process_file(source, self.work / "run")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse((self.work / "run/cleaned.csv").exists())

    def test_broken_quoting_and_wrong_record_width_hold(self):
        result, output = self.run_sample("malformed.csv")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["source_fully_parsed"], "false")
        self.assertFalse((output / "cleaned.csv").exists())
        source = self.write_source([["F1", "too few fields"]])
        result = process_file(source, self.work / "wrong-width")
        self.assertEqual(result["status"], "BLOCKED")

    def test_utf8_bom_and_quoted_multiline_names_are_read_as_records(self):
        source = self.write_source([
            ["F1", "Alex\nMorgan", "NY", "2022-04-15", "", "Y"],
        ], encoding="utf-8-sig")
        result = process_file(source, self.work / "run")
        self.assertEqual(result["parsed_records"], 1)
        self.assertEqual(read_csv(self.work / "run/cleaned.csv")[0]["name"], "Alex Morgan")

    def test_bad_encoding_is_reported_without_guessing(self):
        source = self.work / "bad-encoding.csv"
        source.write_bytes(b"customer_id,name\nF1,\xff\n")
        result = process_file(source, self.work / "run")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["source_fully_parsed"], "false")

    def test_ambiguous_alias_columns_hold(self):
        source = self.write_source([], header=list(FIELDS) + ["Fan_ID"])
        result = process_file(source, self.work / "run")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("Two source columns", read_csv(self.work / "run/rejected.csv")[0]["message"])

    def test_empty_source_and_empty_snapshot_hold(self):
        source = self.work / "empty.csv"
        source.write_text("", encoding="utf-8")
        self.assertEqual(process_file(source, self.work / "empty-run")["status"], "BLOCKED")
        source = self.write_source([])
        self.assertEqual(process_file(source, self.work / "header-run")["status"], "BLOCKED")

    def test_same_file_reruns_are_deterministic_and_never_overwrite(self):
        source = ROOT / "samples/valid.csv"
        first = process_file(source, self.work / "one")
        second = process_file(source, self.work / "two")
        self.assertEqual((self.work / "one/cleaned.csv").read_bytes(), (self.work / "two/cleaned.csv").read_bytes())
        with self.assertRaises(FileExistsError):
            process_file(source, self.work / "one")

    def test_configuration_can_add_a_confirmed_alias_without_code_changes(self):
        config = self.work / "config"
        config.mkdir()
        for name in ("column_aliases.csv", "permission_values.csv"):
            (config / name).write_bytes((ROOT / "config" / name).read_bytes())
        with (config / "column_aliases.csv").open("a", encoding="utf-8") as handle:
            handle.write("supporter_number,customer_id\n")
        result, output = self.run_sample("breaking_change.csv", config_dir=config)
        self.assertEqual(result["status"], "READY")
        self.assertEqual(read_csv(output / "cleaned.csv")[0]["customer_id"], "F001")

    def test_report_write_failure_never_creates_a_ready_marker(self):
        output = self.work / "interrupted"
        with patch("process_export.write_csv", side_effect=OSError("simulated disk failure")):
            with self.assertRaises(OSError):
                process_file(ROOT / "samples/valid.csv", output)
        self.assertFalse((output / "READY").exists())
        self.assertFalse((output / "BLOCKED").exists())
        self.assertFalse((output / "READY_WITH_EXCEPTIONS").exists())

    def test_cli_exit_status_and_missing_input(self):
        def invoke(sample, name):
            return subprocess.run([
                sys.executable, str(ROOT / "process_export.py"),
                "--input", str(ROOT / "samples" / sample),
                "--output", str(self.work / name),
            ], capture_output=True, text=True)
        self.assertEqual(invoke("valid.csv", "valid-cli").returncode, 0)
        self.assertEqual(invoke("bad_values.csv", "partial-cli").returncode, 0)
        self.assertEqual(invoke("breaking_change.csv", "blocked-cli").returncode, 3)
        failure = invoke("does-not-exist.csv", "missing-cli")
        self.assertEqual(failure.returncode, 1)
        self.assertFalse((self.work / "missing-cli").exists())


    def test_ten_thousand_records_preserve_800_exceptions_and_release_9200(self):
        rows = [[f"F{i:05d}" if i >= 800 else "", f"Person {i}", "NY", "2022-04-15", "", "Y"]
                for i in range(10000)]
        source = self.write_source(rows)
        original = source.read_bytes()
        output = self.work / "large-run"
        result = process_file(source, output)
        self.assertEqual(result["status"], "READY_WITH_EXCEPTIONS")
        self.assertEqual((result["parsed_records"], result["released_records"], result["rejected_records"]), (10000, 9200, 800))
        self.assertEqual((output / "received.csv").read_bytes(), original)
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual({r["customer_id"] for r in read_csv(output / "cleaned.csv")},
                         {f"F{i:05d}" for i in range(800, 10000)})
        states = read_csv(output / "record_status.csv")
        self.assertEqual(len(states), 10000)
        self.assertEqual(sum(r["validation_status"] == "NEEDS_CORRECTION" for r in states), 800)

    def test_no_and_unknown_remain_distinct(self):
        source = self.write_source([
            ["F1", "Alex", "NY", "2022-04-15", "", "N"],
            ["F2", "Casey", "CA", "2022-04-15", "", ""],
        ])
        output = self.work / "permissions"
        self.assertEqual(process_file(source, output)["status"], "READY")
        self.assertEqual([r["marketing_permission"] for r in read_csv(output / "cleaned.csv")], ["NO", "UNKNOWN"])
        self.assertEqual([r["validation_status"] for r in read_csv(output / "record_status.csv")],
                         ["ACCEPTED", "ACCEPTED_WITH_WARNING"])

    def test_customerdata_id_needs_an_explicitly_approved_mapping(self):
        source = self.write_source([["001", "Alex", "NY", "2022-04-15", "", "Y"]],
                                   header=["customerdata_id", *FIELDS[1:]])
        blocked = self.work / "unapproved"
        self.assertEqual(process_file(source, blocked)["status"], "BLOCKED")
        self.assertEqual((blocked / "received.csv").read_bytes(), source.read_bytes())
        config = self.work / "approved-config"
        config.mkdir()
        for name in ("column_aliases.csv", "permission_values.csv"):
            (config / name).write_bytes((ROOT / "config" / name).read_bytes())
        with (config / "column_aliases.csv").open("a", encoding="utf-8") as handle:
            handle.write("customerdata_id,customer_id\n")
        self.assertEqual(process_file(source, self.work / "approved", config)["status"], "READY")
        self.assertEqual(read_csv(self.work / "approved/cleaned.csv")[0]["customer_id"], "001")

    def test_structure_error_after_valid_rows_prevents_any_release(self):
        source = self.write_source([["F1", "Alex", "NY", "2022-04-15", "", "Y"], ["F2", "short row"]])
        output = self.work / "incomplete"
        result = process_file(source, output)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["released_records"], 0)
        self.assertFalse((output / "cleaned.csv").exists())
        self.assertEqual(read_csv(output / "record_status.csv")[0]["validation_status"], "NOT_RELEASED")
        self.assertEqual((output / "received.csv").read_bytes(), source.read_bytes())

    def test_completion_marker_failure_cannot_look_like_success(self):
        original = Path.write_text
        def fail_marker(path, *args, **kwargs):
            if path.name == "READY_WITH_EXCEPTIONS":
                raise OSError("simulated completion-marker failure")
            return original(path, *args, **kwargs)
        output = self.work / "interrupted-partial"
        with patch.object(Path, "write_text", fail_marker):
            with self.assertRaises(OSError):
                process_file(ROOT / "samples/bad_values.csv", output)
        for marker in ["READY", "READY_WITH_EXCEPTIONS", "BLOCKED"]:
            self.assertFalse((output / marker).exists())


if __name__ == "__main__":
    unittest.main()
