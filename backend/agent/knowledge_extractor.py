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

    prompt = f"""You are JARVIS' Cognitive Memory Subsystem.
Your job is to analyze the following interaction and extract operational memory into Obsidian Markdown files.
Today's date is {datetime.now().strftime("%Y-%m-%d")}.

Interaction Transcript:
{transcript}

Tools Executed: {', '.join(tools_executed) if tools_executed else 'None'}

Instructions:
1. Generate one or more Markdown notes if there is useful context, people, projects, tools, or decisions mentioned.
2. Use backlinks like [[Entity]].
3. Return your response ONLY as a JSON array of objects, with each object having "filepath" (e.g. "conversations/2026-06-16-Meeting.md" or "people/Juan.md") and "content" (the full markdown string).

Example:
[
  {{
    "filepath": "conversations/{datetime.now().strftime("%Y-%m-%d")}_Reagendar.md",
    "content": "# Reagendar Reunión\nEl usuario pidió usar [[Gmail]] para contactar a [[Juan]].\nResultado: Exito."
  }}
]
"""

    llm = get_llm(model_id="llama3-8b-8192") # Using a fast Groq model for extraction if possible
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        import json
        
        # Parse JSON from markdown block
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        notes = json.loads(content.strip())
        
        base_dir = "backend/data/brain"
        for note in notes:
            filepath = os.path.join(base_dir, note["filepath"])
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(note["content"])
            logger.info(f"Saved memory to {filepath}")
            
    except Exception as e:
        logger.error(f"Failed to extract knowledge: {e}")

    return {}
