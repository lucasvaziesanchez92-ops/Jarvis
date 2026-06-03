import asyncio
import os
from pathlib import Path
from backend.agent.graph import get_graph
from backend.tools.registry import ALL_TOOLS
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()

async def verify_obsidian_brain():
    print("🚀 INICIALIZANDO CEREBRO DE JARVIS (OBSIDIAN MODE)")
    graph = get_graph(tools=ALL_TOOLS)
    config = {"configurable": {"thread_id": "brain_session_001"}}
    
    # 1. Investigación Web y Aprendizaje
    print("\n[PASO 1] Investigando y Aprendiendo...")
    query = "Investiga qué es el patrón Circuit Breaker y guárdalo en mi wiki con wikilinks a Microservicios."
    inputs = {"messages": [HumanMessage(content=query)]}
    
    async for event in graph.astream(inputs, config=config, stream_mode="values"):
        message = event["messages"][-1]
        if hasattr(message, "content") and message.content:
            # Filtramos para no imprimir demasiada basura de herramientas si no es necesario
            if not hasattr(message, "tool_calls") or not message.tool_calls:
                 print(f"Jarvis: {message.content}")

    # 2. Verificación de Archivos (El rastro de Obsidian)
    print("\n[PASO 2] Verificando rastro en el sistema de archivos...")
    wiki_path = Path("data/wiki")
    index_file = wiki_path / "index.md"
    log_file = wiki_path / "log.md"
    
    if index_file.exists():
        print(f"✅ index.md actualizado:\n{index_file.read_text()[:200]}...")
    else:
        print("❌ index.md no encontrado.")
        
    if log_file.exists():
        print(f"✅ log.md actualizado:\n{log_file.read_text().splitlines()[-5:]}")
    else:
        print("❌ log.md no encontrado.")

    # 3. Consulta de Memoria Local (El Círculo se Cierra)
    print("\n[PASO 3] Consultando el nuevo conocimiento...")
    query = "¿Qué guardaste sobre los Circuit Breakers?"
    inputs = {"messages": [HumanMessage(content=query)]}
    
    async for event in graph.astream(inputs, config=config, stream_mode="values"):
        message = event["messages"][-1]
        if hasattr(message, "content") and message.content:
             print(f"Jarvis: {message.content}")

if __name__ == "__main__":
    asyncio.run(verify_obsidian_brain())
