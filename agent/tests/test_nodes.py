import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.nodes import AgentState, llm_node, tool_executor_node


@pytest.fixture
def human_state():
    return AgentState(messages=[HumanMessage(content="강남구 카페 매출 상위 5곳")])


@pytest.fixture
def mock_llm_with_tool_call():
    tool_call = {
        "id": "call_1",
        "name": "analyze_commercial_district",
        "args": {"input_data": {"query": "강남구 카페"}},
    }
    ai_msg = AIMessage(content="", tool_calls=[tool_call])
    llm = MagicMock()
    llm.invoke.return_value = ai_msg
    return llm


@pytest.fixture
def mock_llm_final_answer():
    ai_msg = AIMessage(content="분석 완료: 강남역 1위")
    llm = MagicMock()
    llm.invoke.return_value = ai_msg
    return llm


@pytest.fixture
def mock_tool():
    tool = AsyncMock()
    tool.name = "analyze_commercial_district"
    tool.ainvoke.return_value = [
        {
            "type": "text",
            "text": json.dumps(
                {"result": {"report": "강남역 1위", "executed_sql": "SELECT 1"}}
            ),
        }
    ]
    return tool


def test_llm_node_returns_ai_message(human_state, mock_llm_with_tool_call):
    result = llm_node(human_state, llm=mock_llm_with_tool_call)
    assert "messages" in result
    assert isinstance(result["messages"][-1], AIMessage)


def test_llm_node_passes_all_messages_to_llm(human_state, mock_llm_with_tool_call):
    llm_node(human_state, llm=mock_llm_with_tool_call)
    mock_llm_with_tool_call.invoke.assert_called_once_with(human_state.messages)


async def test_tool_executor_node_returns_tool_message(mock_tool):
    tool_call = {
        "id": "call_1",
        "name": "analyze_commercial_district",
        "args": {"input_data": {"query": "강남구"}},
    }
    ai_msg = AIMessage(content="", tool_calls=[tool_call])
    state = AgentState(messages=[HumanMessage(content="강남구"), ai_msg])

    result = await tool_executor_node(
        state, tools_by_name={"analyze_commercial_district": mock_tool}
    )
    assert "messages" in result
    assert any(isinstance(m, ToolMessage) for m in result["messages"])


async def test_tool_executor_node_formats_report_in_tool_message(mock_tool):
    tool_call = {
        "id": "call_2",
        "name": "analyze_commercial_district",
        "args": {"input_data": {"query": "강남구"}},
    }
    ai_msg = AIMessage(content="", tool_calls=[tool_call])
    state = AgentState(messages=[HumanMessage(content="강남구"), ai_msg])

    result = await tool_executor_node(
        state, tools_by_name={"analyze_commercial_district": mock_tool}
    )
    tool_msg = next(m for m in result["messages"] if isinstance(m, ToolMessage))
    assert "강남역 1위" in tool_msg.content


async def test_tool_executor_node_handles_error_response():
    error_tool = AsyncMock()
    error_tool.name = "analyze_commercial_district"
    error_tool.ainvoke.return_value = [
        {"type": "text", "text": json.dumps({"error": "DB 파일 없음"})}
    ]
    tool_call = {
        "id": "call_3",
        "name": "analyze_commercial_district",
        "args": {"input_data": {"query": "테스트"}},
    }
    ai_msg = AIMessage(content="", tool_calls=[tool_call])
    state = AgentState(messages=[HumanMessage(content="테스트"), ai_msg])

    result = await tool_executor_node(
        state, tools_by_name={"analyze_commercial_district": error_tool}
    )
    tool_msg = next(m for m in result["messages"] if isinstance(m, ToolMessage))
    assert "DB 파일 없음" in tool_msg.content
