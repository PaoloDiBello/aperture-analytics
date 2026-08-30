# Aperture Analytics

**Ask anything. It sees into your data.** Ask natural-language questions about
a CSV, answered by a tool-using AI agent.

Upload a CSV on a clean landing page, then ask questions in the workspace — like
"Which product generated the most revenue?" or "Why did revenue drop in March?"
A frontend-friendly agent decides which tools to call, runs real calculations on
your data, and answers with *evidence, not guesses*.

```
┌──────────────┐      ┌──────────────┐      ┌──────────────────────┐
│    React     │ ───▶ │   FastAPI    │ ───▶ │     AI Agent         │
│  TypeScript  │      │    (API)     │      │  (route / context)   │
└──────┬───────┘      └──────┬───────┘      └──────────┬───────────┘
       │                     │                          │
       │                     └──────────────┐           │  model picks tools
       ▼                                    ▼           ▼
  Chart rendering                 ┌────────────────────────────┐
  (Recharts)                      │  analyze_data  calculate   │
                                  │        chart               │
                                  └────────────────────────────┘
```

The headline isn't "an AI chatbot." It's an **agent loop**: the model receives
a compact dataset context, decides which whitelisted tools it needs, and our
code (not the model) performs the actual data work. The model can only compute
via tools — it can't invent numbers.

---

## Why this is an engineering project (not just a prompt)

This deliberately avoids the naive `React → LLM → text` pipe. The interesting
parts are infrastructure, not prompt-writing:

- **Tool calling** — the model emits structured function calls; a `ToolExecutor`
  maps them to safe, guarded pandas operations.
- **Agent loop** — messages round-trip between the model and the tool executor
  until the model produces a final answer (see `backend/app/agent.py`).
- **Structured / safe tool boundary** — the AI cannot run arbitrary Python. It
  can only call `analyze_data`, `calculate`, and `chart`, each with a fixed
  OpenAPI schema (`backend/app/tools.py`).
- **Anti-hallucination by construction** — the model never sees raw full data.
  It sees schema/sample context and must use tools to get real numbers, which
  are passed back for the answer.
- **Serializable chart specs** — the `chart` tool returns a JSON spec the
  frontend renders with Recharts, keeping AI output and UI decoupled.

See [`AI_ENGINEERING.md`](./AI_ENGINEERING.md) for the full design notes,
prompt/tool definitions, and what was done by the coding agent vs. hand-written.

---

## Tech stack

| Layer      | Choice                                                |
| ---------- | ----------------------------------------------------- |
| Frontend   | React 19 + TypeScript + Vite                          |
| Styling    | Tailwind CSS v4 + shadcn-style primitives (`src/ui`)  |
| Charts     | Recharts                                              |
| Backend    | Python + FastAPI                                      |
| Data       | Pandas (wrapped behind a small `Dataframe` abstraction) |
| AI         | OpenAI-compatible chat + tool calling via OpenRouter  |
| Deploy     | Frontend → Vercel · Backend → Railway                 |

---

## Project structure

```
aperture-analytics/
├── frontend/                 # React + Vite (Tailwind v4)
│   └── src/
│       ├── App.tsx           # landing (upload) + workspace (chat) orchestration
│       ├── api.ts            # typed API client
│       ├── types.ts          # shared response/preview types
│       ├── lib/utils.ts      # cn() class-merge helper
│       ├── components/
│       │   └── Answer.tsx    # safe, tiny markdown-lite renderer for answers
│       └── ui/               # shadcn-style primitives
│           ├── badge.tsx
│           ├── button.tsx
│           ├── card.tsx
│           ├── input.tsx
│           └── separator.tsx
├── backend/                  # FastAPI
│   └── app/
│       ├── main.py           # app + CORS + routers
│       ├── config.py         # settings (OpenRouter, CORS origins)
│       ├── frame.py          # Dataframe wrapper (safe data ops)
│       ├── store.py          # in-memory dataset store (V1)
│       ├── tools.py          # tool schemas + ToolExecutor
│       ├── agent.py          # agent loop + prompt
│       ├── llm.py            # OpenRouter client (tool calling, retries)
│       └── api/
│           ├── upload.py     # POST /api/upload
│           └── query.py      # POST /api/query
└── examples/sales.csv        # sample dataset to try
```

---

## Getting started

### Backend

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate        # Windows
#  source .venv/bin/activate    # macOS/Linux
pip install -r requirements.txt
```

Set your OpenRouter API key:

```bash
cp .env.example .env
# edit .env → OPENROUTER_API_KEY=...
```

The default model is `openai/gpt-4o-mini` (reliable tool calling). Free models
sometimes work but are frequently rate-limited; set `OPENROUTER_MODEL` to any
OpenRouter model id if you'd like to try others.

Run the API:

```bash
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local      # VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

Open `http://localhost:5173`, drag & drop or choose `examples/sales.csv`, then
ask a question in the assistant panel.

---

## API

| Method | Endpoint      | Body                                             | Returns           |
| ------ | ------------- | ------------------------------------------------ | ----------------- |
| POST   | `/api/upload` | multipart `file` (CSV)                           | `dataset_id` + preview |
| POST   | `/api/query`  | `{ "dataset_id", "question" }`                   | `{ "answer" }`    |
| GET    | `/api/health` | —                                                | `{ "status": "ok" }` |

---

## Try it

Upload `examples/sales.csv` and ask:

- "Which product generated the most revenue?"
- "Show me the top products by profit."
- "Why did revenue drop in March?"
- "What is the average revenue per month?"

---

## Deploying

### Backend → Railway

1. Push the `backend/` folder to a Railway service (or connect the monorepo
   path `aperture-analytics/backend`).
2. Add environment variables: `OPENROUTER_API_KEY`, `CORS_ORIGINS` (your
   deployed frontend URL), `OPENROUTER_MODEL` (optional).
3. Railway uses `backend/railway.toml` (uvicorn, port from `$PORT`).

### Frontend → Vercel

1. Import the `frontend/` directory as a Vite project (or set root to it).
2. Add env var `VITE_API_BASE_URL` = your Railway URL.
3. Deploy — Vercel runs `npm run build` and serves `dist` (see `frontend/vercel.json`).

---

## Tests

```bash
cd backend
.\.venv\Scripts\python -m test_tools   # tool executor sanity (no network)
.\.venv\Scripts\python -m test_agent   # agent loop with stubbed LLM (no network)
```

The frontend build (which runs `tsc` type-checking) can be verified with:

```bash
cd frontend
npm run build
```

---

## Roadmap / V2 ideas

- True token streaming from the model to the UI.
- Excel/XLSX upload.
- Referenced chart rendering directly in chat (the `chart` tool already emits a
  spec — expose it).
- Persistence instead of the in-memory store.
- Auth, teams, saved datasets.

## License

MIT — see `LICENSE`.
