#!/usr/bin/env python3
"""Reproduce a blocked heading, then an explicitly confirmed alias in a temporary workspace."""
import csv
import shutil
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from process_export import process_file


def main():
    with tempfile.TemporaryDirectory(prefix='mapping-walkthrough-') as folder:
        workspace = Path(folder)
        config = workspace / 'config'
        shutil.copytree(ROOT / 'config', config)
        source = workspace / 'renamed.csv'
        with (ROOT / 'samples/valid.csv').open(newline='', encoding='utf-8-sig') as handle:
            rows = list(csv.reader(handle))
        # Change only the customer-ID heading; the values remain unchanged.
        rows[0][0] = 'customerdata_id'
        with source.open('w', newline='', encoding='utf-8') as handle:
            csv.writer(handle).writerows(rows)
        before = process_file(source, workspace / 'before', config)
        assert before['status'] == 'BLOCKED'
        assert not (workspace / 'before/cleaned.csv').exists()
        print('Before approval: BLOCKED; no cleaned.csv released.')
        # Exercise assumption: the source owner has confirmed identical meaning.
        # This script does not obtain or replace that confirmation.
        with (config / 'column_aliases.csv').open('a', encoding='utf-8', newline='') as handle:
            csv.writer(handle).writerow(['customerdata_id', 'customer_id'])
        after = process_file(source, workspace / 'after', config)
        baseline = process_file(ROOT / 'samples/valid.csv', workspace / 'baseline', config)
        assert after['status'] == baseline['status'] == 'READY'
        assert after['released_records'] == baseline['released_records'] == 3
        assert (workspace / 'after/cleaned.csv').read_bytes() == (workspace / 'baseline/cleaned.csv').read_bytes()
        print('After assumed source-owner confirmation and a mapping-only change: READY; 3 records released.')
        print('Verified: normalized output equals the original valid export; processor and repository mappings unchanged.')


if __name__ == '__main__':
    main()
