from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from agent.graph import build_agent_graph, should_continue


def _make_mock_llm(with_tool_calls: bool = False):
    tool_call = {"id": "c1", "name": "analyze_commercial_district", "args": {}}
    msg = AIMessage(
        content="" if with_tool_calls else "완료",
        tool_calls=[tool_call] if with_tool_calls else [],
    )
    llm = MagicMock()
    llm.invoke.return_value = msg
    return llm


def test_build_agent_graph_returns_compiled_graph():
    """그래프가 정상적으로 컴파일되어 invoke 메서드를 가짐."""
    graph = build_agent_graph(llm=_make_mock_llm(), tools=[])
    assert hasattr(graph, "invoke") or hasattr(graph, "ainvoke")


def test_should_continue_with_tool_calls_returns_tools():
    from agent.nodes import AgentState

    tool_call = {"id": "c1", "name": "some_tool", "args": {}}
    state = AgentState(messages=[AIMessage(content="", tool_calls=[tool_call])])
    assert should_continue(state) == "tools"


def test_should_continue_without_tool_calls_returns_end():
    from agent.nodes import AgentState

    state = AgentState(messages=[AIMessage(content="최종 답변")])
    assert should_continue(state) == "__end__"


def test_build_agent_graph_has_llm_and_tools_nodes():
    """그래프 내부에 llm, tools 노드가 존재하는지 확인."""
    graph = build_agent_graph(llm=_make_mock_llm(), tools=[])
    node_names = set(graph.get_graph().nodes.keys())
    assert "llm" in node_names
    assert "tools" in node_names
