from advisor.core import recommend
from advisor.models import OnPremProfile, Severity, Tier


def test_retired_target_version_is_blocker():
    # 5.7 is GA (Retired): you can no longer create a server on it.
    profile = OnPremProfile(
        mysql_version="5.7.44",
        cpu_cores=2,
        memory_gib=8,
        data_size_gib=50,
        is_production=True,
    )
    rec = recommend(profile, target_version="5.7")
    codes = {f.code for f in rec.blockers}
    assert "TARGET_VERSION_UNSUPPORTED" in codes
    for f in rec.blockers:
        assert f.source


def test_unknown_target_version_is_blocker():
    profile = OnPremProfile(
        mysql_version="8.0.36",
        cpu_cores=2,
        memory_gib=8,
        data_size_gib=50,
        is_production=True,
    )
    rec = recommend(profile, target_version="9.5")
    codes = {f.code for f in rec.blockers}
    assert "TARGET_VERSION_UNSUPPORTED" in codes


def test_same_major_is_in_place_no_blocker():
    profile = OnPremProfile(
        mysql_version="8.0.36",
        cpu_cores=2,
        memory_gib=8,
        data_size_gib=50,
        is_production=True,
    )
    rec = recommend(profile, target_version="8.0")
    all_codes = {f.code for f in rec.findings}
    blocker_codes = {f.code for f in rec.blockers}
    assert "VERSION_MATCH" in all_codes
    assert "MAJOR_VERSION_UPGRADE" not in all_codes
    assert "VERSION_DOWNGRADE_UNSUPPORTED" not in blocker_codes


def test_cross_major_upgrade_is_warning_not_blocker():
    # 5.7 source -> 8.0 target is a supported but risky major upgrade.
    profile = OnPremProfile(
        mysql_version="5.7.44",
        cpu_cores=2,
        memory_gib=8,
        data_size_gib=50,
        is_production=True,
    )
    rec = recommend(profile, target_version="8.0")
    warning_codes = {f.code for f in rec.warnings}
    blocker_codes = {f.code for f in rec.blockers}
    assert "MAJOR_VERSION_UPGRADE" in warning_codes
    assert "TARGET_VERSION_UNSUPPORTED" not in blocker_codes


def test_target_8_4_from_8_0_is_upgrade():
    profile = OnPremProfile(
        mysql_version="8.0.36",
        cpu_cores=2,
        memory_gib=8,
        data_size_gib=50,
        is_production=True,
    )
    rec = recommend(profile, target_version="8.4")
    warning_codes = {f.code for f in rec.warnings}
    assert "MAJOR_VERSION_UPGRADE" in warning_codes
    assert not rec.blockers


def test_downgrade_target_is_blocker():
    profile = OnPremProfile(
        mysql_version="8.4.7",
        cpu_cores=2,
        memory_gib=8,
        data_size_gib=50,
        is_production=True,
    )
    rec = recommend(profile, target_version="8.0")
    codes = {f.code for f in rec.blockers}
    assert "VERSION_DOWNGRADE_UNSUPPORTED" in codes


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
        mysql_version="5.7.44",
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
