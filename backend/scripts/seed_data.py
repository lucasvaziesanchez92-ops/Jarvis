"""Seed data script — populate the database with sample data for development."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime, timedelta
from backend.storage.sqlite_store import get_store, NoteModel, TodoModel, ThreadModel, MessageModel


def seed_data():
    """Populate database with sample notes, todos, and threads."""
    store = get_store()
    session = store.get_session()

    try:
        # ── Sample Notes ──────────────────────────────────────
        notes = [
            NoteModel(
                id="note_001",
                title="Meeting Notes - Project Alpha",
                content="Discussed timeline and deliverables for Q2. Key points:\n- Design review next week\n- Backend API freeze by end of month\n- Mobile beta testing starts in 2 weeks",
                tags='["meeting", "project-alpha", "planning"]',
            ),
            NoteModel(
                id="note_002",
                title="Book Recommendations",
                content="Books to read this year:\n1. Atomic Habits - James Clear\n2. Deep Work - Cal Newport\n3. The Pragmatic Programmer",
                tags='["books", "personal"]',
            ),
            NoteModel(
                id="note_003",
                title="Grocery List",
                content="Milk\nEggs\nBread\nAvocados\nChicken breast\nRice\nVegetables (broccoli, carrots, spinach)",
                tags='["shopping", "weekly"]',
            ),
        ]

        # ── Sample Todos ──────────────────────────────────────
        now = datetime.now()
        todos = [
            TodoModel(
                id="todo_001",
                text="Complete project proposal",
                completed=False,
                priority="high",
                due_date=now + timedelta(days=2),
            ),
            TodoModel(
                id="todo_002",
                text="Review pull requests",
                completed=False,
                priority="medium",
                due_date=now + timedelta(days=1),
            ),
            TodoModel(
                id="todo_003",
                text="Buy groceries",
                completed=False,
                priority="low",
                due_date=now + timedelta(days=3),
            ),
            TodoModel(
                id="todo_004",
                text="Schedule dentist appointment",
                completed=True,
                priority="medium",
                due_date=now - timedelta(days=5),
            ),
            TodoModel(
                id="todo_005",
                text="Update resume",
                completed=False,
                priority="low",
                due_date=now + timedelta(weeks=2),
            ),
        ]

        # ── Sample Thread with Messages ───────────────────────
        thread = ThreadModel(
            id="thread_001",
            title="Morning Planning Session",
            status="active",
            meta='{"user_id": "demo_user", "session_type": "planning"}',
        )

        messages = [
            MessageModel(
                id="msg_001",
                thread_id="thread_001",
                role="user",
                content="What's on my agenda today?",
            ),
            MessageModel(
                id="msg_002",
                thread_id="thread_001",
                role="assistant",
                content="Here's your schedule for today:\n\n9:00 AM - Team standup\n11:00 AM - Design review\n2:00 PM - Client call\n4:00 PM - Code review\n\nYou also have 3 pending todos. Want me to prioritize them?",
            ),
            MessageModel(
                id="msg_003",
                thread_id="thread_001",
                role="user",
                content="Yes, please prioritize my todos",
            ),
            MessageModel(
                id="msg_004",
                thread_id="thread_001",
                role="assistant",
                content="Here are your todos by priority:\n\n🔴 High: Complete project proposal (due in 2 days)\n🟡 Medium: Review pull requests (due tomorrow)\n🟢 Low: Buy groceries, Update resume\n\nWant me to create calendar blocks for the high priority ones?",
            ),
        ]

        # Add everything to the database
        session.add_all(notes)
        session.add_all(todos)
        session.add(thread)
        session.add_all(messages)
        session.commit()

        print("✅ Seed data created successfully!")
        print(f"  - {len(notes)} notes")
        print(f"  - {len(todos)} todos")
        print(f"  - 1 thread with {len(messages)} messages")

    except Exception as e:
        session.rollback()
        print(f"❌ Error seeding data: {e}")
        raise
    finally:
        session.close()
        store.close()


if __name__ == "__main__":
    seed_data()
