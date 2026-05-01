import json
import logging
import os
import time
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv
from fastmcp import FastMCP
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

_folder = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_folder, "..", ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

mcp_server = FastMCP(name="SeoulMetroExpert")

# 지하철 실시간 API는 별도 키 필요. 미설정 시 샘플 키(조회 제한 있음) 사용.
METRO_API_KEY = os.getenv("SEOUL_METRO_API_KEY") or "sample"
METRO_API_BASE = "http://swopenapi.seoul.go.kr/api/subway"
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("METRO_MCP_PORT", "9003"))

_TRAIN_STATUS = {"0": "진입", "1": "도착", "2": "출발", "3": "전역출발"}
_ARVL_CODE = {
    "0": "진입",
    "1": "도착",
    "2": "출발",
    "3": "전역출발",
    "99": "운행중",
}

# 하루 1000건 API 제한 대응 TTL 캐시 (도착: 60초, 위치: 120초)
_CACHE_TTL_ARRIVAL = 60.0
_CACHE_TTL_POSITION = 120.0
_api_cache: dict[str, tuple[list[dict], float]] = {}


def _cache_get(key: str, ttl: float) -> list[dict] | None:
    entry = _api_cache.get(key)
    if entry and (time.time() - entry[1]) < ttl:
        return entry[0]
    return None


def _cache_set(key: str, data: list[dict]) -> None:
    _api_cache[key] = (data, time.time())


def _fetch_arrival(station_name: str) -> list[dict] | None:
    """역명으로 실시간 도착 정보 조회. TTL 60초 캐시 적용."""
    cache_key = f"arrival:{station_name}"
    cached = _cache_get(cache_key, _CACHE_TTL_ARRIVAL)
    if cached is not None:
        logger.info("도착 캐시 히트: '%s' (%d건)", station_name, len(cached))
        return cached

    url = f"{METRO_API_BASE}/{METRO_API_KEY}/json/realtimeStationArrival/0/30/{station_name}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        result = data.get("errorMessage", {})
        if result.get("code") not in ("INFO-000", None) and result.get("status") != 200:
            logger.warning("도착 API 오류: %s", result.get("message"))
            return None
        arrivals = data.get("realtimeArrivalList", [])
        _cache_set(cache_key, arrivals)
        return arrivals
    except Exception as exc:
        logger.error("도착 API 호출 오류: %s", exc)
        return None


def _fetch_position(line_name: str) -> list[dict] | None:
    """호선명으로 실시간 열차 위치 정보 조회. TTL 120초 캐시 적용."""
    cache_key = f"position:{line_name}"
    cached = _cache_get(cache_key, _CACHE_TTL_POSITION)
    if cached is not None:
        logger.info("위치 캐시 히트: '%s' (%d건)", line_name, len(cached))
        return cached

    url = f"{METRO_API_BASE}/{METRO_API_KEY}/json/realtimePosition/0/200/{line_name}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        result = data.get("errorMessage", {})
        if result.get("code") not in ("INFO-000", None) and result.get("status") != 200:
            logger.warning("위치 API 오류: %s", result.get("message"))
            return None
        positions = data.get("realtimePositionList", [])
        _cache_set(cache_key, positions)
        return positions
    except Exception as exc:
        logger.error("위치 API 호출 오류: %s", exc)
        return None


class MetroQueryInput(BaseModel):
    query: str = Field(description="지하철 실시간 정보를 위한 자연어 질문")


@mcp_server.tool(
    name="get_realtime_arrival",
    description="특정 지하철 역의 실시간 열차 도착 정보를 조회하고 분석합니다. '강남역 다음 열차', '홍대입구 2호선 도착 시간' 등의 질문에 사용합니다.",
)
def get_realtime_arrival(input_data: MetroQueryInput) -> Dict[str, Any]:
    """자연어 질문에서 역명을 추출하고 실시간 도착 정보를 반환."""
    t_total = time.perf_counter()
    logger.info("도착 정보 요청: '%s'", input_data.query)

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    extract_prompt = f"""
    다음 질문에서 조회할 지하철 역명만 추출하세요.
    역명만 출력하고, 다른 설명은 절대 포함하지 마세요.
    '역' 접미어도 제외하세요. (예: 강남역 → 강남)

    질문: {input_data.query}
    """

    t0 = time.perf_counter()
    station_name = llm.invoke(extract_prompt).content.strip()
    logger.info("역명 추출 (%.2fs): '%s'", time.perf_counter() - t0, station_name)

    t0 = time.perf_counter()
    arrivals = _fetch_arrival(station_name)
    logger.info(
        "도착 조회 (%.2fs): %d건",
        time.perf_counter() - t0,
        len(arrivals) if arrivals else 0,
    )

    if arrivals is None:
        return {"error": f"'{station_name}' 역의 도착 정보를 가져오지 못했습니다."}
    if not arrivals:
        return {
            "error": f"'{station_name}' 역의 실시간 도착 데이터가 없습니다. 역명을 확인해주세요."
        }

    simplified = [
        {
            "호선": r.get("subwayId", ""),
            "방향": r.get("updnLine", ""),
            "행선지": r.get("trainLineNm", ""),
            "현재위치": r.get("bstatnNm", ""),
            "도착예정": r.get("arvlMsg2", ""),
            "위치안내": r.get("arvlMsg3", ""),
            "도착코드": _ARVL_CODE.get(str(r.get("arvlCd", "")), r.get("arvlCd", "")),
            "열차번호": r.get("btrainNo", ""),
            "열차종류": r.get("btrainSttus", "일반"),
            "막차여부": "막차" if r.get("lstcarAt") == "1" else "일반",
            "수신시각": r.get("recptnDt", ""),
        }
        for r in arrivals
    ]

    report_prompt = f"""
    당신은 서울 지하철 실시간 정보 전문가입니다.
    다음은 '{station_name}' 역의 실시간 도착 정보입니다.
    사용자 질문 의도에 맞게 핵심 정보를 간결하게 요약하고 안내하세요.

    ### 사용자 질문:
    {input_data.query}

    ### 실시간 도착 데이터:
    {json.dumps(simplified, indent=2, ensure_ascii=False)}

    - 도착 예정 시간, 방향, 행선지 중심으로 안내하세요.
    - 막차 정보가 있으면 강조하세요.
    - 마크다운 형식으로 작성하세요.
    """

    t0 = time.perf_counter()
    report = llm.invoke(report_prompt).content
    logger.info("도착 보고서 생성 (%.2fs)", time.perf_counter() - t0)
    logger.info("전체 처리 완료 (총 %.2fs)", time.perf_counter() - t_total)

    return {
        "result": {
            "station": station_name,
            "report": report,
            "raw_data": simplified,
        }
    }


