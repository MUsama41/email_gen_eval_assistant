# Email Generation Assistant — Final Plan

> Class-based, modular FastAPI service. Email generation and evaluation are each a **LangGraph multi-agent graph** (multiple nodes → one goal) running on **Groq** models, with **Instructor** for structured output. Ships with 10 scenarios, 3 custom metrics, and a 2×2 model/strategy comparison.

---

## 1. Engineering Conventions (binding)

- **Class-based**: every graph is a class (e.g. `EmailGenerationGraph`); nodes are methods. LLM access, config, reporting are classes too.
- **PEP 8** throughout; LF end-of-line; max line length 100; `snake_case` functions/vars, `PascalCase` classes, `UPPER_SNAKE` constants.
- **Modular**: one responsibility per module; `__init__.py` in every package (proper imports, clean public surface).
- **DRY**: shared behavior (LLM provider, base graph, prompt assembly) lives in one place and is reused — not copied.
- **OCP**: adding a new graph, node, metric, or model must require *extending* (new class/module), not editing existing ones. Achieved via a `BaseGraph`, a metric registry, and config-driven model/strategy selection.
- **No over-engineering**: no speculative abstraction. Build the two graphs the assessment needs; generalize only where DRY/OCP already demand it.
- **No hardcoded values**: model names, temperatures, thresholds, paths, word-count bands, scenario count → `configuration.py` (typed settings) sourced from `.env`. No magic literals in graph/metric code.
- **No catch-all shared files**: there is **no** root `llm.py`, `prompts.py`, or `pydantic_schemas.py`. Each graph owns its own `prompts/` and `schemas.py`; cross-cutting infra lives in `core/` as named classes.

---

## 2. Prompt Conventions (binding)

Advanced technique = **Role-Playing + Few-Shot + Chain-of-Thought**, realized across graph nodes.

**System prompt** — holds *all* instructions. Structure, in this order, using Markdown:
```
## Context        — who the model is (role-play) + task framing
## Scope          — In scope / Out of scope (bullets)
## Steps          — ordered steps the model follows (CoT)
## Output         — exact output contract; escape literal JSON with {{ }}
### Example       — few-shot example(s); literal braces escaped as {{ }}
```
Rules:
- Clean and concise — **no verbose or repetitive statements**.
- Refers to inputs **by name** (the keys supplied by the human prompt).
- Any literal `{` / `}` in examples or the output contract is escaped as `{{` / `}}` (LangChain template safety).

**Human prompt** — **inputs only**, no instructions:
```python
VALIDATE_INPUT_HUMAN_PROMPT = """
Intent:
{intent}

Key facts:
{key_facts}

Tone:
{tone}
"""
```

**Example (system-prompt few-shot block, braces escaped):**
```
### Example
**intent:** "Follow up after a meeting"
**key_facts:** ["Discussed Q3 roadmap", "Next sync on Friday"]
**tone:** "formal"
**Output:**
{{
  "subject": "Follow-up: Q3 Roadmap Discussion",
  "body": "Dear ...",
  "is_valid": true
}}
```

---

## 3. Architecture

### 3.1 Concepts (mirrors the reference project)
- **Client** = `email_assistant` (the domain unit) holding all graphs under `ai_client/`.
- **Graph** = a `StateGraph` subclass with **many nodes → one goal**. Each node: build prompt → run `prompt_tmpl | get_llm()` chain → return state delta.
- **Structured output**: Groq has no native structured output → nodes use **Instructor** with a Pydantic `response_model`; the chain returns a validated object.

### 3.2 The two graphs
| Graph | Goal | Nodes (multiple → one goal) |
|-------|------|------------------------------|
| `email_generation` | (intent, facts, tone) → finished email | `validate_input → plan_outline (CoT) → draft → self_critique → revise → finalize` |
| `evaluation` | score one email on the 3 metrics | `judge_fact_recall → judge_tone → score_fluency → aggregate` |

### 3.3 OCP seams (where extension happens without edits)
- **`BaseGraph`** (`core/`): owns graph compilation, the `get_llm()` chain helper, and prompt-template assembly. New graphs subclass it.
- **`LLMProvider`** (`core/`): wraps the Instructor-patched Groq client; `get_llm(model_name)` selects any configured model. Adding a model = config only.
- **Strategy switch**: `advanced` vs `baseline` is a config flag the `email_generation` graph reads to pick the draft prompt and skip/keep the critique loop — same graph, no fork.
- **Metric registry** (`evaluation`): metrics register themselves; adding a 4th metric = new node module, no edits to the runner.

