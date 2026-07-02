"""Platform-compatibility reference data (on-prem -> PaaS, version-independent).

Every set / value below is transcribed from official docs; see the doc URLs.
These are 'axis 2' facts: they hold even for a same-version (e.g. 8.0 -> 8.0)
migration, because they stem from Flexible Server being a managed service.
"""
from __future__ import annotations

LIMITATIONS_DOC = (
    "https://learn.microsoft.com/azure/mysql/flexible-server/concepts-limitations"
)
SERVER_PARAMETERS_DOC = (
    "https://learn.microsoft.com/azure/mysql/flexible-server/concepts-server-parameters"
)
SUPPORTED_VERSIONS_DOC = (
    "https://learn.microsoft.com/azure/mysql/flexible-server/concepts-supported-versions"
)

# Major versions you can CREATE a new Flexible Server on — i.e. valid migration
# targets. concepts-supported-versions (ms.date 2026-05-13):
#   5.7  -> GA (Retired): new servers can no longer be created.
#   8.0  -> GA (current minor 8.0.44)
#   8.4  -> GA (current minor 8.4.7)
#   9.5  -> Innovation preview: no HA / replica / backup, 30-day lifecycle; not a
#           production migration target.
CREATABLE_TARGET_VERSIONS = {"8.0", "8.4"}
# Retired majors that still run but cannot be created fresh (so not a target).
RETIRED_VERSIONS = {"5.7"}
# Sensible default target when the caller does not specify one.
DEFAULT_TARGET_VERSION = "8.0"

# Storage engines — concepts-limitations (updated 2025-11-10).
SUPPORTED_STORAGE_ENGINES = {"INNODB", "MEMORY"}
UNSUPPORTED_STORAGE_ENGINES = {"MYISAM", "BLACKHOLE", "ARCHIVE", "FEDERATED"}

# Restricted static privileges — concepts-limitations.
# The DBA role is also restricted; DEFINER requires SUPER and is therefore restricted.
RESTRICTED_PRIVILEGES = {"SUPER", "FILE", "CREATE TABLESPACE", "SHUTDOWN"}

# lower_case_table_names allowed values by source major version —
# concepts-server-parameters (updated 2026-06-03). Default is 1.
# Note: the on-prem Linux default of 0 (case-sensitive) is NOT offered, and the
# value is fixed at server creation (also copied to replicas / restores).
LCTN_ALLOWED_VALUES: dict[str, set[int]] = {"8.0": {1, 2}, "5.7": {1, 2}}
LCTN_DEFAULT = 1
