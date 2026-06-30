from advisor.core import recommend
from advisor.models import OnPremProfile, Tier


def test_small_nonprod_picks_burstable():
    profile = OnPremProfile(
        mysql_version="8.0.36",
        cpu_cores=1,
        memory_gib=2,
        data_size_gib=10,
        is_production=False,
    )
    rec = recommend(profile)
    assert rec.sku is not None
    assert rec.sku.tier is Tier.BURSTABLE


def test_production_excludes_burstable():
    profile = OnPremProfile(
        mysql_version="8.0.36",
        cpu_cores=2,
        memory_gib=8,
        data_size_gib=50,
        is_production=True,
    )
    rec = recommend(profile)
    assert rec.sku is not None
    assert rec.sku.tier is not Tier.BURSTABLE


def test_memory_heavy_workload_picks_memory_optimized():
    # 60 GiB memory on only 4 cores: General Purpose (4 GiB/vCore) would need many
    # more vCores than Memory-Optimized (8 GiB/vCore), so MO wins on vCore count.
    profile = OnPremProfile(
        mysql_version="8.0.36",
        cpu_cores=4,
        memory_gib=60,
        data_size_gib=100,
        is_production=True,
    )
    rec = recommend(profile)
    assert rec.sku is not None
    assert rec.sku.tier is Tier.MEMORY_OPTIMIZED


def test_iops_requirement_drives_larger_sku():
    # High IOPS demand should force a bigger compute size even for modest CPU/memory.
    low = OnPremProfile(
        mysql_version="8.0.36",
        cpu_cores=2,
        memory_gib=8,
        data_size_gib=50,
        peak_iops=0,
        is_production=True,
    )
    high = OnPremProfile(
        mysql_version="8.0.36",
        cpu_cores=2,
        memory_gib=8,
        data_size_gib=50,
        peak_iops=15000,
        is_production=True,
    )
    rec_low = recommend(low)
    rec_high = recommend(high)
    assert rec_high.sku.max_iops >= 15000
    assert rec_high.sku.vcores >= rec_low.sku.vcores


def test_storage_respects_minimum():
    profile = OnPremProfile(
        mysql_version="8.0.36",
        cpu_cores=2,
        memory_gib=8,
        data_size_gib=1,
        is_production=True,
    )
    rec = recommend(profile)
    assert rec.storage_gib >= 20
