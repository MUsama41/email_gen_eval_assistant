# Email Generation Assistant

Generates professional emails from structured input (intent, key facts, tone)
using LangGraph graphs, with a custom evaluation suite and a 2x2
model/strategy comparison.

Structured output is enforced with Instructor. The HTTP layer is FastAPI.
LangSmith tracing is optional.

## Architecture

The `email_assistant` client holds two LangGraph graphs.

Email generation:

```
validate_input -> plan_outline -> draft -> self_critique -> revise -> package
```

The advanced strategy uses a role-play system prompt, a few-shot example in the
draft node, a chain-of-thought plan_outline node, and a self_critique/revise
loop. The baseline strategy uses a zero-shot draft prompt and skips the critique
loop, so the same graph runs both and the comparison is fair.

Evaluation:

```
judge_fact_recall -> judge_tone -> score_fluency -> aggregate
```

Each node implements one custom metric; aggregate produces the weighted overall
score.

## Custom metrics

| Metric | Focus | Logic |
|--------|-------|-------|
| Fact Recall & Faithfulness | Fact recall / specificity | LLM judge counts covered key facts (paraphrase allowed) and flags fabrication. covered/total, x0.7 if fabrication detected. |
| Tone Accuracy | Tone accuracy | LLM judge detects the conveyed tone and rates alignment with the requested tone (0-1). |
| Conciseness & Fluency | Conciseness / grammar / fluency | Deterministic Python (word-count band + filler penalty) combined with an LLM judge grammar score. |

The metrics mix deterministic Python with LLM-as-judge. The judge runs at
temperature 0.

## Layout

```
backend/
  app/            FastAPI app, routers, services, schemas
  core/           configuration, llm_provider, base_graph
  email_assistant/
    utils.py      deterministic metric helpers
    ai_client/
      email_generation/   graph.py, state.py, schemas.py, prompts/
      evaluation/         graph.py, state.py, schemas.py, prompts/
  data/scenarios.json     10 scenarios + reference emails
  results/                generated CSV/JSON
  tests/                  pytest, no API calls
  run_comparison.py       runs the full 2x2 evaluation
```

## Setup

Python 3.10+.

```
python -m venv myenv
myenv\Scripts\activate          # Windows
source myenv/bin/activate       # macOS/Linux

pip install -r backend/requirements.txt
cp .env.example .env            # then add your API keys
```

Models are named `provider:model_id`. Supported providers: `groq`, `gemini`,
`cerebras`, `openrouter`. Set the matching `<PROVIDER>_API_KEY` in `.env`. All
models, temperatures, weights, score scale, and word bands are read from `.env`.

The defaults in `.env.example` run on Cerebras:

| Role | Model |
|------|-------|
| Model A | `cerebras:gpt-oss-120b` |
| Model B | `cerebras:zai-glm-4.7` |
| Judge | `cerebras:gpt-oss-120b` |

## Running

Three ways to run — pick whichever fits.

### Option 1 — Docker (full stack)

Starts the API on port 8000 and the frontend UI on port 3000.

```
docker-compose up --build
```

- Frontend: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`

### Option 2 — Docker (backend only)

Useful for Swagger testing without the frontend container.

```
docker-compose up api
```

API docs at `http://localhost:8000/docs`.

### Option 3 — Local venv

```
cd backend
uvicorn app.main:app --reload
```

API docs at `http://127.0.0.1:8000/docs`.

---

### API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/generate` | Generate an email |
| POST | `/evaluate` | Score an email against 3 metrics |
| POST | `/comparison` | Run the full 2×2 evaluation matrix |
| GET  | `/health` | Health check |

Example generate call:

```
curl -X POST http://127.0.0.1:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"intent": "Follow up after a client meeting",
       "key_facts": ["Discussed Q3 roadmap", "Next sync Friday 10 AM"],
       "tone": "formal", "strategy": "advanced"}'
```

### Running the comparison

Via the UI — open the **Run Comparison** tab and click the button.

Via the API — `POST /comparison` (returns JSON when complete).

Via the CLI:

```
cd backend
python run_comparison.py
```

Outputs in `backend/results/`:

- `eval_<model>_<strategy>.csv` — raw per-scenario scores
- `eval_<model>_<strategy>.json` — metric definitions, raw scores, averages
- `comparison.csv` — averages for all four combos

Each scored scenario is cached in `.cache/` (keyed by model, strategy, and
scenario). Re-runs reuse cached results and skip API calls. If a provider's
daily token limit is hit, the run writes what completed and stops; re-run after
the limit resets to continue. Cerebras per-minute 429s are retried automatically
— expect ~5-10 minutes on a cold run.

### Tests (no API key needed)

```
cd backend
pytest
```
