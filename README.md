# Agent Marketplace

A web app that turns purpose-built agents (Sales Lead, Content Research) into
hireable cards. Click a card → chat with the agent → watch it scrape live data
via Apify MCP, scored by GPT, streamed back in real time.

## Stack

- **Backend:** FastAPI + `mcp` + `openai`, WebSocket chat, reuses the existing
  Python agents from `lead_agent.py` and `agent.py` (the originals are kept at
  the repo root as CLI references).
- **Frontend:** React + Vite + TypeScript + Tailwind, dark-mode depth UI.

```
backend/    FastAPI app, refactored agents, MCP session helpers
frontend/   Vite React app, marketplace + chat UI
lead_agent.py / agent.py   Original CLI scripts (unchanged, kept for reference)
```

## Prerequisites

- Python 3.10+ with a virtualenv at `.venv` (already created)
- Node 18+ and npm
- `.env` at the repo root with:
  ```
  OPENAI_API_KEY=sk-...
  APIFY_API_TOKEN=apify_api_...
  ```

## Install

```bash
# Python deps (adds FastAPI + uvicorn + websockets on top of existing)
.venv/bin/pip install -r backend/requirements.txt

# Frontend deps
cd frontend && npm install && cd ..

# Root dev orchestration
npm install
```

## Run

One command starts both servers:

```bash
npm run dev
```

- API → http://localhost:8000 (docs at `/docs`)
- Web → http://localhost:5173

Or run them separately:

```bash
npm run dev:api   # uvicorn on :8000
npm run dev:web   # vite on :5173
```

Vite proxies `/api` and `/ws` to the FastAPI server, so the frontend uses
relative URLs and no CORS headaches.

## Architecture

```
Browser ──HTTP──▶  GET /api/agents          (marketplace cards)
Browser ──WS────▶  /ws/chat/{agent_id}      (chat + streaming events)
Backend ──MCP───▶  mcp.apify.com/sse        (Apify actors)
Backend ──HTTP──▶  api.openai.com           (GPT reasoning + scoring)
```

Each WebSocket connection opens its own Apify MCP session. Events are sent
as JSON objects with a `type` discriminator:
`user_message`, `assistant_message`, `status`, `tool_call`, `tool_result`,
`intent`, `leads_table`, `done`, `error`.

## Adding a new agent

1. Drop a module at `backend/app/agents/<your_agent>.py` exporting:
   ```python
   def new_state() -> dict: ...
   async def run(user_message, session, openai_client, state, emit) -> None: ...
   ```
2. Add an entry to `REGISTRY` in `backend/app/registry.py` with its metadata,
   the Apify actor slugs it needs, and its handler.
3. Add the icon name to the `ICONS` map in
   `frontend/src/components/AgentCard.tsx` if it's not already a Lucide name
   we support.

The card shows up automatically on the marketplace.
