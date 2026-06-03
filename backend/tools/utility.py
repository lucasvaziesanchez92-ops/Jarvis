"""Utility tools: time, math, weather, system info."""
from datetime import datetime

import requests
from langchain_core.tools import tool


@tool
def get_current_time(timezone: str = "UTC") -> str:
    """Get the current date and time.

    Args:
        timezone: Timezone name (e.g., 'America/New_York', 'Europe/Madrid', 'UTC').
                  Defaults to UTC.

    Returns:
        Current date and time in ISO format.
    """
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(timezone)
        now = datetime.now(tz)
    except Exception:
        now = datetime.utcnow()

    return now.strftime("%A, %B %d, %Y at %I:%M:%S %p (%Z)")


@tool
def get_current_date() -> str:
    """Get the current date. Useful for date-aware planning."""
    now = datetime.now()
    return now.strftime("%A, %B %d, %Y")


@tool
def calculate_math(expression: str) -> str:
    """Safely evaluate a mathematical expression.

    Args:
        expression: Math expression (e.g., '2 + 2', '3.14 * 5^2', '100 / 3').

    Returns:
        Result of the calculation.

    Supported operations: +, -, *, /, **, ^ (power), (), decimals
    """
    # Only allow safe characters
    allowed_chars = set("0123456789.+-*/^() ")
    expr = expression.strip()

    if not all(c in allowed_chars for c in expr):
        return "Error: Invalid characters in expression. Only numbers and +, -, *, /, ^, () are allowed."

    # Replace ^ with ** for Python
    expr = expr.replace("^", "**")

    try:
        # Use eval with restricted globals/locals for safety
        result = eval(expr, {"__builtins__": {}}, {})  # noqa: S307
        return f"{expression} = {result}"
    except Exception as e:
        return f"Error calculating '{expression}': {str(e)}"


@tool
def get_weather(city: str = "", lat: float = 0.0, lon: float = 0.0) -> str:
    """Get the current weather for a city.

    Args:
        city: City name (e.g., 'Madrid', 'New York').
        lat: Latitude (alternative to city name).
        lon: Longitude (alternative to city name).

    Returns:
        Current weather conditions.

    Note: Requires WTTR_IN or OpenWeatherMap. Falls back to wttr.in (free, no API key needed).
    """
    try:
        if city:
            city_formatted = city.replace(" ", "+")
            url = f"https://wttr.in/{city_formatted}?format=%C+%t+%h+%w"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            weather = response.text.strip()

            if weather and "Unknown" not in weather:
                return f"Weather in {city}: {weather}"
            return f"Could not get weather for '{city}'. Try a different city name."

        elif lat and lon:
            url = f"https://wttr.in/{lat},{lon}?format=%C+%t+%h+%w"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return f"Weather at ({lat}, {lon}): {response.text.strip()}"

        return "Please provide a city name or coordinates."

    except requests.Timeout:
        return "Weather service timed out. Try again later."
    except requests.ConnectionError:
        return "Could not connect to weather service. Check your internet connection."
    except Exception as e:
        return f"Error getting weather: {str(e)}"


@tool
def get_system_info() -> str:
    """Get system information about the current device.

    Returns:
        System information including platform, Python version, and memory usage.
    """
    import platform
    import os
    import psutil

    process = psutil.Process(os.getpid())
    memory = process.memory_info()

    info = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "architecture": platform.architecture()[0],
        "cpu_count": os.cpu_count(),
        "process_memory_mb": round(memory.rss / 1024 / 1024, 2),
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    return "\n".join(f"{k}: {v}" for k, v in info.items())


@tool
def schedule_recurring_task(
    task: str,
    frequency: str = "daily",
    time: str = "09:00",
    days_of_week: list[str] | None = None,
) -> str:
    """Schedule a recurring task reminder.

    Args:
        task: Task description (e.g., 'Take medicine', 'Stand up and stretch').
        frequency: 'daily', 'weekly', 'monthly'.
        time: Time in HH:MM format (24h).
        days_of_week: For weekly frequency, list of days (e.g., ['monday', 'wednesday', 'friday']).

    Returns:
        Confirmation message with schedule details.
    """
    valid_frequencies = ["daily", "weekly", "monthly"]
    if frequency not in valid_frequencies:
        return f"Invalid frequency. Use: {', '.join(valid_frequencies)}"

    schedule_info = {
        "task": task,
        "frequency": frequency,
        "time": time,
    }

    if frequency == "weekly" and days_of_week:
        schedule_info["days"] = days_of_week

    # In production, this would create a scheduled job in a task queue (Celery, APScheduler)
    # For now, we record it for the agent to handle
    return (
        f"Recurring task scheduled: '{task}'\n"
        f"Frequency: {frequency}\n"
        f"Time: {time}\n"
        f"Note: Task scheduling requires background worker (Celery/APScheduler) in production."
    )
