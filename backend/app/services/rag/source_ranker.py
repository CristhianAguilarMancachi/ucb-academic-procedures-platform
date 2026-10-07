from __future__ import annotations

import re


STOPWORDS = {
    "qué",
    "que",
    "cuál",
    "cual",
    "cómo",
    "como",
    "cuándo",
    "cuando",
    "cuánto",
    "cuanto",
    "cuántos",
    "cuantos",
    "cuántas",
    "cuantas",
    "de",
    "la",
    "el",
    "los",
    "las",
    "un",
    "una",
    "y",
    "o",
    "a",
    "en",
    "por",
    "para",
    "si",
    "se",
    "es",
    "del",
    "al",
    "su",
    "sus",
    "tu",
    "tus",
    "con",
    "sin",
    "como",
    "más",
    "mas",
}


def tokenize(
    text: str,
) -> set[str]:
    words = re.findall(
        r"[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9]+",
        text.lower(),
    )

    return {
        word
        for word in words
        if (
            word not in STOPWORDS
            and len(word) > 2
        )
    }


def calculate_overlap(
    reference_terms: set[str],
    source_terms: set[str],
) -> float:
    if not reference_terms:
        return 0.0

    matches = (
        reference_terms
        & source_terms
    )

    return (
        len(matches)
        / len(reference_terms)
    )


def build_source_key(
    metadata: dict,
) -> tuple:
    return (
        metadata.get("document"),
        metadata.get("page"),
        metadata.get("article_number"),
        metadata.get("section"),
        metadata.get("subsection"),
    )


def rank_sources_by_support(
    *,
    question: str,
    answer: str,
    documents: list[str],
    metadatas: list[dict],
) -> list[dict]:
    if not documents or not metadatas:
        return []

    answer_terms = tokenize(
        answer
    )

    question_terms = tokenize(
        question
    )

    ranked_sources: list[dict] = []

    for index, (
        document,
        metadata,
    ) in enumerate(
        zip(
            documents,
            metadatas,
        )
    ):
        document_terms = tokenize(
            document
        )

        answer_overlap = (
            calculate_overlap(
                answer_terms,
                document_terms,
            )
        )

        question_overlap = (
            calculate_overlap(
                question_terms,
                document_terms,
            )
        )

        retrieval_score = (
            metadata.get(
                "retrieval_score",
                0.0,
            )
            or 0.0
        )

        try:
            retrieval_score = float(
                retrieval_score
            )
        except (
            TypeError,
            ValueError,
        ):
            retrieval_score = 0.0

        retrieval_score = max(
            0.0,
            min(
                retrieval_score,
                1.0,
            ),
        )

        # La respuesta final tiene mayor peso,
        # porque queremos identificar qué fuente
        # respalda realmente lo que se respondió.
        support_score = (
            answer_overlap * 0.60
            + question_overlap * 0.20
            + retrieval_score * 0.20
        )

        ranked_metadata = dict(
            metadata
        )

        ranked_metadata[
            "support_score"
        ] = round(
            support_score,
            4,
        )

        ranked_metadata[
            "_original_index"
        ] = index

        ranked_sources.append(
            ranked_metadata
        )

    ranked_sources.sort(
        key=lambda source: (
            source.get(
                "support_score",
                0.0,
            ),
            source.get(
                "retrieval_score",
                0.0,
            ),
        ),
        reverse=True,
    )

    # Evitamos repetir exactamente la misma
    # referencia varias veces.
    unique_sources: list[dict] = []
    seen: set[tuple] = set()

    for source in ranked_sources:
        key = build_source_key(
            source
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        source.pop(
            "_original_index",
            None,
        )

        unique_sources.append(
            source
        )

    return unique_sources