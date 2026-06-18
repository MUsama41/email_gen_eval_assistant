# Email Generation Assistant — Project Breakdown

> Working prototype that generates professional emails from structured input (Intent + Key Facts + Tone) using **LangGraph multi-agent graphs** on **Groq** models, served via **FastAPI**, with a custom evaluation suite and a 2×2 model/strategy comparison.

---

## 0. Requirements Coverage Map

Every assessment requirement mapped to where it is delivered. Nothing is dropped.

| # | Requirement | Module | Deliverable |
|---|-------------|--------|-------------|
| 1.A | Take 3 inputs (Intent, Facts, Tone) → professional email | M1 Email-Gen Client (graph) | `email_assistant/ai_client/email_generation/graph.py` |
| 1.B | Advanced prompting technique (documented) | M2 Prompting | per-node `prompts.py` + report |
| 2.A | 10 scenarios + 10 human reference emails | M3 Test Data | `data/scenarios.json` |
| 2.B | 3 custom metrics (defined + implemented) | M4 Evaluation Client (graph) | `email_assistant/ai_client/evaluation/` |
| 2.C | Structured output: metric defs + raw scores + averages | M5 Reporting | `results/*.csv` / `*.json` |
| 3 | Run 2 models × 2 strategies on same scenarios + analysis | M6 Comparison | `compare.py` + analysis |
| D | GitHub repo + README | M7 Packaging | `README.md` |
| D | Final report (prompt, metrics, raw data, analysis) | M7 Packaging | `report/REPORT.md` → PDF |

---

## 1. Architecture — LangGraph Multi-Agent, per-Client

**Stack:** Python 3.10+ · **FastAPI** (HTTP layer) · **LangGraph** (`StateGraph`) · **Groq** models · **Instructor** (structured output — Groq has no native `with_structured_output`) · `pytest` · pandas/csv.

### Core concepts (mirrors the Django reference)
- **Client** = a self-contained domain unit. It owns one or more **graphs**.
- **Graph** = a `StateGraph` with **multiple nodes → one goal**. Each node is a method that builds a prompt, invokes a chain, and returns a state delta.
- **Node call pattern** = `prompt_tmpl | get_llm()` chain, `.invoke({...})`. Structured nodes route through Instructor (see §1.3).

### 1.1 Folder rules (carried over from the reference screenshot)
- One **folder per client**; one **subfolder per graph** inside the client's `ai_client/`.
- Each graph folder contains exactly: `graph.py`, `state.py`, `pydantic_schemas.py`, and a `prompts/` package.
- **`prompts/` holds one `*.py` per node** (e.g. `prompts/draft.py`, `prompts/critique.py`) — not one giant prompts file.
- Schemas shared across graphs live at the **client root** (`ai_client/pydantic_schemas.py`, `ai_client/prompts.py`); graph-specific ones live in the graph folder.
- **Utils:** single `utils.py` per client by default; promote to a `utils/` folder **only if** helpers span multiple files.

### 1.2 The two graphs (= two clients' goals)
| Graph | Goal | Key nodes (multiple → one goal) |
|-------|------|---------------------------------|
| **email_generation** | Turn (intent, facts, tone) into a finished email | `validate_input → plan_outline (CoT) → draft → self_critique → revise → finalize` |
| **evaluation** | Score one email against the 3 custom metrics | `judge_fact_recall → judge_tone → score_conciseness_fluency → aggregate` |

> The **advanced prompting technique is structural**: Role-Play system prompt + Few-Shot examples + an explicit Chain-of-Thought `plan_outline` node + a `self_critique → revise` loop. This is the agentic multi-node behavior, not a single prompt.

### 1.3 Structured output via Instructor (Groq has none natively)
- Wrap the Groq client with `instructor.from_openai(...)` / `instructor.patch(...)` so each node can request a Pydantic `response_model`.
- Node chain shape:
  ```python
  prompt = build_prompt(...)            # per-node prompts/<node>.py
  prompt_tmpl = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("user", "{input}")])
  chain = prompt_tmpl | get_llm()       # get_llm() returns the Instructor-patched Groq client
  result = chain.invoke({"input": prompt})   # result is a validated Pydantic object
  ```
- `get_llm()` lives in a shared client wrapper; it takes `model_name` so the same graph runs on either Groq model (needed for the 2×2 comparison).

---

## 2. Modules

