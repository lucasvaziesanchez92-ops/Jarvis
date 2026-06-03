# Jarvis — AI Personal Assistant

A personal assistant built with LangGraph + AWS Bedrock (Python) and React Native (Expo), taught incrementally across 4 phases.

## Quick start

```bash
# 1. Set up environment
cp .env.example .env          # fill in AWS credentials
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the API server
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000

# 4. Open Swagger docs
open http://localhost:8000/docs
```

## Running tests

```bash
# Phase 1 — requires AWS Bedrock
pytest tests/phase1/ -m integration -v

# Phase 2 — no Bedrock needed
pytest tests/phase2/test_tools.py -v

# Phase 2 — agent routing (requires Bedrock)
pytest tests/phase2/test_agent_routing.py -m integration -v

# Phase 2 — email tools (requires Gmail credentials)
pytest tests/phase2/test_email_tools.py -m requires_credentials -v

# Phase 3 — API tests (no Bedrock)
pytest tests/phase3/test_api_endpoints.py -v

# Phase 4 — end-to-end (requires Bedrock)
pytest tests/phase4/test_integration.py -m integration -v
```

## Mobile app

```bash
cd mobile
npm install
npm start       # opens Expo Go — scan QR or press i for iOS simulator
```

Set `EXPO_PUBLIC_API_URL=http://<your-machine-ip>:8000` in `mobile/.env` when running on a physical device.

## Project structure

```
backend/          Python backend (FastAPI + LangGraph)
  config.py       Pydantic-settings (.env)
  llm/            Bedrock LLM factory
  agent/          LangGraph graph, state, nodes, prompts
  tools/          @tool functions + registry
  models/         Pydantic models
  storage/        JSON file store
  api/            FastAPI app, routers, dependencies

mobile/           React Native (Expo) app
  src/
    api/          axios client + TypeScript types
    hooks/        useJarvisChat (WS), useJarvisApi (REST)
    components/   MessageBubble, StreamingText, TypingIndicator
    screens/      Chat, Notes, Todos, Calendar, Email
    navigation/   Bottom tab navigator

tests/
  phase1/         Bedrock connection + graph basics
  phase2/         Tool unit tests + agent routing
  phase3/         API endpoint + WebSocket tests
  phase4/         End-to-end integration

docs/
  architecture.md
  api-contract.md
  tools.md
```

## Phases

| Phase | Focus | Key concepts |
|---|---|---|
| 1 | Real LLM + conversational graph | `MessagesState`, `BaseChatModel`, Bedrock auth |
| 2 | Tool calling + storage | `@tool`, `ToolNode`, `tools_condition`, Gmail OAuth |
| 3 | FastAPI + WebSocket streaming | `astream_events`, async FastAPI, WebSocket protocol |
| 4 | React Native mobile app | WS hook, streaming state, bottom tab navigation |
