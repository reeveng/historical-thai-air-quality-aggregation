"""Shared schema and IO helpers for the air4thai dataset."""

import csv
from pathlib import Path

DATA_DIR = Path("data")

POLLUTANTS = ["PM25", "PM10", "O3", "CO", "NO2", "SO2"]

READING_COLS = (
    ["station_id", "date", "time"]
    + [f"{p.lower()}_{suffix}" for p in POLLUTANTS for suffix in ("aqi", "value")]
    + ["aqi", "aqi_param"]
)

STATION_COLS = [
    "station_id",
    "name_th",
    "name_en",
    "area_th",
    "area_en",
    "station_type",
    "lat",
    "long",
]

# Readings are keyed by (station_id, date, time); the API republishes the same
# hourly reading until the next one lands, so the key is what makes re-runs
# idempotent. Stations are keyed by station_id alone.
READING_KEY = 3
STATION_KEY = 1


def station_row(station):
    return [
        station.get("stationID", ""),
        station.get("nameTH", ""),
        station.get("nameEN", ""),
        station.get("areaTH", ""),
        station.get("areaEN", ""),
        station.get("stationType", ""),
        station.get("lat", ""),
        station.get("long", ""),
    ]


def reading_row(station):
    """Flatten a station's AQILast block, or return None if it has no reading."""
    aqi_last = station.get("AQILast") or {}
    station_id = station.get("stationID")
    date = aqi_last.get("date")
    if not station_id or not date:
        return None

    row = [station_id, date, aqi_last.get("time", "")]
    for pollutant in POLLUTANTS:
        measurement = aqi_last.get(pollutant) or {}
        row += [measurement.get("aqi", ""), measurement.get("value", "")]
    overall = aqi_last.get("AQI") or {}
    row += [overall.get("aqi", ""), overall.get("param", "")]
    return row


def read_csv(path, expected_cols, key_len):
    if not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header != expected_cols:
            raise SystemExit(f"{path}: unexpected header {header}")
        return {tuple(r[:key_len]): r for r in reader if r}


def write_csv(path, cols, rows, sort_key):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        writer.writerows(sorted(rows, key=sort_key))
    tmp.replace(path)


def partition_of(date):
    """Monthly partition name, e.g. '2026-07' from '2026-07-02'."""
    return date[:7]