### M1 — Email-Generation Client (the core graph)
- Inputs: `{ intent: str, key_facts: list[str], tone: str }`. Output: subject + body (validated Pydantic).
- Nodes per §1.2; each node = prompt build → Instructor chain → state delta.
- **Files:** `email_generation/{graph.py, state.py, pydantic_schemas.py}`, `email_generation/prompts/*.py`.

### M2 — Prompt Engineering
- One `prompts/<node>.py` per node (system + human templates). Houses Role-Play / Few-Shot / CoT (see §4).
- **Strategy B (baseline)** = a zero-shot variant of the draft prompt, toggled by config so the *same graph* runs both strategies.

### M3 — Test Data
- 10 unique scenarios (varied intent/tone) + 1 human reference email each.
- **Files:** `data/scenarios.json`, `data/references/ref_01.txt … ref_10.txt`.

### M4 — Evaluation Client (the metrics graph)
- A second graph whose nodes implement the 3 custom metrics (LLM-as-Judge nodes + a deterministic Python node), then aggregate.
- **Files:** `evaluation/{graph.py, state.py, pydantic_schemas.py}`, `evaluation/prompts/*.py`, plus deterministic helpers in client `utils.py`.

### M5 — Reporting
- Serializes metric definitions, per-scenario raw scores, per-metric & overall averages → CSV + JSON.
- **Files:** `app/report.py`, `results/eval_<model>_<strategy>.csv|json`.

### M6 — Model / Strategy Comparison (2×2 grid)
- Runs the identical evaluation across **2 Groq models × {advanced, baseline} = 4 runs**; side-by-side data + written analysis.
- **Files:** `app/compare.py`, `results/comparison.csv`, `report/analysis.md`.

### M7 — Packaging & Docs
- FastAPI entrypoint, README (setup + run), `.env.example` (`GROQ_API_KEY`), `requirements.txt`, final report → PDF.

---

## 3. The 3 Custom Metrics (implemented as evaluation-graph nodes)

Each returns a normalized score, is computed automatically, and is tailored to email generation. One per required focus area.

### Metric 1 — **Fact Recall & Faithfulness** *(Fact Recall / Specificity)*
- Did the email include *all* key facts, accurately, without inventing facts?
- **Node:** LLM-as-Judge (Instructor → Pydantic) cross-checks each key fact → `covered / total`, penalize fabrication.

### Metric 2 — **Tone Accuracy** *(Tone Accuracy / Format Adherence)*
- Does the style match the requested tone (formal/casual/urgent/empathetic)?
- **Node:** LLM-as-Judge classifies tone + rates alignment; optional lexical cross-check (formality/exclamation/hedging counts).

### Metric 3 — **Conciseness & Fluency** *(Conciseness / Grammar / Fluency)*
- Is the email tight, well-structured, grammatically clean — no padding?
- **Node:** Hybrid — deterministic Python (word-count band, filler/redundancy, readability) **+** LLM-as-Judge fluency, combined.

> **Design note:** metrics mix deterministic Python (Metric 3) with LLM-as-Judge (1, 2) to satisfy "combination of automated techniques." Judge at **temperature 0** for reproducibility.

---

## 4. Advanced Prompting Technique

**Strategy A: Role-Playing + Few-Shot + Chain-of-Thought, realized across graph nodes.**
- **Role-Play:** system prompt casts the model as an expert executive communications assistant.
- **Few-Shot:** 2–3 curated (input → ideal email) examples in the `draft` node prompt.
- **Chain-of-Thought:** dedicated `plan_outline` node maps intent/facts/tone before drafting; `self_critique → revise` loop improves fact coverage and tone fit. Internal reasoning suppressed from final output.

**Strategy B (baseline): zero-shot** — single draft instruction, no role/examples/CoT/critique. Same graph, prompt variant selected by config.

---

## 5. Evaluation Strategy

**Run matrix:** 2 Groq models × 2 strategies × 10 scenarios × 3 metrics.

1. Load 10 scenarios.
2. For each (model, strategy) combo: run the **email_generation** graph → 10 emails.
3. Run the **evaluation** graph on each email → Metrics 1–3.
4. Persist raw scores + per-metric & overall averages → CSV/JSON (one block per combo).
5. Diff results → comparison table + analysis.

**Report must contain (brief 2.C):** metric definitions/logic, raw scores for all 10 × 3 (per combo), overall averages.

> **Free-tier cost control:** judge calls also hit Groq. **Cache graph outputs to disk** (keyed by model+strategy+scenario) so re-runs don't re-call; run sequentially with light backoff to respect rate limits.

---

## 6. Testing

