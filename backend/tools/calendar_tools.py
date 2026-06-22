"""LangChain tools for Google Calendar event management."""
from langchain_core.tools import tool


@tool
def create_calendar_event(
    start_datetime: str,
    end_datetime: str = "",
    title: str = "Nueva Cita",
    description: str = "",
    location: str = "",
    calendar_id: str = "primary",
) -> str:
    """Create a calendar event. Datetimes must be ISO format (e.g. 2024-12-31T10:00:00)."""
    from backend.services.calendar_service import create_event
    try:
        if not end_datetime:
            from datetime import datetime, timedelta
            try:
                base = start_datetime[:19]
                dt = datetime.fromisoformat(base)
                end_datetime = (dt + timedelta(hours=1)).isoformat() + (start_datetime[19:] if len(start_datetime) > 19 else "")
            except Exception:
                end_datetime = start_datetime
        event = create_event(title, start_datetime, end_datetime, description, location)
        return f"Event created successfully: {event.get('id')}"
    except Exception as e:
        return f"Error creating calendar event: {str(e)}"


@tool
def list_calendar_events(upcoming_only: bool = True, calendar_id: str = "primary") -> str:
    """List calendar events. By default only shows upcoming events."""
    from backend.services.calendar_service import list_events
    try:
        events = list_events(max_results=20)
        return str(events)
    except Exception as e:
        return f"Error listing calendar events: {str(e)}"


@tool
def update_calendar_event(
    event_id: str,
    title: str | None = None,
    start_datetime: str | None = None,
    end_datetime: str | None = None,
    description: str | None = None,
    location: str | None = None,
    calendar_id: str = "primary",
) -> str:
    """Update an existing calendar event's fields."""
    from backend.services.calendar_service import update_event
    try:
        event = update_event(event_id, title, start_datetime, end_datetime, description)
        return f"Event updated: {event.get('id')}" if event else "Event not found."
    except Exception as e:
        return f"Error updating calendar event: {str(e)}"


@tool
def delete_calendar_event(event_id: str, calendar_id: str = "primary") -> str:
    """Delete a calendar event by its ID."""
    from backend.services.calendar_service import delete_event
    try:
        delete_event(event_id)
        return f"Event {event_id} deleted successfully."
    except Exception as e:
        return f"Error deleting calendar event: {str(e)}"
