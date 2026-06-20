# HotRadar Benchmark

`scripts/benchmark_api.py` runs a local synthetic benchmark against HotRadar storage-layer functions that match the API data paths.

The benchmark does not call external websites and does not modify production data by default. It seeds generated fixture items into temporary SQLite databases and removes them when the process exits.

## What It Measures

- Dashboard retrieval through `storage.get_dashboard_data`.
- History search through `storage.get_history(q="OpenAI", limit=100, offset=0)`.
- History pagination through `storage.get_history(limit=100, offset=<midpoint>)`.

The reported elapsed time is the median across repeated measurements.

## Run

Default run:

```bash
python3 scripts/benchmark_api.py
```

Smaller smoke run:

```bash
python3 scripts/benchmark_api.py --sizes 1000 --repeats 3
```

Keep generated benchmark SQLite files under `data/` for manual inspection:

```bash
python3 scripts/benchmark_api.py --sizes 1000 10000 --keep-database
```

Generated benchmark databases are ignored by Git through `data/*.sqlite`.

## Important Disclaimer

These numbers are local synthetic measurements, not production traffic. They should be used only to discuss query shape, local SQLite behavior, and benchmark methodology. Do not claim production scale, production latency, real users, or performance improvements from these results.

## Latest Local Results

Measured locally on 2026-06-20 with:

```bash
.venv/bin/python scripts/benchmark_api.py --sizes 1000 10000 --repeats 5
```

| dataset_size | operation | elapsed_ms_median | returned_rows |
| ---: | --- | ---: | ---: |
| 1000 | dashboard retrieval | 1.04 | 32 |
| 1000 | history search q=OpenAI limit=100 | 1.54 | 100 |
| 1000 | history pagination limit=100 offset=500 | 2.46 | 100 |
| 10000 | dashboard retrieval | 2.17 | 280 |
| 10000 | history search q=OpenAI limit=100 | 10.16 | 100 |
| 10000 | history pagination limit=100 offset=5000 | 30.26 | 100 |

These are local synthetic numbers only. They are not production latency, user traffic, or an AWS deployment result.
