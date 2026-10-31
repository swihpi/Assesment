"""Measure complete local runs on generated synthetic CSV files; no cloud calls."""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("customer_id", "name", "region", "member_since", "last_purchase_date", "marketing_permission")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int, default=[1000, 100000])
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if any(size <= 0 for size in args.sizes):
        parser.error("Sizes must be positive")
    results = []
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)
        for index, size in enumerate(args.sizes):
            source = temporary / f"source-{index}.csv"
            output = temporary / f"run-{index}"
            with source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle, lineterminator="\n")
                writer.writerow(FIELDS)
                writer.writerows(
                    [f"F{number:07d}", f"Synthetic Person {number}", "NY", "2022-04-15", "2026-10-20", "Y"]
                    for number in range(size)
                )
            started = time.perf_counter()
            completed = subprocess.run([
                sys.executable, str(ROOT / "process_export.py"),
                "--input", str(source), "--output", str(output),
            ], check=True, capture_output=True, text=True)
            elapsed = time.perf_counter() - started
            with (output / "cleaned.csv").open(encoding="utf-8", newline="") as handle:
                actual = sum(1 for _ in csv.DictReader(handle))
            if actual != size or not (output / "READY").exists():
                raise RuntimeError("Benchmark output does not match the generated input")
            summary = dict(line.split(":", 1) for line in (output / "summary.txt").read_text().splitlines())
            result = {
                "input_rows": size, "input_bytes": source.stat().st_size,
                "wall_seconds": round(elapsed, 6), "verified_output_rows": actual,
                "python": platform.python_version(), "platform": platform.platform(),
                "processor_version": summary["processor_version"].strip(),
                "processor_sha256": hashlib.sha256((ROOT / "process_export.py").read_bytes()).hexdigest(),
                "measured_at_utc": datetime.now(timezone.utc).isoformat(),
            }
            results.append(result)
            print(f"{size:,} rows: {elapsed:.3f}s, {actual:,} verified output records")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=results[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(results)


if __name__ == "__main__":
    main()