---

## 4. Schemas — two distinct layers

1. **Route schemas** (`schemas/` at project root) — FastAPI request/response models (HTTP boundary). E.g. `GenerateEmailRequest`, `GenerateEmailResponse`, `EvaluateRequest`, `EvaluateResponse`.
2. **Graph schemas** (`<graph>/schemas.py`) — internal node `response_model`s (e.g. `DraftParser`, `FactRecallParser`). Never exposed over HTTP directly.

This keeps the API contract decoupled from internal LLM-parsing models (DRY boundary, clean OCP — change a node's parser without touching the API).

---

## 5. Modules

| Module | Responsibility | Key files |
|--------|----------------|-----------|
| **Config** | Typed settings from `.env`; no literals elsewhere | `core/configuration.py` |
| **LLM provider** | Instructor-patched Groq, `get_llm(model_name)` | `core/llm_provider.py` |
| **Base graph** | Shared compile + chain + prompt helpers | `core/base_graph.py` |
| **Email-gen graph** | The 6-node generation flow | `email_assistant/ai_client/email_generation/*` |
| **Evaluation graph** | 3 metric nodes + aggregate | `email_assistant/ai_client/evaluation/*` |
| **Route schemas** | HTTP request/response models | `schemas/*` |
| **API** | FastAPI routers/endpoints | `app/main.py`, `app/routers/*` |
| **Runner** | Drive 10 scenarios through both graphs | `app/services/evaluation_runner.py` |
| **Comparison** | 2×2 grid (2 models × 2 strategies) | `app/services/comparison.py` |
| **Reporting** | CSV/JSON: defs + raw scores + averages | `app/services/report_writer.py` |
| **Test data** | 10 scenarios + references | `data/*` |

---

## 6. The 3 Custom Metrics (evaluation-graph nodes)

Each node returns a normalized score (scale fixed in config), tailored to email generation.

1. **Fact Recall & Faithfulness** — LLM-as-Judge: each key fact `covered / total`, penalize fabrication. *(Fact Recall / Specificity)*
2. **Tone Accuracy** — LLM-as-Judge classifies tone + rates alignment; optional lexical cross-check. *(Tone Accuracy)*
3. **Conciseness & Fluency** — Hybrid: deterministic Python (word-count band, filler/redundancy, readability) + LLM-as-Judge fluency. *(Conciseness / Grammar / Fluency)*

> Mixes deterministic Python (3) + LLM-as-Judge (1, 2) → "combination of automated techniques." Judge temperature from config (0 for reproducibility). Word-count band, filler list, weights all live in config.

---

## 7. Evaluation & Comparison Strategy

**Matrix:** 2 Groq models × {advanced, baseline} × 10 scenarios × 3 metrics.

1. Load 10 scenarios (`data/scenarios.json`).
2. For each (model, strategy): run `email_generation` → 10 emails.
3. Run `evaluation` on each email → 3 metric scores.
4. Write raw scores + per-metric & overall averages → CSV + JSON (one block per combo).
5. Diff → comparison table + analysis (winner / loser's biggest failure mode / production recommendation, justified by metric data).

**Free-tier control:** cache graph outputs keyed by `model+strategy+scenario`; sequential calls with light backoff.

---

## 8. Testing

| Layer | Test | How |
|-------|------|-----|
| Unit | Config loads; missing env fails fast | pytest |
| Unit | Per-node prompt assembly; Instructor parsing | pytest, mocked Groq |
| Unit | Each metric node → valid normalized score; edge/empty input | pytest |
| Graph | `email_generation` reaches `finalize` on a fixture | pytest, recorded responses |
| Graph | `evaluation` aggregates 3 metrics correctly | pytest |
| API | `/generate` and `/evaluate` return route schemas | FastAPI TestClient |
| Smoke | Full 2×2 run completes | manual / CI |
| Sanity | Perfect-recall email ≈ max; empty email ≈ 0 on Metric 1 | fixture asserts |

---

## 9. Repo Layout

```
email_gen_assistant/
├── README.md
├── requirements.txt
├── .env.example                         # GROQ_API_KEY, model ids, temps, bands
├── pyproject.toml / setup.cfg           # PEP 8 / flake8 / line length config
├── data/
│   ├── scenarios.json                   # 10 scenarios
│   └── references/ref_01.txt … ref_10.txt
├── results/                             # generated CSV/JSON
├── report/REPORT.md                     # final report → PDF
├── schemas/                             # === ROUTE input/output schemas ===
│   ├── __init__.py
│   ├── generation.py                    # GenerateEmailRequest / Response
│   └── evaluation.py                    # EvaluateRequest / Response
├── core/                                # === cross-cutting infra (named classes) ===
│   ├── __init__.py
│   ├── configuration.py                 # Settings (env-sourced, typed) — no literals elsewhere
│   ├── llm_provider.py                  # LLMProvider.get_llm(model_name) — Instructor + Groq
│   └── base_graph.py                    # BaseGraph: compile + chain + prompt helpers
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI app
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── generation.py                # POST /generate
│   │   └── evaluation.py                # POST /evaluate
│   └── services/
│       ├── __init__.py
│       ├── evaluation_runner.py         # 10 scenarios → both graphs
│       ├── comparison.py                # 2×2 grid
│       └── report_writer.py             # CSV/JSON serialization
└── email_assistant/                     # === the client ===
    ├── __init__.py
    ├── utils.py                         # single file unless helpers grow → utils/
    └── ai_client/
        ├── __init__.py
        ├── email_generation/            # === graph 1 ===
        │   ├── __init__.py
        │   ├── graph.py                 # class EmailGenerationGraph(BaseGraph)
        │   ├── state.py                 # EmailGenerationState (TypedDict)
        │   ├── schemas.py               # node response_models (DraftParser, …)
        │   └── prompts/                 # one module per node
        │       ├── __init__.py
        │       ├── validate_input.py
        │       ├── plan_outline.py
        │       ├── draft.py
        │       ├── critique.py
        │       └── finalize.py
        └── evaluation/                  # === graph 2 ===
            ├── __init__.py
            ├── graph.py                 # class EvaluationGraph(BaseGraph)
            ├── state.py
            ├── schemas.py               # FactRecallParser, ToneParser, FluencyParser
            └── prompts/
                ├── __init__.py
                ├── judge_fact_recall.py
                ├── judge_tone.py
                └── judge_fluency.py
```

> Note: the previously proposed root `llm.py`, `prompts.py`, `pydantic_schemas.py` are **removed**. Their concerns move to `core/` (named classes) and per-graph files. No shared catch-all modules.

---

## 10. Build Order

1. **Foundation** — `core/configuration.py`, `core/llm_provider.py` (Instructor+Groq), `core/base_graph.py`; package `__init__.py`s; PEP 8 tooling.
2. **`email_generation` graph** — `state.py`, `schemas.py`, per-node `prompts/`, `graph.py`; advanced + baseline via config.
3. **Test data** — 10 scenarios + reference emails.
4. **`evaluation` graph** — 3 metric nodes + aggregate; deterministic helpers in `utils.py`.
5. **Services** — `evaluation_runner`, `report_writer` (cache + CSV/JSON).
6. **Comparison** — 2×2 grid + analysis.
7. **API + docs** — routers, route schemas, README, final report → PDF.

---

## 11. Configuration Keys (`.env` → `configuration.py`)

| Key | Purpose |
|-----|---------|
| `GROQ_API_KEY` | Auth |
| `MODEL_A`, `MODEL_B` | The two Groq models (free tier) |
| `JUDGE_MODEL` | LLM-as-Judge model |
| `GEN_TEMPERATURE`, `JUDGE_TEMPERATURE` | Sampling (judge = 0) |
| `SCORE_SCALE` | `0-1` or `0-100` |
| `CONCISENESS_MIN_WORDS`, `CONCISENESS_MAX_WORDS` | Metric 3 band |
| `METRIC_WEIGHTS` | Overall-score weighting |
| `DATA_DIR`, `RESULTS_DIR`, `CACHE_DIR` | Paths |

---

## 12. Decisions

**Locked:** Groq free models · Instructor for structured output · LangGraph (class-based graphs) · FastAPI · class-based + PEP 8 + DRY/OCP · route schemas in root `schemas/` · cross-cutting infra in `core/` (no catch-all files) · 2×2 comparison · all values via config/env.

**Pick at build time:** the two Groq model IDs · judge model · score scale (`0-1` vs `0-100`).
