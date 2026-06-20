from __future__ import annotations

import argparse
import statistics
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import storage  # noqa: E402
from app.schemas import HotItem  # noqa: E402
from app.sources import SOURCES  # noqa: E402


@dataclass(frozen=True)
class BenchmarkResult:
    dataset_size: int
    operation: str
    elapsed_ms: float
    returned_rows: int


def build_fake_item(index: int) -> HotItem:
    source = SOURCES[index % len(SOURCES)]
    keyword = "OpenAI" if index % 5 == 0 else "benchmark"
    return HotItem(
        source=source.id,
        section=source.section,
        title=f"{source.name} synthetic {keyword} item {index:05d}",
        url=f"{source.homepageUrl.rstrip('/')}/synthetic-benchmark-{index:05d}",
        rank=(index % 20) + 1,
        heat=str(100_000 - index),
        summary=f"Synthetic fixture item {index} for local benchmark only.",
        fetchedAt=f"2026-01-01T00:{index % 60:02d}:00+00:00",
        extra={"benchmark": True, "index": index},
    )


def seed_database(db_path: Path, dataset_size: int, batch_size: int = 500) -> None:
    storage.initialize_database(db_path)
    with storage.get_connection(db_path) as conn:
        for start in range(0, dataset_size, batch_size):
            items = [
                build_fake_item(index)
                for index in range(start, min(start + batch_size, dataset_size))
            ]
            storage.save_hot_items(conn, items=items, keywords=["OpenAI", "benchmark"])


def measure(
    dataset_size: int,
    operation: str,
    callback: Callable[[], tuple[object, int]],
    repeats: int,
) -> BenchmarkResult:
    elapsed: list[float] = []
    returned_rows = 0
    for _ in range(repeats):
        started = time.perf_counter()
        _, returned_rows = callback()
        elapsed.append((time.perf_counter() - started) * 1000)
    return BenchmarkResult(
        dataset_size=dataset_size,
        operation=operation,
        elapsed_ms=statistics.median(elapsed),
        returned_rows=returned_rows,
    )


def dashboard_row_count(payload: dict) -> int:
    return sum(
        len(panel["items"])
        for section in payload["sections"]
        for panel in section["sources"]
    )


def run_for_size(dataset_size: int, repeats: int, keep_database: bool) -> list[BenchmarkResult]:
    if keep_database:
        db_path = ROOT / "data" / f"benchmark-{dataset_size}.sqlite"
        if db_path.exists():
            db_path.unlink()
        seed_database(db_path, dataset_size)
        return benchmark_database(db_path, dataset_size, repeats)

    with tempfile.TemporaryDirectory(prefix="hotradar-benchmark-") as tmp:
        db_path = Path(tmp) / "benchmark.sqlite"
        seed_database(db_path, dataset_size)
        return benchmark_database(db_path, dataset_size, repeats)


def benchmark_database(db_path: Path, dataset_size: int, repeats: int) -> list[BenchmarkResult]:
    midpoint_offset = max(dataset_size // 2, 0)
    return [
        measure(
            dataset_size,
            "dashboard retrieval",
            lambda: _dashboard(db_path),
            repeats,
        ),
        measure(
            dataset_size,
            "history search q=OpenAI limit=100",
            lambda: _history_search(db_path),
            repeats,
        ),
        measure(
            dataset_size,
            f"history pagination limit=100 offset={midpoint_offset}",
            lambda: _history_page(db_path, midpoint_offset),
            repeats,
        ),
    ]


def _dashboard(db_path: Path) -> tuple[dict, int]:
    payload = storage.get_dashboard_data(db_path)
    return payload, dashboard_row_count(payload)


def _history_search(db_path: Path) -> tuple[dict, int]:
    payload = storage.get_history(q="OpenAI", limit=100, offset=0, db_path=db_path)
    return payload, len(payload["items"])


def _history_page(db_path: Path, offset: int) -> tuple[dict, int]:
    payload = storage.get_history(limit=100, offset=offset, db_path=db_path)
    return payload, len(payload["items"])


def print_results(results: list[BenchmarkResult]) -> None:
    print("| dataset_size | operation | elapsed_ms_median | returned_rows |")
    print("| ---: | --- | ---: | ---: |")
    for result in results:
        print(
            f"| {result.dataset_size} | {result.operation} | "
            f"{result.elapsed_ms:.2f} | {result.returned_rows} |"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run local synthetic HotRadar storage/API-shape benchmarks."
    )
    parser.add_argument(
        "--sizes",
        type=int,
        nargs="+",
        default=[1000, 10000],
        help="Synthetic item counts to seed. Defaults to 1000 10000.",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=5,
        help="Number of measurements per operation. Median is reported.",
    )
    parser.add_argument(
        "--keep-database",
        action="store_true",
        help="Write data/benchmark-<size>.sqlite instead of using a temporary database.",
    )
    args = parser.parse_args()

    if any(size <= 0 for size in args.sizes):
        parser.error("--sizes must contain positive integers")
    if args.repeats <= 0:
        parser.error("--repeats must be positive")

    print("HotRadar local synthetic benchmark")
    print("Data source: generated fixture items only; no external websites are called.")
    print("Database: temporary SQLite by default; production data is not modified.")
    print()

    results: list[BenchmarkResult] = []
    for size in args.sizes:
        results.extend(run_for_size(size, args.repeats, args.keep_database))
    print_results(results)


if __name__ == "__main__":
    main()
