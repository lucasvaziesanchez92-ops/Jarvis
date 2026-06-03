# Jarvis — Architecture

## Overview

Jarvis is a personal AI assistant built with LangGraph (Python) on the backend and React Native (Expo) on the frontend.

```
Mobile (Expo)
    │  REST (axios)       WebSocket (streaming)
    ▼                     ▼
FastAPI  ──────────  LangGraph Agent
                          │
                    AWS Bedrock (Claude)
                          │
                      Tool calls
                    ┌─────┼─────┐
                  Notes Todos Calendar Email
                    │
                JSON File Store (swappable → SQLite / DynamoDB)
```

## Backend layers

| Layer | Location | Purpose |
|---|---|---|
| Config | `backend/config.py` | Pydantic-settings reads `.env` |
| LLM | `backend/llm/bedrock.py` | `ChatBedrockConverse` factory (provider-agnostic `BaseChatModel`) |
| State | `backend/agent/state.py` | `JarvisState` extends `MessagesState` |
| Graph | `backend/agent/graph.py` | `StateGraph` — `START → agent ↔ tools → END` |
| Nodes | `backend/agent/nodes.py` | `call_model` / `call_model_with_tools` |
| Tools | `backend/tools/` | `@tool` decorated functions |
| Registry | `backend/tools/registry.py` | `ALL_TOOLS` — single place to add tools |
| Storage | `backend/storage/json_store.py` | Thread-safe JSON file persistence |
| API | `backend/api/` | FastAPI app with REST + WebSocket |

## Phase progression

| Phase | What changes |
|---|---|
| 1 | Real Bedrock LLM, basic graph (`START → agent → END`) |
| 2 | Add tools (`ToolNode`), JSON storage, Gmail integration |
| 3 | FastAPI server, REST endpoints, WebSocket streaming |
| 4 | React Native mobile app |

## WebSocket protocol

```
Client → Server:  { "message": str, "session_id": str }
Server → Client:  { "type": "token",      "content": str }
Server → Client:  { "type": "tool_start", "tool_name": str, "tool_input": {} }
Server → Client:  { "type": "tool_end",   "tool_name": str, "tool_output": {} }
Server → Client:  { "type": "done",       "content": "" }
Server → Client:  { "type": "error",      "content": str }
```
