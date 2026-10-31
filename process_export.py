#!/usr/bin/env python3
"""Check and normalize one CRM CSV export, using Python's standard library."""

import argparse
import csv
import re
import shutil
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

FIELDS = ("customer_id", "name", "region", "member_since", "last_purchase_date", "marketing_permission")
ISSUE_FIELDS = ("record", "customer_id", "field", "code", "message", "next_action")
STATUS_FIELDS = ("record", "customer_id", "validation_status", "validation_reason")
HERE = Path(__file__).resolve().parent


def load_mapping(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, strict=True)
        next(reader)
        rows = list(reader)
    mapping = {" ".join(key.split()).casefold(): value.strip() for key, value in rows}
    if len(mapping) != len(rows) or "" in mapping:
        raise ValueError("Mapping contains empty or repeated source values")
    return mapping


def issue(record, customer_id, field, code, message, action):
    return dict(zip(ISSUE_FIELDS, (record, customer_id, field, code, message, action)))


def normalize(raw, number, permissions, warnings):
    row = {field: value.strip() for field, value in raw.items()}
    for field in ("name", "region"):
        row[field] = " ".join(row[field].split())
    problems = [(field, "MISSING_VALUE") for field in FIELDS[:4] if not row[field]]
    for field in ("member_since", "last_purchase_date"):
        if row[field]:
            try:
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row[field]):
                    raise ValueError("Expected YYYY-MM-DD")
                date.fromisoformat(row[field])
            except ValueError:
                problems.append((field, "INVALID_DATE"))
    row["marketing_permission"] = permissions.get(row["marketing_permission"].casefold(), "UNKNOWN")
    if row["marketing_permission"] == "UNKNOWN":
        warnings.append(issue(number, row["customer_id"], "marketing_permission", "UNKNOWN_PERMISSION",
                              "Missing or unrecognised permission", "Confirm in CRM; UNKNOWN is not permission."))
    return row, problems



def problem_detail(field, code):
    label = {"customer_id": "Customer ID", "name": "Name", "region": "Region",
             "member_since": "Joining date", "last_purchase_date": "Last-purchase date"}[field]
    if code == "MISSING_VALUE":
        action = f"Retrieve {label.lower().replace('customer id', 'customer ID')} from the authoritative CRM record, correct the export and re-export."
        if field == "customer_id":
            action += " Do not invent an ID."
        return f"{label} is missing.", action
    return (f"{label} is not a valid YYYY-MM-DD calendar date.",
            f"Confirm {label.lower()} in the authoritative CRM record, correct it and re-export.")


