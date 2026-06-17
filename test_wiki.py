import os
import asyncio
from loguru import logger
import json

from langchain_core.messages import HumanMessage, AIMessage
from backend.agent.knowledge_extractor import extract_knowledge
from backend.api.routers.wiki import get_graph

def test_extraction():
    os.environ["OBSIDIAN_VAULT_PATH"] = "backend/data/test_brain"
    
    # Clean previous test
    import shutil
    if os.path.exists("backend/data/test_brain"):
        shutil.rmtree("backend/data/test_brain")

    print("Running Knowledge Extractor...")
    
    # Mock state
    class MockMessage:
        def __init__(self, type, content):
            self.type = type
            self.content = content
            
    messages = [
        MockMessage("human", "Hola JARVIS, registra esta reunión: El Proyecto Nexus ahora usará la tecnología de ReactJS. Valeria Ramos será la líder y Carlos Mendoza la ayudará. Todo esto está avalado por la UANL."),
        MockMessage("ai", "Entendido. La reunión y la asignación de Valeria Ramos y Carlos Mendoza al Proyecto Nexus usando ReactJS y avalado por la UANL han sido registradas en tu Segundo Cerebro.")
    ]
    
    state = {
        "messages": messages,
        "tools_executed": []
    }
    
    extract_knowledge(state)
    
    print("\n--- Files Generated ---")
    for root, _, files in os.walk("backend/data/test_brain"):
        for file in files:
            filepath = os.path.join(root, file)
            print(f"\n{filepath}:")
            with open(filepath, 'r', encoding='utf-8') as f:
                print(f.read())
                
    print("\n--- Graph Endpoint Test ---")
    graph_data = asyncio.run(get_graph())
    print(json.dumps(graph_data, indent=2))

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(".env.local")
    test_extraction()
