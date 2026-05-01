import os
import tempfile

import duckdb
import pytest


@pytest.fixture
def tmp_duckdb(tmp_path):
    """테스트용 임시 DuckDB 파일 생성."""
    db_path = str(tmp_path / "test_sales.duckdb")
    con = duckdb.connect(db_path)
    con.execute("""
        CREATE TABLE quarterly_sales (
            year_quarter TEXT NOT NULL,
            district_type TEXT,
            district_code TEXT NOT NULL,
            district_name TEXT,
            service_category_code TEXT,
            service_category_name TEXT,
            monthly_sales_amount INTEGER,
            monthly_sales_count INTEGER,
            weekday_sales_amount INTEGER,
            weekend_sales_amount INTEGER,
            sales_monday INTEGER, sales_tuesday INTEGER, sales_wednesday INTEGER,
            sales_thursday INTEGER, sales_friday INTEGER, sales_saturday INTEGER, sales_sunday INTEGER,
            sales_time_00_06 INTEGER, sales_time_06_11 INTEGER, sales_time_11_14 INTEGER,
            sales_time_14_17 INTEGER, sales_time_17_21 INTEGER, sales_time_21_24 INTEGER,
            male_sales_amount INTEGER, female_sales_amount INTEGER,
            sales_by_age_10s INTEGER, sales_by_age_20s INTEGER,
            sales_by_age_30s INTEGER, sales_by_age_40s INTEGER,
            sales_by_age_50s INTEGER, sales_by_age_60s_above INTEGER,
            PRIMARY KEY (year_quarter, district_code, service_category_code)
        )
    """)
    con.close()
    return db_path


def test_get_db_schema_info_returns_schema(monkeypatch, tmp_duckdb):
    monkeypatch.setenv("DUCKDB_PATH", tmp_duckdb)

    import importlib

    import servers.data_analysis_server as server_module

    importlib.reload(server_module)

    schema = server_module.get_db_schema_info()
    assert schema is not None
    assert "quarterly_sales" in schema


def test_get_db_schema_info_returns_none_when_no_db(monkeypatch, tmp_path):
    monkeypatch.setenv("DUCKDB_PATH", str(tmp_path / "nonexistent.duckdb"))

    import importlib

    import servers.data_analysis_server as server_module

    importlib.reload(server_module)

    schema = server_module.get_db_schema_info()
    assert schema is None


def test_db_insert_and_query(tmp_duckdb):
    """DuckDB ON CONFLICT DO NOTHING 동작 검증."""
    con = duckdb.connect(tmp_duckdb)
    con.execute("""
        INSERT INTO quarterly_sales (year_quarter, district_code, service_category_code)
        VALUES ('20251', 'D001', 'S001')
    """)
    con.execute("""
        INSERT INTO quarterly_sales (year_quarter, district_code, service_category_code)
        VALUES ('20251', 'D001', 'S001')
        ON CONFLICT DO NOTHING
    """)
    count = con.execute("SELECT COUNT(*) FROM quarterly_sales").fetchone()[0]
    con.close()
    assert count == 1
