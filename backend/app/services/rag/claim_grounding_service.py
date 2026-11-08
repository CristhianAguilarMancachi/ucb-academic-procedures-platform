
from __future__ import annotations

import json
import logging
import re
import unicodedata

from app.services.rag.grounding_validator import (
    apply_conservative_guards,
)
from app.services.rag.llm_client import (
    LLMUnavailableError,
    complete_text,
)
from app.services.rag.prompt_builder import (
    NO_INFORMATION_MESSAGE,
)


LOGGER = logging.getLogger(__name__)

AUDIT_MAX_COMPLETION_TOKENS = 2400

ALLOWED_TYPES = {
    "fact",
    "inclusion",
    "requirement",
    "equivalence",
    "condition",
    "procedure",
    "other_relation",
}

RELATION_MARKERS = {
    "inclusion": (
        "inclu",
        "conten",
        "comprend",
        "incorpor",
        "integr",
        "abarca",
        "compuest",
        "forma parte",
        "consiste en",
    ),
    "requirement": (
        "debe",
        "requier",
        "exig",
        "neces",
        "oblig",
        "present",
        "entreg",
        "autoriz",
        "poder",
        "solicit",
    ),
    "equivalence": (
        "equival",
        "igual a",
        "sustitu",
        "reemplaz",
        "correspond",
        "se considera",
        "es lo mismo",
    ),
    "condition": (
        "si ",
        "cuando",
        "siempre que",
        "en caso",
        "except",
        "salvo",
        "unicamente",
        "solo ",
        "depende",
    ),
    "procedure": (
        "solicit",
        "present",
        "entreg",
        "llen",
        "pag",
        "realiz",
        "recog",
        "retir",
        "registr",
        "tramita",
        "debe",
    ),
    "other_relation": (
        "depend",
        "caus",
        "permit",
        "implic",
        "aplic",
        "genera",
        "produce",
        "autoriza",
        "debe",
        "puede",
    ),
}

INCLUSION_ASSERTION = re.compile(
    r"\b(?:incluy\w*|inclu\w*|contien\w*|contiene|"
    r"comprend\w*|incorpor\w*|integr\w*|abarca\w*|"
    r"forma\s+parte|todo\s+(?:esta|está)\s+incluido)\b",
    re.IGNORECASE,
)


def normalize_evidence_text(value: str) -> str:
    value = unicodedata.normalize(
        "NFKD",
        value.casefold(),
    )

    value = "".join(
        character
        for character in value
        if not unicodedata.combining(character)
    )

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def evidence_exists(
    evidence: str,
    documents: list[str],
) -> bool:
    evidence = normalize_evidence_text(
        evidence,
    )

    return len(evidence) >= 12 and any(
        evidence in normalize_evidence_text(document)
        for document in documents
    )


def build_claim_audit_prompt(
    question: str,
    answer: str,
    documents: list[str],
) -> str:
    context = "\n\n".join(
        f"[FRAGMENTO {index}]\n{document.strip()}"
        for index, document in enumerate(
            documents,
            start=1,
        )
        if document.strip()
    )

    return f"""
Eres un auditor estricto de respuestas académicas
basadas en documentos institucionales.

NO vuelvas a contestar desde cero.
Descompón la RESPUESTA PROPUESTA en afirmaciones
verificables, sin inventar afirmaciones adicionales.

PREGUNTA:
{question}

RESPUESTA PROPUESTA:
{answer}

CONTEXTO INSTITUCIONAL:
{context}

Para CADA afirmación, decide si está explícitamente
respaldada por el contexto.

Debes comprobar dos aspectos DIFERENTES:

A) ALCANCE DOCUMENTAL:
El requisito, precio, autorización, condición o
procedimiento corresponde al mismo trámite,
documento, situación o modalidad de la pregunta.

B) RELACIÓN DOCUMENTAL:
El documento realmente afirma que un elemento
incluye, requiere, sustituye, permite, condiciona,
equivale o depende de otro.

REGLAS OBLIGATORIAS:

1. La presencia de dos conceptos en un mismo
   fragmento NO demuestra que exista una relación.

2. Una enumeración de documentos o servicios
   NO significa que uno incluya a los demás.

3. Una tarifa compartida NO demuestra inclusión.

4. No transfieras requisitos, autorizaciones,
   documentos o procedimientos entre trámites.

5. Si el contexto no identifica claramente
   a qué trámite aplica un requisito, no lo
   presentes como requisito confirmado.

6. Respeta condiciones, alternativas, excepciones,
   negaciones y relaciones explícitas.

7. Conserva información útil que esté respaldada.

8. Divide las oraciones compuestas cuando una
   parte sea válida y otra no esté respaldada.

9. Si una relación no está documentada,
   supported debe ser false.

10. No inventes evidencia ni citas.

11. No utilices citas que correspondan a otro
    procedimiento para justificar la afirmación.

12. No elimines una relación verdaderamente
    documentada solo por ser una inclusión
    o una obligación.

13. Mantén la respuesta en español.

14. Usa únicamente los siguientes tipos:
    fact, inclusion, requirement, equivalence,
    condition, procedure, other_relation.

Para cada afirmación respaldada proporciona:

- text:
  Afirmación autónoma que se puede mostrar
  directamente al usuario.

- supported:
  true solamente si está respaldada.

- claim_type:
  Tipo de afirmación.

- evidence:
  Cita LITERAL y consecutiva del documento
  que respalda el contenido.

- scope_evidence:
  Cita LITERAL que demuestra a qué trámite
  o situación aplica la afirmación.

- relation_evidence:
  Cita LITERAL que expresa la relación
  que se está afirmando.

Las tres citas, cuando correspondan, deben
provenir del MISMO fragmento recuperado.

Para afirmaciones simples de tipo fact,
relation_evidence puede ser una cadena vacía.

Las citas deben ser suficientemente largas
para aportar un contexto verificable.

No utilices una cita que solo enumere elementos
como respaldo de una afirmación de inclusión.

Devuelve únicamente JSON válido, sin Markdown:

{{
  "claims": [
    {{
      "text": "Afirmación autónoma.",
      "supported": true,
      "claim_type": "requirement",
      "evidence": "Cita literal de evidencia",
      "scope_evidence": "Cita literal de alcance",
      "relation_evidence": "Cita literal de relación"
    }},
    {{
      "text": "Afirmación no respaldada.",
      "supported": false,
      "claim_type": "inclusion",
      "evidence": "",
      "scope_evidence": "",
      "relation_evidence": ""
    }}
  ]
}}
""".strip()


