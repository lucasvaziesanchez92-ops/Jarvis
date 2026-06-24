"""Knowledge Extractor Node — Generates Obsidian notes automatically after interaction."""
import os
import re
from datetime import datetime
from loguru import logger
from langchain_core.messages import SystemMessage, HumanMessage

from backend.agent.state import JarvisState
from backend.llm import get_llm

def extract_knowledge(state: JarvisState) -> dict:
    """Analyze the conversation turn and save findings to the Wiki.
    
    DISABLED: This was creating duplicate junk notes after every single message,
    flooding the database with notes like '2026-06-24-Resumen', '2026-06-24-Archivos', etc.
    Re-enabled only for explicit memory saves via save_memory tool.
    """
    # Early return — knowledge extraction is disabled to prevent note spam.
    # The user can explicitly save memories via save_memory tool or create_note.
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

    prompt = f"""You are JARVIS' Cognitive Memory Subsystem (Hybrid Graph RAG Extractor).
Your job is to analyze the following interaction and extract operational memory into BOTH Markdown files AND structured Graph Nodes/Edges.
Today's date is {datetime.now().strftime("%Y-%m-%d")}.

Interaction Transcript:
{transcript}

Instructions:
1. PULL INFORMATION EXHAUSTIVELY: Extract all context, people, projects, decisions, and technical details.
2. NOTES (Markdown): Create rich markdown notes for deep context. Every note MUST have a YAML frontmatter.
3. GRAPH (Structured): Extract explicit Entities (nodes) and Relationships (edges) from the conversation. 
   - Node Types: Persona, Proyecto, Tarea, Tecnologia, Idea, Concepto.
   - Edges: ES_FUNDADOR_DE, TRABAJA_EN, USA, DEPENDE_DE, etc.
4. FORMAT: Return ONLY a valid JSON object matching the exact format below. Do NOT wrap in markdown code blocks.

JSON Format:
{{
  "notes": [
    {{
      "filepath": "projects/Project Quantum.md",
      "action": "create",
      "content": "---\\ntitle: Project Quantum\\ntags: [proyecto]\\nsummary: Plataforma IA.\\nprovenance: chat\\n---\\n\\nEste proyecto es liderado por [[Lucas]]."
    }}
  ],
  "graph": {{
    "nodes": [
      {{"id": "Project Quantum", "type": "Proyecto", "description": "Plataforma IA bursátil"}},
      {{"id": "Lucas", "type": "Persona", "description": "Usuario y fundador"}}
    ],
    "edges": [
      {{"source": "Lucas", "target": "Project Quantum", "relation": "ES_FUNDADOR_DE"}}
    ]
  }}
}}
"""

    llm = get_llm()
    try:
        try:
            response = llm.invoke([HumanMessage(content=prompt)], config={"callbacks": []})
        except Exception as e:
            logger.error(f"LLM extraction timeout/error: {e}")
            return {}
            
        import json
        import re
        
        content = response.content
        logger.debug(f"LLM extraction output: {content}")
        
        parsed_data = {"notes": [], "graph": {"nodes": [], "edges": []}}
        
        # Try to find the JSON object
        json_match = re.search(r'\{\s*"notes".*\}\s*\}', content, re.DOTALL)
        if not json_match:
            # Fallback for single quotes or slightly mangled roots
            json_match = re.search(r'\{\s*\'notes\'.*\}\s*\}', content, re.DOTALL)
            
        if json_match:
            raw_json = json_match.group(0)
            try:
                parsed_data = json.loads(raw_json, strict=False)
            except json.JSONDecodeError:
                import ast
                try:
                    # ast.literal_eval handles single quotes and python dict strings perfectly
                    parsed_data = ast.literal_eval(raw_json)
                except Exception:
                    cleaned = raw_json.replace('\n', '\\n').replace('\r', '')
                    try:
                        parsed_data = json.loads(cleaned, strict=False)
                    except Exception as e:
                        logger.error(f"Failed to parse cleaned JSON object: {e}")
        else:
            logger.error("No valid JSON found in extraction.")

        notes = parsed_data.get("notes", [])
        graph = parsed_data.get("graph", {"nodes": [], "edges": []})
        graph_nodes = graph.get("nodes", [])
        graph_edges = graph.get("edges", [])
            
        from backend.storage import get_store
        from backend.storage.models import NoteModel, GraphNodeModel, GraphEdgeModel
        import uuid
        
        store = get_store()
        session = store.get_session()
        
        try:
            # 1. Save Markdown Notes
            for note in notes:
                if not isinstance(note, dict) or "filepath" not in note or "content" not in note:
                    continue
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
                        new_note = NoteModel(id=str(uuid.uuid4()), title=title, content=final_content)
                        session.add(new_note)
                        logger.info(f"Created memory in DB note: {title}")

            # 2. Save Graph Nodes
            for node in graph_nodes:
                node_id = node.get("id")
                if not node_id: continue
                existing_node = session.query(GraphNodeModel).filter_by(id=node_id).first()
                if existing_node:
                    existing_node.description = node.get("description", existing_node.description)
                    existing_node.type = node.get("type", existing_node.type)
                else:
                    new_graph_node = GraphNodeModel(
                        id=node_id,
                        label=node_id,
                        type=node.get("type", "Concept"),
                        description=node.get("description", "")
                    )
                    session.add(new_graph_node)

            # 3. Save Graph Edges
            for edge in graph_edges:
                source = edge.get("source")
                target = edge.get("target")
                relation = edge.get("relation")
                if not source or not target or not relation: continue
                
                # Check if edge already exists to prevent duplicates
                existing_edge = session.query(GraphEdgeModel).filter_by(source_id=source, target_id=target, relation=relation).first()
                if not existing_edge:
                    new_edge = GraphEdgeModel(
                        id=str(uuid.uuid4()),
                        source_id=source,
                        target_id=target,
                        relation=relation
                    )
                    session.add(new_edge)

            session.commit()
        except Exception as db_err:
            session.rollback()
            logger.error(f"DB error saving hybrid knowledge: {db_err}")
            raise
        finally:
            session.close()
            
        # [MODIFICACION PARA AHORRAR RAM]:
        # Se ha deshabilitado el re-indexado automático (index_vault()) de vectores ChromaDB 
        # para evitar crashes de memoria (OOM) en Railway de 512MB. 
        # La tabla GraphNodes de PostgreSQL seguirá actualizándose y el RAG funcionará bien.
        # El usuario deberá pulsar "Reindex" en la Wiki manualmente si quiere vectorizar textos.
        logger.info("Hybrid extraction complete. Vector DB re-index skipped to save RAM.")
            
    except Exception as e:
        logger.error(f"Failed to extract knowledge: {e}")

    return {}

