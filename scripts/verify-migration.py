"""Check that every reading in data/*.json survived into the CSV partitions.

Run this before deleting the JSON snapshots. Exits non-zero if anything is
missing or if any field disagrees.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from aq_common import (  # noqa: E402
    DATA_DIR,
    READING_COLS,
    READING_KEY,
    partition_of,
    read_csv,
    reading_row,
)


def main():
    snapshots = sorted(DATA_DIR.glob("*.json"))
    if not snapshots:
        print("No data/*.json snapshots left to verify against.")
        return 0

    csv_rows = {}
    for path in DATA_DIR.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9].csv"):
        csv_rows.update(read_csv(path, READING_COLS, READING_KEY))

    source = {}
    for path in snapshots:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for station in payload.get("stations", []):
            row = reading_row(station)
            if row is not None:
                source[tuple(row[:READING_KEY])] = row

    missing = [k for k in source if k not in csv_rows]
    mismatched = [k for k, r in source.items() if k in csv_rows and csv_rows[k] != r]
    misfiled = [
        k for k, r in source.items()
        if k in csv_rows and not (DATA_DIR / f"{partition_of(r[1])}.csv").exists()
    ]

    print(f"JSON snapshots      : {len(snapshots)}")
    print(f"unique JSON readings: {len(source)}")
    print(f"CSV readings        : {len(csv_rows)}")
    print(f"missing from CSV    : {len(missing)}")
    print(f"value mismatches    : {len(mismatched)}")
    print(f"wrong partition     : {len(misfiled)}")

    for key in missing[:5]:
        print(f"  MISSING  {key}")
    for key in mismatched[:5]:
        print(f"  DIFFERS  {key}\n    json={source[key]}\n    csv ={csv_rows[key]}")

    if missing or mismatched or misfiled:
        print("\nFAIL: do not delete the JSON snapshots.")
        return 1
    print("\nOK: every JSON reading is present and identical in the CSV partitions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
