from functools import partial
from typing import Any

from langgraph.graph import END, StateGraph

from agent.nodes import AgentState, llm_node, tool_executor_node


def should_continue(state: AgentState) -> str:
    """마지막 메시지에 tool_calls가 있으면 tools 노드로, 없으면 종료."""
    last = state.messages[-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END


def build_agent_graph(llm: Any, tools: list[Any], checkpointer: Any = None) -> Any:
    """ReAct 패턴 그래프 빌드: llm → (tool_calls?) → tools → llm → ..."""
    tools_by_name = {t.name: t for t in tools}

    builder = StateGraph(AgentState)
    builder.add_node("llm", partial(llm_node, llm=llm))
    builder.add_node("tools", partial(tool_executor_node, tools_by_name=tools_by_name))

    builder.set_entry_point("llm")
    builder.add_conditional_edges("llm", should_continue, {"tools": "tools", END: END})
    builder.add_edge("tools", "llm")

    return builder.compile(checkpointer=checkpointer)
