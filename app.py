from dotenv import load_dotenv

load_dotenv()
import logging
import os
from typing import Any, List, TypedDict

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableLambda
from langserve import add_routes

from support_agent.personal_assistant.graph import graph


logging.basicConfig(level=logging.INFO)


class ChatInputType(TypedDict):
    messages: List[AnyMessage]


def test_locally():
    for output in graph.stream(
        {"user_question": "What information do you have on me?"},
        config={"configurable": {"thread_id": 888}},
    ):
        for key, value in output.items():
            if "messages" in value:
                try:
                    last_msg = value["messages"][-1]
                    last_msg.pretty_print()
                except Exception as e:
                    print(last_msg)
    print(graph.get_state({"configurable": {"thread_id": 3}}))


def start() -> None:
    app = FastAPI(
        title="Personal AI Agent",
        version="1.0",
        description="A local LangGraph personal assistant for tasks, planning, and scheduling.",
    )

    origins = [
        "http://localhost",
        "http://localhost:3000",
    ]
    public_origin = os.getenv("PUBLIC_ORIGIN")
    if public_origin:
        origins.append(public_origin)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", response_class=HTMLResponse)
    def ui() -> str:
        return """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Personal AI Agent</title>
  <style>
    :root { --bg:#0A0908; --panel:#18160E; --panel2:#201D12; --text:#F5F0E4; --muted:#9A9080; --accent:#4FB39F; --gold:#C49A1A; --line:rgba(255,255,255,0.08); }
    * { box-sizing: border-box; }
    body { margin:0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; background: radial-gradient(circle at top left, rgba(47,143,126,0.16), transparent 34%), var(--bg); color:var(--text); }
    .wrap { max-width: 1120px; margin: 0 auto; padding: 28px; }
    .header { display:grid; grid-template-columns: minmax(0,1fr) auto; align-items:start; gap:20px; margin-bottom: 18px; padding: 28px; border:1px solid var(--line); border-radius:18px; background:rgba(17,16,9,0.82); }
    .badge { display:inline-flex; color:var(--accent); border:1px solid rgba(79,179,159,0.28); background:rgba(79,179,159,0.12); border-radius:999px; padding:6px 10px; font-size:12px; font-weight:800; margin-bottom:12px; }
    .title { font-size: clamp(34px, 5vw, 58px); line-height:1; font-weight: 800; letter-spacing:-0.03em; }
    .sub { color: var(--muted); font-size: 16px; line-height:1.7; max-width: 720px; margin-top:12px; }
    .card { background: linear-gradient(180deg, rgba(255,255,255,0.035), rgba(255,255,255,0.015)), var(--panel); border: 1px solid var(--line); border-radius: 18px; overflow: hidden; }
    .chat { height: 64vh; min-height: 420px; overflow:auto; padding: 16px; background: rgba(0,0,0,0.18); }
    .row { display:flex; margin: 10px 0; }
    .row.user { justify-content:flex-end; }
    .bubble { max-width: 78%; padding: 10px 12px; border-radius: 12px; line-height: 1.35; white-space: pre-wrap; word-break: break-word; }
    .user .bubble { background: rgba(79,179,159,0.14); border: 1px solid rgba(79,179,159,0.28); }
    .bot .bubble { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.10); }
    .meta { margin-top: 4px; font-size: 11px; color: var(--muted); }
    .controls { display:flex; gap: 10px; padding: 12px; border-top: 1px solid rgba(255,255,255,0.10); background: rgba(0,0,0,0.10); }
    textarea { flex: 1; resize:none; padding: 10px 12px; border-radius: 10px; border: 1px solid var(--line); background: #0f0e09; color: var(--text); outline: none; min-height: 44px; max-height: 160px; }
    button { padding: 10px 14px; border-radius: 10px; border: 1px solid var(--line); background: var(--panel2); color: var(--text); cursor:pointer; font-weight:700; }
    button.primary { background: var(--gold); border-color: var(--gold); color:var(--bg); }
    button:disabled { opacity: 0.55; cursor: not-allowed; }
    .pill { font-size: 12px; padding: 8px 12px; border-radius: 999px; border: 1px solid rgba(196,154,26,0.22); background: rgba(196,154,26,0.08); color: var(--muted); white-space:nowrap; }
    a { color: var(--accent); text-decoration: none; }
    .prompts { display:grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap:10px; margin-bottom:14px; }
    .prompt { text-align:left; min-height:64px; color:var(--muted); font-weight:600; }
    .prompt strong { display:block; color:var(--text); margin-bottom:4px; }
    @media(max-width:840px){ .header{grid-template-columns:1fr;} .prompts{grid-template-columns:1fr 1fr;} }
    @media(max-width:560px){ .wrap{padding:16px;} .prompts{grid-template-columns:1fr;} .controls{flex-wrap:wrap;} .controls textarea{flex-basis:100%;} }
  </style>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"header\">
      <div>
        <div class=\"badge\">Live personal agent</div>
        <div class=\"title\">Personal AI Agent</div>
        <div class=\"sub\">A self-hosted LangGraph assistant for task capture, daily planning, free-slot search, and local calendar time-blocking. The agent uses real SQLite tools instead of only generating text.</div>
      </div>
      <div class=\"pill\">API: <a href=\"/docs\" target=\"_blank\">/docs</a> | LangServe: <a href=\"/chat/playground/\" target=\"_blank\">/chat/playground</a></div>
    </div>

    <div class=\"prompts\">
      <button class=\"prompt\" type=\"button\" data-prompt=\"Create a high priority task to prepare my client proposal tomorrow.\"><strong>Create task</strong>High-priority task with due date</button>
      <button class=\"prompt\" type=\"button\" data-prompt=\"Find free slots for 45 minutes tomorrow.\"><strong>Find slots</strong>Search the local calendar</button>
      <button class=\"prompt\" type=\"button\" data-prompt=\"Make my daily plan for tomorrow.\"><strong>Daily plan</strong>Rank open tasks</button>
      <button class=\"prompt\" type=\"button\" data-prompt=\"Time-block my top 3 tasks tomorrow.\"><strong>Time-block</strong>Create scheduled events</button>
    </div>

    <div class=\"card\">
      <div id=\"chat\" class=\"chat\"></div>
      <div class=\"controls\">
        <textarea id=\"msg\" placeholder=\"Type a message...\"></textarea>
        <button id=\"send\" class=\"primary\">Send</button>
        <button id=\"reset\">Reset</button>
      </div>
    </div>
  </div>

  <script>
    const chatEl = document.getElementById('chat');
    const msgEl = document.getElementById('msg');
    const sendBtn = document.getElementById('send');
    const resetBtn = document.getElementById('reset');

    function getThreadId() {
      let id = localStorage.getItem('thread_id');
      if (!id) {
        id = (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()));
        localStorage.setItem('thread_id', id);
      }
      return id;
    }

    function loadHistory() {
      try { return JSON.parse(localStorage.getItem('chat_history') || '[]'); }
      catch { return []; }
    }

    function saveHistory(history) {
      localStorage.setItem('chat_history', JSON.stringify(history));
    }

    function render(history) {
      chatEl.innerHTML = '';
      for (const m of history) {
        const row = document.createElement('div');
        row.className = 'row ' + (m.type === 'human' ? 'user' : 'bot');
        const bubble = document.createElement('div');
        bubble.className = 'bubble';
        bubble.textContent = m.content;
        row.appendChild(bubble);
        chatEl.appendChild(row);
      }
      chatEl.scrollTop = chatEl.scrollHeight;
    }

    async function send() {
      const text = msgEl.value.trim();
      if (!text) return;
      msgEl.value = '';

      const history = loadHistory();
      history.push({ type: 'human', content: text });
      saveHistory(history);
      render(history);

      sendBtn.disabled = true;
      try {
        const threadId = getThreadId();
        const body = {
          input: { messages: history },
          config: { configurable: { thread_id: threadId } },
        };
        const resp = await fetch('/chat/invoke', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        if (!resp.ok) {
          const t = await resp.text();
          throw new Error('HTTP ' + resp.status + ': ' + t);
        }
        const data = await resp.json();
        const ai = data?.output || { type: 'ai', content: '' };
        history.push({ type: 'ai', content: ai.content || '' });
        saveHistory(history);
        render(history);
      } catch (e) {
        const history2 = loadHistory();
        history2.push({ type: 'ai', content: '[Error] ' + (e?.message || String(e)) });
        saveHistory(history2);
        render(history2);
      } finally {
        sendBtn.disabled = false;
      }
    }

    sendBtn.addEventListener('click', send);
    msgEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
    });
    resetBtn.addEventListener('click', () => {
      localStorage.removeItem('chat_history');
      localStorage.removeItem('thread_id');
      render([]);
    });
    document.querySelectorAll('[data-prompt]').forEach((button) => {
      button.addEventListener('click', () => {
        msgEl.value = button.dataset.prompt;
        msgEl.focus();
      });
    });

    render(loadHistory());
  </script>
</body>
</html>"""

    def _coerce_message(m: Any) -> AnyMessage:
        if isinstance(m, (HumanMessage, AIMessage, SystemMessage)):
            return m
        if isinstance(m, dict):
            m_type = m.get("type")
            content = m.get("content", "")
            if m_type == "human":
                return HumanMessage(content=content)
            if m_type == "ai":
                return AIMessage(content=content)
            if m_type == "system":
                return SystemMessage(content=content)
            return HumanMessage(content=content)
        return HumanMessage(content=str(m))

    def _to_graph_state(chat_input: ChatInputType) -> dict:
        messages = [_coerce_message(m) for m in chat_input["messages"]]
        last_human = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
        return {
            "user_id": "local",
            "user_question": last_human.content if last_human else "",
            "messages": messages,
        }

    def _to_chat_output(graph_output: dict):
        messages = graph_output.get("messages", [])
        return messages[-1] if messages else AIMessage(content="")

    runnable = (
        RunnableLambda(_to_graph_state)
        | graph
        | RunnableLambda(_to_chat_output)
    )
    runnable = runnable.with_types(input_type=ChatInputType, output_type=AIMessage)

    add_routes(app, runnable, path="/chat", playground_type="chat")
    port = int(os.getenv("PORT", "8006"))
    print(f"Starting server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    start()
    # test_locally()
