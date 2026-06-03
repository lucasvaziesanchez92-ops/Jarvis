"""Script para reindexar todo el conocimiento en ChromaDB.

Usage:
    python -m backend.scripts.reindex_knowledge
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.service.vector_service import (
    reindex_all_notes,
    reindex_all_wiki,
    get_index_stats
)
from backend.services.notes_service import list_notes
from knowledge_engine import KnowledgeEngine


def reindex_everything():
    print("=" * 60)
    print("REINDEXING ALL KNOWLEDGE IN CHROMADB")
    print("=" * 60)

    print("\n[1/3] Getting all existing notes from SQLite...")
    notes = list_notes()
    print(f"    Found {len(notes)} notes in SQLite")

    if notes:
        print("\n[2/3] Indexing notes in ChromaDB...")
        result = reindex_all_notes(notes)
        print(f"    {result}")
    else:
        print("\n[2/3] No notes to index, skipping...")

    print("\n[3/3] Indexing wiki pages from Obsidian vault...")
    engine = KnowledgeEngine(base_path="data")
    wiki_files = list(engine.wiki_path.glob("*.md"))

    wiki_pages = []
    for wf in wiki_files:
        if wf.stem.lower() in ("index", "log", "unparsed_synthesis"):
            continue
        try:
            content = wf.read_text(encoding="utf-8")
            wiki_pages.append({
                "page_name": wf.stem,
                "content": content,
                "source_file": str(wf)
            })
        except Exception as e:
            print(f"    Warning: Could not read {wf.name}: {e}")

    print(f"    Found {len(wiki_pages)} wiki pages to index")

    if wiki_pages:
        result = reindex_all_wiki(wiki_pages)
        print(f"    {result}")

    print("\n" + "=" * 60)
    print("FINAL STATS:")
    print("=" * 60)
    stats = get_index_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print()


if __name__ == "__main__":
    reindex_everything()
