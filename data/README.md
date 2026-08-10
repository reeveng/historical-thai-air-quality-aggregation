# Data

Hourly air quality readings for Thailand, from the
[air4thai](http://air4thai.com/forweb/getAQI_JSON.php) public API.

## Layout

| File | Contents |
| --- | --- |
| `YYYY-MM.csv` | One row per station per hour, for that month |
| `stations.csv` | Station metadata (name, area, coordinates), one row per station |

Readings are keyed on `(station_id, date, time)` and sorted by `date, time,
station_id`. Re-running the fetcher never duplicates a reading, so a delayed or
repeated workflow run appends nothing.

## Reading schema

`station_id`, `date`, `time`, then `aqi` and `value` for each of `pm25`,
`pm10`, `o3`, `co`, `no2`, `so2`, then the overall `aqi` and the `aqi_param`
that determined it.

An `aqi` or `value` of `-1` means the station did not report that pollutant for
that hour. Join to `stations.csv` on `station_id` for names and coordinates.

The upstream API reports each station's own local timestamp, so a small number
of rows carry stale dates when a station republishes an old reading — this is
why a month partition can pick up a handful of late rows after the month ends.

## Usage

```python
import pandas as pd, glob

readings = pd.concat(pd.read_csv(f) for f in sorted(glob.glob("data/2026-*.csv")))
stations = pd.read_csv("data/stations.csv")
df = readings.merge(stations, on="station_id")
```

```sql
-- DuckDB reads the partitions directly, no import step
SELECT station_id, date, avg(pm25_value) FROM 'data/2026-*.csv'
WHERE pm25_value >= 0 GROUP BY 1, 2;
```

## History

Readings before 2026-07 were originally stored as one pretty-printed JSON
snapshot per fetch (`data/YYYYMMDD_HHMMSS.json`). Those ~2,990 files repeated
all station metadata in every snapshot and were 66% whitespace and duplication,
totalling 663 MB. They were folded into these partitions by
`scripts/migrate-json-to-csv.py` with no loss of readings, and remain in git
history.
