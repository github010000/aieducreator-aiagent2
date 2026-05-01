import argparse
import os
import time
from datetime import date

import duckdb
import requests
from dotenv import load_dotenv

_folder = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_folder, ".env"))

DB_PATH = os.getenv("DUCKDB_PATH", os.path.join(_folder, "sales.duckdb"))


def fetch_sales_data(api_key: str, start_index: int, end_index: int, period: str):
    """서울 열린데이터광장 API에서 상권 매출 데이터를 가져옵니다."""
    url = f"http://openapi.seoul.go.kr:8088/{api_key}/json/VwsmTrdarSelngQq/{start_index}/{end_index}/{period}"
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        data = response.json()
        if "VwsmTrdarSelngQq" in data and "row" in data["VwsmTrdarSelngQq"]:
            return data["VwsmTrdarSelngQq"]["row"]
        result = data.get("VwsmTrdarSelngQq", {}).get("RESULT", {})
        if result.get("CODE") == "INFO-200":
            return []
        error_message = result.get("MESSAGE", "알 수 없는 오류")
        print(f"API 에러: {error_message}")
        if "인증키" in error_message:
            return "AUTH_ERROR"
        return None
    except Exception as exc:
        print(f"API 호출 중 오류 발생: {exc}")
        return None


def initialize_database(db_path: str) -> None:
    """DuckDB 파일 및 quarterly_sales 테이블을 생성합니다."""
    print(f"데이터베이스 '{db_path}' 초기화 중...")
    con = duckdb.connect(db_path)
    try:
        con.execute("""
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
    finally:
        con.close()
    print("데이터베이스 테이블 준비 완료.")


def update_database_for_period(
    db_path: str, api_key: str, year: str, quarter: str
) -> bool:
    """특정 기간의 API 데이터를 수집하여 DB에 upsert합니다."""
    period = f"{year}{quarter}"
    print(f"--- {year}년 {quarter}분기 데이터 수집 시작 ---")
    start, end, total_inserted = 1, 1000, 0

    con = duckdb.connect(db_path)
    try:
        while True:
            print(f"{start} ~ {end} 범위 요청 중...")
            rows = fetch_sales_data(api_key, start, end, period)
            if rows == "AUTH_ERROR":
                return False
            if not rows:
                break

            data_to_insert = [
                (
                    f"{year}{quarter}",
                    r["TRDAR_SE_CD_NM"],
                    r["TRDAR_CD"],
                    r["TRDAR_CD_NM"],
                    r["SVC_INDUTY_CD"],
                    r["SVC_INDUTY_CD_NM"],
                    r["THSMON_SELNG_AMT"],
                    r["THSMON_SELNG_CO"],
                    r["MDWK_SELNG_AMT"],
                    r["WKEND_SELNG_AMT"],
                    r["MON_SELNG_AMT"],
                    r["TUES_SELNG_AMT"],
                    r["WED_SELNG_AMT"],
                    r["THUR_SELNG_AMT"],
                    r["FRI_SELNG_AMT"],
                    r["SAT_SELNG_AMT"],
                    r["SUN_SELNG_AMT"],
                    r["TMZON_00_06_SELNG_AMT"],
                    r["TMZON_06_11_SELNG_AMT"],
                    r["TMZON_11_14_SELNG_AMT"],
                    r["TMZON_14_17_SELNG_AMT"],
                    r["TMZON_17_21_SELNG_AMT"],
                    r["TMZON_21_24_SELNG_AMT"],
                    r["ML_SELNG_AMT"],
                    r["FML_SELNG_AMT"],
                    r["AGRDE_10_SELNG_AMT"],
                    r["AGRDE_20_SELNG_AMT"],
                    r["AGRDE_30_SELNG_AMT"],
                    r["AGRDE_40_SELNG_AMT"],
                    r["AGRDE_50_SELNG_AMT"],
                    r["AGRDE_60_ABOVE_SELNG_AMT"],
                )
                for r in rows
            ]

            con.executemany(
                """
                INSERT INTO quarterly_sales VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                ) ON CONFLICT DO NOTHING
                """,
                data_to_insert,
            )

            inserted_count = len(data_to_insert)
            total_inserted += inserted_count
            print(f"-> {len(rows)}건 확인, {inserted_count}건 처리.")

            if len(rows) < 1000:
                break
            start += 1000
            end += 1000
            time.sleep(0.1)
    finally:
        con.close()

    print(f"--- {year}년 {quarter}분기 완료. 총 {total_inserted}건 처리 ---")
    return True


def _available_quarters() -> list[tuple[str, str]]:
    """API 공개 기준(분기 종료 후 3개월)으로 수집 가능한 분기 목록을 반환."""
    today = date.today()
    # 현재 분기보다 1개 이상 앞선 분기까지 공개됨
    available = []
    for year in range(2024, today.year + 1):
        for q in range(1, 5):
            release_month = q * 3 + 3  # Q1→6월, Q2→9월, Q3→12월, Q4→3월(익년)
            release_year = year if release_month <= 12 else year + 1
            release_month = release_month if release_month <= 12 else release_month - 12
            if date(release_year, release_month, 1) <= today:
                available.append((str(year), str(q)))
    return available


def _existing_quarters(db_path: str) -> set[str]:
    """DB에 이미 수록된 year_quarter 값 집합을 반환."""
    if not os.path.exists(db_path):
        return set()
    con = duckdb.connect(db_path, read_only=True)
    try:
        rows = con.execute(
            "SELECT DISTINCT year_quarter FROM quarterly_sales"
        ).fetchall()
        return {r[0] for r in rows}
    finally:
        con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="서울 열린데이터광장 상권 매출 데이터 수집기",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  특정 분기:   uv run create_database_openapi.py --year 2025 --quarter 2
  범위 수집:   uv run create_database_openapi.py --year 2025 --quarter 2 --to-quarter 4
  누락 자동:   uv run create_database_openapi.py --auto
        """,
    )
    parser.add_argument("--year", type=int, help="수집할 연도 (예: 2025)")
    parser.add_argument("--quarter", type=int, choices=[1, 2, 3, 4], help="시작 분기")
    parser.add_argument(
        "--to-quarter", type=int, choices=[1, 2, 3, 4], help="종료 분기 (범위 수집 시)"
    )
    parser.add_argument(
        "--auto", action="store_true", help="DB 미수록 분기를 자동 감지하여 수집"
    )
    args = parser.parse_args()

    api_key = os.getenv("SEOUL_DATA_API_KEY")
    if not api_key:
        print("[ERROR] 환경변수 SEOUL_DATA_API_KEY가 설정되지 않았습니다.")
        raise SystemExit(1)

    initialize_database(DB_PATH)

    if args.auto:
        existing = _existing_quarters(DB_PATH)
        targets = [
            (y, q) for y, q in _available_quarters() if f"{y}{q}" not in existing
        ]
        if not targets:
            print("수집 가능한 신규 분기가 없습니다. DB가 최신 상태입니다.")
            raise SystemExit(0)
        print(f"누락 분기 {len(targets)}개 감지: {[f'{y}Q{q}' for y, q in targets]}")
    elif args.year and args.quarter:
        start_q = args.quarter
        end_q = args.to_quarter if args.to_quarter else args.quarter
        if end_q < start_q:
            print("[ERROR] --to-quarter는 --quarter 이상이어야 합니다.")
            raise SystemExit(1)
        targets = [(str(args.year), str(q)) for q in range(start_q, end_q + 1)]
    else:
        parser.print_help()
        raise SystemExit(1)

    for year, quarter in targets:
        if not update_database_for_period(DB_PATH, api_key, year, quarter):
            print(f"[ERROR] {year}년 {quarter}분기 수집 실패. 중단합니다.")
            break

    print("\n--- 모든 데이터 수집 및 업데이트 완료 ---")
