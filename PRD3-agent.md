# PRD 3: Jarvis Agent (Local LLM Integration)

> **Technology Stack**: LangGraph + LangChain + Ollama/LM Studio + MCP  
> **Base Directory**: `backend/agent/` + `backend/llm/`  
> **Status**: Phase 2 — Core agent with tool calling works, needs production hardening  
> **Local LLM Options**: Ollama (`http://localhost:11434`), LM Studio (`http://localhost:1234/v1`)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Current State Analysis](#2-current-state-analysis)
3. [LLM Provider Configuration](#3-llm-provider-configuration)
4. [Agent Graph Architecture](#4-agent-graph-architecture)
5. [Node Specifications](#5-node-specifications)
6. [Tool Binding & Execution](#6-tool-binding--execution)
7. [Memory & Context Management](#7-memory--context-management)
8. [Prompt Engineering](#8-prompt-engineering)
9. [Web Search Integration](#9-web-search-integration)
10. [Monitoring & Debugging](#10-monitoring--debugging)
11. [Error Handling & Resilience](#11-error-handling--resilience)
12. [Local LLM Setup Guide](#12-local-llm-setup-guide)
13. [Performance Optimization](#13-performance-optimization)
14. [Implementation Roadmap](#14-implementation-roadmap)

---

## 1. Architecture Overview

### Complete Agent Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Client Request                               │
│  (Mobile App / Web / Claude Desktop / curl)                          │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                    FastAPI Endpoint
                    (POST /chat or WS /ws/chat)
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     LangGraph StateGraph                             │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    JarvisState                                │   │
│  │  messages: Annotated[list, add_messages]                     │   │
│  │  user_id: str | None                                         │   │
│  │  session_id: str | None                                      │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  START                                                               │
│    │                                                                 │
│    ▼                                                                 │
│  ┌─────────────┐                                                    │
│  │  classifier  │  ← Classify intent (notes/todos/calendar/email)   │
│  └──────┬──────┘                                                    │
│         │                                                           │
│    route_by_intent()                                                │
│   ╱         ╲                                                      │
│  ▼           ▼                                                     │
│  ┌─────────┐ ┌───────────┐                                        │
│  │  agent   │←│  memory    │  ← Trim/summarize old messages         │
│  │          │ └─────┬─────┘                                        │
│  │ (LLM +   │       │                                              │
│  │  tools)  │       │                                              │
│  └────┬─────┘       │                                              │
│       │              │                                              │
│  tools_condition()   │                                              │
│   ╱         ╲        │                                              │
│  ▼           ▼       │                                              │
│  END    ┌────────┐   │                                              │
│         │ tools   │   │ ← Execute tool(s)                           │
│         │(ToolNode)│   │                                            │
│         └───┬────┘   │                                              │
│             │         │                                              │
│             ▼         │                                              │
│         back to agent │                                              │
│         (with results)│                                              │
│                       │                                              │
│                    END ◄──────────────────────────────────────────── │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                    LLM Provider Factory
                    (backend/llm/__init__.py)
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
            ┌────────┐  ┌──────────┐  ┌────────────┐
            │ Ollama │  │  Bedrock │  │ LM Studio  │
            │(local) │  │ (cloud)  │  │  (local)   │
            └────────┘  └──────────┘  └────────────┘
                              │
                    Tool Registry (18+ tools)
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
            ┌────────┐  ┌──────────┐  ┌────────────┐
            │ Notes  │  │  Todos   │  │  Calendar  │
            │ (5)    │  │  (4)     │  │  (5)       │
            └────────┘  └──────────┘  └────────────┘
                │             │             │
                ▼             ▼             ▼
            ┌────────┐  ┌──────────┐  ┌────────────┐
            │ Email  │  │  Search  │  │   System   │
            │ (4)    │  │  (NEW)   │  │  (future)  │
            └────────┘  └──────────┘  └────────────┘
```

### Key Files Map

| File | Absolute Path | Purpose |
|------|--------------|---------|
| Agent State | `backend/agent/state.py` | JarvisState(MessagesState) — defines what the graph tracks |
| Agent Graph | `backend/agent/graph.py` | build_graph(), get_graph() — StateGraph assembly |
| Agent Nodes | `backend/agent/nodes.py` | call_model, call_model_with_tools — LLM invocation logic |
| Agent Prompts | `backend/agent/prompts.py` | SYSTEM_PROMPT — instructions for the LLM |
| LLM Factory | `backend/llm/__init__.py` | get_llm() — routes to correct provider |
| LLM Ollama | `backend/llm/ollama.py` | ChatOllama factory |
| LLM Bedrock | `backend/llm/bedrock.py` | ChatBedrockConverse factory |
| Tool Registry | `backend/tools/registry.py` | ALL_TOOLS list |
| Tool: Notes | `backend/tools/notes.py` | 5 LangChain @tool functions |
| Tool: Todos | `backend/tools/todos.py` | 4 LangChain @tool functions |
| Tool: Calendar | `backend/tools/calendar.py` | 5 LangChain @tool functions |
| Tool: Email | `backend/tools/email.py` | 4 LangChain @tool functions |
| MCP Server | `backend/mcp_server.py` | FastMCP exposing same tools |
| Config | `backend/config.py` | Pydantic-settings — all environment variables |

---

## 2. Current State Analysis

### What Works Well

- **LangGraph StateGraph**: Proper implementation with `START → agent ↔ tools → END`
- **Tool Calling**: LLM can choose to call tools or respond directly via `tools_condition()`
- **Provider Toggle**: `llm_provider` in `.env` switches between Ollama and Bedrock
- **Ollama Integration**: Already uses modern `langchain-ollama` (`ChatOllama`), not legacy
- **Pydantic Settings**: Clean `.env` configuration for model, URL, provider
- **Tool Registry**: Single `ALL_TOOLS` list — add a tool once, it's available everywhere
- **MCP Parity**: Same tools exposed via MCP for Claude Desktop

### What Needs Improvement

1. **No Conversation Memory**: Messages are not persisted between turns or server restarts
2. **No Context Window Management**: Long conversations will overflow the LLM's context
3. **No Intent Classification**: All requests go to the same generic agent, no routing optimization
4. **No Checkpointing**: Cannot recover conversation state after errors or restarts
5. **No Web Search**: Agent cannot fetch current/real-time information
6. **No Tool Error Handling**: Tool failures return raw exceptions to the LLM
7. **No Human-in-the-Loop**: Destructive actions (delete, send email) happen without confirmation
8. **No Streaming in Blocking Mode**: POST /chat waits for full response, no partial output
9. **Graph Singleton**: Single global graph doesn't support per-session isolation
10. **No LLM Fallback**: If Ollama is down, no automatic fallback to another provider

---

## 3. LLM Provider Configuration

### 3.1 Provider Comparison

| Provider | Setup | Cost | Latency | Quality | Privacy |
|----------|-------|------|---------|---------|---------|
| **Ollama** | Install Ollama, pull model | Free | 1-5s (local GPU) | Good (Llama 3.2) | ✅ Full local |
| **LM Studio** | Install LM Studio, download model | Free | 1-5s (local GPU) | Good (varies) | ✅ Full local |
| **AWS Bedrock** | AWS account, IAM keys | Pay-per-token | 2-8s (network) | Excellent (Claude) | ⚠️ Cloud |

### 3.2 Ollama Setup (Recommended for Local Dev)

**Step 1: Install Ollama**
```bash
# Windows: Download from https://ollama.com/download
# Or run:
winget install Ollama.Ollama
```

**Step 2: Pull Model**
```bash
# Recommended models for agent use (tool calling support required):
ollama pull llama3.2          # 3B — fast, good for testing
ollama pull llama3.1:8b       # 8B — better reasoning
ollama pull mistral           # 7B — good tool calling
ollama pull qwen2.5:7b        # 7B — excellent tool calling
ollama pull nomic-embed-text  # Embedding model (for vector memory)
```

**Step 3: Configure `.env`**
```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434
```

**Step 4: Verify**
```bash
curl http://localhost:11434/api/tags
# Should return list of pulled models
```

### 3.3 LM Studio Setup (OpenAI-Compatible)

**Step 1: Install LM Studio**
```bash
# Windows: Download from https://lmstudio.ai/
```

**Step 2: Download Model**
- Open LM Studio → Search → Download a model (e.g., `llama-3.1-8b-instruct`)
- Go to Local Server → Start Server (default: `http://localhost:1234/v1`)

**Step 3: Add Provider Code**

Create new file `backend/llm/lm_studio.py`:
```python
"""Factory for LM Studio LLM — OpenAI-compatible local endpoint."""
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from backend.config import settings

def get_llm() -> BaseChatModel:
    """Return a ChatOpenAI instance pointing to LM Studio."""
    return ChatOpenAI(
        model="local-model",  # Model name from LM Studio UI
        openai_api_key="lm-studio",  # Placeholder, not used
        openai_api_base="http://localhost:1234/v1",
        temperature=0.2,
        max_tokens=4096,
    )
```

**Step 4: Update Factory** (`backend/llm/__init__.py`):
```python
def get_llm() -> BaseChatModel:
    if settings.llm_provider == "ollama":
        from backend.llm.ollama import get_llm as get_ollama_llm
        return get_ollama_llm()
    elif settings.llm_provider == "bedrock":
        from backend.llm.bedrock import get_llm as get_bedrock_llm
        return get_bedrock_llm()
    elif settings.llm_provider == "lm_studio":
        from backend.llm.lm_studio import get_llm as get_lm_studio_llm
        return get_lm_studio_llm()
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
```

**Step 5: Configure `.env`**
```env
LLM_PROVIDER=lm_studio
LM_STUDIO_BASE_URL=http://localhost:1234/v1
```

### 3.4 Adding New Settings to Config

**File**: `backend/config.py` — Add these fields:

```python
# LM Studio
lm_studio_base_url: str = Field(default="http://localhost:1234/v1", alias="LM_STUDIO_BASE_URL")

# Memory
max_context_messages: int = Field(default=50, alias="MAX_CONTEXT_MESSAGES")
conversation_memory_type: str = Field(default="window", alias="CONVERSATION_MEMORY_TYPE")

# Web Search
tavily_api_key: str | None = Field(default=None, alias="TAVILY_API_KEY")

# Observability
enable_langsmith: bool = Field(default=False, alias="ENABLE_LANGSMITH")
langsmith_api_key: str | None = Field(default=None, alias="LANGSMITH_API_KEY")
```

### 3.5 Recommended Local Models for Agent Use

Not all local models support tool calling well. These are the best tested:

| Model | Size | Tool Calling | Reasoning | Speed | Notes |
|-------|------|-------------|-----------|-------|-------|
| `qwen2.5:7b` | 7B | ✅ Excellent | ✅ Good | Fast | Best tool calling support |
| `llama3.1:8b` | 8B | ✅ Good | ✅ Good | Fast | Reliable, widely used |
| `mistral:7b` | 7B | ✅ Good | ⚠️ Fair | Fast | Older but stable |
| `llama3.2` | 3B | ⚠️ Fair | ⚠️ Fair | Very Fast | Good for testing only |
| `mistral-nemo` | 12B | ✅ Good | ✅ Good | Medium | Better reasoning |
| `deepseek-r1` | 7B | ⚠️ Fair | ✅ Excellent | Slow | Best reasoning, weak tool use |

**Recommendation**: Start with `qwen2.5:7b` or `llama3.1:8b` for best tool calling support.

---

## 4. Agent Graph Architecture

### 4.1 Current Graph

**File**: `backend/agent/graph.py`

```python
# Phase 2 (with tools):
START → agent ↔ tools → END
```

This is a basic ReAct loop. The LLM decides whether to call a tool or respond. If it calls a tool, the tool executes and the result goes back to the LLM.

### 4.2 Enhanced Graph Architecture

```
START
  │
  ▼
┌─────────────┐
│   memory     │  ← Load conversation history from checkpoint
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  classifier  │  ← Classify intent domain (optional, for routing)
└──────┬──────┘
       │
  route_by_intent()
       │
       ▼
┌─────────────┐
│   agent      │  ← LLM with tools bound
└──────┬──────┘
       │
  tools_condition()
   ╱         ╲
  ▼           ▼
END      ┌─────────┐
         │  tools   │  ← ToolNode executes tool(s)
         └────┬─────┘
              │
              ▼
         back to agent
              │
              ▼
         ┌──────────┐
         │  memory   │  ← Trim/summarize if context too long
         └────┬─────┘
              │
              ▼
         back to agent (with trimmed context)
```

### 4.3 Graph Implementation Plan

**File**: `backend/agent/graph.py` — Enhanced version:

```python
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.sqlite import SqliteSaver

from backend.agent.state import JarvisState
from backend.agent.nodes import (
    call_model_with_tools,
    load_memory,
    trim_memory,
)
from backend.storage.sqlite_store import get_store

def build_graph(tools: list, checkpointer=True):
    builder = StateGraph(JarvisState)
    
    # Memory load node
    builder.add_node("load_memory", load_memory)
    builder.add_edge(START, "load_memory")
    
    # Agent node
    builder.add_node("agent", call_model_with_tools)
    builder.add_edge("load_memory", "agent")
    
    # Tools
    builder.add_node("tools", ToolNode(tools))
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "agent")
    
    # Memory trim node (after tool execution, before END)
    builder.add_node("trim_memory", trim_memory)
    builder.add_edge("agent", "trim_memory")
    builder.add_edge("trim_memory", END)
    
    # Compile with checkpoint
    if checkpointer:
        store = get_store()
        saver = SqliteSaver(store.get_session())
        return builder.compile(checkpointer=saver)
    
    return builder.compile()
```

### 4.4 Per-Session State

**Current Problem**: The graph is a singleton — all users/sessions share the same state.

**Solution**: Use LangGraph's `config` parameter with `thread_id`:

```python
# In chat.py endpoint:
config = {
    "configurable": {
        "thread_id": request.session_id or "default",
        "user_id": request.user_id,
    }
}

state = await graph.ainvoke(
    {"messages": [HumanMessage(content=request.message)]},
    config=config,
)
```

This isolates conversation history per session automatically via the checkpointer.

---

## 5. Node Specifications

### 5.1 Current Nodes

**File**: `backend/agent/nodes.py`

| Node | Function | Description |
|------|----------|-------------|
| `call_model` | `call_model(state)` | Invokes LLM without tools (Phase 1) |
| `call_model_with_tools` | `call_model_with_tools(state, llm_with_tools)` | Invokes LLM with bound tools (Phase 2+) |

### 5.2 Nodes to Add

| Node | Function | Purpose | Priority |
|------|----------|---------|----------|
| `load_memory` | `load_memory(state)` | Load previous conversation from checkpoint | High |
| `trim_memory` | `trim_memory(state)` | Remove/summarize old messages to fit context | High |
| `classify_intent` | `classify_intent(state)` | Classify user intent for routing | Medium |
| `human_confirmation` | `human_confirmation(state)` | Wait for user approval before destructive actions | Medium |
| `format_response` | `format_response(state)` | Structure final response for UI consumption | Low |

### 5.3 Memory Load Node

**Purpose**: Load prior conversation from checkpoint store.

```python
# backend/agent/nodes.py
from langchain_core.messages import SystemMessage
from backend.agent.prompts import SYSTEM_PROMPT

def load_memory(state: JarvisState) -> dict:
    """
    Load conversation history from checkpoint.
    With SqliteSaver checkpointer, this is automatic — the graph
    restores the previous state when invoked with the same thread_id.
    
    This node adds the system prompt if not present.
    """
    messages = state.get("messages", [])
    
    # Ensure system prompt is first
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    
    return {"messages": messages}
```

### 5.4 Memory Trim Node

**Purpose**: Prevent context overflow by trimming or summarizing old messages.

```python
def trim_memory(state: JarvisState, max_messages: int = 50) -> dict:
    """
    Trim message history to stay within context window.
    Keeps system prompt + most recent messages.
    """
    messages = state.get("messages", [])
    
    if len(messages) <= max_messages:
        return {}  # No trimming needed
    
    # Keep system prompt + last N messages
    system_msg = None
    if isinstance(messages[0], SystemMessage):
        system_msg = messages[0]
        messages = messages[1:]
    
    recent = messages[-(max_messages - 1):]  # -1 for system prompt
    trimmed = [system_msg] + recent if system_msg else recent
    
    return {"messages": trimmed}
```

**Advanced**: Replace oldest messages with a summary:

```python
def summarize_and_trim(state: JarvisState, max_messages: int = 50) -> dict:
    """Summarize old messages and keep recent context."""
    messages = state.get("messages", [])
    
    if len(messages) <= max_messages:
        return {}
    
    # Separate system, old, and recent messages
    system_msg = messages[0] if isinstance(messages[0], SystemMessage) else None
    old_messages = messages[1:-max_messages+2]  # Messages to summarize
    recent_messages = messages[-max_messages+2:]  # Keep these
    
    # Use LLM to summarize old messages
    if old_messages:
        summary_llm = get_llm()
        summary_prompt = SystemMessage(
            content="Summarize the following conversation history concisely. "
                    "Preserve key facts, decisions, and action items."
        )
        summary = summary_llm.invoke([summary_prompt] + old_messages)
        
        # Replace old messages with summary
        summary_msg = HumanMessage(content=f"[Previous conversation summary: {summary.content}]")
        messages = ([system_msg] if system_msg else []) + [summary_msg] + recent_messages
    else:
        messages = ([system_msg] if system_msg else []) + recent_messages
    
    return {"messages": messages}
```

### 5.5 Intent Classification Node

**Purpose**: Classify the user's request domain to optimize tool selection.

```python
def classify_intent(state: JarvisState) -> dict:
    """
    Classify user intent into domains: notes, todos, calendar, email, general.
    This can be used to filter which tools are available, or for analytics.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"intent": "general"}
    
    last_user_msg = None
    for msg in reversed(messages):
        if hasattr(msg, "content") and not hasattr(msg, "tool_call_id"):
            last_user_msg = msg.content
            break
    
    if not last_user_msg:
        return {"intent": "general"}
    
    # Rule-based classification (fast, no LLM call needed)
    last_user_msg_lower = last_user_msg.lower()
    
    if any(kw in last_user_msg_lower for kw in ["note", "remember", "write down", "jot"]):
        return {"intent": "notes"}
    elif any(kw in last_user_msg_lower for kw in ["todo", "task", "remind", "do", "finish"]):
        return {"intent": "todos"}
    elif any(kw in last_user_msg_lower for kw in ["schedule", "meeting", "calendar", "event", "appoint"]):
        return {"intent": "calendar"}
    elif any(kw in last_user_msg_lower for kw in ["email", "mail", "send", "inbox", "read my mail"]):
        return {"intent": "email"}
    elif any(kw in last_user_msg_lower for kw in ["search", "look up", "what is", "who is", "current", "latest"]):
        return {"intent": "search"}
    else:
        return {"intent": "general"}
```

### 5.6 Human Confirmation Node

**Purpose**: Require user approval before destructive actions.

```python
from langgraph.types import interrupt

def human_confirmation(state: JarvisState) -> dict:
    """
    Interrupt the graph to get human approval for destructive actions.
    This is used with LangGraph's interrupt() function.
    """
    messages = state.get("messages", [])
    last_ai_msg = None
    for msg in reversed(messages):
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tool_call in msg.tool_calls:
                if tool_call["name"] in ["delete_note", "delete_todo", "delete_calendar_event", "send_email"]:
                    # Interrupt and wait for approval
                    approval = interrupt(
                        f"The assistant wants to {tool_call['name']}. Approve? (yes/no)"
                    )
                    if approval.lower() != "yes":
                        return {"approved": False, "tool_call": tool_call}
    
    return {"approved": True}
```

---

## 6. Tool Binding & Execution

### 6.1 Current Tool Binding

**File**: `backend/agent/graph.py`

```python
llm_with_tools = get_llm().bind_tools(tools)
agent_node = partial(call_model_with_tools, llm_with_tools=llm_with_tools)
```

This is the correct LangChain pattern. The LLM receives tool definitions and decides which to call.

### 6.2 Tool Execution Flow

```
User: "Create a todo to buy groceries by tomorrow"
  │
  ▼
┌───────────────────────────────────────────┐
│  Agent (LLM)                               │
│  Input: messages + tool definitions        │
│  Output: AIMessage with tool_calls         │
│  tool_calls: [{                            │
│    name: "create_todo",                    │
│    args: {                                 │
│      text: "Buy groceries",               │
│      due_date: "2024-12-31T23:59:59",     │
│      priority: "medium"                    │
│    }                                       │
│  }]                                        │
└───────────────────┬───────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────┐
│  ToolNode (ToolNode)                       │
│  Executes: create_todo(text, due_date, ..) │
│  Output: ToolMessage with result           │
│  "Todo created: {id: 'abc', text: ...}"   │
└───────────────────┬───────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────┐
│  Agent (LLM) — second turn                │
│  Input: messages + ToolMessage result      │
│  Output: AIMessage with final response     │
│  "I've created a todo: 'Buy groceries'..." │
└───────────────────────────────────────────┘
```

### 6.3 Tool Error Handling

**Current Problem**: If a tool throws an exception, the raw error propagates to the LLM, which may confuse it.

**Solution**: Wrap tool execution with error handling that returns user-friendly messages.

**Pattern for each tool**:
```python
# backend/tools/todos.py
from langchain_core.tools import tool
from tenacity import retry, stop_after_attempt, wait_exponential

@tool
@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=0.5, max=3))
def create_todo(text: str, priority: str = "medium", due_date: str | None = None) -> dict:
    """Create a new to-do item."""
    try:
        result = todos_service.create_todo(text, priority, due_date)
        return result
    except Exception as e:
        return {"error": f"Failed to create todo: {str(e)}"}
```

The LLM receives `{"error": "..."}` and can respond appropriately to the user.

### 6.4 Parallel Tool Execution

When the LLM calls multiple independent tools (e.g., `list_notes()` + `list_todos()`), LangGraph's `ToolNode` already executes them in parallel by default.

**To ensure parallelism**, verify the LLM emits multiple tool_calls in a single AIMessage:

```python
# The LLM should emit:
AIMessage(
    content="",
    tool_calls=[
        {"name": "list_notes", "args": {}},
        {"name": "list_todos", "args": {}},
    ]
)

# ToolNode executes both in parallel automatically.
```

---

## 7. Memory & Context Management

### 7.1 Memory Strategy Options

| Strategy | Description | Best For | Trade-offs |
|----------|-------------|----------|------------|
| **Window** (current) | Keep last N messages | Short conversations | Loses older context |
| **Summary** | Summarize old messages with LLM | Long conversations | Extra LLM cost |
| **Vector Retrieval** | Store messages in vector DB, retrieve by similarity | Context-aware responses | Complexity + embedding cost |
| **Hybrid** | Window + Summary for very old messages | Production | Best balance |

### 7.2 Recommended: Hybrid Memory

**Implementation**:
```
Messages 0-N:
  [0] System Prompt (always kept)
  [1] Summary Message: "[Earlier: User asked about meeting. Assistant created event at 2pm.]"
  [2..N] Recent messages (last 30-50 messages)
```

**Configuration**:
```env
CONVERSATION_MEMORY_TYPE=hybrid
MAX_CONTEXT_MESSAGES=50
SUMMARY_THRESHOLD=30  # Summarize when messages exceed this
```

### 7.3 LangGraph Checkpointer

**Current State**: No checkpointer — state is lost between invocations.

**Implementation** (SQLite-backed):

```python
# backend/agent/graph.py
from langgraph.checkpoint.sqlite import SqliteSaver
from backend.storage.sqlite_store import get_store

def build_graph(tools: list):
    builder = StateGraph(JarvisState)
    # ... add nodes and edges ...
    
    # Add SQLite checkpointer
    store = get_store()
    saver = SqliteSaver.from_conn_string(f"sqlite:///{store.engine.url.database}")
    
    return builder.compile(checkpointer=saver)
```

**New Table Needed**: LangGraph's `SqliteSaver` creates its own `checkpoints` table automatically.

### 7.4 Using Checkpointer in Endpoints

```python
# backend/api/routers/chat.py
@router.post("/chat")
async def chat(request: ChatRequest, graph=Depends(get_jarvis_graph)):
    # Thread ID = session_id for conversation isolation
    config = {
        "configurable": {
            "thread_id": request.session_id or "default",
        }
    }
    
    state = await graph.ainvoke(
        {"messages": [HumanMessage(content=request.message)]},
        config=config,
    )
    ...
```

---

## 8. Prompt Engineering

### 8.1 Current System Prompt

**File**: `backend/agent/prompts.py`

```python
SYSTEM_PROMPT = """You are Jarvis, a highly capable personal assistant. You are concise, \
helpful, and proactive.

You can help the user with:
- Taking and managing notes
- Managing to-do lists and tasks
- Scheduling and reviewing calendar events
- Reading, searching, and sending emails

Always confirm when you create, update, or delete something. When listing items, \
format them clearly. If the user's request is ambiguous, ask a brief clarifying question.

When listing todos, format each item as a checkbox line:
- [ ] Task text (priority: medium, due: 2024-12-31)
- [x] Completed task
Use [ ] for incomplete and [x] for completed items.
"""
```

### 8.2 Enhanced System Prompt

```python
SYSTEM_PROMPT = """You are Jarvis, a personal AI assistant powered by a local language model.

## Identity
You are concise, helpful, and proactive. You take initiative when appropriate and \
always confirm actions taken.

## Available Tools
You have access to the following tool categories:
- **notes**: create_note, list_notes, get_note, update_note, delete_note
- **todos**: create_todo, list_todos, complete_todo, delete_todo
- **calendar**: create_calendar_event, list_calendar_events, get_calendar_event, update_calendar_event, delete_calendar_event
- **email**: list_emails, get_email, send_email, search_emails
- **search**: web_search (for current/real-time information)

## Tool Usage Guidelines
1. Use tools ONLY when the user's request requires them. Respond directly if no tool is needed.
2. Always verify tool results before responding to the user.
3. If a tool call fails, explain the error clearly and suggest alternatives.
4. If information is missing, ask a brief clarifying question.
5. Never invent or fabricate data. If tools return nothing, say "I don't have that information."
6. For destructive actions (delete, send email), confirm with the user first.

## Response Format
- Confirm actions: "I've created a todo: 'Buy groceries' with medium priority."
- List items clearly formatted with bullet points or checkboxes
- For todos, use this exact format:
  - [ ] Task text (priority: medium, due: 2024-12-31)
  - [x] Completed task
- Offer next steps when applicable: "Would you like me to set a reminder?"

## When to Use Web Search
- User asks about current events, news, or real-time information
- User asks "what is X" for entities you may not know about
- Facts that may have changed recently (prices, schedules, rankings)

## Safety & Privacy
- Never expose raw tool output containing sensitive information (email addresses, IDs)
- Summarize email content appropriately
- Ask before sending emails on the user's behalf
"""
```

### 8.3 Prompt Engineering Best Practices

| Principle | Application |
|-----------|-------------|
| **Modular sections** | Use `##` headers to separate concerns — easy to update individual sections |
| **Under 1000 tokens** | Keep the system prompt concise to save context window for conversation |
| **Tool governance** | Explicitly list what each tool does and when to use it |
| **Output format** | Specify exact format expectations so the mobile app can parse them |
| **Injection prevention** | Use delimiters and treat user content as data |
| **Version control** | Store prompts in files (current pattern), not inline code |
| **Dynamic injection** | Add context (current time, user name) at runtime |

### 8.4 Dynamic Prompt Injection

```python
# backend/agent/nodes.py
from datetime import datetime

def call_model_with_tools(state: JarvisState, llm_with_tools) -> dict:
    """Invoke LLM with dynamic system prompt."""
    
    # Build dynamic system prompt
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dynamic_prompt = SYSTEM_PROMPT + f"\n\n## Current Context\n- Current time: {current_time}"
    
    messages = [SystemMessage(content=dynamic_prompt)] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}
```

---

## 9. Web Search Integration

### 9.1 Why the Agent Needs Web Search

Local LLMs have a training cutoff date. Without web search, the agent cannot answer:
- "What's the weather today?"
- "What are the latest news about AI?"
- "Who won the Super Bowl this year?"
- "What's the current price of Bitcoin?"

### 9.2 Option A: Tavily Search (Recommended)

**Tavily** is a search engine built for AI agents, natively supported by LangChain.

**Setup**:
```bash
pip install langchain-tavily
```

**Get API Key**: https://tavily.com/ (free tier: 1000 searches/month)

**Implementation**:

Create `backend/tools/web_search.py`:
```python
"""LangChain tool for web search via Tavily."""
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from backend.config import settings

@tool
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web for current information. Use when you need up-to-date facts."""
    if not settings.tavily_api_key:
        return "Web search is not configured. Please set TAVILY_API_KEY in .env"
    
    try:
        search = TavilySearch(max_results=max_results)
        results = search.run(query)
        return results
    except Exception as e:
        return f"Error performing web search: {str(e)}"
```

**Register in `backend/tools/registry.py`**:
```python
from backend.tools.web_search import web_search

ALL_TOOLS = [
    # ... existing 18 tools ...
    web_search,  # NEW — Tool #19
]
```

**Add to `.env`**:
```env
TAVILY_API_KEY=tvly-your-key-here
```

### 9.3 Option B: DuckDuckGo (Free, No API Key)

**Alternative**: DuckDuckGo search — no API key needed, but less reliable results.

```python
# backend/tools/web_search.py
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun

@tool
def web_search(query: str) -> str:
    """Search the web using DuckDuckGo. Use for current events and real-time info."""
    try:
        search = DuckDuckGoSearchRun()
        return search.run(query)
    except Exception as e:
        return f"Error performing web search: {str(e)}"
```

### 9.4 When the Agent Should Trigger Web Search

Add to system prompt:
```
## When to Use Web Search
- User asks about events happening now or in the future
- User asks "what is" about recent developments
- User asks for prices, schedules, or rankings
- User asks about weather, sports, stocks, news
```

---

## 10. Monitoring & Debugging

### 10.1 LangSmith (LangChain's Observability Platform)

**What it provides**:
- Trace every LLM call, tool call, and graph step
- Measure latency per step
- View token usage and costs
- Debug failed tool calls
- Compare different prompts/models

**Setup**:

1. **Install**:
```bash
pip install langsmith
```

2. **Configure `.env`**:
```env
ENABLE_LANGSMITH=true
LANGSMITH_API_KEY=your_key_here
LANGSMITH_PROJECT=jarvis
```

3. **Enable in code** (`backend/api/main.py`):
```python
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.enable_langsmith:
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGSMITH_PROJECT"] = "jarvis"
    
    get_jarvis_graph()
    yield
```

4. **View traces**: https://smith.langchain.com/

### 10.2 Console Debugging (Local Dev)

**Enable verbose logging** on the graph:

```python
# backend/agent/graph.py
graph = builder.compile(checkpointer=saver)

# Print all graph steps (for debugging):
for event in graph.stream(
    {"messages": [HumanMessage(content="list my todos")]},
    stream_mode="values",
):
    print(event)
```

### 10.3 Tool Call Logging

**Every tool call should log**:
```python
import logging

logger = logging.getLogger("jarvis.tools")

@tool
def create_todo(text: str, ...) -> dict:
    logger.info(f"create_todo called: text='{text}', priority=...")
    try:
        result = todos_service.create_todo(text, ...)
        logger.info(f"create_todo succeeded: id={result['id']}")
        return result
    except Exception as e:
        logger.error(f"create_todo failed: {e}")
        return {"error": str(e)}
```

### 10.4 Metrics to Track

| Metric | Why It Matters | How to Collect |
|--------|---------------|----------------|
| Tool call frequency | Understand which tools users need most | Log every tool call |
| Tool error rate | Identify unreliable tools | Log failures / total calls |
| LLM latency | User experience impact | Timestamp before/after LLM invoke |
| Token usage per turn | Cost optimization | LangSmith or manual counting |
| Conversation length | Memory management needs | Count messages in state |
| Session duration | Engagement metric | Track session start/end |

---

## 11. Error Handling & Resilience

### 11.1 Error Categories

| Error Type | Example | Handling Strategy |
|------------|---------|-------------------|
| LLM Unavailable | Ollama not running | Fallback to Bedrock or return user-friendly error |
| Tool Failure | Gmail API token expired | Return error message, suggest re-auth |
| Context Overflow | Too many messages | Summarize old messages, keep recent |
| Timeout | Calendar API slow | Retry with backoff, then fail gracefully |
| Invalid Input | Malformed datetime | Validate before calling service |
| Network Error | Can't reach Google | Retry 3x with exponential backoff |

### 11.2 LLM Fallback Pattern

```python
# backend/llm/__init__.py
import logging

logger = logging.getLogger("jarvis.llm")

def get_llm() -> BaseChatModel:
    provider = settings.llm_provider
    primary_func = {
        "ollama": lambda: __import__("backend.llm.ollama", fromlist=["get_llm"]).get_llm(),
        "bedrock": lambda: __import__("backend.llm.bedrock", fromlist=["get_llm"]).get_llm(),
        "lm_studio": lambda: __import__("backend.llm.lm_studio", fromlist=["get_llm"]).get_llm(),
    }.get(provider)
    
    if not primary_func:
        raise ValueError(f"Unknown LLM provider: {provider}")
    
    try:
        return primary_func()
    except Exception as e:
        fallback = "bedrock" if provider == "ollama" else "ollama"
        logger.warning(f"Primary provider '{provider}' failed ({e}). Falling back to '{fallback}'.")
        
        fallback_func = {
            "ollama": lambda: __import__("backend.llm.ollama", fromlist=["get_llm"]).get_llm(),
            "bedrock": lambda: __import__("backend.llm.bedrock", fromlist=["get_llm"]).get_llm(),
        }.get(fallback)
        
        if fallback_func:
            return fallback_func()
        raise
```

### 11.3 Circuit Breaker for External Services

```python
# backend/services/email_service.py
import pybreaker

email_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    recovery_timeout=120,
)

@email_breaker
def send_email(to: str, subject: str, body: str) -> str:
    # Gmail API call
    ...
```

When the circuit is "open" (too many failures), calls fail immediately instead of waiting for a timeout.

### 11.4 Graceful Degradation

When a tool is unavailable, the agent should:
1. Acknowledge the limitation
2. Explain what it cannot do
3. Suggest alternatives

```python
@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email."""
    try:
        return email_service.send_email(to, subject, body)
    except FileNotFoundError:
        return (
            "Error: Gmail credentials not found. "
            "Please configure your Gmail credentials file and try again."
        )
    except Exception as e:
        return f"Failed to send email: {str(e)}"
```

---

## 12. Local LLM Setup Guide

### 12.1 Complete Ollama Setup (Step by Step)

**Step 1: Install Ollama**
```bash
# Windows (PowerShell):
winget install Ollama.Ollama

# Or download from https://ollama.com/download
```

**Step 2: Start Ollama Service**
```bash
# Ollama runs as a background service automatically after install.
# Verify:
ollama list
```

**Step 3: Pull Recommended Model**
```bash
# Best for tool calling:
ollama pull qwen2.5:7b

# Alternative:
ollama pull llama3.1:8b

# Embedding model (for future vector memory):
ollama pull nomic-embed-text
```

**Step 4: Verify Model**
```bash
ollama run qwen2.5:7b "Hello, can you list my todos?"
# Type /bye to exit
```

**Step 5: Configure `.env`**
```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_BASE_URL=http://localhost:11434
```

**Step 6: Start Backend**
```bash
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Step 7: Test**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "List my todos", "session_id": "test"}'
```

### 12.2 Complete LM Studio Setup

**Step 1: Install LM Studio**
```
Download from https://lmstudio.ai/
Install and open the application
```

**Step 2: Download Model**
```
1. Click "Search" in the left sidebar
2. Search for "Llama 3.1 8B Instruct" or "Qwen 2.5 7B Instruct"
3. Click Download on a quantized version (e.g., Q4_K_M)
```

**Step 3: Start Local Server**
```
1. Click "Local Server" in the left sidebar
2. Select the downloaded model
3. Click "Start Server"
4. Server runs at http://localhost:1234/v1
```

**Step 4: Add LM Studio Provider Code**
(See Section 3.3 above for `backend/llm/lm_studio.py`)

**Step 5: Configure `.env`**
```env
LLM_PROVIDER=lm_studio
LM_STUDIO_BASE_URL=http://localhost:1234/v1
```

**Step 6: Start Backend**
```bash
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 12.3 Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| `ConnectionError` to Ollama | Ollama not running | Start Ollama service |
| `Model not found` | Wrong model name in `.env` | Check `ollama list` output |
| Slow responses | Model too large for RAM | Use a smaller model (3B vs 8B) |
| `404` from LM Studio | Server not started | Start server in LM Studio |
| Tool calls not working | Model doesn't support tool calling | Switch to qwen2.5 or llama3.1 |
| `bind_tools` error | Using old `Ollama` class instead of `ChatOllama` | Verify `backend/llm/ollama.py` uses `ChatOllama` |

---

## 13. Performance Optimization

### 13.1 Latency Breakdown

| Step | Typical Time | Optimization |
|------|-------------|--------------|
| LLM inference (local) | 1-5s | Use smaller model, GPU acceleration |
| LLM inference (cloud) | 2-8s | Network latency, unavoidable |
| Tool execution (SQLite) | <50ms | Already fast |
| Tool execution (Gmail/Calendar) | 500ms-2s | Caching, connection pooling |
| WebSocket streaming | Real-time | Already optimal |

### 13.2 Optimization Strategies

| Strategy | Impact | Complexity |
|----------|--------|------------|
| **Use smaller model** (3B vs 8B) | 2-3x faster | Low |
| **GPU acceleration** | 5-10x faster | Medium (needs GPU) |
| **Speculative decoding** | 1.5-2x faster | Medium |
| **Cache tool results** | Avoid redundant calls | Low |
| **Batch independent tool calls** | Parallel execution | Already supported |
| **Stream responses** | Perceived latency ~0 | Already implemented |
| **Pre-warm LLM on startup** | First response faster | Low |

### 13.3 Token Management

**Context Window Limits**:
| Model | Context Window | Max Messages (~400 tokens each) |
|-------|---------------|--------------------------------|
| Llama 3.2 | 128K | ~300 messages |
| Llama 3.1 8B | 128K | ~300 messages |
| Qwen 2.5 7B | 32K | ~80 messages |
| Mistral 7B | 32K | ~80 messages |

**Recommendation**: Set `MAX_CONTEXT_MESSAGES=50` for 7B models to stay well within limits.

### 13.4 Memory Profiling

For production monitoring, track:
```python
import psutil
import logging

logger = logging.getLogger("jarvis.system")

def log_memory_usage():
    process = psutil.Process()
    mem = process.memory_info()
    logger.info(f"RSS: {mem.rss / 1024 / 1024:.1f}MB, VMS: {mem.vms / 1024 / 1024:.1f}MB")
```

---

## 14. Implementation Roadmap

### Phase A: Immediate (Do First)

| Task | Files | Effort | Description |
|------|-------|--------|-------------|
| **Add LM Studio provider** | New `backend/llm/lm_studio.py`, update `__init__.py` | Small | Third LLM provider |
| **Add web search tool** | New `backend/tools/web_search.py`, update `registry.py` | Small | Tavily or DuckDuckGo |
| **Update system prompt** | `backend/agent/prompts.py` | Small | Add tool guidelines, web search triggers |
| **Add conversation checkpointer** | Update `backend/agent/graph.py` | Medium | SQLite-based state persistence |
| **Per-session state isolation** | Update `chat.py` to pass `thread_id` config | Small | Isolate conversations |
| **Add tool error handling** | All `backend/tools/*.py` files | Medium | Wrap with try/except, user-friendly errors |
| **Add current time to prompt** | Update `nodes.py` | Tiny | Dynamic context injection |

### Phase B: Near-Term (Do Next)

| Task | Files | Effort | Description |
|------|-------|--------|-------------|
| **Memory trim node** | New node in `nodes.py` | Medium | Summarize old messages |
| **Intent classification** | New node in `nodes.py`, update `graph.py` | Medium | Route by domain |
| **LangSmith integration** | `.env` + `main.py` lifespan | Small | Observability |
| **Request logging** | New middleware | Small | Log all requests |
| **LLM fallback** | Update `llm/__init__.py` | Small | Auto-failover |
| **Add `get_current_time` tool** | New `backend/tools/system.py` | Tiny | Date/time awareness |
| **Add pagination** | All list endpoints | Medium | `?skip=0&limit=20` |

### Phase C: Production-Ready

| Task | Files | Effort | Description |
|------|-------|--------|-------------|
| **Vector store for semantic memory** | New `backend/storage/vector_store.py` | Large | ChromaDB + embeddings |
| **Human-in-the-loop confirmation** | Update `graph.py` with interrupt | Medium | Approve destructive actions |
| **APScheduler for background tasks** | New `backend/scheduler/` | Large | Recurring tasks |
| **API Key authentication** | New `backend/api/security.py` | Small | Secure endpoints |
| **Rate limiting** | `slowapi` middleware | Small | Prevent abuse |
| **Circuit breakers** | Update services | Small | Resilient external API calls |
| **Docker containerization** | `Dockerfile`, `docker-compose.yml` | Medium | Easy deployment |

---

## References

- **LangGraph Agents**: https://langchain-ai.github.io/langgraph/concepts/agent_graphs/
- **LangChain Tool Calling**: https://python.langchain.com/docs/modules/agents/tools/
- **ChatOllama Documentation**: https://python.langchain.com/docs/integrations/chat/ollama/
- **LM Studio Server**: https://lmstudio.ai/docs/local-server
- **LangSmith Observability**: https://docs.smith.langchain.com/
- **Tavily Search**: https://docs.tavily.com/documentation
- **Ollama Models**: https://ollama.com/library
- **LangChain Checkpointing**: https://langchain-ai.github.io/langgraph/concepts/persistence/
- **Prompt Engineering Guide**: https://www.promptingguide.ai/
- **Local AI Agent Best Practices**: https://aihaven.com/news/build-local-ai-agent-ollama-langchain
