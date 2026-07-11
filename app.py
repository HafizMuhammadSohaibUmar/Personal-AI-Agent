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
    :root { --bg:#0b1020; --panel:#111a33; --panel2:#0f1730; --text:#e7ecff; --muted:#aab3d5; --accent:#6ea8fe; --danger:#ff6b6b; }
    * { box-sizing: border-box; }
    body { margin:0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; background: radial-gradient(1200px 800px at 20% 0%, #1a2455 0%, var(--bg) 50%, #070a14 100%); color:var(--text); }
    .wrap { max-width: 980px; margin: 0 auto; padding: 24px; }
    .header { display:flex; justify-content:space-between; align-items:center; gap:16px; margin-bottom: 16px; }
    .title { font-size: 18px; font-weight: 650; }
    .sub { color: var(--muted); font-size: 12px; }
    .card { background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03)); border: 1px solid rgba(255,255,255,0.10); border-radius: 14px; overflow: hidden; }
    .chat { height: 64vh; min-height: 420px; overflow:auto; padding: 16px; background: rgba(0,0,0,0.18); }
    .row { display:flex; margin: 10px 0; }
    .row.user { justify-content:flex-end; }
    .bubble { max-width: 78%; padding: 10px 12px; border-radius: 12px; line-height: 1.35; white-space: pre-wrap; word-break: break-word; }
    .user .bubble { background: rgba(110,168,254,0.20); border: 1px solid rgba(110,168,254,0.35); }
    .bot .bubble { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.10); }
    .meta { margin-top: 4px; font-size: 11px; color: var(--muted); }
    .controls { display:flex; gap: 10px; padding: 12px; border-top: 1px solid rgba(255,255,255,0.10); background: rgba(0,0,0,0.10); }
    textarea { flex: 1; resize:none; padding: 10px 12px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.14); background: rgba(0,0,0,0.20); color: var(--text); outline: none; min-height: 44px; max-height: 160px; }
    button { padding: 10px 14px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.16); background: rgba(255,255,255,0.08); color: var(--text); cursor:pointer; }
    button.primary { background: rgba(110,168,254,0.25); border-color: rgba(110,168,254,0.45); }
    button:disabled { opacity: 0.55; cursor: not-allowed; }
    .pill { font-size: 12px; padding: 6px 10px; border-radius: 999px; border: 1px solid rgba(255,255,255,0.14); background: rgba(0,0,0,0.20); color: var(--muted); }
    a { color: var(--accent); text-decoration: none; }
  </style>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"header\">
      <div>
        <div class=\"title\">Personal AI Agent</div>
        <div class=\"sub\">Task planning, calendar scheduling, and daily prioritization with local SQLite memory.</div>
      </div>
      <div class=\"pill\">API: <a href=\"/docs\" target=\"_blank\">/docs</a> | LangServe: <a href=\"/chat/playground/\" target=\"_blank\">/chat/playground</a></div>
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
