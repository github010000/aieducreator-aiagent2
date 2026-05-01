import asyncio
import os
import uuid

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agent.config import SERVER_REGISTRY
from agent.graph import build_agent_graph

_root = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_root, ".env"))

_CHECKPOINT_DB = os.path.join(_root, "analyze_commercial_district_checkpoint.sqlite")


async def _setup_agent(memory: AsyncSqliteSaver):
    """MCP 클라이언트 연결 및 LangGraph 에이전트 초기화."""
    client = MultiServerMCPClient(SERVER_REGISTRY)

    print("\n--- MCP 서버로부터 도구 로드 중... ---")
    tools = await client.get_tools()
    if not tools:
        raise RuntimeError("서버로부터 도구를 가져오지 못했습니다.")

    tool_names = [t.name for t in tools]
    print(f"--- 로드된 도구: {tool_names} ---\n")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind_tools(tools)
    return build_agent_graph(llm=llm, tools=tools, checkpointer=memory)


async def _run_console_loop(agent) -> None:
    """콘솔 입력을 받아 에이전트를 실행하는 대화 루프."""
    print("==================================================")
    print("      서울시 상권 분석 전문 AI 에이전트 (콘솔 모드)      ")
    print("==================================================")
    print("질문해주세요. (종료: 'exit' 또는 '종료')\n")

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    while True:
        try:
            user_input = input("사용자: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "종료"):
                print("AI 에이전트: 종료합니다.")
                break

            print("AI 에이전트: (분석 중...)")
            final_state = await agent.ainvoke(
                {"messages": [HumanMessage(content=user_input)]}, config=config
            )
            answer = final_state["messages"][-1].content
            print("\n" + "=" * 25 + " 최종 결과 " + "=" * 25)
            print(answer)
            print("=" * 62 + "\n")

        except KeyboardInterrupt:
            print("\nAI 에이전트: 종료합니다.")
            break
        except Exception as exc:
            print(f"[오류] {exc}")


async def main() -> None:
    async with AsyncSqliteSaver.from_conn_string(_CHECKPOINT_DB) as memory:
        agent = await _setup_agent(memory)
        await _run_console_loop(agent)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n프로그램이 중단되었습니다.")
