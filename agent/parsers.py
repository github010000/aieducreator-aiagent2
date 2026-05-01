import json
from typing import Any


def parse_mcp_response(raw: Any) -> dict:
    """MCP tool.ainvoke() 반환값을 dict로 정규화."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        return json.loads(raw)
    if isinstance(raw, list):
        if not raw:
            return {}
        first = raw[0]
        text = (
            first.get("text", "")
            if isinstance(first, dict)
            else getattr(first, "text", "")
        )
        return json.loads(text) if text else {}
    return {}
