"""Test script to verify the agent can perform real actions."""
import asyncio
from backend.agent.graph import build_graph
from backend.tools.registry import ALL_TOOLS

async def test_agent():
    print("=" * 60)
    print("Testing Jarvis Agent with LM Studio")
    print("=" * 60)
    
    # Build graph with all tools
    print("\n[1/4] Loading agent graph with tools...")
    graph = build_graph(tools=ALL_TOOLS)
    print("✓ Agent graph loaded successfully")
    
    # Test 1: Simple conversation
    print("\n[2/4] Testing simple conversation...")
    config = {"configurable": {"thread_id": "test-1"}}
    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": "Hello! What can you help me with?"}]},
        config,
    )
    assistant_msg = result["messages"][-1]
    print(f"✓ Agent responded: {assistant_msg.content[:100]}...")
    
    # Test 2: Create a todo via agent
    print("\n[3/4] Testing todo creation via agent...")
    config2 = {"configurable": {"thread_id": "test-2"}}
    result2 = await graph.ainvoke(
        {"messages": [{"role": "user", "content": "Create a todo: Buy milk with high priority"}]},
        config2,
    )
    
    # Check if tool was called
    messages = result2["messages"]
    tool_calls = [msg for msg in messages if hasattr(msg, 'tool_calls') and msg.tool_calls]
    if tool_calls:
        print(f"✓ Agent called tools: {len(tool_calls)} tool call(s) detected")
        for msg in tool_calls:
            for tc in msg.tool_calls:
                print(f"  - Tool: {tc['name']}")
    else:
        print("⚠ No tool calls detected (agent might have responded conversationally)")
    
    # Test 3: Create a note via agent
    print("\n[4/4] Testing note creation via agent...")
    config3 = {"configurable": {"thread_id": "test-3"}}
    result3 = await graph.ainvoke(
        {"messages": [{"role": "user", "content": "Create a note titled 'Meeting Notes' with content 'Discuss Q1 goals'"}]},
        config3,
    )
    
    messages3 = result3["messages"]
    tool_calls3 = [msg for msg in messages3 if hasattr(msg, 'tool_calls') and msg.tool_calls]
    if tool_calls3:
        print(f"✓ Agent called tools: {len(tool_calls3)} tool call(s) detected")
        for msg in tool_calls3:
            for tc in msg.tool_calls:
                print(f"  - Tool: {tc['name']}")
    else:
        print("⚠ No tool calls detected")
    
    print("\n" + "=" * 60)
    print("✓ Agent testing completed!")
    print("=" * 60)
    print("\nAvailable tools:")
    for tool in ALL_TOOLS:
        print(f"  • {tool.name}")

if __name__ == "__main__":
    asyncio.run(test_agent())
