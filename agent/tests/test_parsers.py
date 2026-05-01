import json

import pytest

from agent.parsers import parse_mcp_response


def test_parse_list_of_text_dict():
    """langchain_mcp_adapters 실제 반환 형식: [{"type": "text", "text": "<json>"}]"""
    raw = [
        {
            "type": "text",
            "text": json.dumps(
                {"result": {"report": "ok", "executed_sql": "SELECT 1"}}
            ),
        }
    ]
    result = parse_mcp_response(raw)
    assert result == {"result": {"report": "ok", "executed_sql": "SELECT 1"}}


def test_parse_raw_string():
    raw = json.dumps({"result": {"report": "test"}})
    result = parse_mcp_response(raw)
    assert result["result"]["report"] == "test"


def test_parse_dict_passthrough():
    raw = {"result": {"report": "direct"}}
    result = parse_mcp_response(raw)
    assert result["result"]["report"] == "direct"


def test_parse_empty_list_returns_empty_dict():
    result = parse_mcp_response([])
    assert result == {}


def test_parse_error_response():
    raw = [{"type": "text", "text": json.dumps({"error": "DB not found"})}]
    result = parse_mcp_response(raw)
    assert result == {"error": "DB not found"}


def test_parse_content_block_with_text_attribute():
    """text 속성을 가진 객체(dict가 아닌 경우) 처리"""

    class FakeBlock:
        text = json.dumps({"result": {"report": "attr"}})

    result = parse_mcp_response([FakeBlock()])
    assert result["result"]["report"] == "attr"
