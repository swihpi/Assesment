#!/usr/bin/env python3
"""Check and normalize one CRM CSV export, using Python's standard library."""

import argparse
import csv
import hashlib
import re
import shutil
import sys
import time
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import NamedTuple

VERSION = "1.1.0"
FIELDS = ("customer_id", "name", "region", "member_since", "last_purchase_date", "marketing_permission")
REQUIRED_FIELDS = ("customer_id", "name", "region", "member_since")
LINE_FIELDS = ("source_line_start", "source_line_end")
ISSUE_FIELDS = ("record", "customer_id", "field", "code", "message", "next_action") + LINE_FIELDS
STATUS_FIELDS = ("record", "customer_id", "validation_status", "validation_reason") + LINE_FIELDS
HERE = Path(__file__).resolve().parent


class ConfigurationError(ValueError):
    """An invalid mapping file or unsupported configuration."""


class ProcessingError(RuntimeError):
    """A processing invariant failed; output must not be consumed."""


class SourceRecord(NamedTuple):
    number: int
    row: dict
    problems: list
    source_line_start: int
    source_line_end: int


def normalize_key(value):
    return " ".join(value.split()).casefold()


def load_mapping(path, expected_header, allowed_values):
    """Validate a two-column mapping without discarding an unchecked first row."""
    mapping = {}
    reader = None
    row_start = 1
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, strict=True)
            header = next(reader, None)
            if header is None:
                raise ConfigurationError(f"{path.name}, row 1: mapping file is empty")
            if tuple(normalize_key(value) for value in header) != expected_header:
                raise ConfigurationError(f"{path.name}, row 1: expected header {','.join(expected_header)}")
            while True:
                row_start = reader.line_num + 1
                values = next(reader, None)
                if values is None:
                    break
                if len(values) != 2:
                    raise ConfigurationError(f"{path.name}, row {row_start}: expected 2 columns, found {len(values)}")
                key, value = normalize_key(values[0]), values[1].strip()
                if not key or key in mapping:
                    raise ConfigurationError(f"{path.name}, row {row_start}: empty or repeated source value")
                if value not in allowed_values:
                    raise ConfigurationError(f"{path.name}, row {row_start}: unsupported output value {value!r}")
                mapping[key] = value
    except UnicodeDecodeError as error:
        raise ConfigurationError(f"{path.name}: mapping must be valid UTF-8") from error
    except csv.Error as error:
        raise ConfigurationError(f"{path.name}, row {row_start}: invalid CSV: {error}") from error
    if not mapping:
        raise ConfigurationError(f"{path.name}: mapping contains no data rows")
    return mapping


def issue(record, customer_id, field, code, message, action, source_line_start="", source_line_end=""):
    return dict(zip(ISSUE_FIELDS, (record, customer_id, field, code, message, action,
                                  source_line_start, source_line_end)))


def normalize(raw, number, permissions, warnings, source_line_start="", source_line_end=""):
    row = {field: value.strip() for field, value in raw.items()}
    for field in ("name", "region"):
        row[field] = unicodedata.normalize("NFC", " ".join(row[field].split()))
    problems = [(field, "MISSING_VALUE") for field in REQUIRED_FIELDS if not row[field]]
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
    row["marketing_permission"] = permissions.get(normalize_key(row["marketing_permission"]), "UNKNOWN")
    if row["marketing_permission"] == "UNKNOWN":
        warnings.append(issue(number, row["customer_id"], "marketing_permission", "UNKNOWN_PERMISSION",
                              "Missing or unrecognised permission", "Confirm in CRM; UNKNOWN is not permission.",
                              source_line_start, source_line_end))
    return row, problems



def problem_detail(field, code):
    label, action_label = {"customer_id": ("Customer ID", "customer ID"), "name": ("Name", "name"),
                           "region": ("Region", "region"), "member_since": ("Joining date", "joining date"),
                           "last_purchase_date": ("Last-purchase date", "last-purchase date")}[field]
    if code == "MISSING_VALUE":
        action = f"Retrieve {action_label} from the authoritative CRM record, correct the export and re-export."
        if field == "customer_id":
            action += " Do not invent an ID."
        return f"{label} is missing.", action
    return (f"{label} is not a valid YYYY-MM-DD calendar date.",
            f"Confirm {action_label} in the authoritative CRM record, correct it and re-export.")


