"""Decision-core models. Pure data, no external dependencies."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Tier(str, Enum):
    BURSTABLE = "Burstable"
    GENERAL_PURPOSE = "GeneralPurpose"
    MEMORY_OPTIMIZED = "MemoryOptimized"


@dataclass(frozen=True)
class SkuSpec:
    """A single Azure MySQL Flexible Server compute size.

    Every numeric field is sourced from official docs; see `source`.
    """

    tier: Tier
    name: str               # Azure compute size, e.g. "Standard_D2ds_v4"
    vcores: int
    memory_gib: int         # Physical Memory Size (GiB)
    max_iops: int           # Max Supported IOPS for this compute size
    max_connections: int    # Max Connections for this compute size
    source: str             # provenance for the numbers above


@dataclass
class OnPremProfile:
    """The self-managed / on-prem MySQL server being assessed."""

    mysql_version: str
    cpu_cores: int
    memory_gib: float
    data_size_gib: float
    peak_iops: int | None = None
    peak_connections: int | None = None
    is_production: bool = True
    requires_ha: bool = False
    requires_read_replica: bool = False
    # Current server parameters (e.g. {"lower_case_table_names": "0"}).
    params: dict[str, str] = field(default_factory=dict)
    # Storage engines in use (e.g. ["InnoDB", "MyISAM"]).
    storage_engines: list[str] = field(default_factory=list)
    # Privileges the workload relies on (e.g. ["SUPER", "FILE"]).
    privileges_used: list[str] = field(default_factory=list)
    # Reserved for future schema-level compatibility rules.
    features_used: list[str] = field(default_factory=list)


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    BLOCKER = "blocker"


@dataclass
class Finding:
    code: str
    severity: Severity
    message: str
    source: str | None = None


@dataclass
class Recommendation:
    sku: SkuSpec | None
    sizing_rationale: str
    storage_gib: int
    storage_notes: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def blockers(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.BLOCKER]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.WARNING]
