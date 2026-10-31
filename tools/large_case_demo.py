"""Generate, process and independently verify a retained 10,000-record example."""

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("customer_id", "name", "region", "member_since", "last_purchase_date", "marketing_permission")


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def demonstrate(folder):
    # A new folder keeps earlier demonstrations and their evidence intact.
    folder.mkdir(parents=True, exist_ok=False)
    source, output = folder / "input-10000.csv", folder / "result"
    with source.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(FIELDS)
        writer.writerows([f"F{i:05d}" if i >= 800 else "", f"Person {i}", "NY",
                          "2022-04-15", "", "Y"] for i in range(10000))
    command = [sys.executable, str(ROOT / "process_export.py"), "--input", str(source), "--output", str(output)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    (folder / "execution.log").write_text(
        "Command: " + " ".join(command) + "\n" + result.stdout + result.stderr +
        f"Exit code: {result.returncode}\n", encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"Processor exited {result.returncode}; inspect {folder / 'execution.log'}")
    actual_input = read_rows(source)
    cleaned = read_rows(output / "cleaned.csv")
    rejected = read_rows(output / "rejected.csv")
    statuses = read_rows(output / "record_status.csv")
    counts = {"input_records": len(actual_input), "released_records": len(cleaned),
              "rejected_records": len(rejected), "status_records": len(statuses)}
    if counts != {"input_records": 10000, "released_records": 9200,
                  "rejected_records": 800, "status_records": 10000}:
        raise RuntimeError(f"Unexpected independently counted results: {counts}")
    checks = {
        "input_has_800_missing_ids": sum(not row["customer_id"] for row in actual_input) == 800,
        "received_bytes_preserved": source.read_bytes() == (output / "received.csv").read_bytes(),
        "expected_released_ids": {row["customer_id"] for row in cleaned} == {f"F{i:05d}" for i in range(800, 10000)},
        "rejected_missing_ids": all(row["field"] == "customer_id" and row["code"] == "MISSING_VALUE" for row in rejected),
        "all_statuses_accounted_for": sum(row["validation_status"] == "NEEDS_CORRECTION" for row in statuses) == 800
            and sum(row["validation_status"] == "ACCEPTED" for row in statuses) == 9200,
        "successful_completion_marker": (output / "READY_WITH_EXCEPTIONS").is_file(),
    }
    summary = dict(line.split(":", 1) for line in (output / "summary.txt").read_text().splitlines())
    checks["summary_matches_files"] = all(int(summary[key]) == counts[target] for key, target in
                                          (("parsed_records", "input_records"), ("released_records", "released_records"),
                                           ("rejected_records", "rejected_records")))
    if not all(checks.values()):
        raise RuntimeError(f"Independent verification failed: {checks}")
    verification = {**counts, "status": "READY_WITH_EXCEPTIONS", "checks": checks,
                    "processor_version": summary["processor_version"].strip(),
                    "processor_sha256": hashlib.sha256((ROOT / "process_export.py").read_bytes()).hexdigest()}
    (folder / "verification.json").write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8")
    print(result.stdout.strip())
    print("VERIFIED: 10000 input records; 9200 released; 800 rejected; 10000 record statuses.")
    print("Verified received bytes, expected released IDs, missing-ID errors, statuses and summary counts.")
    print(f"Retained input: {source}")
    print(f"Retained results: {output}")
    print(f"Independent verification: {folder / 'verification.json'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="New folder for generated input, results and verification")
    args = parser.parse_args()
    try:
        demonstrate(args.output)
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f"ERROR: {error}\n")


if __name__ == "__main__":
    main()