def write_csv(path, columns, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def process_file(input_path, output_path, config_dir=None):
    """Process one input; preserve incomplete runs with best-effort diagnostics."""
    run = {"processor_version": VERSION,
           "started_at_utc": datetime.now(timezone.utc).isoformat(), "input_sha256": ""}
    try:
        return _process_file(input_path, output_path, config_dir, run)
    except Exception as error:
        if run.get("output_created"):
            try:
                metadata = "\n".join(f"{key}: {run[key]}" for key in
                                     ("processor_version", "started_at_utc", "input_sha256"))
                with (Path(output_path) / "run.log").open("a", encoding="utf-8") as handle:
                    handle.write(f"{metadata}\nERROR {type(error).__name__}: {error}\n"
                                 "INCOMPLETE: require a READY or READY_WITH_EXCEPTIONS marker.\n")
            except OSError:
                pass  # A storage failure may also prevent the diagnostic write.
        raise


def _process_file(input_path, output_path, config_dir, run):
    started = time.perf_counter()
    source, output = Path(input_path), Path(output_path)
    if output.exists():
        raise FileExistsError("Choose a new output folder; existing runs are never overwritten")
    config = Path(config_dir) if config_dir else HERE / "config"
    aliases = load_mapping(config / "column_aliases.csv", ("source_column", "output_column"), set(FIELDS))
    permissions = load_mapping(config / "permission_values.csv", ("source_value", "output_value"), {"YES", "NO"})
    if set(aliases.values()) != set(FIELDS):
        missing = ", ".join(sorted(set(FIELDS) - set(aliases.values())))
        raise ConfigurationError(f"column_aliases.csv: missing output fields: {missing}")
    groups = defaultdict(list)
    rejected, warnings, accepted, statuses = [], [], [], []
    parsed, removed, complete = 0, 0, False
    with source.open("rb") as incoming:
        output.mkdir(parents=True, exist_ok=False)
        run["output_created"] = True
        with (output / "received.csv").open("wb") as snapshot:
            shutil.copyfileobj(incoming, snapshot)
    with (output / "received.csv").open("rb") as snapshot:
        run["input_sha256"] = hashlib.file_digest(snapshot, "sha256").hexdigest()
    source_line_start = 1
    try:
        with (output / "received.csv").open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, strict=True)
            headers = next(reader, [])
            names = [normalize_key(name) for name in headers]
            mapped = [aliases.get(name) for name in names]
            known = [name for name in mapped if name]
            missing = set(FIELDS) - set(known)
            if not names or "" in names or len(set(names)) != len(names):
                raise ValueError("Empty or repeated source headings")
            if len(set(known)) != len(known):
                raise ValueError("Two source columns map to the same output field")
            if missing:
                raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))
            for header, target in zip(headers, mapped):
                if target is None:
                    warnings.append(issue(0, "", header, "EXTRA_COLUMN", "Unused column ignored",
                                          "Review whether this new field is needed.", 1, reader.line_num))
            while True:
                source_line_start = reader.line_num + 1
                values = next(reader, None)
                if values is None:
                    break
                source_line_end = reader.line_num
                if not values:
                    continue
                if len(values) != len(headers):
                    raise ValueError(f"Wrong column count near physical line {reader.line_num}")
                parsed += 1
                raw = {field: value for field, value in zip(mapped, values) if field}
                row, problems = normalize(raw, parsed, permissions, warnings, source_line_start, source_line_end)
                key = ("id", row["customer_id"]) if row["customer_id"] else ("missing", parsed)
                groups[key].append(SourceRecord(parsed, row, problems, source_line_start, source_line_end))
            if not parsed:
                raise ValueError("No data records; confirm whether the CRM export is complete")
            complete = True
    except (ValueError, csv.Error) as error:
        # Buffered decoding may fail ahead of the current record; do not guess a line.
        known_line = not isinstance(error, UnicodeDecodeError) and source_line_start <= reader.line_num
        line_start = source_line_start if known_line else ""
        line_end = reader.line_num if known_line else ""
        rejected.append(issue("FILE", "", "file/header", "SOURCE_CONTRACT", str(error),
                              "Check the approved headings, UTF-8 encoding, and CSV structure.", line_start, line_end))

    for records in groups.values():
        first = records[0].row
        conflict = len(records) > 1 and any(record.row != first for record in records)
        for index, record in enumerate(records):
            number, row, problems = record.number, record.row, record.problems
            location = {"source_line_start": record.source_line_start, "source_line_end": record.source_line_end}
            row_status, reason = "ACCEPTED", "Required checks passed"
            if conflict or problems:
                # Keep one report row per rejected record so counts still reconcile.
                fields, codes, messages, actions = [], [], [], []
                if conflict:
                    fields.append("customer_id")
                    codes.append("CONFLICTING_RECORDS_FOR_ID")
                    messages.append("Repeated ID has conflicting normalized records.")
                    actions.append("Resolve in the source; no winner is guessed.")
                for field, code in problems:
                    message, action = problem_detail(field, code)
                    fields.append(field)
                    codes.append(code)
                    messages.append(message)
                    actions.append(action)
                row_status, reason = "NEEDS_CORRECTION", "; ".join(codes)
                rejected.append(issue(number, row["customer_id"], "; ".join(fields), "; ".join(codes),
                                      " ".join(messages), " ".join(actions), **location))
            elif index:
                removed += 1
                row_status, reason = "DUPLICATE_IGNORED", "Identical normalized copy retained once"
                warnings.append(issue(number, row["customer_id"], "customer_id", "IDENTICAL_DUPLICATE",
                                      "Identical normalized copy removed", "One copy retained; review the export.", **location))
            else:
                accepted.append(row)
                if row["marketing_permission"] == "UNKNOWN":
                    row_status, reason = "ACCEPTED_WITH_WARNING", "Permission not confirmed"
            if not complete and row_status.startswith("ACCEPTED"):
                row_status, reason = "NOT_RELEASED", "Input could not be interpreted completely"
            statuses.append(dict(zip(STATUS_FIELDS, (number, row["customer_id"], row_status, reason,
                                                    record.source_line_start, record.source_line_end))))
    rejected_count = sum(row["record"] != "FILE" for row in rejected)
    if complete and parsed != len(accepted) + rejected_count + removed:
        raise ProcessingError("Counts do not reconcile; no result released")
    status = ("READY_WITH_EXCEPTIONS" if rejected else "READY") if complete and accepted else "BLOCKED"
    blocking_reason = "; ".join(row["message"] for row in rejected if row["record"] == "FILE")
    if status == "BLOCKED" and not blocking_reason:
        blocking_reason = "No valid records remain; see rejected.csv for record errors."
    summary = dict(status=status, source_file=source.name, source_fully_parsed=str(complete).lower(),
                   processor_version=run["processor_version"], started_at_utc=run["started_at_utc"],
                   input_sha256=run["input_sha256"], blocking_reason=blocking_reason,
                   parsed_records=parsed, valid_records=len(accepted), rejected_records=rejected_count,
                   released_records=len(accepted) if status != "BLOCKED" else 0,
                   identical_duplicates_removed=removed, warnings=len(warnings),
                   processing_seconds_before_report_write=round(time.perf_counter() - started, 6))
    write_csv(output / "rejected.csv", ISSUE_FIELDS, rejected)
    write_csv(output / "warnings.csv", ISSUE_FIELDS, warnings)
    write_csv(output / "record_status.csv", STATUS_FIELDS, sorted(statuses, key=lambda row: row["record"]))
    (output / "summary.txt").write_text("\n".join(f"{key}: {value}".rstrip() for key, value in summary.items()) + "\n", encoding="utf-8")
    metadata = "\n".join(f"{key}: {run[key]}" for key in ("processor_version", "started_at_utc", "input_sha256"))
    reason_line = f"REASON {blocking_reason}\n" if blocking_reason else ""
    (output / "run.log").write_text(f"{metadata}\nREAD {source.name}\nCHECK {parsed} parsed, {rejected_count} rejected, {removed} duplicates removed\nRESULT {status}\n{reason_line}", encoding="utf-8")
    if status != "BLOCKED":
        write_csv(output / "cleaned.part", FIELDS, accepted)
        (output / "cleaned.part").replace(output / "cleaned.csv")
    (output / status).write_text("Processing completed.\n", encoding="utf-8")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path, help="New run folder")
    parser.add_argument("--config-dir", type=Path, help="Mapping folder (default: config beside this script)")
    parser.add_argument("--debug", action="store_true", help="Show a traceback on processing errors")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    args = parser.parse_args(argv)
    try:
        result = process_file(args.input, args.output, args.config_dir)
    except Exception as error:
        if args.debug:
            raise
        expected = isinstance(error, (OSError, ConfigurationError, ProcessingError))
        prefix = "ERROR" if expected else f"UNEXPECTED ERROR ({type(error).__name__})"
        parser.exit(1, f"{prefix}: {error}\nUse --debug for a traceback.\nRequire a READY or READY_WITH_EXCEPTIONS marker before using output.\n")
    if result["status"] == "BLOCKED":
        print(f"BLOCKED: {result['blocking_reason']} No records released. See {args.output / 'summary.txt'}", file=sys.stderr)
        return 3
    print(f"{result['status']}: {result['released_records']} released, {result['rejected_records']} need correction. See {args.output / 'summary.txt'}")
    return 0


# Run the command-line interface when invoked as a script.
if __name__ == "__main__":
    raise SystemExit(main())
