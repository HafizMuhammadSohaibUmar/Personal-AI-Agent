import os
import logging
from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_mistralai import ChatMistralAI

from support_agent.personal_assistant.state import PersonalAssistantState
from support_agent.personal_assistant.tools import personal_assistant_tools


logger = logging.getLogger(__name__)


if not os.getenv("MISTRALAI_API_KEY"):
    raise RuntimeError(
        "MISTRALAI_API_KEY is not set (or is empty). Add it to your .env or environment before running."
    )

if not os.getenv("MISTRAL_API_KEY"):
    os.environ["MISTRAL_API_KEY"] = os.environ["MISTRALAI_API_KEY"]


model_with_tools = ChatMistralAI(model="mistral-large-latest").bind_tools(
    personal_assistant_tools
)

primary_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an AI-powered personal assistant. You manage tasks and a local calendar stored in SQLite. "
            "You can automatically schedule within working hours 09:00-21:00 local time. "
            "You MUST base decisions on the user's stored priority rules (use get_priority_rules). "
            "When the user asks for a daily plan, call daily_plan. "
            "When the user asks to time-block their day or 'schedule my tasks', call timeblock_top_tasks. "
            "When the user asks to schedule something without an exact time, prefer using auto_schedule_event. "
            "Use tools to create/list/complete tasks and create/find/schedule events. "
            "If required information is missing (e.g., day or duration), ask a concise follow-up question. "
            "Current time: {time}.",
        ),
        ("placeholder", "{messages}"),
    ]
).partial(time=datetime.now())


def assistant_node(state: PersonalAssistantState) -> Dict[str, Any]:
    chain = primary_prompt | model_with_tools

    messages = state.get("messages", [])
    cleaned_messages = []
    for m in messages:
        if isinstance(m, ToolMessage):
            tool_call_id = getattr(m, "tool_call_id", None)
            if not tool_call_id:
                continue
            # Work around strict provider tool-message ordering issues by:
            # 1) removing tool call metadata from the preceding AI message
            # 2) converting the tool output into a normal HumanMessage
            if cleaned_messages and isinstance(cleaned_messages[-1], AIMessage):
                prev: AIMessage = cleaned_messages[-1]
                prev_content = (prev.content or "").strip()
                if not prev_content:
                    prev_content = "(tool invocation)"
                ak = dict(prev.additional_kwargs or {})
                ak.pop("tool_calls", None)
                cleaned_messages[-1] = AIMessage(
                    content=prev_content,
                    additional_kwargs=ak,
                    tool_calls=[],
                )
            cleaned_messages.append(
                HumanMessage(content=f"Tool result (tool_call_id={tool_call_id}): {m.content}")
            )
            continue
        elif isinstance(m, AIMessage):
            # Strip any tool metadata from prior AI messages before sending to Mistral.
            safe_content = (m.content or "").strip()
            if not safe_content:
                safe_content = "(assistant)"
            cleaned_messages.append(
                AIMessage(content=safe_content, tool_calls=[], additional_kwargs={})
            )
            continue
        elif isinstance(m, dict):
            msg_type = m.get("type") or m.get("role")
            if msg_type == "tool":
                if not m.get("tool_call_id"):
                    continue
            if msg_type in {"ai", "assistant"}:
                tcs = m.get("tool_calls") or []
                for tc in tcs:
                    if isinstance(tc, dict) and not tc.get("id"):
                        tc["id"] = f"call_{uuid4().hex}"
                ak = m.get("additional_kwargs") or {}
                raw_tcs = ak.get("tool_calls") or []
                for tc in raw_tcs:
                    if isinstance(tc, dict) and not tc.get("id"):
                        tc["id"] = f"call_{uuid4().hex}"
        else:
            msg_type = getattr(m, "type", None)
            if msg_type == "tool":
                tool_call_id = getattr(m, "tool_call_id", None)
                if not tool_call_id:
                    continue
            if msg_type in {"ai", "assistant"}:
                tcs = getattr(m, "tool_calls", None) or []
                for tc in tcs:
                    if isinstance(tc, dict) and not tc.get("id"):
                        tc["id"] = f"call_{uuid4().hex}"
                    else:
                        tc_id = getattr(tc, "id", None)
                        if not tc_id:
                            try:
                                setattr(tc, "id", f"call_{uuid4().hex}")
                            except Exception:
                                pass
        cleaned_messages.append(m)
    cleaned_state = {**state, "messages": cleaned_messages}

    try:
        preview = []
        for m in cleaned_messages:
            if isinstance(m, ToolMessage):
                preview.append(
                    {
                        "cls": type(m).__name__,
                        "type": "tool",
                        "tool_call_id": getattr(m, "tool_call_id", None),
                        "ak_tool_call_id": (m.additional_kwargs or {}).get("tool_call_id"),
                        "ak_keys": list((m.additional_kwargs or {}).keys()),
                    }
                )
            elif isinstance(m, dict):
                t = m.get("type") or m.get("role")
                if t == "tool":
                    preview.append(
                        {
                            "cls": "dict",
                            "type": "tool",
                            "tool_call_id": m.get("tool_call_id"),
                            "keys": list(m.keys()),
                        }
                    )
                else:
                    preview.append({"cls": "dict", "type": t})
            else:
                t = getattr(m, "type", None)
                if t == "tool":
                    preview.append(
                        {
                            "cls": type(m).__name__,
                            "type": "tool",
                            "tool_call_id": getattr(m, "tool_call_id", None),
                            "ak_tool_call_id": (getattr(m, "additional_kwargs", None) or {}).get(
                                "tool_call_id"
                            ),
                            "ak_keys": list((getattr(m, "additional_kwargs", None) or {}).keys()),
                        }
                    )
                else:
                    preview.append({"cls": type(m).__name__, "type": t})
        logger.info("assistant_node: cleaned_messages_preview=%s", preview)
    except Exception:
        pass

    res = chain.invoke(input=cleaned_state)

    logger.info(
        "assistant_node: model=%s content_len=%s tool_calls=%s additional_tool_calls=%s",
        type(res).__name__,
        len(getattr(res, "content", "") or ""),
        getattr(res, "tool_calls", None),
        (getattr(res, "additional_kwargs", None) or {}).get("tool_calls"),
    )

    # Normalize tool call ids for both LangChain-native (res.tool_calls) and
    # provider-native (res.additional_kwargs['tool_calls']) representations.
    tool_calls = getattr(res, "tool_calls", None) or []
    for tc in tool_calls:
        if isinstance(tc, dict) and not tc.get("id"):
            tc["id"] = f"call_{uuid4().hex}"
        elif not isinstance(tc, dict):
            if not getattr(tc, "id", None):
                try:
                    setattr(tc, "id", f"call_{uuid4().hex}")
                except Exception:
                    pass

    additional_kwargs = getattr(res, "additional_kwargs", None) or {}
    ak_tool_calls = additional_kwargs.get("tool_calls") or []
    if isinstance(ak_tool_calls, list):
        for tc in ak_tool_calls:
            if not isinstance(tc, dict):
                continue
            if not tc.get("id"):
                tc["id"] = f"call_{uuid4().hex}"
            # Some providers put name/args under tc['function']
            fn = tc.get("function")
            if isinstance(fn, dict):
                # keep shape, just ensure id exists at top-level
                pass
        additional_kwargs["tool_calls"] = ak_tool_calls
        res.additional_kwargs = additional_kwargs
    return {"messages": [res]}
