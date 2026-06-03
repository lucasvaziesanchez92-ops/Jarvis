"""
Storage factory - switches between SQLite and NeonDB PostgreSQL.
Set STORAGE_TYPE=neon and DATABASE_URL environment variable to use NeonDB.

Usage:
    # .env for SQLite (default)
    STORAGE_TYPE=sqlite
    DATA_DIR=data

    # .env for NeonDB
    STORAGE_TYPE=neon
    DATABASE_URL=postgresql://user:pass@host/db?sslmode=require
"""
from backend.config import settings

_sqlite_store = None
_neon_store = None


def get_store():
    """Get the appropriate storage instance based on STORAGE_TYPE setting."""
    global _sqlite_store, _neon_store

    storage_type = getattr(settings, 'storage_type', 'sqlite') or 'sqlite'

    if storage_type == 'neon':
        from backend.storage.neon_store import PostgresStore
        if _neon_store is None:
            database_url = getattr(settings, 'database_url', None)
            if not database_url:
                raise ValueError(
                    "STORAGE_TYPE=neon requires DATABASE_URL environment variable. "
                    "Example: postgresql://user:pass@host/db?sslmode=require"
                )
            _neon_store = PostgresStore(database_url)
        return _neon_store
    else:
        from backend.storage.sqlite_store import SqliteStore
        if _sqlite_store is None:
            _sqlite_store = SqliteStore()
        return _sqlite_store


def reset_storage():
    global _sqlite_store, _neon_store
    if _sqlite_store:
        _sqlite_store.close()
        _sqlite_store = None
    if _neon_store:
        _neon_store.close()
        _neon_store = None


__all__ = [
    'get_store',
    'reset_storage',
]