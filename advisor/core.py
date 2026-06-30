"""Deterministic decision engine — the single source of recommendation rules.

No LLM, no randomness: same input always yields the same recommendation.
Every Azure fact used here is traceable to an official source (see `source`
fields on findings and on the SKU catalog).
"""
from __future__ import annotations

import math

from advisor.models import (
    Finding,
    OnPremProfile,
    Recommendation,
    Severity,
    SkuSpec,
    Tier,
)
from advisor.specs.compatibility import (
    LCTN_ALLOWED_VALUES,
    LIMITATIONS_DOC,
    RESTRICTED_PRIVILEGES,
    SERVER_PARAMETERS_DOC,
    UNSUPPORTED_STORAGE_ENGINES,
)
from advisor.specs.sku_catalog import (
    CATALOG,
    STORAGE_MAX_GIB,
    STORAGE_MAX_GIB_MEMORY_OPT,
    STORAGE_MIN_GIB,
)

# Default capacity headroom applied to on-prem CPU / memory / storage.
DEFAULT_HEADROOM = 0.20

# Cheaper tiers first, so ties resolve to the lower-cost option.
_TIER_RANK = {Tier.BURSTABLE: 0, Tier.GENERAL_PURPOSE: 1, Tier.MEMORY_OPTIMIZED: 2}

# TODO: verify against the official supported-versions doc —
# https://learn.microsoft.com/azure/mysql/flexible-server/concepts-supported-versions
_SUPPORTED_MAJOR_VERSIONS = {"5.7", "8.0"}

_MIGRATION_DOC = (
    "https://learn.microsoft.com/azure/mysql/migrate/"
    "mysql-on-premises-azure-db/08-data-migration"
)
_TIERS_DOC = (
    "https://learn.microsoft.com/azure/mysql/flexible-server/"
    "concepts-service-tiers-storage"
)


def recommend(profile: OnPremProfile, headroom: float = DEFAULT_HEADROOM) -> Recommendation:
    """Produce a sizing + compatibility recommendation for a source server."""
    findings: list[Finding] = []

    _check_version(profile, findings)
    _check_storage_engines(profile, findings)
    _check_lower_case_table_names(profile, findings)
    _check_restricted_privileges(profile, findings)

    sku, rationale = _select_sku(profile, headroom, findings)
    storage_gib, storage_notes = _estimate_storage(profile, sku, headroom, findings)

    _check_tier_caveats(profile, sku, findings)

    return Recommendation(
        sku=sku,
        sizing_rationale=rationale,
        storage_gib=storage_gib,
        storage_notes=storage_notes,
        findings=findings,
    )


def _major(version: str) -> str:
    return ".".join(version.split(".")[:2])


def _check_version(profile: OnPremProfile, findings: list[Finding]) -> None:
    major = _major(profile.mysql_version)
    if major not in _SUPPORTED_MAJOR_VERSIONS:
        supported = ", ".join(sorted(_SUPPORTED_MAJOR_VERSIONS))
        findings.append(
            Finding(
                code="VERSION_UPGRADE_REQUIRED",
                severity=Severity.BLOCKER,
                message=(
                    f"Source runs MySQL {profile.mysql_version}; Flexible Server targets "
                    f"major versions {{{supported}}}. Upgrade the source to a supported "
                    "major version first, and run the MySQL upgrade checker to surface "
                    "schema conflicts (reserved words, utf8mb3, ZEROFILL/display width, "
                    "FK constraint names > 64 chars, temporal types)."
                ),
                source=_MIGRATION_DOC,
            )
        )


def _check_storage_engines(profile: OnPremProfile, findings: list[Finding]) -> None:
    for engine in profile.storage_engines:
        if engine.upper() in UNSUPPORTED_STORAGE_ENGINES:
            findings.append(
                Finding(
                    code="UNSUPPORTED_STORAGE_ENGINE",
                    severity=Severity.BLOCKER,
                    message=(
                        f"Storage engine '{engine}' is not supported on Flexible Server "
                        "(supported engines: InnoDB, MEMORY). Convert affected tables to "
                        "InnoDB before migrating."
                    ),
                    source=LIMITATIONS_DOC,
                )
            )


def _check_lower_case_table_names(profile: OnPremProfile, findings: list[Finding]) -> None:
    raw = profile.params.get("lower_case_table_names")
    if raw is None:
        return
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return
    major = _major(profile.mysql_version)
    allowed = LCTN_ALLOWED_VALUES.get(major, {1, 2})
    if value not in allowed:
        findings.append(
            Finding(
                code="LOWER_CASE_TABLE_NAMES_UNSUPPORTED",
                severity=Severity.BLOCKER,
                message=(
                    f"Source has lower_case_table_names={value}, but Flexible Server "
                    f"(MySQL {major}) supports only {sorted(allowed)}. This value is fixed "
                    "at server creation and cannot be changed afterward, so identifier "
                    "case-sensitivity behavior will differ after migration."
                ),
                source=SERVER_PARAMETERS_DOC,
            )
        )
    else:
        findings.append(
            Finding(
                code="LOWER_CASE_TABLE_NAMES_IMMUTABLE",
                severity=Severity.INFO,
                message=(
                    f"lower_case_table_names={value} must be set at server creation; it "
                    "cannot be changed afterward (it is also copied to replicas and restores)."
                ),
                source=SERVER_PARAMETERS_DOC,
            )
        )


