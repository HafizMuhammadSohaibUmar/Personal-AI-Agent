# Personal AI Agent

A self-hosted personal productivity agent built with FastAPI, LangServe, LangGraph, Mistral, and SQLite.

The agent manages personal productivity through a browser chat interface. It can create tasks, list tasks, complete tasks, create calendar events, find free time slots, auto-schedule work, generate a daily plan, and time-block priority tasks. Runtime data is stored in SQLite on the server running the app.

## Live Demo

- Live demo: `https://personal-ai-agent.sohaib.systems/`
- API docs: `https://personal-ai-agent.sohaib.systems/docs`
- LangServe playground: `https://personal-ai-agent.sohaib.systems/chat/playground/`
- Repository: `https://github.com/HafizMuhammadSohaibUmar/Personal-AI-Agent`

How to evaluate the demo:

1. Ask it to create a task with a due date and priority.
2. Ask it to list open tasks.
3. Ask it to find free slots for a duration.
4. Ask it to make a daily plan.
5. Ask it to time-block top tasks.
6. Confirm the answers reflect real SQLite task and event state rather than only generic text.

## Related AI Systems

| System | Purpose | Live Demo | Repository |
| --- | --- | --- | --- |
| LeadPilot AI Voice Agent | Inbound phone agent for call qualification, emergency detection, and lead logging. | [Live Demo](https://leadpilotai.sohaib.systems/) | [Repository](https://github.com/HafizMuhammadSohaibUmar/LeadPilotAI) |
| Missed Call Text-Back AI Agent | SMS recovery and qualification after no-answer or busy calls. | [Live Demo](https://missed-call-text-back-ai-agent.sohaib.systems/demo) | [Repository](https://github.com/HafizMuhammadSohaibUmar/Missed-Call-Text-Back-AI-Agent) |
| Outbound Follow-Up AI Agent | Estimate, no-show, re-engagement, and seasonal follow-up campaigns. | [Live Demo](https://outbound-followup-ai-agent.sohaib.systems/demo) | [Repository](https://github.com/HafizMuhammadSohaibUmar/Outbound-Follow-Up-AI-Agent) |
| AI Auto Review Request Agent | Sentiment-aware post-job review and private feedback routing. | [Live Demo](https://ai-review-agent.sohaib.systems/demo) | [Repository](https://github.com/HafizMuhammadSohaibUmar/AI-Auto-Review-Request-Agent) |
| Web Chat Lead Qualifier Agent | Embeddable RAG chat widget for contractor websites. | [Live Demo](https://web-chat-lead-qualifier-agent.sohaib.systems/demo) | [Repository](https://github.com/HafizMuhammadSohaibUmar/Web-Chat-Lead-Qualifier-Agent) |
| Personal AI Agent | Self-hosted task, planning, and local-calendar assistant with LangGraph tools. | [Live Demo](https://personal-ai-agent.sohaib.systems/) | **This repo** |
| Invoxia AI for ERPNext | Frappe/ERPNext assistant layer for navigation, voice input foundations, and live ERP answers. | [Live Demo](https://invoxia.sohaib.systems/) | [Repository](https://github.com/HafizMuhammadSohaibUmar/InvoxiaAI-ERPNext) |

## What It Does

- Runs a FastAPI web app with a built-in browser chat UI.
- Exposes LangServe endpoints at `/chat`.
- Uses a LangGraph tool-calling workflow for assistant actions.
- Stores tasks, events, and priority rules in SQLite.
- Stores conversation checkpoints in SQLite so each browser session can continue where it left off.
- Uses Mistral through `langchain-mistralai`.

## Architecture

```text
Browser Chat UI
  -> FastAPI /
  -> LangServe /chat/invoke
  -> LangGraph assistant node
  -> Mistral tool-calling model
  -> SQLite tools for tasks, events, and priority rules
  -> LangGraph SQLite checkpoint memory
```

## Engineering Points

- Tool-calling agents can operate over real local state rather than only generating text.
- LangGraph keeps the workflow explicit: assistant turn, tool route, tool execution, assistant response.
- A small single-user assistant can be self-hosted with FastAPI, LangServe, Mistral, and SQLite-backed state.
- The assistant can turn natural language into practical actions: task creation, daily planning, free-slot search, and time-blocking.

## Core Features

- **Task management:** create, list, and complete tasks.
- **Calendar management:** create events and avoid overlapping time blocks.
- **Free-slot search:** find available times between 09:00 and 21:00 local time.
- **Auto scheduling:** schedule events into the best available slot using priority rules.
- **Daily planning:** rank open tasks by priority, due date, tags, and stored user preferences.
- **Time blocking:** place top tasks onto the local calendar automatically.
- **Persistent sessions:** browser `localStorage` keeps the thread ID and chat history.
- **LangServe playground:** available at `/chat/playground/`.

## Project Structure

```text
.
app.py
support_agent/
  personal_assistant/
    db.py
    graph.py
    nodes.py
    state.py
    tools.py
pyproject.toml
poetry.lock
.env.example
DECISIONS.md
README.md
```

## How It Works

1. The browser UI sends the chat history to `/chat/invoke`.
2. `app.py` converts the chat history into LangChain messages.
3. The LangGraph workflow runs the assistant node.
4. If the model requests a tool, LangGraph routes to the tool node.
5. The tool reads or writes local SQLite data.
6. The graph returns the final assistant message to the browser.

The active graph is defined in `support_agent/personal_assistant/graph.py`.

## API Surface

| Route | Purpose |
| --- | --- |
| `GET /` | Browser chat UI |
| `GET /docs` | FastAPI OpenAPI docs |
| `POST /chat/invoke` | LangServe chat invocation endpoint |
| `GET /chat/playground/` | LangServe playground |

## Tech Stack

- FastAPI
- LangServe
- LangGraph
- LangChain message and tool abstractions
- Mistral via `langchain-mistralai`
- SQLite for tasks, events, priority rules, and checkpoints
- Poetry

## Production Features

- Tool-calling workflow over real local state
- SQLite persistence for tasks and events
- SQLite checkpoint persistence for conversation state
- Browser UI with local thread persistence
- Explicit assistant and tool nodes in LangGraph
- Local scheduling logic with conflict avoidance
- Priority-rule based daily planning and time-blocking

## Verification

There is no full automated test suite yet. Current verification is done through:

- direct tool invocation for `daily_plan` and `timeblock_top_tasks`
- browser chat prompts
- LangServe playground calls
- SQLite state inspection when needed

Planned test coverage should include task creation, free-slot search, daily planning, time-blocking, and invalid tool-argument handling.

## Environment Variables

Create a `.env` file:

```env
MISTRALAI_API_KEY=your_mistral_api_key
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=personal-ai-agent
PUBLIC_ORIGIN=https://personal-ai-agent.example.com
PORT=8006
```

`MISTRALAI_API_KEY` is required. LangSmith variables are optional.

## Run Locally

```bash
pip install poetry
poetry install
poetry run python app.py
```

Open:

```text
http://localhost:8006
```

Useful endpoints:

- `GET /` - custom chat UI
- `GET /docs` - FastAPI docs
- `GET /chat/playground/` - LangServe playground
- `POST /chat/invoke` - chat invocation endpoint

## Example Prompts

```text
Create a high priority task to prepare my client proposal tomorrow.
List my open tasks.
Schedule a 45 minute workout tomorrow evening.
Find free slots for 30 minutes on 2026-07-12.
Make my daily plan for tomorrow.
Time-block my top 3 tasks tomorrow.
Mark task 2 complete.
```

## Runtime Data

Runtime data is stored beside the running app:

- `assistant.sqlite` stores tasks, events, and priority rules.
- `checkpoints_pa.sqlite` stores LangGraph checkpoints.

These files are ignored by Git because they contain runtime state.

## Limitations

- This is a single-user assistant by default.
- Tasks and events are stored in SQLite on the running host.
- There is no login system yet.
- Calendar events are local only; Google Calendar or Outlook sync is not implemented.
- The assistant depends on the configured Mistral API key.

## Deployment

Run the app with the configured `PORT`:

```bash
poetry install
poetry run python app.py
```

For a server deployment, run it behind a process manager such as systemd and expose the service through a reverse proxy.
