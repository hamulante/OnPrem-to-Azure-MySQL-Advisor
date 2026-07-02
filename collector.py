"""Collector facade: connect to a source MySQL (read-only) and emit a profile YAML.

Run this on a host that can reach the source server. It issues only SELECT / SHOW
statements. Host-level fields it cannot observe (cpu_cores, memory_gib, peak_iops)
are emitted as null for you to fill in before running the advisor.

Password is read from the MYSQL_PWD environment variable, or prompted for
interactively — never passed on the command line.
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys

import pymysql
import yaml

from advisor.collect import QueryFn, collect_profile
from advisor.core import recommend
from advisor.models import OnPremProfile
from advisor.specs.compatibility import (
    CREATABLE_TARGET_VERSIONS,
    DEFAULT_TARGET_VERSION,
)
from cli import format_report


def make_query_fn(conn: "pymysql.connections.Connection") -> QueryFn:
    def query(sql: str) -> list[tuple]:
        head = sql.lstrip().upper()
        if not (head.startswith("SELECT") or head.startswith("SHOW")):
            raise ValueError(f"Refusing non-read-only statement: {sql!r}")
        with conn.cursor() as cur:
            cur.execute(sql)
            return list(cur.fetchall())

    return query


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Collect a read-only profile from a source MySQL server."
    )
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--user", required=True)
    parser.add_argument("--ssl-ca", help="Path to a CA cert to require TLS.")
    parser.add_argument(
        "--cpu-cores",
        type=int,
        help="Source host physical CPU cores (MySQL cannot report this).",
    )
    parser.add_argument(
        "--memory-gib",
        type=float,
        help="Source host RAM in GiB (MySQL cannot report this).",
    )
    parser.add_argument(
        "--peak-iops",
        type=int,
        help="Observed peak IOPS from OS/storage monitoring, if known.",
    )
    parser.add_argument("--out", help="Write YAML to this file instead of stdout.")
    parser.add_argument(
        "--advise",
        action="store_true",
        help="Also run the advisor and print the sizing report (one-command flow).",
    )
    parser.add_argument(
        "--target-version",
        default=DEFAULT_TARGET_VERSION,
        help=(
            "Azure MySQL Flexible Server target major version for --advise "
            f"(creatable: {', '.join(sorted(CREATABLE_TARGET_VERSIONS))}; "
            f"default: {DEFAULT_TARGET_VERSION})."
        ),
    )
    args = parser.parse_args(argv)

    password = os.environ.get("MYSQL_PWD") or getpass.getpass("MySQL password: ")
    ssl = {"ca": args.ssl_ca} if args.ssl_ca else None

    conn = pymysql.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=password,
        connect_timeout=10,
        ssl=ssl,
    )
    try:
        profile = collect_profile(
            make_query_fn(conn),
            cpu_cores=args.cpu_cores,
            memory_gib=args.memory_gib,
            peak_iops=args.peak_iops,
        )
    finally:
        conn.close()

    missing = [k for k in ("cpu_cores", "memory_gib") if profile.get(k) is None]
    if missing:
        header = (
            "# Auto-collected from source MySQL (read-only).\n"
            "# These host/OS-level fields are still null and MUST be set before advising:\n"
            f"#   {', '.join(missing)}\n"
            "# Either edit them here, or re-run with --cpu-cores / --memory-gib / --peak-iops.\n"
        )
    else:
        header = "# Auto-collected from source MySQL (read-only). Ready for cli.py.\n"
    body = yaml.safe_dump(profile, sort_keys=False, allow_unicode=True)
    output = header + body

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Wrote {args.out}")
    elif not args.advise:
        sys.stdout.write(output)

    if args.advise:
        if missing:
            sys.stderr.write(
                "Cannot advise: host field(s) still unknown: "
                f"{', '.join(missing)}. Provide --cpu-cores / --memory-gib.\n"
            )
            return 2
        # Reuse the deterministic core; no rules are duplicated here.
        rec = recommend(OnPremProfile(**profile), target_version=args.target_version)
        print(format_report(rec, OnPremProfile(**profile), args.target_version))
        return 1 if rec.blockers else 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