def _check_restricted_privileges(profile: OnPremProfile, findings: list[Finding]) -> None:
    used = {p.upper() for p in profile.privileges_used}
    restricted = sorted(used & RESTRICTED_PRIVILEGES)
    if restricted:
        findings.append(
            Finding(
                code="RESTRICTED_PRIVILEGES",
                severity=Severity.WARNING,
                message=(
                    f"These privileges are restricted on Flexible Server: "
                    f"{', '.join(restricted)}. The DBA role is not granted; rework "
                    "dependencies such as DEFINER clauses (which require SUPER) before "
                    "migrating."
                ),
                source=LIMITATIONS_DOC,
            )
        )


def _allowed_tiers(profile: OnPremProfile) -> set[Tier]:
    allowed = set(Tier)
    # Burstable is not for production and supports neither HA nor read replicas.
    if profile.is_production or profile.requires_ha or profile.requires_read_replica:
        allowed.discard(Tier.BURSTABLE)
    return allowed


def _select_sku(
    profile: OnPremProfile, headroom: float, findings: list[Finding]
) -> tuple[SkuSpec | None, str]:
    req_vcores = math.ceil(profile.cpu_cores * (1 + headroom))
    req_memory = profile.memory_gib * (1 + headroom)
    req_iops = profile.peak_iops or 0
    req_conns = profile.peak_connections or 0

    allowed = _allowed_tiers(profile)
    candidates = [
        s
        for s in CATALOG
        if s.tier in allowed
        and s.vcores >= req_vcores
        and s.memory_gib >= req_memory
        and s.max_iops >= req_iops
        and s.max_connections >= req_conns
    ]

    rationale = (
        f"Required (with {int(headroom * 100)}% headroom): "
        f">= {req_vcores} vCores, >= {req_memory:.1f} GiB memory"
        + (f", >= {req_iops} IOPS" if req_iops else "")
        + (f", >= {req_conns} connections" if req_conns else "")
        + "."
    )

    if not candidates:
        findings.append(
            Finding(
                code="NO_FITTING_SKU",
                severity=Severity.BLOCKER,
                message=(
                    "No available compute size meets the required vCores / memory / IOPS / "
                    "connections. The workload may exceed the largest offered size, or "
                    "requirements should be re-examined."
                ),
                source=_TIERS_DOC,
            )
        )
        return None, rationale

    best = min(candidates, key=lambda s: (s.vcores, s.memory_gib, _TIER_RANK[s.tier]))
    rationale += f" Smallest fitting size: {best.name} ({best.tier.value})."
    return best, rationale


def _estimate_storage(
    profile: OnPremProfile,
    sku: SkuSpec | None,
    headroom: float,
    findings: list[Finding],
) -> tuple[int, str]:
    # Provision for data growth, and keep headroom below the 5% read-only threshold.
    raw = max(profile.data_size_gib * (1 + headroom), profile.data_size_gib / 0.95)
    storage_gib = max(STORAGE_MIN_GIB, math.ceil(raw))

    tier_max = (
        STORAGE_MAX_GIB_MEMORY_OPT
        if sku is not None and sku.tier is Tier.MEMORY_OPTIMIZED
        else STORAGE_MAX_GIB
    )
    if storage_gib > tier_max:
        findings.append(
            Finding(
                code="STORAGE_EXCEEDS_MAX",
                severity=Severity.BLOCKER,
                message=(
                    f"Estimated storage {storage_gib} GiB exceeds the maximum "
                    f"{tier_max} GiB for the selected tier."
                ),
                source=_TIERS_DOC,
            )
        )
        storage_gib = tier_max

    notes = (
        f"Provision ~{storage_gib} GiB (data {profile.data_size_gib:.0f} GiB + headroom). "
        "Storage scales up only, never down. The server goes read-only when free space "
        "drops below 5% (or 5 GiB above 100 GiB); enable storage autogrow."
    )
    return storage_gib, notes


def _check_tier_caveats(
    profile: OnPremProfile, sku: SkuSpec | None, findings: list[Finding]
) -> None:
    if sku is None:
        return
    if sku.tier is Tier.BURSTABLE and profile.is_production:
        findings.append(
            Finding(
                code="BURSTABLE_IN_PRODUCTION",
                severity=Severity.WARNING,
                message=(
                    "Burstable tier is not recommended for production: it runs on a CPU "
                    "credit model and supports neither high availability nor read replicas."
                ),
                source=_TIERS_DOC,
            )
        )