| Layer | What to test | How |
|-------|--------------|-----|
| Unit | Input validation, per-node prompt assembly, Instructor parsing | pytest, mocked Groq |
| Unit | Each metric node returns valid normalized score; edge/empty input | pytest |
| Graph | `email_generation` graph reaches `finalize` on a fixture scenario | pytest, recorded responses |
| Graph | `evaluation` graph aggregates 3 metrics correctly | pytest |
| Smoke | Full 2×2 run completes without crashing | manual / CI |
| Determinism | Judge at temp 0 → stable scores on rerun | spot-check |
| Sanity | Perfect-recall email ≈1.0; empty email ≈0 on Metric 1 | fixture asserts |

---

## 7. Deliverables Checklist

- [ ] **Code repo (GitHub)** — FastAPI + LangGraph clients, runnable.
- [ ] **README** — setup (env, deps, `GROQ_API_KEY`), how to run API / evaluate / compare.
- [ ] **`scenarios.json`** — 10 scenarios + references.
- [ ] **3 metric implementations** — evaluation-graph nodes, defined + coded.
- [ ] **`results/` exports** — CSV + JSON with defs, raw scores, averages (all 4 combos).
- [ ] **Final report (PDF/Doc)**: prompt template · 3 metric defs+logic · raw data · comparative analysis (winner / loser's biggest failure mode / production recommendation, justified by metric data).

---

## 8. Proposed Repo Layout (per-client, mirrors reference)

```
email_gen_assistant/
├── README.md
├── requirements.txt
├── .env.example                      # GROQ_API_KEY
├── data/
│   ├── scenarios.json
│   └── references/ref_01.txt … ref_10.txt
├── results/                          # generated CSV/JSON
├── report/REPORT.md                  # final report → PDF
├── app/
│   ├── main.py                       # FastAPI entrypoint
│   ├── evaluate.py                   # drives evaluation graph over scenarios
│   ├── compare.py                    # 2×2 grid runner
│   └── report.py                     # CSV/JSON serialization
└── email_assistant/                  # === the client ===
    ├── ai_client/
    │   ├── llm.py                     # get_llm(model_name) — Instructor-patched Groq
    │   ├── prompts.py                 # shared/cross-graph prompts (if any)
    │   ├── pydantic_schemas.py        # shared/cross-graph schemas (if any)
    │   ├── email_generation/          # === graph 1 (one goal) ===
    │   │   ├── graph.py
    │   │   ├── state.py
    │   │   ├── pydantic_schemas.py
    │   │   └── prompts/
    │   │       ├── validate_input.py
    │   │       ├── plan_outline.py
    │   │       ├── draft.py
    │   │       ├── critique.py
    │   │       └── finalize.py
    │   └── evaluation/                # === graph 2 (one goal) ===
    │       ├── graph.py
    │       ├── state.py
    │       ├── pydantic_schemas.py
    │       └── prompts/
    │           ├── judge_fact_recall.py
    │           ├── judge_tone.py
    │           └── judge_fluency.py
    └── utils.py                       # single file unless helpers grow → utils/
```

---

## 9. Build Order (recommended)

1. **Scaffold** the client/graph folder structure + `get_llm()` (Instructor + Groq).
2. **email_generation graph** (M1+M2) — nodes + per-node prompts → one good email end-to-end.
3. **M3** — author 10 scenarios + reference emails.
4. **evaluation graph** (M4) — 3 metric nodes + aggregate; validate on fixtures.
5. **M5** — reporting (CSV/JSON) with caching.
6. **M6** — 2×2 runner + comparison/analysis.
7. **FastAPI + M7** — endpoints, README, final report → PDF.

---

## 10. Decisions (locked)

- **Provider:** Groq API, **free models** (no paid usage). Key via `GROQ_API_KEY`.
- **Structured output:** **Instructor** (Groq lacks native structured output) → Pydantic `response_model` per node.
- **Orchestration:** **LangGraph** `StateGraph`, one graph per goal; node chains via `prompt_tmpl | get_llm()`.
- **HTTP:** FastAPI.
- **Stack:** Python.
- **Comparison:** full **2×2 grid** — 2 Groq models × {advanced, baseline} prompt.

### Still to pick at build time
- **Which two Groq models** (confirm current free-tier model IDs from Groq docs before coding).
- **Judge model** for LLM-as-Judge metrics (one capable free Groq model, temp 0).
- **Score scale:** 0–1 vs. 0–100 (pick one, keep consistent).