def parse_audit_json(
    raw_text: str,
) -> dict | None:
    text = raw_text.strip()

    if text.startswith("```"):
        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\s*```$",
            "",
            text,
        )

    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return None

    if not isinstance(data, dict):
        return None

    claims = data.get("claims")

    if not isinstance(claims, list) or not claims:
        return None

    for claim in claims:
        if not isinstance(claim, dict):
            return None

        if type(claim.get("supported")) is not bool:
            return None

        if claim.get("claim_type") not in ALLOWED_TYPES:
            return None

        for field in (
            "text",
            "evidence",
            "scope_evidence",
            "relation_evidence",
        ):
            if not isinstance(
                claim.get(field),
                str,
            ):
                return None

    return data


def find_supporting_document(
    claim: dict,
    documents: list[str],
) -> str | None:
    evidence = normalize_evidence_text(
        claim["evidence"]
    )

    scope = normalize_evidence_text(
        claim["scope_evidence"]
    )

    relation = normalize_evidence_text(
        claim["relation_evidence"]
    )

    if len(evidence) < 12 or len(scope) < 12:
        return None

    claim_type = claim["claim_type"]

    is_inclusion = bool(
        INCLUSION_ASSERTION.search(
            claim["text"]
        )
    )

    if is_inclusion and claim_type != "inclusion":
        return None

    if claim_type != "fact":
        if len(relation) < 12:
            return None

        markers = RELATION_MARKERS[claim_type]

        if not any(
            marker in relation
            for marker in markers
        ):
            return None

    for document in documents:
        normalized_document = normalize_evidence_text(
            document
        )

        if (
            evidence in normalized_document
            and scope in normalized_document
            and (
                not relation
                or relation in normalized_document
            )
        ):
            return document

    return None


def render_supported_claims(
    claims: list[dict],
    documents: list[str],
) -> str | None:
    accepted: list[str] = []
    seen: set[str] = set()

    for claim in claims:
        if not claim["supported"]:
            continue

        statement = claim["text"].strip()

        if not statement:
            continue

        supporting_document = (
            find_supporting_document(
                claim,
                documents,
            )
        )

        if supporting_document is None:
            continue

        key = normalize_evidence_text(
            statement
        )

        if key in seen:
            continue

        seen.add(key)
        accepted.append(statement)

    if not accepted:
        return None

    if len(accepted) == 1:
        return accepted[0]

    return "\n".join(
        f"{index}. {statement}"
        for index, statement in enumerate(
            accepted,
            start=1,
        )
    )


def validate_claims_grounded_answer(
    question: str,
    answer: str,
    documents: list[str],
) -> str:
    if not answer.strip():
        return answer

    if not documents:
        return NO_INFORMATION_MESSAGE

    prompt = build_claim_audit_prompt(
        question=question,
        answer=answer,
        documents=documents,
    )

    try:
        raw_audit = complete_text(
            prompt,
            temperature=0.0,
            max_completion_tokens=AUDIT_MAX_COMPLETION_TOKENS,
            reasoning_effort="medium",
            task="grounding",
        )

    except LLMUnavailableError:
        LOGGER.warning(
            "[RAG][AUDIT] proveedor_no_disponible"
        )
        return NO_INFORMATION_MESSAGE

    parsed = parse_audit_json(
        raw_audit
    )

    if parsed is None:
        LOGGER.warning(
            "[RAG][AUDIT] formato_invalido"
        )
        return NO_INFORMATION_MESSAGE

    validated = render_supported_claims(
        parsed["claims"],
        documents,
    )

    total = len(parsed["claims"])

    accepted = (
        0
        if validated is None
        else (
            1
            if "\n" not in validated
            else validated.count("\n") + 1
        )
    )

    LOGGER.info(
        "[RAG][AUDIT] claims=%s accepted=%s",
        total,
        accepted,
    )

    if validated is None:
        LOGGER.warning(
            "[RAG][AUDIT] sin_afirmaciones_verificables"
        )
        return NO_INFORMATION_MESSAGE

    return apply_conservative_guards(
        question=question,
        answer=validated,
    )
