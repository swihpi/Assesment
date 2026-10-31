"""Independent regression cases for diagnostics, provenance and configuration."""

import contextlib
import csv
from datetime import datetime, timezone
import hashlib
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import process_export as processor

ROOT = Path(__file__).resolve().parents[1]


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "input.csv"
        self.output = self.root / "run"
        self.valid = ["C1", "Alice", "West", "2026-01-01", "", "yes"]

    def write_input(self, rows):
        with self.source.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(processor.FIELDS)
            writer.writerows(rows)

    def read(self, name):
        with (self.output / name).open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def cli(self, *options):
        return subprocess.run([sys.executable, str(ROOT / "process_export.py"), *options],
                              capture_output=True, text=True, timeout=15)

    def test_bad_mapping_messages_identify_file_and_row(self):
        cases = (
            ("", "row 1: mapping file is empty"),
            ("yes,YES\nno,NO\n", "row 1: expected header"),
            ("source_value,output_value\n", "mapping contains no data rows"),
            ("source_value,output_value\nyes,YES,extra\n", "row 2: expected 2 columns, found 3"),
            ("source_value,output_value\nyes\n", "row 2: expected 2 columns, found 1"),
            ("source_value,output_value\n\n", "row 2: expected 2 columns, found 0"),
            ("source_value,output_value\n,YES\n", "row 2: empty or repeated source value"),
            ("source_value,output_value\nyes,YES\n YES ,NO\n", "row 3: empty or repeated source value"),
            ("source_value,output_value\nyes,maybe\n", "row 2: unsupported output value"),
            ("source_value,output_value\nyes,\n", "row 2: unsupported output value"),
            ('source_value,output_value\n"unterminated', "row 2: invalid CSV"),
        )
        path = self.root / "permission_values.csv"
        for text, expected in cases:
            with self.subTest(expected=expected):
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(processor.ConfigurationError) as caught:
                    processor.load_mapping(path, ("source_value", "output_value"), {"YES", "NO"})
                self.assertIn(path.name, str(caught.exception))
                self.assertIn(expected, str(caught.exception))

    def test_mapping_invalid_utf8_has_clear_message(self):
        path = self.root / "permission_values.csv"
        path.write_bytes(b"source_value,output_value\nyes,\xff\n")
        with self.assertRaisesRegex(processor.ConfigurationError, "permission_values.csv: mapping must be valid UTF-8"):
            processor.load_mapping(path, ("source_value", "output_value"), {"YES", "NO"})

    def test_mapping_bom_crlf_and_normalized_keys_are_supported(self):
        path = self.root / "permission_values.csv"
        path.write_bytes(b"\xef\xbb\xbfsource_value,output_value\r\n Opt  In , YES \r\n")
        self.assertEqual(processor.load_mapping(path, ("source_value", "output_value"), {"YES", "NO"}),
                         {"opt in": "YES"})

    def test_bad_configuration_stops_before_creating_output(self):
        self.write_input([self.valid])
        config = self.root / "config"
        shutil.copytree(ROOT / "config", config)
        (config / "permission_values.csv").write_text("yes,YES\n", encoding="utf-8")
        with self.assertRaises(processor.ConfigurationError):
            processor.process_file(self.source, self.output, config)
        self.assertFalse(self.output.exists())

    def test_required_fields_are_independent_of_output_order(self):
        raw = dict(zip(processor.FIELDS, ["", "", "", "", "", "yes"]))
        with patch.object(processor, "FIELDS", tuple(reversed(processor.FIELDS))):
            _, problems = processor.normalize(raw, 1, {"yes": "YES"}, [])
        self.assertEqual(problems, [(field, "MISSING_VALUE") for field in processor.REQUIRED_FIELDS])

    def test_nfc_names_and_regions_do_not_create_false_conflicts(self):
        self.write_input([["C1", "Jos\u00e9", "Qu\u00e9bec", *self.valid[3:]],
                          ["C1", "Jose\u0301", "Que\u0301bec", *self.valid[3:]]])
        result = processor.process_file(self.source, self.output)
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["identical_duplicates_removed"], 1)
        self.assertEqual(self.read("cleaned.csv")[0]["name"], "Jos\u00e9")
        self.assertEqual(self.read("cleaned.csv")[0]["region"], "Qu\u00e9bec")

    def test_customer_ids_remain_exact_and_case_sensitive(self):
        ids = ["C1", "c1", "\u00e9", "e\u0301"]
        self.write_input([[customer_id, *self.valid[1:]] for customer_id in ids])
        result = processor.process_file(self.source, self.output)
        self.assertEqual(result["released_records"], 4)
        self.assertEqual([row["customer_id"] for row in self.read("cleaned.csv")], ids)

    def test_dates_require_ascii_digits(self):
        self.write_input([[*self.valid[:3], "\u0662\u0660\u0662\u0666-01-01", "", "yes"]])
        self.assertEqual(processor.process_file(self.source, self.output)["status"], "BLOCKED")
        self.assertEqual(self.read("rejected.csv")[0]["code"], "INVALID_DATE")

    def test_multiline_record_ranges_survive_blanks_rejections_and_duplicates(self):
        self.source.write_text(','.join(processor.FIELDS) + '\n\n'
                               'C1,"Alex\nMorgan",West,2026-01-01,,maybe\n'
                               'C2,Pat,West,bad,,yes\n\n'
                               'C1,"Alex\nMorgan",West,2026-01-01,,maybe\n', encoding="utf-8")
        processor.process_file(self.source, self.output)
        statuses = self.read("record_status.csv")
        self.assertEqual([(r["record"], r["source_line_start"], r["source_line_end"]) for r in statuses],
                         [("1", "3", "4"), ("2", "5", "5"), ("3", "7", "8")])
        rejected = self.read("rejected.csv")[0]
        self.assertEqual((rejected["source_line_start"], rejected["source_line_end"]), ("5", "5"))
        warnings = self.read("warnings.csv")
        self.assertEqual([(r["source_line_start"], r["source_line_end"]) for r in warnings],
                         [("3", "4"), ("7", "8"), ("7", "8")])

    def test_structure_error_reports_physical_range(self):
        self.source.write_text(','.join(processor.FIELDS) + '\n\nC1,short\n', encoding="utf-8")
        processor.process_file(self.source, self.output)
        issue = self.read("rejected.csv")[0]
        self.assertEqual((issue["source_line_start"], issue["source_line_end"]), ("3", "3"))

    def test_provenance_matches_snapshot_and_utc_time(self):
        self.write_input([self.valid])
        before = datetime.now(timezone.utc)
        result = processor.process_file(self.source, self.output)
        after = datetime.now(timezone.utc)
        digest = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.assertEqual(result["input_sha256"], digest)
        self.assertEqual(result["processor_version"], processor.VERSION)
        started = datetime.fromisoformat(result["started_at_utc"])
        self.assertTrue(before <= started <= after)
        self.assertEqual(started.utcoffset().total_seconds(), 0)
        for name in ("summary.txt", "run.log"):
            text = (self.output / name).read_text()
            for key in ("input_sha256", "processor_version", "started_at_utc"):
                self.assertIn(f"{key}: {result[key]}", text)

    def test_blocked_cli_explains_missing_header_on_stderr(self):
        result = self.cli("--input", str(ROOT / "samples/breaking_change.csv"), "--output", str(self.output))
        self.assertEqual(result.returncode, 3)
        self.assertEqual(result.stdout, "")
        self.assertIn("Missing required columns: customer_id", result.stderr)
        self.assertIn("No records released", result.stderr)

    def test_usage_error_and_version_are_distinct(self):
        self.assertEqual(self.cli().returncode, 2)
        result = self.cli("--version")
        self.assertEqual(result.returncode, 0)
        self.assertIn(processor.VERSION, result.stdout)

    def test_debug_controls_traceback_for_operational_error(self):
        args = ["--input", str(self.root / "missing.csv"), "--output", str(self.output)]
        normal = self.cli(*args)
        debug = self.cli(*args, "--debug")
        self.assertEqual((normal.returncode, debug.returncode), (1, 1))
        self.assertNotIn("Traceback", normal.stderr)
        self.assertIn("Use --debug", normal.stderr)
        self.assertIn("Traceback", debug.stderr)
        self.assertIn("FileNotFoundError", debug.stderr)

    def test_unexpected_programming_error_is_identified_and_debug_reraises(self):
        args = ["--input", str(self.source), "--output", str(self.output)]
        stderr = io.StringIO()
        with patch.object(processor, "process_file", side_effect=KeyError("example bug")):
            with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as caught:
                processor.main(args)
            self.assertEqual(caught.exception.code, 1)
            self.assertIn("UNEXPECTED ERROR (KeyError)", stderr.getvalue())
            with self.assertRaises(KeyError):
                processor.main([*args, "--debug"])

    def test_report_failure_logs_error_and_provenance_without_success_marker(self):
        self.write_input([self.valid])
        with patch.object(processor, "write_csv", side_effect=OSError("simulated report failure")):
            with self.assertRaisesRegex(OSError, "simulated report failure"):
                processor.process_file(self.source, self.output)
        text = (self.output / "run.log").read_text()
        self.assertIn("ERROR OSError: simulated report failure", text)
        self.assertIn(hashlib.sha256(self.source.read_bytes()).hexdigest(), text)
        for marker in ("READY", "READY_WITH_EXCEPTIONS", "BLOCKED", "FAILED"):
            self.assertFalse((self.output / marker).exists())

    def test_snapshot_failure_after_mkdir_is_logged(self):
        self.write_input([self.valid])
        with patch.object(processor.shutil, "copyfileobj", side_effect=OSError("simulated copy failure")):
            with self.assertRaisesRegex(OSError, "simulated copy failure"):
                processor.process_file(self.source, self.output)
        self.assertIn("simulated copy failure", (self.output / "run.log").read_text())
        self.assertFalse((self.output / "READY").exists())

    def test_failed_diagnostic_write_preserves_original_exception(self):
        self.write_input([self.valid])
        original = Path.open
        def failing_open(path, *args, **kwargs):
            if path.name == "run.log":
                raise OSError("log also failed")
            return original(path, *args, **kwargs)
        with patch.object(processor, "write_csv", side_effect=OSError("original failure")), \
                patch.object(Path, "open", failing_open):
            with self.assertRaisesRegex(OSError, "original failure"):
                processor.process_file(self.source, self.output)

    def test_existing_output_log_is_not_modified_on_failure(self):
        self.output.mkdir()
        log = self.output / "run.log"
        log.write_text("prior run", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            processor.process_file(self.source, self.output)
        self.assertEqual(log.read_text(), "prior run")

    def test_semicolon_delimiter_blocks_release(self):
        self.source.write_text(';'.join(processor.FIELDS) + '\n' + ';'.join(self.valid) + '\n', encoding="utf-8")
        result = processor.process_file(self.source, self.output)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse((self.output / "cleaned.csv").exists())

    def test_decode_failure_after_valid_prefix_blocks_all_release(self):
        prefix = (','.join(processor.FIELDS) + '\n' + (','.join(self.valid) + '\n') * 2000).encode()
        self.source.write_bytes(prefix + b'\xff\n')
        result = processor.process_file(self.source, self.output)
        self.assertGreater(result["parsed_records"], 0)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["released_records"], 0)
        self.assertFalse((self.output / "cleaned.csv").exists())
        issue = self.read("rejected.csv")[0]
        self.assertEqual((issue["source_line_start"], issue["source_line_end"]), ("", ""))


if __name__ == "__main__":
    unittest.main()
