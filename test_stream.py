from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import HumanMessage, AIMessage

def node1(state: MessagesState):
    return {"messages": [AIMessage(content="Hello!")]}

graph = StateGraph(MessagesState)
graph.add_node("node1", node1)
graph.add_edge(START, "node1")
graph.add_edge("node1", END)
compiled = graph.compile()

import asyncio

async def main():
    state = {"messages": [HumanMessage(content="Hi!")]}
    async for ev in compiled.astream(state, stream_mode="values"):
        print("Emitted:", ev)

asyncio.run(main())
