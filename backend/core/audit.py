"""Audit logging for compliance and debugging."""
import json
from datetime import datetime
from pathlib import Path
from threading import Lock

from backend.config import settings

AUDIT_LOG_DIR = Path(settings.data_dir) / "audit_logs"
AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)

AUDIT_LOG_FILE = AUDIT_LOG_DIR / "audit.jsonl"
_audit_lock = Lock()


class AuditAction:
    """Standardized audit action constants."""
    LOGIN = "login"
    LOGOUT = "logout"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    READ = "read"
    TOOL_EXECUTION = "tool_execution"
    AGENT_RUN = "agent_run"
    PERMISSION_CHANGE = "permission_change"
    SETTINGS_CHANGE = "settings_change"


def audit_log(
    action: str,
    resource: str,
    user_id: str | None = None,
    session_id: str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
    success: bool = True,
    error_message: str | None = None,
) -> None:
    """
    Write an audit log entry.

    Usage:
        audit_log(
            action=AuditAction.CREATE,
            resource="todo",
            user_id="user123",
            details={"text": "Buy milk"},
        )
    """
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "resource": resource,
        "user_id": user_id,
        "session_id": session_id,
        "details": details or {},
        "ip_address": ip_address,
        "success": success,
        "error_message": error_message,
    }

    with _audit_lock:
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str, ensure_ascii=False) + "\n")


def audit_resource_changes(resource: str, since: datetime | None = None) -> list[dict]:
    """Get all changes to a specific resource since a given time."""
    if not AUDIT_LOG_FILE.exists():
        return []

    changes = []
    with open(AUDIT_LOG_FILE, encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                if entry.get("resource") == resource and entry.get("success"):
                    if since is None:
                        changes.append(entry)
                    else:
                        ts = datetime.fromisoformat(entry["timestamp"])
                        if ts >= since:
                            changes.append(entry)
            except (json.JSONDecodeError, ValueError):
                continue

    return changes


def audit_user_activity(user_id: str, hours: int = 24) -> dict:
    """Get summary of user activity over the last N hours."""
    if not AUDIT_LOG_FILE.exists():
        return {"user_id": user_id, "actions": [], "total_actions": 0}

    cutoff = datetime.utcnow()
    from datetime import timedelta
    cutoff = cutoff - timedelta(hours=hours)

    actions: dict[str, int] = {}
    total = 0
    errors = 0

    with open(AUDIT_LOG_FILE, encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                if entry.get("user_id") == user_id:
                    ts = datetime.fromisoformat(entry["timestamp"])
                    if ts >= cutoff:
                        total += 1
                        action = entry.get("action", "unknown")
                        actions[action] = actions.get(action, 0) + 1
                        if not entry.get("success", True):
                            errors += 1
            except (json.JSONDecodeError, ValueError):
                continue

    return {
        "user_id": user_id,
        "period_hours": hours,
        "total_actions": total,
        "actions": actions,
        "errors": errors,
    }
