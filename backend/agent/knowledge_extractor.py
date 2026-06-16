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
1. PULL INFORMATION: Extract context, people, projects, decisions.
2. SCHEMA: Every note MUST have a YAML frontmatter block at the top with `title`, `tags` (array), `summary` (1-2 sentences), and `provenance` (string).
3. CONNECTIONS: Use backlinks like [[Entity Name]] to connect related concepts.
4. MERGE vs CREATE: If the concept belongs to an existing file, specify action "merge" and provide ONLY the new information to append. If it's a new concept, specify action "create" and provide the full file with Frontmatter.
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
        response = llm.invoke([HumanMessage(content=prompt)], config={"callbacks": []})
        import json
        import re
        
        content = response.content
        logger.debug(f"LLM extraction output: {content}")
        
        json_match = re.search(r'\[\s*\{.*?\}\s*\]', content, re.DOTALL)
        if json_match:
            try:
                notes = json.loads(json_match.group(0), strict=False)
            except json.JSONDecodeError:
                cleaned = json_match.group(0).replace('\n', '\\n').replace('\r', '')
                notes = json.loads(cleaned, strict=False)
        else:
            notes = json.loads(content.strip(), strict=False)
        
        for note in notes:
            filepath = os.path.join(base_dir, note["filepath"])
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            action = note.get("action", "create")
            final_content = note["content"].replace('\\n', '\n')
            
            if action == "merge" and os.path.exists(filepath):
                with open(filepath, "a", encoding="utf-8") as f:
                    f.write("\n" + final_content)
                logger.info(f"Merged memory into {filepath}")
            else:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(final_content)
                logger.info(f"Created memory at {filepath}")
            
    except Exception as e:
        logger.error(f"Failed to extract knowledge: {e}")

    return {}

