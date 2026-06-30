"""Command-line front end. A thin facade over advisor.core — no rules live here."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

import yaml

from advisor.core import recommend
from advisor.models import OnPremProfile, Recommendation


def load_profile(path: str) -> OnPremProfile:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return OnPremProfile(**data)


def format_report(rec: Recommendation) -> str:
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("Azure Database for MySQL — Migration Sizing Report")
    lines.append("=" * 60)
    if rec.sku is not None:
        s = rec.sku
        lines.append(f"Recommended compute : {s.name}  ({s.tier.value})")
        lines.append(f"  vCores / memory   : {s.vcores} vCores, {s.memory_gib} GiB")
        lines.append(f"  Max IOPS / conns  : {s.max_iops} IOPS, {s.max_connections} connections")
    else:
        lines.append("Recommended compute : (none — see blockers)")
    lines.append(f"Recommended storage : {rec.storage_gib} GiB")
    lines.append("")
    lines.append(f"Sizing rationale    : {rec.sizing_rationale}")
    lines.append(f"Storage notes       : {rec.storage_notes}")

    if rec.blockers:
        lines.append("")
        lines.append("BLOCKERS:")
        for f in rec.blockers:
            lines.append(f"  [X] {f.code}: {f.message}")
            if f.source:
                lines.append(f"      source: {f.source}")
    if rec.warnings:
        lines.append("")
        lines.append("WARNINGS:")
        for f in rec.warnings:
            lines.append(f"  [!] {f.code}: {f.message}")
            if f.source:
                lines.append(f"      source: {f.source}")
    if not rec.blockers and not rec.warnings:
        lines.append("")
        lines.append("No blockers or warnings detected.")
    return "\n".join(lines)


def _to_dict(rec: Recommendation) -> dict:
    d = asdict(rec)
    d["blockers"] = [asdict(f) for f in rec.blockers]
    d["warnings"] = [asdict(f) for f in rec.warnings]
    return d


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Advise on sizing & risks for migrating on-prem MySQL to Azure."
    )
    parser.add_argument("input", help="Path to a YAML profile of the source server.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args(argv)

    profile = load_profile(args.input)
    rec = recommend(profile)

    if args.json:
        print(json.dumps(_to_dict(rec), indent=2, default=str))
    else:
        print(format_report(rec))

    return 1 if rec.blockers else 0


if __name__ == "__main__":
    sys.exit(main())
