"""initial migration — create all tables with indexes and soft deletes

Revision ID: 001_initial
Revises:
Create Date: 2026-04-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Notes table
    op.create_table(
        "notes",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tags", sa.Text(), default="[]"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_notes_created_at", "notes", ["created_at"])
    op.create_index("ix_notes_deleted_at", "notes", ["deleted_at"])

    # Todos table
    op.create_table(
        "todos",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("completed", sa.Boolean(), default=False),
        sa.Column("priority", sa.String(), default="medium"),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_todos_created_at", "todos", ["created_at"])
    op.create_index("ix_todos_deleted_at", "todos", ["deleted_at"])
    op.create_index("ix_todos_completed", "todos", ["completed"])

    # Threads table
    op.create_table(
        "threads",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("status", sa.String(), default="active"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("meta", sa.Text(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_threads_created_at", "threads", ["created_at"])
    op.create_index("ix_threads_deleted_at", "threads", ["deleted_at"])

    # Messages table
    op.create_table(
        "messages",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("thread_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(), default="user"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("meta", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_messages_thread_id", "messages", ["thread_id"])
    op.create_index("ix_messages_created_at", "messages", ["created_at"])


def downgrade() -> None:
    op.drop_table("messages")
    op.drop_table("threads")
    op.drop_table("todos")
    op.drop_table("notes")
