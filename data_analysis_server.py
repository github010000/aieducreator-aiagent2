### 1. 필요한 모듈 / 함수 임포트
import json
import os
import sqlite3
from typing import Any, Dict

from dotenv import load_dotenv
from fastmcp import FastMCP
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

### 2. 환경 설정

# 실행 파일 폴더 경로 가져오기
folder_path = os.path.dirname(os.path.abspath(__file__))

# OpenAI API Key 가져오기
env_file_path = os.path.join(folder_path, ".env")
load_dotenv(env_file_path)

# 분석 서버 생성하기
mcp_server = FastMCP(name="DataAnalysisExpert")

# llm 생성하기
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# DB 파일 경로 설정하기
DB_PATH = os.path.join(folder_path, "sales.db")


### 3. DB 스키마 정보 생성 함수 정의


def get_db_schema_info() -> str | None:
    """데이터베이스의 스키마 정보를 텍스트로 반환합니다."""
    if not os.path.exists(DB_PATH):
        return None
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='quarterly_sales';"
        )
        result = cursor.fetchone()
        return result[0] if result else None


### 4. 분석 전문가 도구 함수 정의


class AnalysisInput(BaseModel):
    query: str = Field(description="상권 분석을 위한 사용자의 자연어 질문")


@mcp_server.tool(
    name="analyze_commercial_district",
    description="사용자의 자연어 질문을 SQL로 변환하고 데이터베이스를 조회하여, 그 결과를 바탕으로 전문적인 분석 보고서를 생성합니다.",
)
def analyze_commercial_district(input_data: AnalysisInput) -> Dict[str, Any]:
    """사용자 질문을 분석하여 보고서를 작성하는 전문가 도구"""
    print(f"--- [DataAnalysisExpert] 분석 요청 접수: '{input_data.query}' ---")

    # 1. DB 스키마 정보 생성
    db_schema = get_db_schema_info()
    if not db_schema:
        return {
            "error": f"분석을 위한 데이터베이스 파일({DB_PATH})이 없습니다. 담당자가 먼저 DB를 생성해야 합니다."
        }

    # 2. LLM을 이용한 SQL 쿼리 생성용 프롬프트 정의
    sql_prompt = f"""
    당신은 대한민국 서울시 상권분석 전문가이자 SQL 마스터입니다.
    아래 DB 스키마와 컬럼 의미를 참고하여, 사용자 질문에 가장 적합한 SQLite 쿼리를 생성해주세요.

    ### 데이터베이스 스키마:
    {db_schema}
    
    ### 데이터 구조 이해 (필수):
    - 이 DB는 개별 매장(상호명) 단위가 아닌 **상권(구역) 단위** 집계 데이터입니다. 개별 상호명 컬럼은 존재하지 않습니다.
    - 동일한 상권이 분기마다 1개 행씩 존재합니다 (예: 강남역 × 5개 분기 = 5행).
    - 따라서 상권 순위를 낼 때는 반드시 `GROUP BY district_name`으로 중복을 제거하고 `SUM` 또는 집계 함수를 사용하세요.

    ### 주요 컬럼 의미 (영문 컬럼명 -> 한글 의미):
    - year_quarter: 기준년도분기 (예: '20241' = 2024년 1분기, '2024%' = 2024년 전체)
    - district_type: 상권 유형 (예: '골목상권', '발달상권', '전통시장', '관광특구')
    - district_name: 상권명 — "강남역", "성수동카페거리" 같은 개별 상권 이름 (행정구명 아님)
    - service_category_name: 서비스 업종명 (예: '커피-음료', '한식', '일반의류')
    - monthly_sales_amount: 월평균 추정 매출액
    - monthly_sales_count: 월평균 추정 매출 건수
    - weekday_sales_amount: 주중 매출액
    - weekend_sales_amount: 주말 매출액
    - sales_time_11_14: 점심시간(11시~14시) 매출액
    - sales_time_17_21: 저녁시간(17시~21시) 매출액
    - male_sales_amount: 남성 매출액
    - female_sales_amount: 여성 매출액
    - sales_by_age_10s ~ sales_by_age_60s_above: 연령대별 매출액

    ### 검색 규칙 (반드시 준수):
    1. 행정구(강남구, 마포구 등)로 검색할 때는 `district_name LIKE '%강남%'` 방식을 사용하세요.
    2. 카페/커피숍은 `service_category_name = '커피-음료'`를 사용하세요. '카페'라는 값은 DB에 없습니다.
    3. 업종명이 불확실할 때는 `service_category_name LIKE '%키워드%'` 방식으로 검색하세요.
    4. 상권 순위/TOP N 질문에는 `GROUP BY district_name`을 사용하고 SELECT에 `district_name, year_quarter`를 포함하세요.
    5. 기간이 명시되지 않으면 최신 분기(`year_quarter = '20251'`)를 기준으로 하세요.
    6. 사용자가 '점심 시간'을 언급하면 `sales_time_11_14`, '저녁'이면 `sales_time_17_21` 컬럼을 사용하세요.

    ### 사용자의 질문:
    {input_data.query}

    - 다른 설명 없이 오직 실행 가능한 SQLite 쿼리만 생성해주세요.
    """
    try:
        # 3. SQL 쿼리 생성
        sql_query = (
            llm.invoke(sql_prompt).content.strip().replace("`", "").replace("sql", "")
        )
        print(f"생성된 SQL 쿼리:\n{sql_query}")

        # 4. 생성된 SQL 쿼리 실행
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql_query)
            results = [dict(row) for row in cursor.fetchall()]

        if not results:
            report = "분석 결과, 해당 조건에 맞는 데이터가 없습니다. 다른 조건으로 질문해 보시는 것은 어떨까요?"
        else:
            # 5. LLM을 이용한 최종 보고서 생성
            report_prompt = f"""
            당신은 전문 데이터 분석가이자 보고서 작성가입니다.
            다음은 사용자의 원본 질문과 데이터베이스에서 추출한 분석 결과입니다.
            이 데이터를 단순히 나열하지 말고, 사용자가 질문한 의도에 맞춰 의미 있는 인사이트를 도출하고, 비교 및 분석하여 상세한 최종 보고서를 마크다운 형식으로 작성해주세요.

            ### 원본 사용자 질문:
            {input_data.query}

            ### 데이터베이스 조회 결과 (JSON 형식):
            {json.dumps(results, indent=2, ensure_ascii=False)}

            ### 최종 분석 보고서 (마크다운 형식):
            """
            report = llm.invoke(report_prompt).content

        print("--- [DataAnalysisExpert] 보고서 생성 완료 ---")
        return {"result": {"report": report, "executed_sql": sql_query}}

    except sqlite3.Error as e:
        error_message = (
            f"SQL 실행 중 오류가 발생했습니다: {e}\n실패한 쿼리: {sql_query}"
        )
        print(f"[ERROR] {error_message}")
        return {"error": error_message}
    except Exception as e:
        error_message = f"분석 프로세스 중 예측하지 못한 오류 발생: {e}"
        print(f"[ERROR] {error_message}")
        return {"error": error_message}


### 5. 서버 실행
if __name__ == "__main__":
    print("MCP [DataAnalysisExpert] 서버가 시작되었습니다.")
    mcp_server.run()
