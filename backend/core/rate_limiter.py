"""Rate limiting configuration using slowapi."""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],  # Default: 100 requests per minute per IP
    storage_uri="memory://",  # In production use Redis: "redis://localhost:6379"
)


# ── Rate Limit Presets ────────────────────────────────────────

# Chat endpoints — more restrictive (expensive LLM calls)
CHAT_LIMIT = "10/minute"
AGENT_RUN_LIMIT = "20/minute"

# CRUD endpoints — moderate
CRUD_LIMIT = "200/minute"

# Read endpoints — less restrictive
READ_LIMIT = "500/minute"

# WebSocket connections
WS_LIMIT = "5/minute"  # Max 5 new WS connections per minute per IP
