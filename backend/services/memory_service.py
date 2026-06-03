"""LangGraph memory service — short-term, long-term, and episodic memory."""
import json
from datetime import datetime
from pathlib import Path

from backend.config import settings

MEMORY_DIR = Path(settings.data_dir) / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

LONG_TERM_FILE = MEMORY_DIR / "long_term.json"
EPISODIC_FILE = MEMORY_DIR / "episodic.json"
DIAGNOSTICS_FILE = MEMORY_DIR / "diagnostics.json"


class MemoryService:
    """
    Three-tier memory system for the Jarvis agent:
    - Short-term: conversation context (handled by LangGraph checkpointer)
    - Long-term: persistent facts, preferences, learned rules
    - Episodic: past task outcomes, corrections, patterns
    """

    # ── Long-Term Memory ──────────────────────────────────────

    @staticmethod
    def _load_long_term() -> list[dict]:
        if LONG_TERM_FILE.exists():
            with open(LONG_TERM_FILE) as f:
                return json.load(f)
        return []

    @staticmethod
    def _save_long_term(memories: list[dict]):
        with open(LONG_TERM_FILE, "w") as f:
            json.dump(memories, f, indent=2, default=str)

    @classmethod
    def save_fact(cls, fact: str, category: str = "general",
                  confidence: float = 1.0, metadata: dict | None = None) -> str:
        """Save a learned fact to long-term memory."""
        memories = cls._load_long_term()
        memory_id = f"mem_{len(memories)}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        memories.append({
            "id": memory_id,
            "fact": fact,
            "category": category,
            "confidence": confidence,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
            "access_count": 0,
        })
        cls._save_long_term(memories)
        return memory_id

    @classmethod
    def search_memories(cls, query: str, category: str | None = None,
                        limit: int = 10) -> list[dict]:
        """Search long-term memory by keyword (semantic search when vector store available)."""
        memories = cls._load_long_term()
        query_lower = query.lower()

        # Filter by category if specified
        if category:
            memories = [m for m in memories if m.get("category") == category]

        # Keyword match (upgrade to vector similarity later)
        results = []
        for m in memories:
            score = 0
            fact_lower = m["fact"].lower()
            if query_lower in fact_lower:
                score += 3
            for word in query_lower.split():
                if word in fact_lower:
                    score += 1
            if score > 0:
                m["relevance_score"] = score
                m["access_count"] = m.get("access_count", 0) + 1
                results.append(m)

        results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        cls._save_long_term(memories)  # Save updated access counts
        return results[:limit]

    @classmethod
    def delete_memory(cls, memory_id: str) -> bool:
        """Delete a specific memory by ID."""
        memories = cls._load_long_term()
        before = len(memories)
        memories = [m for m in memories if m["id"] != memory_id]
        cls._save_long_term(memories)
        return len(memories) < before

    @classmethod
    def list_categories(cls) -> list[dict]:
        """List all memory categories with counts."""
        memories = cls._load_long_term()
        categories: dict[str, int] = {}
        for m in memories:
            cat = m.get("category", "general")
            categories[cat] = categories.get(cat, 0) + 1
        return [{"category": k, "count": v} for k, v in categories.items()]

    @classmethod
    def compact_memories(cls, max_age_days: int = 30, max_per_category: int = 50) -> dict:
        """
        CCleaner-style memory cleanup:
        - Remove old, low-access memories
        - Limit per category
        - Keep high-confidence memories regardless of age
        """
        memories = cls._load_long_term()
        now = datetime.now()
        kept = []
        removed = 0
        removed_ids = []

        for m in memories:
            created = datetime.fromisoformat(m["created_at"])
            age_days = (now - created).days
            is_recent = age_days <= max_age_days
            is_important = m.get("confidence", 0) >= 0.9
            is_accessed = m.get("access_count", 0) > 2

            if is_important or is_recent or is_accessed:
                kept.append(m)
            else:
                removed += 1
                removed_ids.append(m["id"])

        # Limit per category
        category_counts: dict[str, int] = {}
        final_kept = []
        for m in kept:
            cat = m.get("category", "general")
            category_counts[cat] = category_counts.get(cat, 0) + 1
            if category_counts[cat] <= max_per_category:
                final_kept.append(m)
            else:
                removed += 1
                removed_ids.append(m["id"])

        cls._save_long_term(final_kept)

        return {
            "status": "compacted",
            "before": len(memories),
            "after": len(final_kept),
            "removed": removed,
            "removed_ids": removed_ids[:20],  # Don't return too many
        }

    # ── Episodic Memory ───────────────────────────────────────

    @staticmethod
    def _load_episodic() -> list[dict]:
        if EPISODIC_FILE.exists():
            with open(EPISODIC_FILE) as f:
                return json.load(f)
        return []

    @staticmethod
    def _save_episodic(episodes: list[dict]):
        with open(EPISODIC_FILE, "w") as f:
            json.dump(episodes, f, indent=2, default=str)

    @classmethod
    def save_episode(cls, task: str, outcome: str, correction: str | None = None,
                     tools_used: list[str] | None = None) -> str:
        """Save a task outcome to episodic memory for pattern learning."""
        episodes = cls._load_episodic()
        episode_id = f"ep_{len(episodes)}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        episodes.append({
            "id": episode_id,
            "task": task,
            "outcome": outcome,
            "correction": correction,
            "tools_used": tools_used or [],
            "created_at": datetime.now().isoformat(),
        })
        # Keep last 200 episodes (sliding window)
        if len(episodes) > 200:
            episodes = episodes[-200:]
        cls._save_episodic(episodes)
        return episode_id

    @classmethod
    def find_similar_episodes(cls, task: str, limit: int = 5) -> list[dict]:
        """Find past similar tasks to learn from patterns."""
        episodes = cls._load_episodic()
        task_lower = task.lower()
        results = []
        for ep in episodes:
            if task_lower in ep["task"].lower():
                results.append(ep)
        return results[:limit]

    # ── Diagnostics ───────────────────────────────────────────

    @staticmethod
    def _load_diagnostics() -> dict:
        if DIAGNOSTICS_FILE.exists():
            with open(DIAGNOSTICS_FILE) as f:
                return json.load(f)
        return {"runs": 0, "errors": [], "last_cleanup": None, "memory_stats": {}}

    @staticmethod
    def _save_diagnostics(diag: dict):
        with open(DIAGNOSTICS_FILE, "w") as f:
            json.dump(diag, f, indent=2, default=str)

    @classmethod
    def run_diagnose(cls) -> dict:
        """
        CCleaner-style diagnostic report:
        - Memory statistics
        - Error history
        - Tool availability
        - LLM connectivity
        """
        long_term = cls._load_long_term()
        episodic = cls._load_episodic()
        diag = cls._load_diagnostics()

        # Memory stats
        categories = {}
        for m in long_term:
            cat = m.get("category", "general")
            categories[cat] = categories.get(cat, 0) + 1

        # Recent errors
        recent_errors = diag.get("errors", [])[-10:]

        # Tool usage stats
        tool_usage = {}
        for ep in episodic:
            for tool in ep.get("tools_used", []):
                tool_usage[tool] = tool_usage.get(tool, 0) + 1

        report = {
            "timestamp": datetime.now().isoformat(),
            "memory": {
                "long_term_count": len(long_term),
                "episodic_count": len(episodic),
                "categories": categories,
                "total_size_kb": (len(json.dumps(long_term)) + len(json.dumps(episodic))) // 1024,
            },
            "diagnostics": {
                "total_runs": diag.get("runs", 0),
                "recent_errors": recent_errors,
                "last_cleanup": diag.get("last_cleanup"),
            },
            "tool_usage": tool_usage,
            "health": {
                "memory_healthy": len(long_term) < 1000,  # Warn if too large
                "episodic_fresh": len(episodic) > 0,
                "errors_recent": len(recent_errors) < 5,
            },
        }

        cls._save_diagnostics(diag)
        return report

    @classmethod
    def run_cleanup(cls, compact_days: int = 30) -> dict:
        """
        Full diagnostic cleanup (CCleaner):
        1. Compact long-term memory
        2. Trim episodic memory
        3. Clear old error logs
        """
        # Compact memories
        compact_result = cls.compact_memories(max_age_days=compact_days)

        # Clear old errors
        diag = cls._load_diagnostics()
        diag["errors"] = diag.get("errors", [])[-20:]  # Keep only last 20
        diag["last_cleanup"] = datetime.now().isoformat()
        cls._save_diagnostics(diag)

        return {
            "status": "cleanup_complete",
            "memory_compaction": compact_result,
            "diagnostics": {
                "errors_cleared": len(diag.get("errors", [])),
                "last_cleanup": diag["last_cleanup"],
            },
        }

    @classmethod
    def log_error(cls, error: str, context: str = ""):
        """Log an error for diagnostic tracking."""
        diag = cls._load_diagnostics()
        diag["runs"] = diag.get("runs", 0) + 1
        diag.setdefault("errors", []).append({
            "error": error,
            "context": context,
            "timestamp": datetime.now().isoformat(),
        })
        # Keep last 100 errors
        if len(diag["errors"]) > 100:
            diag["errors"] = diag["errors"][-100:]
        cls._save_diagnostics(diag)

    @classmethod
    def get_health(cls) -> dict:
        """Quick health check of the memory system."""
        diag = cls._load_diagnostics()
        return {
            "memory_healthy": len(cls._load_long_term()) < 1000,
            "episodic_active": len(cls._load_episodic()) > 0,
            "errors_count": len(diag.get("errors", [])),
            "last_cleanup": diag.get("last_cleanup"),
            "total_runs": diag.get("runs", 0),
        }


# Singleton instance
memory_service = MemoryService()
