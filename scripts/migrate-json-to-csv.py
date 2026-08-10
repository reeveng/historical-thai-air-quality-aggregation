"""One-time migration: fold data/*.json snapshots into monthly CSV partitions.

Every snapshot repeats all station metadata and pretty-prints with indent=2, so
~66% of each file is overhead. This rebuilds the same readings as append-only
monthly CSVs, deduplicated on (station_id, date, time).

Existing CSV partitions are merged with, not overwritten, so the migration is
safe to re-run.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from aq_common import (  # noqa: E402
    DATA_DIR,
    READING_COLS,
    READING_KEY,
    STATION_COLS,
    STATION_KEY,
    partition_of,
    read_csv,
    reading_row,
    station_row,
    write_csv,
)


def main():
    snapshots = sorted(DATA_DIR.glob("*.json"))
    if not snapshots:
        print("No data/*.json snapshots found; nothing to migrate.")
        return

    readings = {}
    stations = {}
    skipped = 0

    for i, path in enumerate(snapshots, 1):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  skipping unreadable {path.name}: {exc}")
            skipped += 1
            continue

        for station in payload.get("stations", []):
            row = reading_row(station)
            if row is None:
                continue
            stations[row[0]] = station_row(station)
            readings[tuple(row[:3])] = row

        if i % 500 == 0:
            print(f"  read {i}/{len(snapshots)} snapshots", flush=True)

    # Merge with anything already migrated so re-runs are idempotent.
    for path in DATA_DIR.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9].csv"):
        readings.update(read_csv(path, READING_COLS, READING_KEY))
    existing = read_csv(DATA_DIR / "stations.csv", STATION_COLS, STATION_KEY)
    stations = {**{k[0]: v for k, v in existing.items()}, **stations}

    by_month = defaultdict(list)
    for row in readings.values():
        by_month[partition_of(row[1])].append(row)

    for month, rows in sorted(by_month.items()):
        path = DATA_DIR / f"{month}.csv"
        write_csv(path, READING_COLS, rows, sort_key=lambda r: (r[1], r[2], r[0]))
        print(f"  {path.name}  {len(rows):>7} rows  {path.stat().st_size / 1e6:>6.2f} MB")

    write_csv(DATA_DIR / "stations.csv", STATION_COLS, stations.values(), sort_key=lambda r: r[0])

    print(
        f"\nMigrated {len(snapshots) - skipped} snapshots -> "
        f"{len(readings)} unique readings across {len(by_month)} monthly partitions "
        f"({len(stations)} stations)."
    )
    print("Verify with scripts/verify-migration.py, then delete data/*.json.")


if __name__ == "__main__":
    main()
