from langgraph.graph import END, START, StateGraph

from core.base_graph import BaseGraph, render
from email_assistant.ai_client.evaluation.prompts.judge_fact_recall import (
    JUDGE_FACT_RECALL_HUMAN_PROMPT,
    JUDGE_FACT_RECALL_SYSTEM_PROMPT,
)
from email_assistant.ai_client.evaluation.prompts.judge_fluency import (
    JUDGE_FLUENCY_HUMAN_PROMPT,
    JUDGE_FLUENCY_SYSTEM_PROMPT,
)
from email_assistant.ai_client.evaluation.prompts.judge_tone import (
    JUDGE_TONE_HUMAN_PROMPT,
    JUDGE_TONE_SYSTEM_PROMPT,
)
from email_assistant.ai_client.evaluation.schemas import (
    FactRecallParser,
    FluencyParser,
    ToneParser,
)
from email_assistant.ai_client.evaluation.state import EvaluationState
from email_assistant.utils import (
    conciseness_score,
    filler_penalty,
    scale_value,
)


class EvaluationGraph(BaseGraph):
    def _facts_text(self, state: EvaluationState) -> str:
        return "\n".join(f"- {fact}" for fact in state.get("key_facts", []))

    def _judge_fact_recall(self, state: EvaluationState) -> dict:
        result = self.llm.judge(
            system_prompt=JUDGE_FACT_RECALL_SYSTEM_PROMPT,
            human_prompt=render(
                JUDGE_FACT_RECALL_HUMAN_PROMPT,
                key_facts=self._facts_text(state),
                subject=state["subject"],
                body=state["body"],
            ),
            response_model=FactRecallParser,
        )
        total = result.total_facts or len(state.get("key_facts", [])) or 1
        recall = result.covered_facts / total
        if result.fabricated:
            recall *= 0.7
        normalized = max(0.0, min(1.0, recall))
        return {
            "fact_recall_score": normalized,
            "fact_recall_reason": result.reason,
        }

    def _judge_tone(self, state: EvaluationState) -> dict:
        result = self.llm.judge(
            system_prompt=JUDGE_TONE_SYSTEM_PROMPT,
            human_prompt=render(
                JUDGE_TONE_HUMAN_PROMPT,
                tone=state["tone"],
                subject=state["subject"],
                body=state["body"],
            ),
            response_model=ToneParser,
        )
        normalized = max(0.0, min(1.0, result.alignment))
        return {
            "tone_score": normalized,
            "tone_reason": f"{result.detected_tone}: {result.reason}",
        }

    def _score_fluency(self, state: EvaluationState) -> dict:
        result = self.llm.judge(
            system_prompt=JUDGE_FLUENCY_SYSTEM_PROMPT,
            human_prompt=render(
                JUDGE_FLUENCY_HUMAN_PROMPT,
                subject=state["subject"],
                body=state["body"],
            ),
            response_model=FluencyParser,
        )
        concise = conciseness_score(
            state["body"],
            self.settings.conciseness_min_words,
            self.settings.conciseness_max_words,
        )
        penalty = filler_penalty(state["body"])
        judge_fluency = max(0.0, min(1.0, result.fluency))
        combined = (0.5 * judge_fluency) + (0.5 * concise) - penalty
        normalized = max(0.0, min(1.0, combined))
        return {
            "fluency_score": normalized,
            "fluency_reason": (
                f"judge={judge_fluency:.2f}, concise={concise:.2f}, "
                f"filler_penalty={penalty:.2f}. {result.reason}"
            ),
        }

    def _aggregate(self, state: EvaluationState) -> dict:
        weights = self.settings.metric_weights
        scale = self.settings.score_scale

        fact = state["fact_recall_score"]
        tone = state["tone_score"]
        fluency = state["fluency_score"]

        overall = (
            fact * weights["fact_recall"]
            + tone * weights["tone"]
            + fluency * weights["fluency"]
        )

        scores = {
            "fact_recall": scale_value(fact, scale),
            "tone_accuracy": scale_value(tone, scale),
            "conciseness_fluency": scale_value(fluency, scale),
            "overall": scale_value(overall, scale),
        }
        return {"overall_score": scores["overall"], "scores": scores}

    def _build(self) -> StateGraph:
        builder = StateGraph(EvaluationState)

        builder.add_node("judge_fact_recall", self._judge_fact_recall)
        builder.add_node("judge_tone", self._judge_tone)
        builder.add_node("score_fluency", self._score_fluency)
        builder.add_node("aggregate", self._aggregate)

        builder.add_edge(START, "judge_fact_recall")
        builder.add_edge("judge_fact_recall", "judge_tone")
        builder.add_edge("judge_tone", "score_fluency")
        builder.add_edge("score_fluency", "aggregate")
        builder.add_edge("aggregate", END)

        return builder

    def run(self, intent, key_facts, tone, subject, body, reference_email=None) -> dict:
        return self.invoke(
            {
                "intent": intent,
                "key_facts": key_facts,
                "tone": tone,
                "subject": subject,
                "body": body,
                "reference_email": reference_email,
            }
        )
