"""Azure Database for MySQL Flexible Server compute catalog.

All vCore / memory / Max IOPS / Max Connections values below are transcribed from
the official "Service Tiers - Azure Database for MySQL" doc:
  https://learn.microsoft.com/azure/mysql/flexible-server/concepts-service-tiers-storage
  (ms.date 2025-11-25)

Only the v4 compute sizes are listed as canonical. The doc lists v5 / ads-v5
equivalents (e.g. Standard_D2ads_v5, Standard_E2ds_v5) with identical
vCore / memory / IOPS / connection specs.

Storage limits (same source):
  - Burstable & General Purpose: 20 GiB to 16 TiB
  - Memory-Optimized:            20 GiB to 32 TiB
  - Scaled in 1-GiB increments, cannot be scaled down.
  - Minimum IOPS is 360 across all compute sizes.
"""
from __future__ import annotations

from advisor.models import SkuSpec, Tier

_SOURCE = (
    "https://learn.microsoft.com/azure/mysql/flexible-server/"
    "concepts-service-tiers-storage (ms.date 2025-11-25)"
)

# Storage bounds in GiB.
STORAGE_MIN_GIB = 20
STORAGE_MAX_GIB = 16 * 1024            # 16 TiB (Burstable / General Purpose)
STORAGE_MAX_GIB_MEMORY_OPT = 32 * 1024  # 32 TiB (Memory-Optimized)
MIN_IOPS = 360

CATALOG: list[SkuSpec] = [
    # Burstable (B-series). Not recommended for production; no HA / read replicas.
    SkuSpec(Tier.BURSTABLE, "Standard_B1ms", 1, 2, 640, 341, _SOURCE),
    SkuSpec(Tier.BURSTABLE, "Standard_B2s", 2, 4, 1280, 683, _SOURCE),
    SkuSpec(Tier.BURSTABLE, "Standard_B2ms", 2, 8, 1700, 1365, _SOURCE),
    SkuSpec(Tier.BURSTABLE, "Standard_B4ms", 4, 16, 2400, 2731, _SOURCE),
    SkuSpec(Tier.BURSTABLE, "Standard_B8ms", 8, 32, 3100, 5461, _SOURCE),
    SkuSpec(Tier.BURSTABLE, "Standard_B12ms", 12, 48, 3800, 8193, _SOURCE),
    SkuSpec(Tier.BURSTABLE, "Standard_B16ms", 16, 64, 4300, 10923, _SOURCE),
    SkuSpec(Tier.BURSTABLE, "Standard_B20ms", 20, 80, 5000, 13653, _SOURCE),
    # General Purpose (Ddsv4). Memory = 4 GiB per vCore.
    SkuSpec(Tier.GENERAL_PURPOSE, "Standard_D2ds_v4", 2, 8, 3200, 1365, _SOURCE),
    SkuSpec(Tier.GENERAL_PURPOSE, "Standard_D4ds_v4", 4, 16, 6400, 2731, _SOURCE),
    SkuSpec(Tier.GENERAL_PURPOSE, "Standard_D8ds_v4", 8, 32, 12800, 5461, _SOURCE),
    SkuSpec(Tier.GENERAL_PURPOSE, "Standard_D16ds_v4", 16, 64, 20000, 10923, _SOURCE),
    SkuSpec(Tier.GENERAL_PURPOSE, "Standard_D32ds_v4", 32, 128, 20000, 21845, _SOURCE),
    SkuSpec(Tier.GENERAL_PURPOSE, "Standard_D48ds_v4", 48, 192, 48000, 32768, _SOURCE),
    SkuSpec(Tier.GENERAL_PURPOSE, "Standard_D64ds_v4", 64, 256, 48000, 43691, _SOURCE),
    # Memory-Optimized (Edsv4). Memory = 8 GiB per vCore (except very large sizes).
    SkuSpec(Tier.MEMORY_OPTIMIZED, "Standard_E2ds_v4", 2, 16, 5000, 2731, _SOURCE),
    SkuSpec(Tier.MEMORY_OPTIMIZED, "Standard_E4ds_v4", 4, 32, 10000, 5461, _SOURCE),
    SkuSpec(Tier.MEMORY_OPTIMIZED, "Standard_E8ds_v4", 8, 64, 18000, 10923, _SOURCE),
    SkuSpec(Tier.MEMORY_OPTIMIZED, "Standard_E16ds_v4", 16, 128, 28000, 21845, _SOURCE),
    SkuSpec(Tier.MEMORY_OPTIMIZED, "Standard_E20ds_v4", 20, 160, 28000, 27306, _SOURCE),
    SkuSpec(Tier.MEMORY_OPTIMIZED, "Standard_E32ds_v4", 32, 256, 38000, 43691, _SOURCE),
    SkuSpec(Tier.MEMORY_OPTIMIZED, "Standard_E48ds_v4", 48, 384, 48000, 65536, _SOURCE),
    SkuSpec(Tier.MEMORY_OPTIMIZED, "Standard_E64ds_v4", 64, 504, 64000, 86016, _SOURCE),
]
