"""Read-only collection logic: source MySQL -> profile dict.

This module contains only pure mapping logic. It takes a `query` callable so it
can be unit-tested without a live database; the actual DB connection lives in
the `collector.py` facade.

Honesty note: cpu_cores, memory_gib and peak_iops are host / OS-level facts that
a MySQL connection cannot observe. They are returned as None for manual entry —
never guessed.
"""
from __future__ import annotations

from typing import Any, Callable

# A QueryFn runs a read-only SQL string and returns a list of row tuples.
QueryFn = Callable[[str], list[tuple[Any, ...]]]

_SYSTEM_SCHEMAS = ("mysql", "sys", "information_schema", "performance_schema")
_SCHEMA_FILTER = (
    "table_schema NOT IN "
    "('mysql','sys','information_schema','performance_schema')"
)


def _scalar(query: QueryFn, sql: str) -> Any:
    rows = query(sql)
    if not rows or not rows[0]:
        return None
    return rows[0][0]


def _status_value(query: QueryFn, name: str) -> Any:
    # SHOW GLOBAL STATUS rows are (Variable_name, Value).
    rows = query(f"SHOW GLOBAL STATUS LIKE '{name}'")
    if not rows or len(rows[0]) < 2:
        return None
    return rows[0][1]


def collect_profile(query: QueryFn) -> dict:
    """Assemble a YAML-serializable profile dict from read-only queries."""
    version = _scalar(query, "SELECT VERSION()")
    lctn = _scalar(query, "SELECT @@lower_case_table_names")
    data_gib = _scalar(
        query,
        "SELECT ROUND(COALESCE(SUM(data_length + index_length), 0) "
        f"/ 1024 / 1024 / 1024, 1) FROM information_schema.tables WHERE {_SCHEMA_FILTER}",
    )
    max_used_conn = _status_value(query, "Max_used_connections")
    engine_rows = query(
        "SELECT DISTINCT engine FROM information_schema.tables "
        f"WHERE {_SCHEMA_FILTER} AND engine IS NOT NULL"
    )
    engines = sorted({row[0] for row in engine_rows if row and row[0] is not None})

    return {
        "mysql_version": str(version) if version is not None else None,
        # Host-level — MySQL cannot report these; fill in manually.
        "cpu_cores": None,
        "memory_gib": None,
        "data_size_gib": float(data_gib) if data_gib is not None else 0.0,
        # OS / storage-level — not available via SQL.
        "peak_iops": None,
        "peak_connections": int(max_used_conn) if max_used_conn is not None else None,
        "storage_engines": engines,
        "params": {"lower_case_table_names": str(lctn)} if lctn is not None else {},
    }
