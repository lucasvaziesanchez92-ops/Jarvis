"""Google Calendar service — list, create, update, delete events."""
from datetime import datetime, timezone
from typing import Optional

from backend.services.google_auth import GoogleAuthService, get_refresh_token

DEFAULT_USER = "default_user"


def _get_calendar_service(user_id: str = DEFAULT_USER):
    token = get_refresh_token(user_id)
    if not token:
        raise RuntimeError("Google no está conectado. Hacé login en Google primero.")
    creds = GoogleAuthService.get_credentials(token)
    return GoogleAuthService.build_calendar(creds)


def list_events(max_results: int = 20, time_min: Optional[str] = None, time_max: Optional[str] = None, query: str = "", user_id: str = DEFAULT_USER) -> list[dict]:
    """List upcoming calendar events."""
    service = _get_calendar_service(user_id)
    now = datetime.now(timezone.utc).isoformat()
    params = {
        "calendarId": "primary",
        "maxResults": max_results,
        "singleEvents": True,
        "orderBy": "startTime",
        "timeMin": time_min or now,
    }
    if time_max:
        params["timeMax"] = time_max
    if query:
        params["q"] = query
    events = service.events().list(**params).execute()
    results = []
    for event in events.get("items", []):
        start = event["start"].get("dateTime", event["start"].get("date"))
        end = event["end"].get("dateTime", event["end"].get("date"))
        results.append({
            "id": event["id"],
            "summary": event.get("summary", "(sin título)"),
            "description": event.get("description", ""),
            "start": start,
            "end": end,
            "location": event.get("location", ""),
            "attendees": [a.get("email", "") for a in event.get("attendees", [])],
        })
    return results


def create_event(summary: str, start_time: str, end_time: str, description: str = "", location: str = "", attendees: list[str] | None = None, user_id: str = DEFAULT_USER) -> dict:
    """Create a calendar event."""
    service = _get_calendar_service(user_id)
    event_body = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_time, "timeZone": _get_local_timezone()},
        "end": {"dateTime": end_time, "timeZone": _get_local_timezone()},
    }
    if location:
        event_body["location"] = location
    if attendees:
        event_body["attendees"] = [{"email": e} for e in attendees]
    created = service.events().insert(calendarId="primary", body=event_body, sendUpdates="all").execute()
    return {"id": created["id"], "summary": created.get("summary", ""), "status": "created"}


def update_event(event_id: str, summary: str | None = None, start_time: str | None = None, end_time: str | None = None, description: str | None = None, user_id: str = DEFAULT_USER) -> dict:
    """Update an existing calendar event."""
    service = _get_calendar_service(user_id)
    event = service.events().get(calendarId="primary", eventId=event_id).execute()
    if summary:
        event["summary"] = summary
    if description:
        event["description"] = description
    if start_time:
        event["start"]["dateTime"] = start_time
    if end_time:
        event["end"]["dateTime"] = end_time
    updated = service.events().update(calendarId="primary", eventId=event_id, body=event, sendUpdates="all").execute()
    return {"id": updated["id"], "summary": updated.get("summary", ""), "status": "updated"}


def delete_event(event_id: str, user_id: str = DEFAULT_USER) -> dict:
    """Delete a calendar event."""
    service = _get_calendar_service(user_id)
    service.events().delete(calendarId="primary", eventId=event_id, sendUpdates="all").execute()
    return {"id": event_id, "status": "deleted"}


def _get_local_timezone() -> str:
    import time
    is_dst = time.localtime().tm_isdst
    offset_seconds = -(time.timezone if not is_dst else time.altzone)
    hours = offset_seconds // 3600
    minutes = (abs(offset_seconds) % 3600) // 60
    sign = "+" if offset_seconds >= 0 else "-"
    return f"{sign}{abs(hours):02d}:{minutes:02d}"
