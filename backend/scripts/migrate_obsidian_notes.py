"""
Migrate notes from Obsidian vault to JARVIS DB.
Run: OBSIDIAN_VAULT_PATH="C:\\path\\to\\vault" python backend/scripts/migrate_obsidian_notes.py
"""
import os
import re
import json
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4

from backend.storage.sqlite_store import get_store, NoteModel


def extract_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter from markdown content."""
    match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    if not match:
        return {}, content
    frontmatter = {}
    for line in match.group(1).split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            frontmatter[key.strip()] = value.strip().strip('"').strip("'")
    body = content[len(match.group(0)):]
    return frontmatter, body


def extract_title_and_tags(content: str, filename: str) -> tuple[str, list[str], str]:
    """Extract title from first # heading or filename, extract tags from content."""
    tags = []

    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else Path(filename).stem.replace('-', ' ').replace('_', ' ').title()

    tag_matches = re.findall(r'(?<!`)#([a-zA-Z][a-zA-Z0-9_-]+)', content)
    tags = list(set(tag_matches))[:10]

    return title, tags, content


def migrate_notes(vault_path: str = None) -> dict:
    """
    Migrate all .md files from Obsidian vault to JARVIS DB.
    Returns stats: {found: int, migrated: int, skipped: int}
    """
    if not vault_path:
        vault_path = os.getenv("OBSIDIAN_VAULT_PATH", "")

    if not vault_path or not os.path.exists(vault_path):
        return {"error": f"Vault path not found: {vault_path}"}

    store = get_store()
    session = store.get_session()

    stats = {"found": 0, "migrated": 0, "skipped": 0, "errors": []}

    try:
        md_files = list(Path(vault_path).rglob("*.md"))
        stats["found"] = len(md_files)
    except Exception as e:
        return {"error": f"Error scanning vault: {e}"}

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding='utf-8')
            if content.startswith('---'):
                fm, body = extract_frontmatter(content)
            else:
                fm, body = {}, content

            title, tags, _ = extract_title_and_tags(body, md_file.name)

            existing = session.query(NoteModel).filter(
                NoteModel.title == title
            ).first()

            if existing:
                stats["skipped"] += 1
                continue

            note_id = fm.get('id', str(uuid4()))
            note_model = NoteModel(
                id=note_id,
                title=title,
                content=body.strip(),
                tags=json.dumps(tags),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(note_model)
            stats["migrated"] += 1

        except Exception as e:
            stats["errors"].append(f"{md_file.name}: {str(e)}")

    session.commit()
    session.close()

    return stats


if __name__ == "__main__":
    vault = os.getenv("OBSIDIAN_VAULT_PATH")
    if not vault:
        print("ERROR: Set OBSIDIAN_VAULT_PATH environment variable")
        print("Example: OBSIDIAN_VAULT_PATH='C:\\Users\\First\\Documents\\Obsidian\\Vault' python migrate_obsidian_notes.py")
        exit(1)

    print(f"[*] Migrating notes from: {vault}")
    result = migrate_notes(vault)
    if "error" in result:
        print(f"[X] {result['error']}")
    else:
        print(f"[*] Found: {result.get('found', 0)}")
        print(f"[*] Migrated: {result.get('migrated', 0)}")
        print(f"[*] Skipped (existing): {result.get('skipped', 0)}")
        if result.get('errors'):
            print(f"[!] Errors: {result['errors'][:5]}")