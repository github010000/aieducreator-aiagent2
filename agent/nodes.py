from typing import Annotated, Any

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel

from agent.parsers import parse_mcp_response


class AgentState(BaseModel):
    messages: Annotated[list[BaseMessage], add_messages]


def llm_node(state: AgentState, llm: Any) -> dict[str, Any]:
    """LLM을 호출하여 다음 행동(툴 호출 or 최종 답변)을 결정."""
    response = llm.invoke(state.messages)
    return {"messages": [response]}


async def tool_executor_node(
    state: AgentState, tools_by_name: dict[str, Any]
) -> dict[str, Any]:
    """LLM이 요청한 tool_calls를 실행하고 ToolMessage로 반환."""
    last_message = state.messages[-1]
    tool_messages: list[ToolMessage] = []

    for tool_call in last_message.tool_calls:
        tool = tools_by_name.get(tool_call["name"])
        if tool is None:
            content = f"[오류] '{tool_call['name']}' 툴을 찾을 수 없습니다."
        else:
            raw = await tool.ainvoke(tool_call["args"])
            data = parse_mcp_response(raw)
            content = _format_tool_result(data)

        tool_messages.append(ToolMessage(content=content, tool_call_id=tool_call["id"]))

    return {"messages": tool_messages}


def _format_tool_result(data: dict) -> str:
    """툴 반환 dict를 사람이 읽기 좋은 문자열로 변환."""
    if "error" in data:
        return f"[분석 오류] {data['error']}"
    result = data.get("result", {})
    report = result.get("report", "")
    sql = result.get("executed_sql", "")
    parts = []
    if report:
        parts.append(f"### 분석 보고서\n{report}")
    if sql:
        parts.append(f"### 실행된 SQL\n```sql\n{sql}\n```")
    return "\n\n".join(parts) if parts else str(data)
