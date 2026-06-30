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
    parser.add_argument("--out", help="Write YAML to this file instead of stdout.")
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
        profile = collect_profile(make_query_fn(conn))
    finally:
        conn.close()

    header = (
        "# Auto-collected from source MySQL (read-only).\n"
        "# Fields left null are host/OS-level and MUST be filled in manually before\n"
        "# running the advisor: cpu_cores, memory_gib, peak_iops.\n"
    )
    body = yaml.safe_dump(profile, sort_keys=False, allow_unicode=True)
    output = header + body

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Wrote {args.out}")
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
