from pathlib import Path

from langgraph.checkpoint.aiosqlite import AsyncSqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt.tool_node import ToolNode

from support_agent.personal_assistant.nodes import assistant_node
from support_agent.personal_assistant.state import PersonalAssistantState
from support_agent.personal_assistant.tools import personal_assistant_tools


def route_tools(state: PersonalAssistantState) -> str:
    messages = state.get("messages", [])
    if not messages:
        return END
    ai_message = messages[-1]
    tool_calls = getattr(ai_message, "tool_calls", None) or []
    if tool_calls:
        return "tools"
    return END


workflow = StateGraph(PersonalAssistantState)
workflow.add_node("assistant", assistant_node)
workflow.add_node("tools", ToolNode(personal_assistant_tools))

workflow.set_entry_point("assistant")
workflow.add_conditional_edges("assistant", route_tools, {"tools": "tools", END: END})
workflow.add_edge("tools", "assistant")

checkpoints_path = Path(__file__).resolve().parent.parent.parent / "checkpoints_pa.sqlite"
memory = AsyncSqliteSaver.from_conn_string(str(checkpoints_path))

graph = workflow.compile(checkpointer=memory)
