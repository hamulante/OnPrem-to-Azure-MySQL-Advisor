from advisor.collect import collect_profile


def make_fake(rows_by_substring: dict[str, list[tuple]]):
    def query(sql: str) -> list[tuple]:
        for key, rows in rows_by_substring.items():
            if key in sql:
                return rows
        return []

    return query


def test_collect_profile_maps_queryable_fields():
    fake = make_fake(
        {
            "VERSION()": [("8.0.36",)],
            "@@lower_case_table_names": [(0,)],
            "data_length + index_length": [(123.4,)],
            "Max_used_connections": [("Max_used_connections", "1500")],
            "DISTINCT engine": [("InnoDB",), ("MyISAM",)],
        }
    )
    profile = collect_profile(fake)

    assert profile["mysql_version"] == "8.0.36"
    assert profile["params"]["lower_case_table_names"] == "0"
    assert profile["data_size_gib"] == 123.4
    assert profile["peak_connections"] == 1500
    assert profile["storage_engines"] == ["InnoDB", "MyISAM"]


def test_collect_profile_leaves_host_fields_null():
    # MySQL cannot observe host CPU / memory / IOPS — these must stay None, not guessed.
    fake = make_fake({"VERSION()": [("8.0.36",)]})
    profile = collect_profile(fake)

    assert profile["cpu_cores"] is None
    assert profile["memory_gib"] is None
    assert profile["peak_iops"] is None


def test_collect_profile_accepts_host_field_overrides():
    # When the caller supplies host facts on the command line, they flow through.
    fake = make_fake({"VERSION()": [("8.0.36",)]})
    profile = collect_profile(fake, cpu_cores=4, memory_gib=16, peak_iops=4500)

    assert profile["cpu_cores"] == 4
    assert profile["memory_gib"] == 16
    assert profile["peak_iops"] == 4500


def test_collect_profile_handles_empty_results():
    profile = collect_profile(lambda sql: [])
    assert profile["mysql_version"] is None
    assert profile["data_size_gib"] == 0.0
    assert profile["peak_connections"] is None
    assert profile["storage_engines"] == []
    assert profile["params"] == {}
