METRIC_DEFINITIONS = {
    "fact_recall": {
        "name": "Fact Recall & Faithfulness",
        "focus": "Fact Recall / Specificity",
        "logic": (
            "LLM-as-Judge counts how many provided key facts are accurately present "
            "(paraphrase allowed) and flags fabricated facts. Score = covered / total, "
            "multiplied by 0.7 when fabrication is detected."
        ),
    },
    "tone": {
        "name": "Tone Accuracy",
        "focus": "Tone Accuracy",
        "logic": (
            "LLM-as-Judge identifies the tone the email conveys and rates alignment with "
            "the requested tone from 0.0 to 1.0."
        ),
    },
    "fluency": {
        "name": "Conciseness & Fluency",
        "focus": "Conciseness / Grammar / Fluency",
        "logic": (
            "Hybrid: deterministic Python scores conciseness against a word-count band and "
            "penalizes filler phrases; an LLM-as-Judge scores grammar and readability. "
            "Combined = 0.5 * judge_fluency + 0.5 * conciseness - filler_penalty."
        ),
    },
}