@mcp_server.tool(
    name="get_realtime_operation",
    description="특정 호선의 실시간 열차 운행 현황(열차 위치)을 조회하고 분석합니다. '2호선 운행 현황', '신분당선 열차 위치' 등의 질문에 사용합니다.",
)
def get_realtime_operation(input_data: MetroQueryInput) -> Dict[str, Any]:
    """자연어 질문에서 호선명을 추출하고 실시간 운행 현황을 반환."""
    t_total = time.perf_counter()
    logger.info("운행 현황 요청: '%s'", input_data.query)

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    extract_prompt = f"""
    다음 질문에서 조회할 지하철 호선명만 추출하세요.
    호선명만 출력하고, 다른 설명은 절대 포함하지 마세요.
    형식은 반드시 'N호선' 또는 '신분당선', '경의중앙선' 등 정식 호선명으로 출력하세요.
    (예: 2호선, 신분당선, 경의중앙선, 공항철도)

    질문: {input_data.query}
    """

    t0 = time.perf_counter()
    line_name = llm.invoke(extract_prompt).content.strip()
    logger.info("호선명 추출 (%.2fs): '%s'", time.perf_counter() - t0, line_name)

    t0 = time.perf_counter()
    positions = _fetch_position(line_name)
    logger.info(
        "위치 조회 (%.2fs): %d건",
        time.perf_counter() - t0,
        len(positions) if positions else 0,
    )

    if positions is None:
        return {"error": f"'{line_name}' 운행 현황을 가져오지 못했습니다."}
    if not positions:
        return {
            "error": f"'{line_name}'의 실시간 운행 데이터가 없습니다. 호선명을 확인해주세요."
        }

    simplified = [
        {
            "호선": r.get("subwayNm", ""),
            "열차번호": r.get("trainNo", ""),
            "현재역": r.get("statnNm", ""),
            "종착역": r.get("statnTnm", ""),
            "방향": "상행" if str(r.get("updnLine")) == "1" else "하행",
            "상태": _TRAIN_STATUS.get(str(r.get("trainSttus", "")), "운행중"),
            "급행여부": "급행" if r.get("directAt") == "1" else "일반",
            "막차여부": "막차" if r.get("lstcarAt") == "1" else "일반",
            "수신시각": r.get("recptnDt", ""),
        }
        for r in positions
    ]

    report_prompt = f"""
    당신은 서울 지하철 실시간 운행 현황 전문가입니다.
    다음은 '{line_name}'의 실시간 열차 위치 정보입니다.
    사용자 질문 의도에 맞게 운행 현황을 간결하게 요약하세요.

    ### 사용자 질문:
    {input_data.query}

    ### 실시간 운행 데이터 ({len(simplified)}개 열차):
    {json.dumps(simplified, indent=2, ensure_ascii=False)}

    - 전체 운행 열차 수, 상행/하행 분포를 요약하세요.
    - 급행/막차 정보를 강조하세요.
    - 특이사항(지연, 혼잡 구간 등)이 보이면 안내하세요.
    - 마크다운 형식으로 작성하세요.
    """

    t0 = time.perf_counter()
    report = llm.invoke(report_prompt).content
    logger.info("운행 보고서 생성 (%.2fs)", time.perf_counter() - t0)
    logger.info("전체 처리 완료 (총 %.2fs)", time.perf_counter() - t_total)

    return {
        "result": {
            "line": line_name,
            "train_count": len(simplified),
            "report": report,
            "raw_data": simplified,
        }
    }


if __name__ == "__main__":
    if not METRO_API_KEY:
        raise SystemExit("[ERROR] 환경변수 SEOUL_DATA_API_KEY가 설정되지 않았습니다.")
    logger.info(
        "MCP [SeoulMetroExpert] 서버 시작 (host=%s, port=%d)", MCP_HOST, MCP_PORT
    )
    mcp_server.run(transport="streamable-http", host=MCP_HOST, port=MCP_PORT)
