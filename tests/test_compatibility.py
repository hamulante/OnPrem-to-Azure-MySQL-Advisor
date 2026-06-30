from advisor.core import recommend
from advisor.models import OnPremProfile, Severity, Tier


def test_unsupported_version_is_blocker():
    profile = OnPremProfile(
        mysql_version="5.5.62",
        cpu_cores=2,
        memory_gib=8,
        data_size_gib=50,
        is_production=True,
    )
    rec = recommend(profile)
    codes = {f.code for f in rec.blockers}
    assert "VERSION_UPGRADE_REQUIRED" in codes
    # Blocker findings must carry a source for traceability.
    for f in rec.blockers:
        assert f.source


def test_supported_version_has_no_version_blocker():
    profile = OnPremProfile(
        mysql_version="8.0.36",
        cpu_cores=2,
        memory_gib=8,
        data_size_gib=50,
        is_production=True,
    )
    rec = recommend(profile)
    codes = {f.code for f in rec.blockers}
    assert "VERSION_UPGRADE_REQUIRED" not in codes


def test_ha_requirement_excludes_burstable():
    profile = OnPremProfile(
        mysql_version="8.0.36",
        cpu_cores=1,
        memory_gib=2,
        data_size_gib=10,
        is_production=False,
        requires_ha=True,
    )
    rec = recommend(profile)
    assert rec.sku is not None
    assert rec.sku.tier is not Tier.BURSTABLE


def test_every_finding_has_source():
    profile = OnPremProfile(
        mysql_version="5.6.0",
        cpu_cores=2,
        memory_gib=8,
        data_size_gib=50,
        is_production=True,
    )
    rec = recommend(profile)
    for f in rec.findings:
        assert f.source, f"finding {f.code} is missing a source"


def test_unsupported_storage_engine_is_blocker():
    profile = OnPremProfile(
        mysql_version="8.0.36",
        cpu_cores=2,
        memory_gib=8,
        data_size_gib=50,
        storage_engines=["InnoDB", "MyISAM"],
    )
    rec = recommend(profile)
    codes = {f.code for f in rec.blockers}
    assert "UNSUPPORTED_STORAGE_ENGINE" in codes


def test_supported_storage_engine_has_no_blocker():
    profile = OnPremProfile(
        mysql_version="8.0.36",
        cpu_cores=2,
        memory_gib=8,
        data_size_gib=50,
        storage_engines=["InnoDB", "MEMORY"],
    )
    rec = recommend(profile)
    codes = {f.code for f in rec.findings}
    assert "UNSUPPORTED_STORAGE_ENGINE" not in codes


def test_lower_case_table_names_zero_is_blocker():
    # 0 (case-sensitive) is the common on-prem Linux default but unsupported on Flex.
    profile = OnPremProfile(
        mysql_version="8.0.36",
        cpu_cores=2,
        memory_gib=8,
        data_size_gib=50,
        params={"lower_case_table_names": "0"},
    )
    rec = recommend(profile)
    codes = {f.code for f in rec.blockers}
    assert "LOWER_CASE_TABLE_NAMES_UNSUPPORTED" in codes


def test_lower_case_table_names_one_is_info_not_blocker():
    profile = OnPremProfile(
        mysql_version="8.0.36",
        cpu_cores=2,
        memory_gib=8,
        data_size_gib=50,
        params={"lower_case_table_names": "1"},
    )
    rec = recommend(profile)
    blocker_codes = {f.code for f in rec.blockers}
    all_codes = {f.code for f in rec.findings}
    assert "LOWER_CASE_TABLE_NAMES_UNSUPPORTED" not in blocker_codes
    assert "LOWER_CASE_TABLE_NAMES_IMMUTABLE" in all_codes


def test_restricted_privilege_super_is_warning():
    profile = OnPremProfile(
        mysql_version="8.0.36",
        cpu_cores=2,
        memory_gib=8,
        data_size_gib=50,
        privileges_used=["SUPER"],
    )
    rec = recommend(profile)
    codes = {f.code for f in rec.warnings}
    assert "RESTRICTED_PRIVILEGES" in codes
