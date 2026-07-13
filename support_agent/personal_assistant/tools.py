import json
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from support_agent.personal_assistant.db import (
    complete_task as _complete_task,
    create_event as _create_event,
    create_task as _create_task,
    get_priority_rules as _get_priority_rules,
    init_db,
    list_events_between as _list_events_between,
    list_tasks as _list_tasks,
    set_priority_rules as _set_priority_rules,
)

init_db()


def _parse_date(d: str) -> date:
    value = (d or "").strip().lower()
    today = datetime.now().astimezone().date()
    if value in {"today", "this day"}:
        return today
    if value in {"tomorrow", "next day"}:
        return today + timedelta(days=1)
    return date.fromisoformat(value)


def _to_iso(dt: datetime) -> str:
    return dt.astimezone().isoformat(timespec="seconds")


def _normalize_day(day: str) -> str:
    return _parse_date(day).isoformat()


def _parse_local_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return parsed


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


def _default_work_window(day: date) -> tuple[datetime, datetime]:
    tz = datetime.now().astimezone().tzinfo
    start = datetime.combine(day, time(9, 0), tzinfo=tz)
    end = datetime.combine(day, time(21, 0), tzinfo=tz)
    return start, end


def _score_slot(slot_start: datetime, tags: List[str], rules: Dict[str, Any]) -> int:
    score = 0
    tags_priority = rules.get("tags_priority", {}) or {}
    for t in tags:
        score += int(tags_priority.get(t, 0))

    prefer_morning_for = set(rules.get("prefer_morning_for", []) or [])
    prefer_evening_for = set(rules.get("prefer_evening_for", []) or [])

    if any(t in prefer_morning_for for t in tags):
        score += 2 if slot_start.hour < 12 else 0
    if any(t in prefer_evening_for for t in tags):
        score += 2 if slot_start.hour >= 17 else 0

    return score


def _priority_value(priority: Optional[str]) -> int:
    if priority == "high":
        return 3
    if priority == "medium":
        return 2
    if priority == "low":
        return 1
    return 0


def _score_task(task: Dict[str, Any], rules: Dict[str, Any]) -> int:
    tags = json.loads(task.get("tags") or "[]")
    tags_priority = rules.get("tags_priority", {}) or {}
    score = 0
    score += int(rules.get("priority_weight", 0)) * _priority_value(task.get("priority"))
    score += sum(int(tags_priority.get(t, 0)) for t in tags)
    due_at = task.get("due_at")
    if due_at:
        try:
            due_dt = datetime.fromisoformat(due_at)
            days = max((due_dt.date() - datetime.now().date()).days, 0)
            due_weight = int(rules.get("due_date_weight", 0))
            score += max(0, due_weight * (7 - min(days, 7)))
        except Exception:
            pass
    return score


@tool
def get_priority_rules(user_id: str = "local") -> Dict[str, Any]:
    """Fetch the user's priority rules from the local SQLite preferences store."""
    return _get_priority_rules(user_id)


@tool
def set_priority_rules(user_id: str, rules_json: str) -> str:
    """Set/replace the user's priority rules JSON in the local SQLite preferences store."""
    rules = json.loads(rules_json)
    _set_priority_rules(user_id, rules)
    return "ok"


