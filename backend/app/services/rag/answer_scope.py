
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict


_FUNCTION_WORDS = frozenset({
    "a", "al", "ante", "con", "contra", "como", "cuando",
    "cual", "cuales", "cuanto", "cuantos", "de", "del",
    "desde", "donde", "el", "ella", "en", "es", "esa",
    "ese", "esta", "estan", "este", "esto", "ha",
    "hacer", "hay", "la", "las", "le", "lo", "los",
    "me", "mi", "mis", "no", "o", "para", "pero",
    "por", "puede", "puedo", "que", "quien", "se",
    "ser", "si", "sin", "son", "su", "sus", "te",
    "tengo", "tiene", "un", "una", "unas", "uno",
    "unos", "y", "yo",
})


_INCLUSION_CLAIM = re.compile(
    r"\b(?:incluy\w*|incluid\w*|incluir|"
    r"contien\w*|contiene|comprend\w*|"
    r"incorpor\w*|integr\w*|abarca\w*|"
    r"consta\s+de|forma(?:n)?\s+parte\s+de|"
    r"viene\s+con|est[aá]n?\s+incluid\w*)\b",
    re.IGNORECASE,
)

_IMPLIED_INCLUSION_CLAIM = re.compile(
    r"\b(?:no\s+(?:es\s+)?necesari\w*\s+"
    r"(?:solicitar|pedir|tramitar|obtener)\w*"
    r"[^.!?]{0,110}"
    r"(?:separad\w*|diferent\w*|distint\w*)|"
    r"(?:todo\w*|ambos)\s+"
    r"(?:viene\w*|va\w*|estan|esta)\s+"
    r"(?:en|dentro\s+de)\s+"
    r"(?:un\s+)?(?:mismo|solo|unico))\b",
    re.IGNORECASE,
)

_INCLUSION_EVIDENCE = re.compile(
    r"\b(?:incluy\w*|incluid\w*|incluir|"
    r"contien\w*|contiene|comprend\w*|"
    r"incorpor\w*|integr\w*|abarca\w*|"
    r"consta\s+de|forma(?:n)?\s+parte\s+de|"
    r"se\s+compone\s+de|"
    r"est[aá]n?\s+incluid\w*)\b",
    re.IGNORECASE,
)

_INCLUSION_QUESTION = re.compile(
    r"\b(?:incluy\w*|incluid\w*|incluir|"
    r"contien\w*|contiene|comprend\w*|"
    r"viene\s+con|forma(?:n)?\s+parte|"
    r"junt\w*|mismo\s+documento)\b",
    re.IGNORECASE,
)


def _normalize(value: str) -> str:
    value = unicodedata.normalize(
        "NFKD",
        (value or "").casefold(),
    )

    value = "".join(
        character
        for character in value
        if not unicodedata.combining(character)
    )

    return re.sub(
        r"[^a-z0-9]+",
        " ",
        value,
    ).strip()


def _tokens(value: str) -> list[str]:
    return _normalize(value).split()


def _topic_phrases(question: str) -> set[str]:
    words = _tokens(question)
    phrases: set[str] = set()

    for size in (2, 3, 4, 5):
        for position in range(
            len(words) - size + 1
        ):
            group = words[
                position:position + size
            ]

            content = [
                word
                for word in group
                if (
                    word not in _FUNCTION_WORDS
                    and len(word) >= 4
                )
            ]

            if len(content) >= 2:
                phrases.add(
                    " ".join(group)
                )

    return phrases


def scope_retrieved_context(
    question: str,
    documents: list[str],
    metadatas: list[dict],
) -> tuple[list[str], list[dict]]:
    """
    Organiza los fragmentos por documento y página.

    Selecciona contexto temático solo cuando existe
    una coincidencia textual suficientemente clara.

    Si no hay evidencia suficiente para delimitar,
    conserva íntegramente la recuperación original.
    """

    if (
        not documents
        or len(documents) != len(metadatas)
    ):
        return documents, metadatas

    # Las comparaciones pueden necesitar información
    # de distintos procedimientos y documentos.
    if re.search(
        r"\b(?:diferencia|comparar|comparacion|versus)\b",
        _normalize(question),
    ):
        return documents, metadatas

    phrases = _topic_phrases(question)

    if not phrases:
        return documents, metadatas

    groups: dict[tuple, list[int]] = defaultdict(
        list
    )

    for index, metadata in enumerate(metadatas):
        metadata = (
            metadata
            if isinstance(metadata, dict)
            else {}
        )

        document_name = _normalize(
            str(
                metadata.get("document")
                or ""
            )
        )

        page = metadata.get("page")

        if document_name and page is not None:
            group_key = (
                document_name,
                str(page),
            )
        else:
            group_key = (
                "unknown",
                index,
            )

        groups[group_key].append(index)

    if len(groups) < 2:
        return documents, metadatas

    scores: dict[tuple, int] = {}

    for group_key, indexes in groups.items():
        combined_text = _normalize(
            " ".join(
                documents[index]
                for index in indexes
            )
        )

        padded_text = f" {combined_text} "

        matches = [
            phrase
            for phrase in phrases
            if f" {phrase} " in padded_text
        ]

        scores[group_key] = sum(
            len(phrase.split()) ** 2
            for phrase in matches
        )

    best_score = max(
        scores.values(),
        default=0,
    )

    if best_score < 4:
        return documents, metadatas

    selected_groups = {
        group_key
        for group_key, score in scores.items()
        if (
            score > 0
            and score >= best_score * 0.55
        )
    }

    selected_indexes = [
        index
        for index in range(len(documents))
        if any(
            index in groups[group_key]
            for group_key in selected_groups
        )
    ]

    if (
        not selected_indexes
        or len(selected_indexes) == len(documents)
    ):
        return documents, metadatas

    selected_length = sum(
        len(documents[index].strip())
        for index in selected_indexes
    )

    if selected_length < 120:
        return documents, metadatas

    return (
        [
            documents[index]
            for index in selected_indexes
        ],
        [
            metadatas[index]
            for index in selected_indexes
        ],
    )


