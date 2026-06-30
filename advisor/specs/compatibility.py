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
