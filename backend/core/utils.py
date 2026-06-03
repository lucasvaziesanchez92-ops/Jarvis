"""Common utility functions for the backend."""
from datetime import datetime
from typing import Any, TypeVar

from pydantic import BaseModel


# ── Pagination ────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    """Standard paginated response wrapper."""
    items: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


def paginate(
    items: list,
    total: int,
    page: int,
    page_size: int,
) -> PaginatedResponse:
    """Create a paginated response from a list of items."""
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


# ── DateTime Parsing ─────────────────────────────────────────

def parse_datetime_safely(value: str | datetime | None) -> datetime | None:
    """
    Safely parse datetime strings with fallback.

    Supports:
    - ISO 8601 strings (2024-12-31T10:00:00)
    - ISO with timezone (2024-12-31T10:00:00+00:00)
    - Common formats (2024-12-31 10:00:00)
    - Already datetime objects (passthrough)
    - None (passthrough)
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None

        # Try common formats
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue

        # Fallback: try fromisoformat (Python 3.7+)
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass

    raise ValueError(f"Unable to parse datetime: {value}")


# ── Soft Delete ───────────────────────────────────────────────

class SoftDeleteMixin:
    """Mixin for models that support soft deletion."""
    # Note: This is a documentation mixin. Actual implementation in SQLAlchemy models.
    # Add to your SQLAlchemy model:
    #
    # deleted_at = Column(DateTime, nullable=True, default=None, index=True)
    #
    # Then filter queries with: .filter(deleted_at.is_(None))
    pass


# ── Generic Types ─────────────────────────────────────────────

T = TypeVar("T")
