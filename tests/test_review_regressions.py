"""Regression tests using synthetic CRM data and isolated temporary folders."""

import csv
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import process_export as validator


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.config = self.root / "config"
        self.config.mkdir()
        self.source = self.root / "source.csv"
        self.output = self.root / "run"
        self.write_csv(self.config / "column_aliases.csv", [
            ("source", "target"), *[(name, name) for name in validator.FIELDS],
        ])
        self.write_csv(self.config / "permission_values.csv", [
            ("source", "target"), ("yes", "YES"), ("no", "NO"), ("opt in", "YES"),
        ])
        self.valid = ["C1", "Alice", "West", "2026-01-01", "", "yes"]

    @staticmethod
    def write_csv(path, rows):
        with path.open("w", encoding="utf-8", newline="") as handle:
            csv.writer(handle).writerows(rows)

    def input_rows(self, rows):
        self.write_csv(self.source, [validator.FIELDS, *rows])

    def report(self, filename):
        with (self.output / filename).open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def process(self):
        summary = validator.process_file(self.source, self.output, self.config)
        self.assertTrue((self.output / summary["status"]).is_file())
        if summary["source_fully_parsed"] == "true":
            self.assertEqual(summary["parsed_records"], summary["valid_records"] +
                             summary["rejected_records"] + summary["identical_duplicates_removed"])
        if summary["status"] == "BLOCKED":
            self.assertEqual(summary["released_records"], 0)
            self.assertFalse((self.output / "cleaned.csv").exists())
            self.assertFalse((self.output / "READY").exists())
            self.assertFalse((self.output / "READY_WITH_EXCEPTIONS").exists())
        else:
            self.assertEqual(len(self.report("cleaned.csv")), summary["released_records"])
        return summary

    def test_valid_input_and_snapshot_preserved(self):
        self.input_rows([self.valid])
        original = self.source.read_bytes()
        summary = self.process()
        self.assertEqual(summary["status"], "READY")
        self.assertEqual(summary["released_records"], 1)
        self.assertEqual(self.report("cleaned.csv")[0]["marketing_permission"], "YES")
        self.assertEqual((self.output / "received.csv").read_bytes(), original)
        self.assertEqual(self.source.read_bytes(), original)

    def test_empty_record_is_counted_and_rejected(self):
        self.input_rows([self.valid, [""] * len(validator.FIELDS)])
        summary = self.process()
        self.assertEqual(summary["status"], "READY_WITH_EXCEPTIONS")
        self.assertEqual(summary["parsed_records"], 2)
        self.assertEqual(summary["rejected_records"], 1)
        rejected = self.report("rejected.csv")[0]
        self.assertEqual(rejected["record"], "2")
        self.assertEqual(rejected["field"].split("; "), list(validator.FIELDS[:4]))
        self.assertEqual(self.report("record_status.csv")[1]["validation_status"], "NEEDS_CORRECTION")

    def test_only_empty_record_blocks_release(self):
        self.input_rows([[""] * len(validator.FIELDS)])
        summary = self.process()
        self.assertEqual(summary["status"], "BLOCKED")
        self.assertEqual(summary["parsed_records"], 1)
        self.assertEqual(summary["rejected_records"], 1)

    def test_physical_blank_lines_are_skipped(self):
        self.input_rows([self.valid])
        with self.source.open("a", encoding="utf-8") as handle:
            handle.write("\n\n")
        summary = self.process()
        self.assertEqual(summary["status"], "READY")
        self.assertEqual(summary["parsed_records"], 1)

    def test_empty_wrong_width_records_block_release(self):
        for values in (["", ""], [" "] * 7, ["   "]):
            with self.subTest(values=values):
                self.output = self.root / ("run-" + str(len(values)))
                self.input_rows([self.valid, values])
                summary = self.process()
                self.assertEqual(summary["status"], "BLOCKED")
                self.assertEqual(summary["source_fully_parsed"], "false")
                self.assertIn("Wrong column count", self.report("rejected.csv")[0]["message"])
                self.assertEqual(self.report("record_status.csv")[0]["validation_status"], "NOT_RELEASED")

    def test_permission_whitespace_and_case_match_mapping(self):
        variants = ("opt  in", "  OPT\tIN  ", "opt\nin", "OpT in")
        self.input_rows([[f"C{index}", *self.valid[1:-1], value]
                         for index, value in enumerate(variants)])
        summary = self.process()
        self.assertEqual(summary["warnings"], 0)
        self.assertEqual([row["marketing_permission"] for row in self.report("cleaned.csv")],
                         ["YES"] * len(variants))

    def test_unknown_permission_stays_unknown(self):
        self.input_rows([[*self.valid[:-1], "not configured"]])
        summary = self.process()
        self.assertEqual(summary["warnings"], 1)
        self.assertEqual(self.report("cleaned.csv")[0]["marketing_permission"], "UNKNOWN")
        self.assertEqual(self.report("record_status.csv")[0]["validation_status"], "ACCEPTED_WITH_WARNING")

    def test_identical_invalid_duplicates_report_date_error(self):
        invalid = [*self.valid[:3], "2026-02-30", "", "yes"]
        self.input_rows([invalid, invalid])
        summary = self.process()
        self.assertEqual(summary["status"], "BLOCKED")
        self.assertEqual(summary["rejected_records"], 2)
        self.assertEqual(summary["identical_duplicates_removed"], 0)
        for row in self.report("rejected.csv"):
            self.assertEqual(row["field"], "member_since")
            self.assertEqual(row["code"], "INVALID_DATE")

    def test_conflict_retains_field_errors_and_counts_each_record_once(self):
        invalid = [*self.valid[:3], "2026-02-30", "", "yes"]
        other = ["C2", *self.valid[1:]]
        self.input_rows([self.valid, invalid, other])
        summary = self.process()
        self.assertEqual(summary["status"], "READY_WITH_EXCEPTIONS")
        self.assertEqual(summary["rejected_records"], 2)
        self.assertEqual(summary["released_records"], 1)
        rejected = self.report("rejected.csv")
        self.assertEqual(rejected[0]["code"], "CONFLICTING_RECORDS_FOR_ID")
        self.assertEqual(rejected[1]["code"], "CONFLICTING_RECORDS_FOR_ID; INVALID_DATE")
        self.assertEqual(rejected[1]["field"], "customer_id; member_since")
        self.assertIn("Joining date", rejected[1]["message"])
        self.assertEqual(self.report("cleaned.csv")[0]["customer_id"], "C2")

    def test_conflicting_valid_rows_are_both_rejected(self):
        other = [self.valid[0], "Bob", *self.valid[2:]]
        self.input_rows([self.valid, other])
        summary = self.process()
        self.assertEqual(summary["status"], "BLOCKED")
        self.assertEqual(summary["rejected_records"], 2)
        self.assertEqual([row["code"] for row in self.report("rejected.csv")],
                         ["CONFLICTING_RECORDS_FOR_ID"] * 2)

    def test_identical_valid_duplicates_still_removed(self):
        equivalent = [*self.valid[:-1], " YES "]
        self.input_rows([self.valid, equivalent])
        summary = self.process()
        self.assertEqual(summary["status"], "READY")
        self.assertEqual(summary["released_records"], 1)
        self.assertEqual(summary["identical_duplicates_removed"], 1)
        self.assertEqual(self.report("record_status.csv")[1]["validation_status"], "DUPLICATE_IGNORED")

    def test_malformed_csv_blocks_release(self):
        self.input_rows([self.valid])
        with self.source.open("a", encoding="utf-8") as handle:
            handle.write('"unterminated')
        summary = self.process()
        self.assertEqual(summary["status"], "BLOCKED")
        self.assertEqual(self.report("rejected.csv")[0]["code"], "SOURCE_CONTRACT")

    def test_invalid_utf8_blocks_release(self):
        self.input_rows([self.valid])
        with self.source.open("ab") as handle:
            handle.write(b"\xff")
        self.assertEqual(self.process()["status"], "BLOCKED")

    def test_existing_output_is_preserved(self):
        self.input_rows([self.valid])
        self.output.mkdir()
        sentinel = self.output / "sentinel.txt"
        sentinel.write_text("keep", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            validator.process_file(self.source, self.output, self.config)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")
        self.assertEqual(list(self.output.iterdir()), [sentinel])

    def test_cli_success_exceptions_blocked_and_error_exit_codes(self):
        cases = (
            ("valid", [self.valid], 0, "READY"),
            ("exceptions", [self.valid, [""] * 6], 0, "READY_WITH_EXCEPTIONS"),
            ("blocked", [[""] * 6], 2, "BLOCKED"),
        )
        for name, rows, exit_code, status in cases:
            with self.subTest(name=name):
                self.input_rows(rows)
                self.output = self.root / name
                command = [sys.executable, str(Path(validator.__file__).resolve()),
                           "--input", str(self.source), "--output", str(self.output),
                           "--config-dir", str(self.config)]
                result = subprocess.run(command, capture_output=True, text=True, timeout=10,
                                        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
                self.assertEqual(result.returncode, exit_code, result.stderr)
                self.assertIn(status + ":", result.stdout)
                self.assertTrue((self.output / status).is_file())
                self.assertEqual((self.output / "cleaned.csv").exists(), status != "BLOCKED")
                retry = subprocess.run(command, capture_output=True, text=True, timeout=10)
                self.assertEqual(retry.returncode, 1)
                self.assertIn("existing runs are never overwritten", retry.stderr)


if __name__ == "__main__":
    unittest.main()
