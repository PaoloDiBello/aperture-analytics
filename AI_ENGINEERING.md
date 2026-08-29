# AI Engineering Notes

This document explains the AI design decisions in Aperture Analytics and, honestly,
how a coding agent was used to help build it — and what was reviewed by hand.

It doubles as an engineering artifact: it shows *how* the agent works, why we
chose structured tool calling over raw generation, and how we reasoned about
hallucinations and evaluation.

---

## 1. Product architecture: agent-with-tools, not prompt-only

The core decision was to **not** ship `React → LLM → text`. That approach lets
the model answer from its priors and fabricate numbers. Instead:

```
User question
      │  +
      ▼
compact dataset context (schema, types, sample rows — NOT the full data)
      │
      ▼
┌───────────── agent loop ─────────────┐
│ model picks tool(s) to call           │
│   ▼                                   │
│ ToolExecutor runs a SAFE pandas op    │
│   ▼                                   │
│ real result passed back to the model  │
│   ▼                                   │
│ repeat until the model writes a final │
│ text answer                           │
└───────────────────────────────────────┘
      │
      ▼
answer + (optional) chart spec → UI
```

### Why this is the right shape

1. **Correctness.** The model reasons over real computed values instead of
   inventing them. If the tool returns `Widget B = $35,550`, that number is
   what lands in the answer.
2. **Safety.** The model cannot execute arbitrary Python. Its entire capability
   surface is three whitelisted tools (`analyze_data`, `calculate`, `chart`),
   each with a fixed JSON schema (`backend/app/tools.py`).
3. **Auditability.** Every numeric claim traces back to a tool call with a
   concrete result, which we can log and inspect.

## 2. The safe tool boundary

`backend/app/tools.py` defines the OpenAPI-style `tools` payload. Tools are the
*only* way the model touches data:

| Tool            | Purpose                                            |
| --------------- | -------------------------------------------------- |
| `analyze_data`  | Schema, types, missing values, per-column stats. Called first to understand shape. |
| `calculate`     | `sum`/`mean` grouped by a category, or `top_n` by a numeric column. Returns a small row set. |
| `chart`         | Emits a **serializable chart spec** (type, title, x/y fields, data rows) for Recharts — it does not render. |

Two concrete choices worth noting:

- **Tools, not free-form Python.** `TOOL_DEFINITIONS` + a `ToolExecutor` that
  maps a tool name to a guarded method. A `KeyError` on a bad column returns a
  helpful error to the model ("Column not found. Available columns: …") rather
  than crashing.
- **Chart data passes through the data layer, not the model's imagination.**
  The `chart` tool rebuilds rows from stored columns when `x_field`/`y_field`
  are real columns, so the rendered chart always reflects the dataset.

## 3. Prompt design (the small part)

Prompting is a deliberately *minor* component. `backend/app/agent.py` has one
system prompt and one injected context block. The key structural choices:

- The model is told it **must use tools for any numeric claim** and to say so
  when it can't — not guess.
- It receives a `context_block()` with shape, columns/types, missing values,
  and ~10 sample rows. Enough to plan, too little to hallucinate full rows
  from.
- No chain-of-thought tricks or huge few-shot examples — the tools do the
  heavy lifting, which keeps cost and latency low.

We treat the prompt as configuration that guides tool *selection*, while the
tools guarantee data *correctness*. That split is the real anti-hallucination
mechanism.

## 4. Structured outputs

- **Tool calls** are structured JSON from the model (`tool_calls` array),
  parsed and dispatched by name. Malformed arguments fail safe to `{}`.
- The **`chart` tool returns a structured spec**, so the frontend renders
  whatever the JSON says with no free-form HTML from the model.
- The final **answer** is plain text with light Markdown structure (bullets,
  bold, inline code) that the tiny `Answer.tsx` renderer safely displays.

We stopped short of model-agnostic structured *answer* JSON (e.g. a `{explanation,
numbers[], chart?}` object) in V1 to keep the loop simple — but the chart spec
already points that direction and is listed as a V2 item.

## 5. Hallucination controls (recap)

1. The model never sees the full dataset — only schema + a sample.
2. All numbers must come through tools; the executor returns real values.
3. Bad column names yield explicit, helpful errors.
4. Chart data is rebuilt from stored data rather than trusting model output.
5. The system prompt forbids guessing and invites "I can't compute that."

## 6. Evaluation

V1 evaluation is lightweight and honest:

- **Deterministic tool tests** (`test_tools.py`) — assert correct aggregation,
  chart serialization, and graceful errors, with no network.
- **Fake-LLM agent test** (`test_agent.py`) — proves the full agent loop
  (tool call → execute → answer) works end to end without an API key.
- **Manual spot checks** against `examples/sales.csv` for the three example
  questions; the answers match the ground truth in the data.

A stronger V2 would add golden-set evaluation comparing model answers against
known query→result pairs, and traceability/replay of tool calls.

## 7. How a coding agent helped (the second story)

This project was built with an AI coding agent (opencode). To be transparent
about what was AI-generated vs. hand-reviewed:

**Generated by the agent, then reviewed:**
- MVP scaffolding (project structure, Vite boilerplate, FastAPI skeleton),
  typed API client, CSS, and initial versions of the components/endpoints.
- Draft README, tool schemas, system prompt drafts.

**Chosen/decided by hand (the important architectural calls):**
- The **agent-with-tools** architecture over a prompt-only pipe.
- The **whitelisted tool boundary** and the decision that code (not the model)
  executes data operations.
- The **data-over-model hallucination strategy** (context block, chart rebuilt
  from data).
- Scope discipline — no auth, payments, or database in V1.
- The project's framing/branding and interview narrative.

**Reviewed/corrected by hand:**
- TypeScript strict-mode fixes (type-only imports, `JSX` namespace).
- The local-vs-deployed CORS and env-var split.
- Security/scope calls (in-memory store cap, no arbitrary code execution).

The takeaway: the agent accelerates the *implementation*, but the *reasoning*
about correctness, safety, scope, and architecture is the engineer's job — and
that's the part a technical interviewer actually probes.
