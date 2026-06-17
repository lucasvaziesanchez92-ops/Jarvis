"""Knowledge Extractor Node — Generates Obsidian notes automatically after interaction."""
import os
import re
from datetime import datetime
from loguru import logger
from langchain_core.messages import SystemMessage, HumanMessage

from backend.agent.state import JarvisState
from backend.llm import get_llm

def extract_knowledge(state: JarvisState) -> dict:
    """Analyze the conversation turn and save findings to the Wiki."""
    messages = state.get("messages", [])
    if not messages:
        return {}

    tools_executed = state.get("tools_executed", [])
    if not tools_executed:
        # If no action was taken, we might not need to record anything unless it's a significant conversation.
        # But per user request: "Cada conversacion, herramienta, tarea debe generar memoria conectada".
        pass

    # Build the transcript of the current turn (last User -> Assistant messages)
    transcript = ""
    for m in messages[-5:]:
        role = getattr(m, "type", "unknown")
        content = getattr(m, "content", str(m))
        if role == "human":
            transcript += f"\nUser: {content}"
        elif role == "ai":
            transcript += f"\nJARVIS: {content}"
        elif role == "tool":
            transcript += f"\n[Tool Result]: {content[:200]}..."

    import glob
    
    base_dir = os.getenv("OBSIDIAN_VAULT_PATH", os.path.join("backend", "data", "brain"))
    
    # Get existing files for awareness
    existing_files = []
    if os.path.exists(base_dir):
        for root, _, files in os.walk(base_dir):
            for f in files:
                if f.endswith(".md"):
                    rel_path = os.path.relpath(os.path.join(root, f), base_dir).replace("\\", "/")
                    existing_files.append(rel_path)

    prompt = f"""You are JARVIS' Cognitive Memory Subsystem (Wiki Ingest Engine).
Your job is to analyze the following interaction and extract operational memory into Obsidian Markdown files.
Today's date is {datetime.now().strftime("%Y-%m-%d")}.

Interaction Transcript:
{transcript}

Existing Wiki Files:
{', '.join(existing_files) if existing_files else 'None'}

Instructions:
1. PULL INFORMATION EXHAUSTIVELY: Extract all context, people, projects, decisions, technical details, and nuances. DO NOT SUMMARIZE TOO MUCH. The user prefers CLARITY and DETAIL over brevity. Include exact quotes or critical parameters if present.
2. SCHEMA: Every note MUST have a YAML frontmatter block at the top with `title`, `tags` (array), `summary` (1-2 sentences), and `provenance` (string).
3. CONNECTIONS: Use backlinks like [[Entity Name]] to connect related concepts.
4. MERGE vs CREATE: If the concept belongs to an existing file, specify action "merge" and provide ONLY the new information to append. If it's a new concept, specify action "create" and write a highly structured, readable, and fully detailed markdown document.
5. FORMAT: Return ONLY a JSON array.

JSON Format:
[
  {{
    "filepath": "projects/Proyecto Nexus.md",
    "action": "create",
    "content": "---\\ntitle: Proyecto Nexus\\ntags: [proyecto]\\nsummary: Iniciativa para conectar con UANL.\\nprovenance: chat\\n---\\n\\nEste proyecto es liderado por [[Valeria Ramos]]."
  }},
  {{
    "filepath": "people/Carlos Mendoza.md",
    "action": "merge",
    "content": "\\n- **{datetime.now().strftime("%Y-%m-%d")}**: Empezó a colaborar con [[Valeria Ramos]] en el [[Proyecto Nexus]]."
  }}
]
"""

    llm = get_llm()
    try:
        import asyncio
        from requests.exceptions import Timeout
        
        try:
            response = llm.invoke([HumanMessage(content=prompt)], config={"callbacks": []})
        except Exception as e:
            logger.error(f"LLM extraction timeout/error: {e}")
            return {}
            
        import json
        import re
        
        content = response.content
        logger.debug(f"LLM extraction output: {content}")
        
        notes = []
        json_match = re.search(r'\[\s*\{.*?\}\s*\]', content, re.DOTALL)
        if json_match:
            try:
                notes = json.loads(json_match.group(0), strict=False)
            except json.JSONDecodeError:
                cleaned = json_match.group(0).replace('\n', '\\n').replace('\r', '')
                try:
                    notes = json.loads(cleaned, strict=False)
                except:
                    logger.error("Failed to parse cleaned JSON array.")
        else:
            try:
                # Try to find just a single object
                obj_match = re.search(r'\{\s*".*?\s*\}', content, re.DOTALL)
                if obj_match:
                    notes = [json.loads(obj_match.group(0), strict=False)]
                else:
                    logger.error("No JSON found in extraction.")
            except:
                pass
                
        if not isinstance(notes, list):
            notes = [notes] if isinstance(notes, dict) else []
            
        from backend.storage import get_store
        from backend.storage.models import NoteModel
        import uuid
        
        store = get_store()
        session = store.get_session()
        
        try:
            for note in notes:
                if not isinstance(note, dict):
                    continue
                if "filepath" not in note or "content" not in note:
                    continue
                    
                # Use filepath as title, dropping the .md extension
                title = os.path.splitext(note["filepath"])[0]
                action = note.get("action", "create")
                final_content = note["content"].replace('\\n', '\n')
                
                existing = session.query(NoteModel).filter_by(title=title, deleted_at=None).first()
                
                if action == "merge" and existing:
                    existing.content += "\n" + final_content
                    logger.info(f"Merged memory into DB note: {title}")
                else:
                    if existing:
                        existing.content = final_content
                        logger.info(f"Overwrote memory in DB note: {title}")
                    else:
                        new_note = NoteModel(
                            id=str(uuid.uuid4()),
                            title=title,
                            content=final_content
                        )
                        session.add(new_note)
                        logger.info(f"Created memory in DB note: {title}")
            session.commit()
        except Exception as db_err:
            session.rollback()
            logger.error(f"DB error saving knowledge: {db_err}")
            raise
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Failed to extract knowledge: {e}")

    return {}

