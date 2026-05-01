"""sales.db (SQLite) → sales.duckdb (DuckDB) 일회성 마이그레이션 스크립트."""

import os
import sqlite3
import time

import duckdb
from dotenv import load_dotenv

_folder = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_folder, ".env"))

SQLITE_PATH = os.path.join(_folder, "sales.db")
DUCKDB_PATH = os.getenv("DUCKDB_PATH", os.path.join(_folder, "sales.duckdb"))
BATCH_SIZE = 5000


def create_duckdb_table(duck_con: duckdb.DuckDBPyConnection) -> None:
    duck_con.execute("""
        CREATE TABLE IF NOT EXISTS quarterly_sales (
            year_quarter              TEXT NOT NULL,
            district_type             TEXT,
            district_code             TEXT NOT NULL,
            district_name             TEXT,
            service_category_code     TEXT,
            service_category_name     TEXT,
            monthly_sales_amount      BIGINT,
            monthly_sales_count       BIGINT,
            weekday_sales_amount      BIGINT,
            weekend_sales_amount      BIGINT,
            sales_monday              BIGINT,
            sales_tuesday             BIGINT,
            sales_wednesday           BIGINT,
            sales_thursday            BIGINT,
            sales_friday              BIGINT,
            sales_saturday            BIGINT,
            sales_sunday              BIGINT,
            sales_time_00_06          BIGINT,
            sales_time_06_11          BIGINT,
            sales_time_11_14          BIGINT,
            sales_time_14_17          BIGINT,
            sales_time_17_21          BIGINT,
            sales_time_21_24          BIGINT,
            male_sales_amount         BIGINT,
            female_sales_amount       BIGINT,
            sales_by_age_10s          BIGINT,
            sales_by_age_20s          BIGINT,
            sales_by_age_30s          BIGINT,
            sales_by_age_40s          BIGINT,
            sales_by_age_50s          BIGINT,
            sales_by_age_60s_above    BIGINT,
            PRIMARY KEY (year_quarter, district_code, service_category_code)
        )
    """)


def migrate() -> None:
    """SQLite quarterly_sales → DuckDB quarterly_sales 배치 마이그레이션."""
    if not os.path.exists(SQLITE_PATH):
        print(f"[ERROR] SQLite 파일을 찾을 수 없습니다: {SQLITE_PATH}")
        return

    sqlite_con = sqlite3.connect(SQLITE_PATH)
    duck_con = duckdb.connect(DUCKDB_PATH)

    try:
        create_duckdb_table(duck_con)

        total = sqlite_con.execute("SELECT COUNT(*) FROM quarterly_sales").fetchone()[0]
        print(f"마이그레이션 시작: {total:,}건 (배치 크기: {BATCH_SIZE})")

        inserted, skipped, offset = 0, 0, 0
        start_time = time.time()

        # id 컬럼(index=0) 제외, 나머지 30개 컬럼만 추출
        query = """
            SELECT
                year_quarter, district_type, district_code, district_name,
                service_category_code, service_category_name,
                monthly_sales_amount, monthly_sales_count,
                weekday_sales_amount, weekend_sales_amount,
                sales_monday, sales_tuesday, sales_wednesday, sales_thursday,
                sales_friday, sales_saturday, sales_sunday,
                sales_time_00_06, sales_time_06_11, sales_time_11_14,
                sales_time_14_17, sales_time_17_21, sales_time_21_24,
                male_sales_amount, female_sales_amount,
                sales_by_age_10s, sales_by_age_20s, sales_by_age_30s,
                sales_by_age_40s, sales_by_age_50s, sales_by_age_60s_above
            FROM quarterly_sales
            LIMIT ? OFFSET ?
        """

        while True:
            rows = sqlite_con.execute(query, (BATCH_SIZE, offset)).fetchall()
            if not rows:
                break

            before = duck_con.execute(
                "SELECT COUNT(*) FROM quarterly_sales"
            ).fetchone()[0]
            duck_con.executemany(
                """
                INSERT INTO quarterly_sales VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                ) ON CONFLICT DO NOTHING
                """,
                rows,
            )
            after = duck_con.execute("SELECT COUNT(*) FROM quarterly_sales").fetchone()[
                0
            ]

            batch_inserted = after - before
            batch_skipped = len(rows) - batch_inserted
            inserted += batch_inserted
            skipped += batch_skipped
            offset += len(rows)

            elapsed = time.time() - start_time
            print(
                f"  진행: {offset:>7,}/{total:,} | "
                f"삽입 {inserted:,} | 스킵 {skipped:,} | {elapsed:.1f}s"
            )

        elapsed = time.time() - start_time
        print(
            f"\n완료: 삽입 {inserted:,}건 | 중복 스킵 {skipped:,}건 | 소요 {elapsed:.1f}s"
        )
        print(
            f"DuckDB 최종 행 수: {duck_con.execute('SELECT COUNT(*) FROM quarterly_sales').fetchone()[0]:,}"
        )

    finally:
        sqlite_con.close()
        duck_con.close()


if __name__ == "__main__":
    migrate()
