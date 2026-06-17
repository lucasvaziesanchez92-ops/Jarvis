import os
import asyncio
from loguru import logger
import json

from langchain_core.messages import HumanMessage, AIMessage
from backend.agent.knowledge_extractor import extract_knowledge
from backend.api.routers.wiki import get_graph

def test_extraction_thread():
    os.environ["OBSIDIAN_VAULT_PATH"] = "backend/data/test_brain_thread"
    
    import shutil
    if os.path.exists("backend/data/test_brain_thread"):
        shutil.rmtree("backend/data/test_brain_thread")

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
    return state

async def main():
    state = test_extraction_thread()
    print("Running in executor...")
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, extract_knowledge, state)
    
    print("\n--- Files Generated ---")
    for root, _, files in os.walk("backend/data/test_brain_thread"):
        for file in files:
            filepath = os.path.join(root, file)
            print(f"\n{filepath}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(".env.local")
    asyncio.run(main())
