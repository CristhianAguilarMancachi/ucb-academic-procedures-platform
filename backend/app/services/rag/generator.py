from __future__ import annotations

from app.services.rag.grounding_validator import (
    validate_grounded_answer,
)
from app.services.rag.llm_client import (
    complete_text,
)
from app.services.rag.prompt_builder import (
    build_rag_prompt,
)


GENERATION_TOKEN_BUDGETS = {
    "comparison": 1600,
    "procedure": 1600,
    "consequence": 1400,
    "eligibility": 1400,
}

DEFAULT_GENERATION_TOKEN_BUDGET = 900


REASONING_BY_QUERY_TYPE = {
    "comparison": "medium",
    "procedure": "medium",
    "consequence": "medium",
    "eligibility": "medium",
}

DEFAULT_REASONING_EFFORT = "low"


def generate_answer(
    question: str,
    documents: list[str],
    metadatas: list[dict],
    query_type: str = "general",
) -> str:
    prompt = build_rag_prompt(
        question=question,
        documents=documents,
        metadatas=metadatas,
        query_type=query_type,
    )

    reasoning_effort = (
        REASONING_BY_QUERY_TYPE.get(
            query_type,
            DEFAULT_REASONING_EFFORT,
        )
    )

    max_tokens = (
        GENERATION_TOKEN_BUDGETS.get(
            query_type,
            DEFAULT_GENERATION_TOKEN_BUDGET,
        )
    )

    generated_answer = complete_text(
        prompt,
        temperature=0.0,
        max_completion_tokens=max_tokens,
        reasoning_effort=reasoning_effort,
        task="generation",
    )

    validated_answer = validate_grounded_answer(
        question=question,
        answer=generated_answer,
        documents=documents,
    )

    return validated_answer