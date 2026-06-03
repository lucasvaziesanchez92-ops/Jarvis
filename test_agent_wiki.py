import asyncio
import os
from backend.agent.graph import get_graph
from backend.tools.registry import ALL_TOOLS
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()

async def test_wiki_interaction():
    print("Initializing Jarvis Agent...")
    graph = get_graph(tools=ALL_TOOLS)
    
    config = {"configurable": {"thread_id": "test_session_1"}}
    
    # Test 1: Ask about something not in the wiki
    print("\n--- Test 1: Querying unknown info ---")
    inputs = {"messages": [HumanMessage(content="¿Qué sabes sobre la arquitectura de microservicios según mis notas?")]}
    async for event in graph.astream(inputs, config=config, stream_mode="values"):
        message = event["messages"][-1]
        if hasattr(message, "content") and message.content:
            print(f"Jarvis: {message.content}")

    # Test 2: Ingest a research note
    print("\n--- Test 2: Saving research ---")
    inputs = {"messages": [HumanMessage(content="Investiga brevemente qué es un 'Circuit Breaker' en microservicios y guárdalo en mi wiki.")]}
    async for event in graph.astream(inputs, config=config, stream_mode="values"):
        message = event["messages"][-1]
        if hasattr(message, "content") and message.content:
             print(f"Jarvis: {message.content}")

    # Test 3: Query the newly added info
    print("\n--- Test 3: Querying newly added info ---")
    inputs = {"messages": [HumanMessage(content="Ahora, ¿qué me puedes decir sobre los Circuit Breakers basado en lo que guardamos?")]}
    async for event in graph.astream(inputs, config=config, stream_mode="values"):
        message = event["messages"][-1]
        if hasattr(message, "content") and message.content:
             print(f"Jarvis: {message.content}")

if __name__ == "__main__":
    asyncio.run(test_wiki_interaction())
