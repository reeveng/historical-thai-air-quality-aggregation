"""Fetch current air4thai readings and append them to the monthly CSV partition.

Writes are keyed on (station_id, date, time), so a delayed or repeated run adds
nothing when the upstream reading has not advanced. Only the rows that are new
hit the diff, which is what keeps the repo small.
"""

import sys
from collections import defaultdict
from pathlib import Path

import requests

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

API_URL = "http://air4thai.com/forweb/getAQI_JSON.php"


def main():
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()
    payload = response.json()

    fetched = {}
    stations = {}
    for station in payload.get("stations", []):
        row = reading_row(station)
        if row is None:
            continue
        stations[station["stationID"]] = station_row(station)
        fetched[tuple(row[:READING_KEY])] = row

    if not fetched:
        raise SystemExit("API returned no usable readings; leaving data untouched.")

    by_month = defaultdict(dict)
    for key, row in fetched.items():
        by_month[partition_of(row[1])][key] = row

    added = 0
    for month, rows in sorted(by_month.items()):
        path = DATA_DIR / f"{month}.csv"
        existing = read_csv(path, READING_COLS, READING_KEY)
        new_keys = rows.keys() - existing.keys()
        if not new_keys:
            continue
        existing.update(rows)
        write_csv(path, READING_COLS, existing.values(), sort_key=lambda r: (r[1], r[2], r[0]))
        added += len(new_keys)
        print(f"{path.name}: +{len(new_keys)} readings ({len(existing)} total)")

    stations_path = DATA_DIR / "stations.csv"
    known = {k[0]: v for k, v in read_csv(stations_path, STATION_COLS, STATION_KEY).items()}
    if any(known.get(sid) != row for sid, row in stations.items()):
        known.update(stations)
        write_csv(stations_path, STATION_COLS, known.values(), sort_key=lambda r: r[0])
        print(f"stations.csv: {len(known)} stations")

    if added == 0:
        print("No new readings; upstream has not advanced since the last run.")


if __name__ == "__main__":
    main()
