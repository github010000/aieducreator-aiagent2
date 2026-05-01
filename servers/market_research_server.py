### 1. 환경 설정

# 필요한 함수 임포트
import logging
import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from fastmcp import FastMCP
from langchain_tavily import TavilySearch
from pydantic import BaseModel, Field

_folder = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_folder, "..", ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MARKET_MCP_PORT", "9001"))


### 2. 서버 및 도구 설정

# 서버 설정
mcp_server = FastMCP(name="MarketResearchExpert")

# 도구 설정
tavily_tool = TavilySearch(max_results=3)


### 3. 전문가 도구 함수 정의


# 입력 스키마 정의
class ResearchInput(BaseModel):
    topic: str = Field(description="조사할 시장 또는 주제")


# 전문가 도구 함수 정의
@mcp_server.tool(
    name="conduct_market_research",
    description="주어진 주제에 대해 웹 검색을 수행하고, 분석에 필요한 핵심 정보를 요약하여 반환합니다.",
)
def conduct_market_research(input_data: ResearchInput) -> Dict[str, Any]:
    """
    Tavily 검색을 사용하여 시장 정보를 수집하고, 가공하여 반환하는 전문가 도구.
    """
    print(
        f"--- [MarketResearchExpert] 주제 '{input_data.topic}'에 대한 조사를 시작합니다. ---"
    )
    try:
        # 웹 검색 실행
        tool_output = tavily_tool.invoke(input_data.topic)

        # ======================= 수집된 데이터 전처리 =======================
        # 1. 딕셔너리(tool_output)에서 필요한 정보만 추출하여 가공한다
        processed_content = []
        for res in tool_output.get("results", []):
            processed_content.append(
                f"출처: {res.get('url')}\n내용: {res.get('content')}"
            )

        # 2. 읽기 쉽게 가공된 텍스트를 하나의 문자열로 병합한다
        summary_text = "\n\n---\n\n".join(processed_content)
        # =============================================================

        # 3. 깨끗하게 가공된 '문자열'을 research_summary에 저장
        # 정해진 프로토콜에 따라 결과 반환
        return {
            "result": {
                "research_summary": f"시장 조사 및 트렌드 요약:\n\n{summary_text}"
            }
        }
    except Exception as e:
        error_message = f"시장 조사 중 오류 발생: {e}"
        print(f"[ERROR] {error_message}")
        return {"error": error_message}


### 4. 서버 실행
if __name__ == "__main__":
    logger.info("MCP [MarketResearchExpert] 서버 시작 (host=%s, port=%d)", MCP_HOST, MCP_PORT)
    mcp_server.run(transport="streamable-http", host=MCP_HOST, port=MCP_PORT)
