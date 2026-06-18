from langgraph.graph import END, START, StateGraph

from core.base_graph import BaseGraph, render
from email_assistant.ai_client.email_generation.prompts.critique import (
    CRITIQUE_HUMAN_PROMPT,
    CRITIQUE_SYSTEM_PROMPT,
)
from email_assistant.ai_client.email_generation.prompts.draft import (
    DRAFT_ADVANCED_SYSTEM_PROMPT,
    DRAFT_BASELINE_SYSTEM_PROMPT,
    DRAFT_HUMAN_PROMPT,
)
from email_assistant.ai_client.email_generation.prompts.finalize import (
    FINALIZE_HUMAN_PROMPT,
    FINALIZE_SYSTEM_PROMPT,
)
from email_assistant.ai_client.email_generation.prompts.plan_outline import (
    PLAN_OUTLINE_HUMAN_PROMPT,
    PLAN_OUTLINE_SYSTEM_PROMPT,
)
from email_assistant.ai_client.email_generation.prompts.validate_input import (
    VALIDATE_INPUT_HUMAN_PROMPT,
    VALIDATE_INPUT_SYSTEM_PROMPT,
)
from email_assistant.ai_client.email_generation.schemas import (
    CritiqueParser,
    DraftParser,
    InputValidationParser,
    OutlineParser,
)
from email_assistant.ai_client.email_generation.state import EmailGenerationState

STRATEGY_ADVANCED = "advanced"
STRATEGY_BASELINE = "baseline"


class EmailGenerationGraph(BaseGraph):
    def _model_for(self, state: EmailGenerationState) -> str:
        return state.get("model_name") or self.settings.model_a

    def _strategy_for(self, state: EmailGenerationState) -> str:
        return state.get("strategy") or STRATEGY_ADVANCED

    def _facts_text(self, state: EmailGenerationState) -> str:
        return "\n".join(f"- {fact}" for fact in state.get("key_facts", []))

    def _validate_input(self, state: EmailGenerationState) -> dict:
        result = self.llm.generate(
            model_name=self._model_for(state),
            system_prompt=VALIDATE_INPUT_SYSTEM_PROMPT,
            human_prompt=render(
                VALIDATE_INPUT_HUMAN_PROMPT,
                intent=state["intent"],
                key_facts=self._facts_text(state),
                tone=state["tone"],
            ),
            response_model=InputValidationParser,
        )
        return {"is_valid": result.is_valid, "validation_reason": result.reason}

    def _input_decision(self, state: EmailGenerationState) -> str:
        return "plan_outline" if state["is_valid"] else "input_error"

    def _input_error(self, state: EmailGenerationState) -> dict:
        return {
            "response": {
                "type": "ERROR",
                "message": state.get("validation_reason") or "Insufficient input.",
            }
        }

    def _plan_outline(self, state: EmailGenerationState) -> dict:
        result = self.llm.generate(
            model_name=self._model_for(state),
            system_prompt=PLAN_OUTLINE_SYSTEM_PROMPT,
            human_prompt=render(
                PLAN_OUTLINE_HUMAN_PROMPT,
                intent=state["intent"],
                key_facts=self._facts_text(state),
                tone=state["tone"],
            ),
            response_model=OutlineParser,
        )
        return {"outline": result.outline}

    def _draft(self, state: EmailGenerationState) -> dict:
        advanced = self._strategy_for(state) == STRATEGY_ADVANCED
        system_prompt = (
            DRAFT_ADVANCED_SYSTEM_PROMPT if advanced else DRAFT_BASELINE_SYSTEM_PROMPT
        )
        result = self.llm.generate(
            model_name=self._model_for(state),
            system_prompt=system_prompt,
            human_prompt=render(
                DRAFT_HUMAN_PROMPT,
                intent=state["intent"],
                key_facts=self._facts_text(state),
                tone=state["tone"],
                outline=state.get("outline", ""),
            ),
            response_model=DraftParser,
        )
        return {"subject": result.subject, "body": result.body}

    def _draft_decision(self, state: EmailGenerationState) -> str:
        return "self_critique" if self._strategy_for(state) == STRATEGY_ADVANCED else "package"

    def _self_critique(self, state: EmailGenerationState) -> dict:
        result = self.llm.generate(
            model_name=self._model_for(state),
            system_prompt=CRITIQUE_SYSTEM_PROMPT,
            human_prompt=render(
                CRITIQUE_HUMAN_PROMPT,
                key_facts=self._facts_text(state),
                tone=state["tone"],
                subject=state["subject"],
                body=state["body"],
            ),
            response_model=CritiqueParser,
        )
        return {"needs_revision": result.needs_revision, "critique": result.critique}

    def _critique_decision(self, state: EmailGenerationState) -> str:
        return "revise" if state.get("needs_revision") else "package"

    def _revise(self, state: EmailGenerationState) -> dict:
        result = self.llm.generate(
            model_name=self._model_for(state),
            system_prompt=FINALIZE_SYSTEM_PROMPT,
            human_prompt=render(
                FINALIZE_HUMAN_PROMPT,
                intent=state["intent"],
                key_facts=self._facts_text(state),
                tone=state["tone"],
                critique=state.get("critique", ""),
                subject=state["subject"],
                body=state["body"],
            ),
            response_model=DraftParser,
        )
        return {"subject": result.subject, "body": result.body}

    def _package(self, state: EmailGenerationState) -> dict:
        return {
            "response": {
                "type": "EMAIL",
                "subject": state["subject"],
                "body": state["body"],
            }
        }

    def _build(self) -> StateGraph:
        builder = StateGraph(EmailGenerationState)

        builder.add_node("validate_input", self._validate_input)
        builder.add_node("input_error", self._input_error)
        builder.add_node("plan_outline", self._plan_outline)
        builder.add_node("draft", self._draft)
        builder.add_node("self_critique", self._self_critique)
        builder.add_node("revise", self._revise)
        builder.add_node("package", self._package)

        builder.add_edge(START, "validate_input")
        builder.add_conditional_edges(
            "validate_input",
            self._input_decision,
            {"plan_outline": "plan_outline", "input_error": "input_error"},
        )
        builder.add_edge("plan_outline", "draft")
        builder.add_conditional_edges(
            "draft",
            self._draft_decision,
            {"self_critique": "self_critique", "package": "package"},
        )
        builder.add_conditional_edges(
            "self_critique",
            self._critique_decision,
            {"revise": "revise", "package": "package"},
        )
        builder.add_edge("revise", "package")
        builder.add_edge("input_error", END)
        builder.add_edge("package", END)

        return builder

    def run(self, intent: str, key_facts: list, tone: str, model_name: str, strategy: str) -> dict:
        return self.invoke(
            {
                "intent": intent,
                "key_facts": key_facts,
                "tone": tone,
                "model_name": model_name,
                "strategy": strategy,
            }
        )