def write_csv(path, columns, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def process_file(input_path, output_path, config_dir=None):
    started = time.perf_counter()
    source, output = Path(input_path), Path(output_path)
    if output.exists():
        raise FileExistsError("Choose a new output folder; existing runs are never overwritten")
    config = Path(config_dir) if config_dir else HERE / "config"
    aliases = load_mapping(config / "column_aliases.csv")
    permissions = load_mapping(config / "permission_values.csv")
    if set(aliases.values()) != set(FIELDS) or not set(permissions.values()) <= {"YES", "NO"}:
        raise ValueError("Configuration contains unsupported output fields or permission values")
    groups = defaultdict(list)
    rejected, warnings, accepted, statuses = [], [], [], []
    parsed, removed, complete = 0, 0, False
    with source.open("rb") as incoming:
        output.mkdir(parents=True, exist_ok=False)
        with (output / "received.csv").open("wb") as snapshot:
            shutil.copyfileobj(incoming, snapshot)
    try:
        with (output / "received.csv").open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, strict=True)
            headers = next(reader, [])
            names = [" ".join(name.split()).casefold() for name in headers]
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
                                          "Review whether this new field is needed."))
            for values in reader:
                if not values or all(not value.strip() for value in values):
                    continue
                if len(values) != len(headers):
                    raise ValueError(f"Wrong column count near physical line {reader.line_num}")
                parsed += 1
                raw = {field: value for field, value in zip(mapped, values) if field}
                row, problems = normalize(raw, parsed, permissions, warnings)
                key = ("id", row["customer_id"]) if row["customer_id"] else ("missing", parsed)
                groups[key].append((parsed, row, problems))
            if not parsed:
                raise ValueError("No data records; confirm whether the CRM export is complete")
            complete = True
    except (ValueError, csv.Error, UnicodeDecodeError) as error:
        rejected.append(issue("FILE", "", "file/header", "SOURCE_CONTRACT", str(error),
                              "Check the approved headings, UTF-8 encoding, and CSV structure."))

    for records in groups.values():
        first = records[0][1]
        conflict = len(records) > 1 and any(problems or row != first for _, row, problems in records)
        for index, (number, row, problems) in enumerate(records):
            row_status, reason = "ACCEPTED", "Required checks passed"
            if conflict:
                row_status, reason = "NEEDS_CORRECTION", "Conflicting records for the same customer ID"
                rejected.append(issue(number, row["customer_id"], "customer_id", "CONFLICTING_RECORDS_FOR_ID",
                                      "Repeated ID has conflicting or invalid records", "Resolve in the source; no winner is guessed."))
            elif problems:
                fields, codes = zip(*problems)
                row_status, reason = "NEEDS_CORRECTION", "; ".join(codes)
                messages, actions = zip(*(problem_detail(field, code) for field, code in problems))
                rejected.append(issue(number, row["customer_id"], "; ".join(fields), "; ".join(codes),
                                      " ".join(messages), " ".join(actions)))
            elif index:
                removed += 1
                row_status, reason = "DUPLICATE_IGNORED", "Identical normalized copy retained once"
                warnings.append(issue(number, row["customer_id"], "customer_id", "IDENTICAL_DUPLICATE",
                                      "Identical normalized copy removed", "One copy retained; review the export."))
            else:
                accepted.append(row)
                if row["marketing_permission"] == "UNKNOWN":
                    row_status, reason = "ACCEPTED_WITH_WARNING", "Permission not confirmed"
            if not complete and row_status.startswith("ACCEPTED"):
                row_status, reason = "NOT_RELEASED", "Input could not be interpreted completely"
            statuses.append(dict(zip(STATUS_FIELDS, (number, row["customer_id"], row_status, reason))))
    rejected_count = sum(row["record"] != "FILE" for row in rejected)
    if complete and parsed != len(accepted) + rejected_count + removed:
        raise RuntimeError("Counts do not reconcile; no result released")
    status = ("READY_WITH_EXCEPTIONS" if rejected else "READY") if complete and accepted else "BLOCKED"
    summary = dict(status=status, source_file=source.name, source_fully_parsed=str(complete).lower(),
                   parsed_records=parsed, valid_records=len(accepted), rejected_records=rejected_count,
                   released_records=len(accepted) if status != "BLOCKED" else 0,
                   identical_duplicates_removed=removed, warnings=len(warnings),
                   processing_seconds_before_report_write=round(time.perf_counter() - started, 6))
    write_csv(output / "rejected.csv", ISSUE_FIELDS, rejected)
    write_csv(output / "warnings.csv", ISSUE_FIELDS, warnings)
    write_csv(output / "record_status.csv", STATUS_FIELDS, sorted(statuses, key=lambda row: row["record"]))
    (output / "summary.txt").write_text("\n".join(f"{key}: {value}" for key, value in summary.items()) + "\n", encoding="utf-8")
    (output / "run.log").write_text(f"READ {source.name}\nCHECK {parsed} parsed, {rejected_count} rejected, {removed} duplicates removed\nRESULT {status}\n", encoding="utf-8")
    if status != "BLOCKED":
        write_csv(output / "cleaned.part", FIELDS, accepted)
        (output / "cleaned.part").replace(output / "cleaned.csv")
    (output / status).write_text("Processing completed.\n", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path, help="New run folder")
    parser.add_argument("--config-dir", type=Path, default=HERE / "config")
    args = parser.parse_args()
    try:
        result = process_file(args.input, args.output, args.config_dir)
    except (OSError, ValueError, KeyError, StopIteration, csv.Error, RuntimeError) as error:
        parser.exit(1, f"ERROR: {error}\nRequire a READY or READY_WITH_EXCEPTIONS marker before using output.\n")
    print(f"{result['status']}: {result['released_records']} released, {result['rejected_records']} need correction. See {args.output / 'summary.txt'}")
    return 2 if result["status"] == "BLOCKED" else 0


# Run the command-line interface when invoked as a script.
if __name__ == "__main__":
    raise SystemExit(main())
