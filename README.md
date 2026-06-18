# Email Generation Assistant

A working prototype that generates professional emails from structured input (Intent, Key Facts, Tone) using **LangGraph multi-agent graphs** running on **Groq** models, with a custom evaluation suite and a 2×2 model/strategy comparison.

Structured output is enforced with **Instructor** (Groq has no native structured-output API). Tracing is wired through **LangSmith**. The HTTP layer is **FastAPI**.

---

## Architecture

The system is built as a **client** (`email_assistant`) containing two **LangGraph** graphs, each with multiple nodes leading to one goal.

### Graph 1 — Email Generation (`email_generation`)

```
validate_input -> plan_outline -> draft -> self_critique -> revise -> package
```

The advanced prompting technique is structural: a **role-play** system prompt, **few-shot** examples in the draft node, a **chain-of-thought** `plan_outline` node, and a `self_critique -> revise` loop. The `baseline` strategy uses a zero-shot draft prompt and skips the critique loop, enabling a fair prompt-strategy comparison.

### Graph 2 — Evaluation (`evaluation`)

```
judge_fact_recall -> judge_tone -> score_fluency -> aggregate
```

Each node implements one custom metric; `aggregate` produces the weighted overall score.

---

## Custom Metrics

| Metric | Focus | Logic |
|--------|-------|-------|
| **Fact Recall & Faithfulness** | Fact Recall / Specificity | LLM-as-Judge counts accurately covered key facts (paraphrase allowed) and penalizes fabrication. `covered / total`, × 0.7 if fabrication detected. |
| **Tone Accuracy** | Tone Accuracy | LLM-as-Judge detects the conveyed tone and rates alignment with the requested tone (0–1). |
| **Conciseness & Fluency** | Conciseness / Grammar / Fluency | Hybrid: deterministic Python (word-count band + filler penalty) combined with an LLM-as-Judge grammar score. |

The metrics deliberately mix deterministic Python with LLM-as-Judge to satisfy the "combination of automated techniques" requirement. The judge runs at temperature 0 for reproducibility.

---

## Project Layout

```
email_gen_assistant/
├── app/                        FastAPI app, routers, services
│   ├── main.py
│   ├── dependencies.py
│   ├── routers/                /generate, /evaluate
│   └── services/               runner, comparison, report_writer, metric_definitions
├── core/                       configuration, llm_provider, base_graph
├── email_assistant/            the client
│   ├── utils.py                deterministic metric helpers
│   └── ai_client/
│       ├── email_generation/   graph.py, state.py, schemas.py, prompts/
│       └── evaluation/         graph.py, state.py, schemas.py, prompts/
├── schemas/                    HTTP request/response models
├── data/scenarios.json         10 scenarios + reference emails
├── results/                    generated CSV/JSON
├── tests/                      pytest (no API calls)
└── run_comparison.py           runs the full 2×2 evaluation
```

---

## Setup

Requires Python 3.10+.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env   # then edit .env with your keys
```

Set in `.env`:

- `GROQ_API_KEY` — required.
- `LANGSMITH_API_KEY` — optional; set `LANGSMITH_TRACING=true` to enable tracing.

Default models (all current Groq production models, free-tier accessible):

| Role | Model |
|------|-------|
| Model A (generation) | `llama-3.3-70b-versatile` |
| Model B (generation) | `llama-3.1-8b-instant` |
| Judge | `openai/gpt-oss-120b` |

All models, temperatures, score scale, word bands, and weights are configurable via `.env` — no values are hardcoded.

---

## Running

### API server

```bash
uvicorn app.main:app --reload
```

Then open `http://127.0.0.1:8000/docs`.

Generate an email:

```bash
curl -X POST http://127.0.0.1:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
        "intent": "Follow up after a client meeting",
        "key_facts": ["Discussed Q3 roadmap", "Next sync Friday 10 AM"],
        "tone": "formal",
        "strategy": "advanced"
      }'
```

### Full evaluation and comparison

Runs all 10 scenarios across 2 models × 2 strategies, writes per-combo CSV/JSON plus a comparison file, and prints the winner:

```bash
python run_comparison.py
```

Outputs land in `results/`:

- `eval_<model>_<strategy>.csv` — raw per-scenario scores.
- `eval_<model>_<strategy>.json` — metric definitions + raw scores + averages.
- `comparison.csv` — side-by-side averages for all four combos.

Generations are cached in `.cache/` keyed by model + strategy + scenario, so re-runs do not re-call the API.

### Tests

```bash
pytest
```

Tests use a fake LLM and run with no API calls.
