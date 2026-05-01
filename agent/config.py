import os

from dotenv import load_dotenv

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_root, ".env"))

SERVER_REGISTRY: dict[str, dict] = {
    "DataAnalysisExpert": {
        "url": os.getenv("DATA_ANALYSIS_MCP_URL", "http://localhost:9000/mcp"),
        "transport": "streamable_http",
    },
    "MarketResearchExpert": {
        "url": os.getenv("MARKET_RESEARCH_MCP_URL", "http://localhost:9001/mcp"),
        "transport": "streamable_http",
    },
    "ReportWritingExpert": {
        "url": os.getenv("REPORT_WRITING_MCP_URL", "http://localhost:9002/mcp"),
        "transport": "streamable_http",
    },
    "SeoulMetroExpert": {
        "url": os.getenv("SEOUL_METRO_MCP_URL", "http://localhost:9003/mcp"),
        "transport": "streamable_http",
    },
}