def _has_supported_inclusion(
    claim: str,
    documents: list[str],
) -> bool:
    """
    Busca expresiones explícitas de inclusión
    en el contexto seleccionado.

    Esta verificación es conservadora y no
    constituye una demostración semántica formal.
    """

    claim_terms = {
        word
        for word in _tokens(claim)
        if (
            word not in _FUNCTION_WORDS
            and len(word) >= 4
        )
    }

    if not claim_terms:
        return False

    for document in documents:
        paragraphs = re.split(
            r"\n{2,}|(?<=[.;])\s+"
            r"(?=[A-ZÁÉÍÓÚÑ])",
            document,
        )

        for paragraph in paragraphs:
            relation = _INCLUSION_EVIDENCE.search(
                paragraph
            )

            if relation is None:
                continue

            preceding_text = _normalize(
                paragraph[
                    max(0, relation.start() - 22):
                    relation.start()
                ]
            )

            if preceding_text.endswith(
                ("no", "nunca", "tampoco", "sin")
            ):
                continue

            evidence_terms = {
                word
                for word in _tokens(paragraph)
                if (
                    word not in _FUNCTION_WORDS
                    and len(word) >= 4
                )
            }

            if len(
                claim_terms & evidence_terms
            ) >= 2:
                return True

    return False


def _remove_unrequested_catalogue(
    question: str,
    answer: str,
) -> str:
    """
    Evita enumeraciones extensas entre paréntesis
    después de un importe cuando no fueron pedidas.
    """

    normalized_question = _normalize(question)

    comparison_terms = (
        "lista",
        "cuales son",
        "compar",
        "diferencia",
        "inclu",
        "contien",
        "viene con",
    )

    if any(
        term in normalized_question
        for term in comparison_terms
    ):
        return answer

    def replace(match: re.Match) -> str:
        content = match.group(1)

        preceding_text = answer[
            max(0, match.start() - 110):
            match.start()
        ]

        has_price = re.search(
            r"\b(?:bs\.?|bolivianos?)\s*\d",
            _normalize(preceding_text),
        )

        if (
            content.count(",") >= 3
            and len(content) >= 55
            and has_price
            and not re.search(r"\d", content)
        ):
            return ""

        return match.group(0)

    return re.sub(
        r"\s*\(([^()]*)\)",
        replace,
        answer,
    )


def keep_documented_relationships(
    question: str,
    answer: str,
    documents: list[str],
) -> str:
    """
    Conserva información útil y limita afirmaciones
    positivas de inclusión sin evidencia textual.

    No exige JSON y no rechaza respuestas enteras
    por un fallo técnico de formato.
    """

    if not answer.strip() or not documents:
        return answer

    answer = _remove_unrequested_catalogue(
        question,
        answer,
    )

    has_inclusion_claim = (
        _INCLUSION_CLAIM.search(answer)
        or _IMPLIED_INCLUSION_CLAIM.search(answer)
    )

    if not has_inclusion_claim:
        return answer

    sentences = re.split(
        r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ])"
        r"|\n{2,}",
        answer,
    )

    accepted: list[str] = []
    rejected = 0

    for sentence in sentences:
        relation = (
            _INCLUSION_CLAIM.search(sentence)
            or _IMPLIED_INCLUSION_CLAIM.search(
                sentence
            )
        )

        if relation is None:
            accepted.append(sentence)
            continue

        prefix = _normalize(
            sentence[
                max(0, relation.start() - 16):
                relation.start()
            ]
        )

        # Conserva las negaciones explícitas:
        # no son afirmaciones positivas de inclusión.
        if prefix.endswith(
            ("no", "tampoco", "sin")
        ):
            accepted.append(sentence)
            continue

        if _has_supported_inclusion(
            sentence,
            documents,
        ):
            accepted.append(sentence)
        else:
            rejected += 1

    if rejected == 0:
        return answer

    remaining_answer = "\n\n".join(
        sentence
        for sentence in accepted
        if sentence.strip()
    ).strip()

    if remaining_answer:
        return remaining_answer

    if _INCLUSION_QUESTION.search(question):
        return (
            "La documentación disponible no confirma "
            "que esos elementos estén incluidos unos "
            "dentro de otros."
        )

    return (
        "La documentación disponible no permite "
        "confirmar esa relación de inclusión."
    )
