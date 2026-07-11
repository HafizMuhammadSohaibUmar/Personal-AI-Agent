# Decisions

## 1. Local Personal Assistant Boundary

This project is focused on a single-user personal productivity assistant. It does not try to be a CRM, ERP, or team collaboration product. The core jobs are task capture, scheduling, free-slot search, daily planning, and time-blocking.

## 2. FastAPI + LangServe

FastAPI serves the browser UI and LangServe endpoint from one process. This keeps local deployment simple while still exposing a standard `/chat/invoke` interface for testing and future integrations.

## 3. LangGraph for Tool Routing

The assistant uses a small LangGraph workflow with an assistant node and a tool node. This keeps tool execution explicit: the model decides when a tool is needed, LangGraph routes to the tool node, and the assistant then summarizes the result.

## 4. SQLite Runtime Storage

SQLite is used for tasks, events, priority rules, and checkpoints because the assistant is local-first and single-user by default. It avoids an external database dependency while still persisting useful state across sessions.

## 5. Mistral Tool-Calling Model

The assistant uses Mistral through `langchain-mistralai` because the project needs tool calling, concise planning behavior, and a simple API-key deployment path. The model is isolated in `support_agent/personal_assistant/nodes.py` so it can be changed later without rewriting the tools.

## 6. Local Calendar Instead of External Calendar Sync

Calendar events are stored locally. Google Calendar, Outlook, and CalDAV integrations are intentionally not included yet because they introduce OAuth, sync conflicts, and deletion/update rules. The current project proves the agentic scheduling layer first.

## 7. No Authentication Yet

The deployed version should be treated as a controlled demo or private service. There is no login system. Adding authentication is the next production step before exposing personal task data broadly.

## 8. Runtime Files Are Not Versioned

`.env`, `assistant.sqlite`, and checkpoint SQLite files are ignored by Git. They contain local secrets or runtime state and should live only on the machine running the assistant.
