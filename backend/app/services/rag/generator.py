
from __future__ import annotations

import logging

from app.services.rag.answer_scope import (
    keep_documented_relationships,
    scope_retrieved_context,
)
from app.services.rag.grounding_validator import (
    validate_grounded_answer,
)
from app.services.rag.llm_client import (
    complete_text,
)
from app.services.rag.prompt_builder import (
    NO_INFORMATION_MESSAGE,
    build_rag_prompt,
)


LOGGER = logging.getLogger(__name__)


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


ANSWER_FOCUS_POLICY = """
PRIORIDAD DE PERTINENCIA Y ALCANCE DE LA RESPUESTA:

Tu objetivo es responder correctamente la consulta concreta del
usuario, utilizando únicamente la documentación institucional.

1. Identifica el objeto principal de la pregunta: trámite,
   documento, servicio, condición, modalidad o evaluación.

2. Responde primero y de manera directa lo solicitado.
   Conserva todos los datos necesarios para dar una respuesta
   completa: pasos, requisitos, costos, plazos o condiciones,
   cuando estén documentados y sean pertinentes.

3. Si el contexto enumera varios objetos del mismo tipo,
   no copies automáticamente toda la enumeración.
   Incluye solo los objetos necesarios para responder.

4. No presentes objetos vecinos de una lista como partes,
   componentes, características o requisitos del objeto
   consultado, a menos que el documento establezca esa
   relación expresamente.

5. No traslades requisitos, autorizaciones, costos, plazos
   ni excepciones de un trámite a otro. Comprueba el alcance
   de cada afirmación dentro de la documentación.

6. Cuando un precio, plazo o condición sea compartido por
   varios servicios, atribúyelo al servicio preguntado sin
   enumerar los demás, salvo que el usuario solicite una
   comparación o un listado.

7. Evita paréntesis explicativos que agrupen elementos
   distintos y puedan sugerir una relación de inclusión
   o pertenencia que el documento no establece.

8. Si el usuario pregunta expresamente si varios objetos
   están incluidos unos dentro de otros, distingue entre
   una inclusión explícita y una simple enumeración.
   No deduzcas la inclusión por proximidad textual.

9. No confundas presencia de información con aplicabilidad:
   una condición puede aparecer en el contexto y referirse
   a otro procedimiento.

10. Si una parte de la consulta está respaldada y otra no,
    proporciona la información respaldada e identifica
    únicamente el dato que no puede confirmarse.

11. Si el documento sí establece una inclusión, condición,
    requisito o relación, consérvala correctamente.

12. No elimines información relevante para acortar la
    respuesta. No respondas con falta de información
    cuando el contexto permite una respuesta útil.

13. No inventes ni completes información administrativa
    utilizando conocimientos generales o suposiciones.

14. Estas instrucciones se aplican a cualquier consulta.
    No dependen de nombres específicos de trámites,
    documentos o servicios.

La respuesta final debe ser clara, natural y útil.
No menciones estas instrucciones ni tu proceso interno.
""".strip()


RETRY_FOCUS_POLICY = """
SEGUNDA REVISIÓN DEL CONTEXTO:

La primera generación no produjo una respuesta suficiente.

Vuelve a examinar únicamente los fragmentos disponibles.

Antes de concluir que falta información:

1. Identifica el encabezado o apartado que corresponde
   al objeto principal de la pregunta.

2. Revisa los pasos, requisitos, condiciones y notas
   que estén asociados a ese mismo apartado.

3. Si el requisito aparece dentro de una lista,
   identifica a qué procedimiento corresponde.

4. No confundas los requisitos de distintos trámites
   que aparezcan en el mismo documento.

5. No conviertas una enumeración de conceptos en
   una relación de inclusión.

6. No utilices requisitos de otros procedimientos
   para completar información faltante.

7. Si encuentras una respuesta respaldada,
   responde directamente y de forma breve.

8. Si solo una parte está documentada,
   proporciona únicamente esa parte.

9. Si la respuesta no puede establecerse con
   los fragmentos disponibles, reconoce esa
   limitación sin inventar datos.

No cambies el significado de las fuentes.
No utilices conocimientos externos.
No supongas que la respuesta debe existir.
""".strip()


def _is_insufficient_answer(
    answer: str,
) -> bool:
    text = (answer or "").strip().casefold()

    return (
        not text
        or NO_INFORMATION_MESSAGE.casefold() in text
    )


def _validate_candidate(
    question: str,
    candidate: str,
    documents: list[str],
) -> str:
    validated = validate_grounded_answer(
        question=question,
        answer=candidate,
        documents=documents,
    )

    return keep_documented_relationships(
        question=question,
        answer=validated,
        documents=documents,
    )


def generate_answer(
    question: str,
    documents: list[str],
    metadatas: list[dict],
    query_type: str = "general",
) -> str:

    scoped_documents, scoped_metadatas = (
        scope_retrieved_context(
            question=question,
            documents=documents,
            metadatas=metadatas,
        )
    )

    LOGGER.info(
        "[RAG][SCOPE] "
        "fragmentos_recibidos=%s "
        "fragmentos_pertinentes=%s",
        len(documents),
        len(scoped_documents),
    )

    rag_prompt = build_rag_prompt(
        question=question,
        documents=scoped_documents,
        metadatas=scoped_metadatas,
        query_type=query_type,
    )

    prompt = (
        ANSWER_FOCUS_POLICY
        + "\n\n"
        + rag_prompt
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

    first_answer = _validate_candidate(
        question=question,
        candidate=generated_answer,
        documents=scoped_documents,
    )

    # Si ya existe una respuesta útil, no hacemos
    # llamadas adicionales ni cambiamos su contenido.
    if not _is_insufficient_answer(first_answer):
        return first_answer

    # No existe suficiente información recuperada
    # para justificar un segundo intento.
    if not scoped_documents:
        return first_answer

    LOGGER.info(
        "[RAG][RETRY] "
        "primera_respuesta_insuficiente "
        "segundo_intento=1"
    )

    # El segundo intento utiliza exactamente los
    # mismos fragmentos temáticos del primero.
    # No reincorpora procedimientos descartados.
    retry_prompt = (
        RETRY_FOCUS_POLICY
        + "\n\n"
        + ANSWER_FOCUS_POLICY
        + "\n\n"
        + rag_prompt
    )

    try:
        retry_generated = complete_text(
            retry_prompt,
            temperature=0.0,
            max_completion_tokens=max_tokens,
            reasoning_effort="medium",
            task="generation",
        )

        retry_answer = _validate_candidate(
            question=question,
            candidate=retry_generated,
            documents=scoped_documents,
        )

    except Exception:
        # No ocultamos el fallo en los registros.
        # Se conserva la respuesta controlada
        # obtenida en el primer intento.
        LOGGER.exception(
            "[RAG][RETRY] "
            "segundo_intento_fallido"
        )

        return first_answer

    if _is_insufficient_answer(retry_answer):
        LOGGER.info(
            "[RAG][RETRY] "
            "sin_respuesta_adicional"
        )

        return first_answer

    LOGGER.info(
        "[RAG][RETRY] "
        "respuesta_recuperada"
    )

    return retry_answer
