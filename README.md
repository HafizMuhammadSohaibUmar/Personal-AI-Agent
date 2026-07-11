# Personal AI Agent

A local AI personal assistant built with FastAPI, LangServe, LangGraph, Mistral, and SQLite.

The agent helps manage personal productivity through a chat interface. It can create tasks, list tasks, complete tasks, create calendar events, find free time slots, auto-schedule work, generate a daily plan, and time-block priority tasks.

## What It Does

- Runs a FastAPI web app with a built-in browser chat UI.
- Exposes LangServe endpoints at `/chat`.
- Uses a LangGraph tool-calling workflow for assistant actions.
- Stores tasks, events, and priority rules in local SQLite.
- Stores conversation checkpoints in SQLite so each browser session can continue where it left off.
- Uses Mistral through `langchain-mistralai`.

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
├── app.py
├── support_agent/
│   └── personal_assistant/
│       ├── db.py
│       ├── graph.py
│       ├── nodes.py
│       ├── state.py
│       └── tools.py
├── pyproject.toml
├── poetry.lock
├── .env.example
└── README.md
```

## How It Works

1. The browser UI sends the chat history to `/chat/invoke`.
2. `app.py` converts the chat history into LangChain messages.
3. The LangGraph workflow runs the assistant node.
4. If the model requests a tool, LangGraph routes to the tool node.
5. The tool reads or writes local SQLite data.
6. The graph returns the final assistant message to the browser.

The active graph is defined in `support_agent/personal_assistant/graph.py`.

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

Install Poetry if needed:

```bash
pip install poetry
```

Install dependencies:

```bash
poetry install
```

Start the server:

```bash
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

## Local Data

Runtime data is intentionally local:

- `assistant.sqlite` stores tasks, events, and priority rules.
- `checkpoints_pa.sqlite` stores LangGraph checkpoints.

These files are ignored by Git because they contain local runtime state.

## Deployment Notes

This app is designed to run as a small self-hosted service. For production use, put it behind a reverse proxy such as Caddy or Nginx, set a real domain, and keep `.env` only on the server.

See the deployment steps below for a DigitalOcean droplet setup.

## Limitations

- This is a single-user local assistant by default.
- Tasks and events are stored locally in SQLite.
- There is no login system yet.
- Calendar events are local only; Google Calendar or Outlook sync is not implemented.
- The assistant depends on the configured Mistral API key.

## License

MIT