@tool
def create_task(
    user_id: str,
    title: str,
    due_at: Optional[str] = None,
    estimated_minutes: Optional[int] = None,
    tags_json: Optional[str] = None,
    priority: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a task in the local SQLite task store."""
    tags = json.loads(tags_json) if tags_json else []
    task_id = _create_task(
        user_id=user_id,
        title=title,
        notes=notes,
        tags=tags,
        priority=priority,
        due_at=due_at,
        estimated_minutes=estimated_minutes,
    )
    return {"task_id": task_id}


@tool
def list_tasks(user_id: str, status: str = "open") -> List[Dict[str, Any]]:
    """List tasks from the local SQLite task store."""
    return _list_tasks(user_id=user_id, status=status)


@tool
def complete_task(user_id: str, task_id: int) -> str:
    """Mark a task as completed in the local SQLite task store."""
    _complete_task(task_id)
    return "ok"


@tool
def find_free_slots(
    user_id: str,
    day: str,
    duration_minutes: int,
    step_minutes: int = 15,
) -> List[Dict[str, str]]:
    """Find available time slots on a given day within 09:00-21:00 local time, avoiding existing events."""
    target_day = _parse_date(day)
    window_start, window_end = _default_work_window(target_day)

    busy = _list_events_between(user_id, _to_iso(window_start), _to_iso(window_end))
    busy_ranges: List[tuple[datetime, datetime]] = []
    for s, e in busy:
        busy_ranges.append((_parse_local_datetime(s), _parse_local_datetime(e)))

    slots: List[Dict[str, str]] = []
    cursor = window_start
    dur = timedelta(minutes=duration_minutes)
    step = timedelta(minutes=step_minutes)

    while cursor + dur <= window_end:
        candidate_end = cursor + dur
        if not any(_overlaps(cursor, candidate_end, bs, be) for bs, be in busy_ranges):
            slots.append({"starts_at": _to_iso(cursor), "ends_at": _to_iso(candidate_end)})
        cursor += step

    return slots


@tool
def create_event(
    user_id: str,
    title: str,
    starts_at: str,
    ends_at: str,
    tags_json: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a calendar event in the local SQLite events store."""
    tags = json.loads(tags_json) if tags_json else []
    event_id = _create_event(
        user_id=user_id,
        title=title,
        starts_at=starts_at,
        ends_at=ends_at,
        tags=tags,
        notes=notes,
        source="local",
    )
    return {"event_id": event_id}


@tool
def auto_schedule_event(
    user_id: str,
    title: str,
    day: str,
    duration_minutes: int,
    tags_json: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Auto-schedule an event into the best free slot (09:00-21:00) using the user's priority rules."""
    tags = json.loads(tags_json) if tags_json else []
    rules = _get_priority_rules(user_id)
    normalized_day = _normalize_day(day)

    slots = find_free_slots.invoke(
        {
            "user_id": user_id,
            "day": normalized_day,
            "duration_minutes": duration_minutes,
        }
    )
    if not slots:
        return {"error": "no_free_slots"}

    best = None
    best_score = None
    for s in slots:
        start_dt = datetime.fromisoformat(s["starts_at"])
        score = _score_slot(start_dt, tags, rules)
        if best is None or score > (best_score or -10**9):
            best = s
            best_score = score

    event_id = _create_event(
        user_id=user_id,
        title=title,
        starts_at=best["starts_at"],
        ends_at=best["ends_at"],
        tags=tags,
        notes=notes,
        source="local",
    )
    return {"event_id": event_id, "starts_at": best["starts_at"], "ends_at": best["ends_at"]}


@tool
def daily_plan(
    user_id: str,
    day: str,
    max_tasks: int = 5,
) -> Dict[str, Any]:
    """Generate a prioritized plan for the day based on open tasks and existing events.

    Returns tasks sorted by computed priority score and basic day summary.
    """
    normalized_day = _normalize_day(day)
    rules = _get_priority_rules(user_id)
    tasks = _list_tasks(user_id=user_id, status="open")
    scored = [(t, _score_task(t, rules)) for t in tasks]
    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[: max_tasks]
    return {
        "day": normalized_day,
        "tasks": [
            {
                "id": t.get("id"),
                "title": t.get("title"),
                "priority": t.get("priority"),
                "due_at": t.get("due_at"),
                "estimated_minutes": t.get("estimated_minutes"),
                "score": score,
            }
            for t, score in top
        ],
        "rules": rules,
    }


@tool
def timeblock_top_tasks(
    user_id: str,
    day: str,
    max_tasks: int = 3,
) -> Dict[str, Any]:
    """Automatically time-block top tasks into the calendar as local events.

    Creates events titled "Task: <title>" within 09:00-21:00 local time,
    avoiding conflicts with existing events.
    """
    normalized_day = _normalize_day(day)
    rules = _get_priority_rules(user_id)
    plan = daily_plan.invoke(
        {
            "user_id": user_id,
            "day": normalized_day,
            "max_tasks": max_tasks,
        }
    )
    created = []
    for t in plan.get("tasks", []):
        est = t.get("estimated_minutes")
        if not est:
            est = int(rules.get("default_estimated_minutes", 30))
        tags_json = json.dumps(["deep_work"])
        res = auto_schedule_event.invoke(
            {
                "user_id": user_id,
                "title": f"Task: {t.get('title')}",
                "day": normalized_day,
                "duration_minutes": int(est),
                "tags_json": tags_json,
                "notes": f"Auto-blocked from tasks table. task_id={t.get('id')}",
            }
        )
        if "error" not in res:
            created.append({"task_id": t.get("id"), **res})
    return {"day": normalized_day, "created": created}


personal_assistant_tools = [
    get_priority_rules,
    set_priority_rules,
    create_task,
    list_tasks,
    complete_task,
    find_free_slots,
    create_event,
    auto_schedule_event,
    daily_plan,
    timeblock_top_tasks,
]
