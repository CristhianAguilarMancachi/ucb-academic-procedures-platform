from __future__ import annotations

import logging
from functools import lru_cache

from groq import (
    Groq,
    APITimeoutError,
    APIConnectionError,
    RateLimitError,
    AuthenticationError,
    APIStatusError,
)

from app.core.config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    GROQ_TIMEOUT_SECONDS,
    GROQ_MAX_RETRIES,
)


logger = logging.getLogger(__name__)


UNAVAILABLE_MESSAGE = (
    "No pude responder esta consulta en este momento. "
    "Intenta nuevamente en unos instantes."
)

MAX_COMPLETION_TOKENS_HARD_LIMIT = 4096
TRUNCATION_RETRY_MULTIPLIER = 2
TRUNCATION_RETRY_MIN_INCREMENT = 512


class LLMUnavailableError(Exception):
    def __init__(
        self,
        reason: str | None = None,
    ):
        self.reason = reason
        super().__init__(UNAVAILABLE_MESSAGE)


@lru_cache(maxsize=1)
def get_client() -> Groq:
    return Groq(
        api_key=GROQ_API_KEY,
        timeout=GROQ_TIMEOUT_SECONDS,
        max_retries=GROQ_MAX_RETRIES,
    )


def _next_completion_budget(
    current_budget: int,
) -> int:
    doubled = (
        current_budget
        * TRUNCATION_RETRY_MULTIPLIER
    )

    incremented = (
        current_budget
        + TRUNCATION_RETRY_MIN_INCREMENT
    )

    return min(
        max(
            doubled,
            incremented,
        ),
        MAX_COMPLETION_TOKENS_HARD_LIMIT,
    )


def _extract_usage_value(
    usage,
    attribute: str,
) -> int | None:
    if usage is None:
        return None

    value = getattr(
        usage,
        attribute,
        None,
    )

    return (
        value
        if isinstance(value, int)
        else None
    )


def complete_text(
    prompt: str,
    *,
    temperature: float = 0.1,
    max_completion_tokens: int = 768,
    reasoning_effort: str = "low",
    task: str = "general",
) -> str:
    if max_completion_tokens <= 0:
        raise ValueError(
            "max_completion_tokens debe ser mayor que cero."
        )

    token_budget = min(
        max_completion_tokens,
        MAX_COMPLETION_TOKENS_HARD_LIMIT,
    )

    truncation_retry_used = False

    while True:
        try:
            logger.info(
                "[RAG][GROQ] Solicitud "
                "task=%s modelo=%s reasoning=%s max_tokens=%s",
                task,
                GROQ_MODEL,
                reasoning_effort,
                token_budget,
            )

            completion = (
                get_client()
                .chat
                .completions
                .create(
                    model=GROQ_MODEL,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    temperature=temperature,
                    reasoning_effort=reasoning_effort,
                    include_reasoning=False,
                    stream=False,
                    max_completion_tokens=token_budget,
                )
            )

            choices = getattr(
                completion,
                "choices",
                None,
            )

            choice = (
                choices[0]
                if choices
                else None
            )

            message = getattr(
                choice,
                "message",
                None,
            )

            content = getattr(
                message,
                "content",
                None,
            )

            finish_reason = getattr(
                choice,
                "finish_reason",
                None,
            )

            usage = getattr(
                completion,
                "usage",
                None,
            )

            prompt_tokens = _extract_usage_value(
                usage,
                "prompt_tokens",
            )

            completion_tokens = _extract_usage_value(
                usage,
                "completion_tokens",
            )

            total_tokens = _extract_usage_value(
                usage,
                "total_tokens",
            )

            logger.info(
                "[RAG][GROQ] Respuesta recibida "
                "task=%s modelo=%s reasoning=%s "
                "finish_reason=%s prompt_tokens=%s "
                "completion_tokens=%s total_tokens=%s",
                task,
                GROQ_MODEL,
                reasoning_effort,
                finish_reason,
                prompt_tokens,
                completion_tokens,
                total_tokens,
            )

            if finish_reason == "length":
                next_budget = _next_completion_budget(
                    token_budget
                )

                if (
                    not truncation_retry_used
                    and next_budget > token_budget
                ):
                    logger.warning(
                        "[RAG][GROQ] Respuesta truncada; "
                        "reintentando task=%s max_tokens=%s->%s",
                        task,
                        token_budget,
                        next_budget,
                    )

                    token_budget = next_budget
                    truncation_retry_used = True

                    continue

                logger.warning(
                    "[RAG][GROQ] Respuesta truncada sin margen "
                    "de reintento task=%s max_tokens=%s",
                    task,
                    token_budget,
                )

                raise LLMUnavailableError(
                    reason=f"truncated_response:{task}"
                )

            if (
                not isinstance(content, str)
                or not content.strip()
            ):
                logger.warning(
                    "[RAG][GROQ] Respuesta vacía "
                    "task=%s modelo=%s reasoning=%s "
                    "finish_reason=%s",
                    task,
                    GROQ_MODEL,
                    reasoning_effort,
                    finish_reason,
                )

                raise LLMUnavailableError(
                    reason=f"empty_response:{task}"
                )

            return content.strip()

        except LLMUnavailableError:
            raise

        except APITimeoutError:
            logger.warning(
                "[RAG][GROQ] Timeout "
                "task=%s modelo=%s reasoning=%s",
                task,
                GROQ_MODEL,
                reasoning_effort,
            )

            raise LLMUnavailableError(
                reason=f"timeout:{task}"
            ) from None

        except RateLimitError as exc:
            status_code = getattr(
                exc,
                "status_code",
                None,
            )

            logger.warning(
                "[RAG][GROQ] Rate limit "
                "task=%s status=%s modelo=%s reasoning=%s",
                task,
                status_code,
                GROQ_MODEL,
                reasoning_effort,
            )

            raise LLMUnavailableError(
                reason=f"rate_limit:{task}"
            ) from None

        except AuthenticationError as exc:
            status_code = getattr(
                exc,
                "status_code",
                None,
            )

            logger.error(
                "[RAG][GROQ] Error de autenticación "
                "task=%s status=%s modelo=%s",
                task,
                status_code,
                GROQ_MODEL,
            )

            raise LLMUnavailableError(
                reason=f"authentication:{task}"
            ) from None

        except APIConnectionError:
            logger.warning(
                "[RAG][GROQ] Error de conexión "
                "task=%s modelo=%s",
                task,
                GROQ_MODEL,
            )

            raise LLMUnavailableError(
                reason=f"connection:{task}"
            ) from None

        except APIStatusError as exc:
            status_code = getattr(
                exc,
                "status_code",
                None,
            )

            logger.warning(
                "[RAG][GROQ] API status error "
                "task=%s status=%s modelo=%s reasoning=%s",
                task,
                status_code,
                GROQ_MODEL,
                reasoning_effort,
            )

            raise LLMUnavailableError(
                reason=(
                    f"api_status_{status_code}:{task}"
                )
            ) from None

        except Exception as exc:
            logger.exception(
                "[RAG][GROQ] Error inesperado "
                "task=%s tipo=%s modelo=%s",
                task,
                type(exc).__name__,
                GROQ_MODEL,
            )

            raise LLMUnavailableError(
                reason=f"unexpected:{task}"
            ) from None