from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.core.config import TOP_K
from app.repositories.chunk_repository import (
    search_similar_chunks,
)
from app.services.rag.embeddings import (
    generate_query_embeddings,
)


# ============================================================
# CONFIGURACIÓN DE RECUPERACIÓN
# ============================================================

MAX_COSINE_DISTANCE = 0.60

RRF_K = 60.0
FUSION_COMBINED_WEIGHT = 0.70
FUSION_RRF_WEIGHT = 0.20
FUSION_COVERAGE_WEIGHT = 0.10

GENERAL_QUERY_WEIGHT = 1.50
LITERAL_SUBQUERY_WEIGHT = 1.25
EXPANSION_QUERY_WEIGHT = 1.00


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
    "quién",
    "quien",
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
    "uno",
}


# ============================================================
# UTILIDADES DE TOKENIZACIÓN Y METADATOS
# ============================================================

def tokenize(
    text: str,
) -> set[str]:
    words = re.findall(
        r"[a-zA-ZáéíóúÁÉÍÓÚñÑ]+",
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


def get_document_title(
    chunk,
) -> str:
    if (
        chunk.version_documento
        and chunk.version_documento.documento
        and chunk.version_documento.documento.titulo
    ):
        return (
            chunk
            .version_documento
            .documento
            .titulo
        )

    return ""


def get_chunk_id(
    chunk,
):
    return getattr(
        chunk,
        "id_chunk_documento",
        id(chunk),
    )


# ============================================================
# SCORING HÍBRIDO
# ============================================================

def normalize_lexical_score(
    score: float,
) -> float:
    if score <= 0:
        return 0.0

    return min(
        score / 14.0,
        1.0,
    )


def semantic_similarity_from_distance(
    cosine_distance: float,
) -> float:
    similarity = (
        1.0
        - cosine_distance
    )

    return max(
        0.0,
        min(
            similarity,
            1.0,
        ),
    )


def score_chunk(
    chunk,
    query_terms: set[str],
    retrieval_hints: dict[str, list[str]] | None = None,
) -> float:
    content = chunk.contenido or ""
    subsection = chunk.subseccion or ""
    section = chunk.seccion or ""
    article_number = chunk.articulo_numero or ""

    document_title = get_document_title(
        chunk
    )

    content_terms = tokenize(
        content
    )

    subsection_terms = tokenize(
        subsection
    )

    section_terms = tokenize(
        section
    )

    title_terms = tokenize(
        document_title
    )

    score = 0.0

    score += (
        len(
            query_terms
            & content_terms
        )
        * 2.0
    )

    score += (
        len(
            query_terms
            & subsection_terms
        )
        * 3.0
    )

    score += (
        len(
            query_terms
            & section_terms
        )
        * 2.0
    )

    score += (
        len(
            query_terms
            & title_terms
        )
        * 2.0
    )

    word_count = len(
        content.split()
    )

    if word_count < 20:
        score -= 2.5

    elif word_count < 40:
        score -= 1.0

    if 40 <= word_count <= 220:
        score += 1.0

    if retrieval_hints:
        keywords = retrieval_hints.get(
            "keywords",
            [],
        )

        section_boost_terms = retrieval_hints.get(
            "section_boost_terms",
            [],
        )

        negative_terms = retrieval_hints.get(
            "negative_terms",
            [],
        )

        stage_terms = retrieval_hints.get(
            "stage_terms",
            [],
        )

        lowered_content = content.lower()
        lowered_subsection = subsection.lower()
        lowered_section = section.lower()
        lowered_article = article_number.lower()
        lowered_title = document_title.lower()

        for term in keywords:
            normalized = term.lower()

            if normalized in lowered_content:
                score += 1.0

            if normalized in lowered_subsection:
                score += 1.5

            if normalized in lowered_section:
                score += 1.0

        for term in section_boost_terms:
            normalized = term.lower()

            if normalized in lowered_subsection:
                score += 2.0

            if normalized in lowered_section:
                score += 1.5

            if normalized in lowered_article:
                score += 0.5

        for term in stage_terms:
            normalized = term.lower()

            if normalized in lowered_content:
                score += 2.0

            if normalized in lowered_subsection:
                score += 2.5

            if normalized in lowered_section:
                score += 2.0

            if normalized in lowered_title:
                score += 0.5

        for term in negative_terms:
            normalized = term.lower()

            if normalized in lowered_content:
                score -= 1.5

            if normalized in lowered_subsection:
                score -= 1.5

    return score


def rank_candidate_results(
    candidate_results,
    query: str,
    retrieval_hints: dict[str, list[str]] | None = None,
) -> list[dict]:
    query_terms = tokenize(
        query
    )

    ranked_candidates: list[dict] = []

    for (
        chunk,
        cosine_distance,
    ) in candidate_results:

        if (
            cosine_distance
            > MAX_COSINE_DISTANCE
        ):
            continue

        lexical_score = score_chunk(
            chunk=chunk,
            query_terms=query_terms,
            retrieval_hints=retrieval_hints,
        )

        semantic_score = (
            semantic_similarity_from_distance(
                cosine_distance
            )
        )

        normalized_lexical = (
            normalize_lexical_score(
                lexical_score
            )
        )

        combined_score = (
            semantic_score * 0.65
            + normalized_lexical * 0.35
        )

        ranked_candidates.append(
            {
                "chunk": chunk,
                "distance": cosine_distance,
                "semantic_score": semantic_score,
                "lexical_score": lexical_score,
                "combined_score": combined_score,
            }
        )

    ranked_candidates.sort(
        key=lambda item: (
            item["combined_score"]
        ),
        reverse=True,
    )

    return ranked_candidates


# ============================================================
# RECUPERACIÓN SEMÁNTICA BATCH
# ============================================================

def retrieve_query_batch(
    db: Session,
    queries: list[str],
    allowed_documents: list[str] | None,
    retrieval_hints_list: (
        list[dict[str, list[str]] | None]
        | None
    ) = None,
    candidate_ks: list[int] | None = None,
) -> list[list[dict]]:
    """
    Genera todos los embeddings de consulta en una sola petición
    al proveedor de embeddings y después realiza las búsquedas correspondientes en
    PostgreSQL + pgvector.

    Esto evita consumir una llamada API independiente por cada
    subconsulta generada por el retriever.
    """

    if not queries:
        return []

    cleaned_queries = [
        query.strip()
        for query in queries
    ]

    if any(
        not query
        for query in cleaned_queries
    ):
        raise ValueError(
            "Las consultas para recuperación "
            "no pueden estar vacías."
        )

    if retrieval_hints_list is None:
        retrieval_hints_list = [
            None
            for _ in cleaned_queries
        ]

    if candidate_ks is None:
        candidate_ks = [
            25
            for _ in cleaned_queries
        ]

    if (
        len(retrieval_hints_list)
        != len(cleaned_queries)
    ):
        raise ValueError(
            "retrieval_hints_list debe contener "
            "un elemento por cada consulta."
        )

    if (
        len(candidate_ks)
        != len(cleaned_queries)
    ):
        raise ValueError(
            "candidate_ks debe contener "
            "un elemento por cada consulta."
        )

    embeddings = generate_query_embeddings(
        cleaned_queries
    )

    results: list[list[dict]] = []

    for (
        query,
        embedding,
        retrieval_hints,
        candidate_k,
    ) in zip(
        cleaned_queries,
        embeddings,
        retrieval_hints_list,
        candidate_ks,
    ):
        candidates = search_similar_chunks(
            db=db,
            query_embedding=embedding,
            top_k=candidate_k,
            allowed_documents=allowed_documents,
        )

        ranked = rank_candidate_results(
            candidate_results=candidates,
            query=query,
            retrieval_hints=retrieval_hints,
        )

        results.append(
            ranked
        )

    return results


def retrieve_for_subquery(
    db: Session,
    subquery: str,
    allowed_documents: list[str] | None,
    retrieval_hints: dict[str, list[str]] | None,
    candidate_k: int = 25,
) -> list[dict]:
    """
    Mantiene la interfaz anterior para los casos que requieren
    únicamente una consulta semántica.
    """

    return retrieve_query_batch(
        db=db,
        queries=[
            subquery,
        ],
        allowed_documents=allowed_documents,
        retrieval_hints_list=[
            retrieval_hints,
        ],
        candidate_ks=[
            candidate_k,
        ],
    )[0]


# ============================================================
# FUSIÓN Y COBERTURA DE MÚLTIPLES CONSULTAS
# ============================================================

def deduplicate_queries(
    queries: list[str],
) -> list[str]:
    """
    Elimina consultas vacías o duplicadas conservando el orden.
    """

    result: list[str] = []
    seen: set[str] = set()

    for query in queries:
        cleaned = query.strip()

        if not cleaned:
            continue

        key = cleaned.casefold()

        if key in seen:
            continue

        seen.add(key)
        result.append(cleaned)

    return result


def fuse_ranked_results(
    ranked_results: list[list[dict]],
    weights: list[float] | None = None,
    per_query_limit: int = 12,
) -> list[dict]:
    """
    Fusiona varios rankings semántico-léxicos.

    La puntuación de fusión combina:
    - el mejor combined_score observado para el chunk;
    - Reciprocal Rank Fusion (RRF);
    - cobertura entre las distintas formulaciones de la consulta.

    Esto evita que el resultado dependa del orden en que se
    ejecutaron las subconsultas.
    """

    if not ranked_results:
        return []

    if weights is None:
        weights = [
            1.0
            for _ in ranked_results
        ]

    if len(weights) != len(ranked_results):
        raise ValueError(
            "weights debe contener un elemento "
            "por cada ranking."
        )

    total_weight = sum(
        max(weight, 0.0)
        for weight in weights
    )

    if total_weight <= 0:
        raise ValueError(
            "La suma de los pesos de fusión "
            "debe ser mayor que cero."
        )

    max_rrf_score = sum(
        max(weight, 0.0)
        / (RRF_K + 1.0)
        for weight in weights
    )

    fused_by_id: dict[object, dict] = {}

    for (
        ranked,
        weight,
    ) in zip(
        ranked_results,
        weights,
    ):
        if weight <= 0:
            continue

        seen_in_ranking: set[object] = set()

        for rank, item in enumerate(
            ranked[:per_query_limit],
            start=1,
        ):
            chunk_id = get_chunk_id(
                item["chunk"]
            )

            if chunk_id in seen_in_ranking:
                continue

            seen_in_ranking.add(
                chunk_id
            )

            current = fused_by_id.get(
                chunk_id
            )

            if current is None:
                current = {
                    "representative": dict(item),
                    "best_combined_score": float(
                        item["combined_score"]
                    ),
                    "rrf_score": 0.0,
                    "coverage_weight": 0.0,
                    "coverage_count": 0,
                }

                fused_by_id[
                    chunk_id
                ] = current

            elif (
                item["combined_score"]
                > current["best_combined_score"]
            ):
                current["representative"] = dict(
                    item
                )
                current["best_combined_score"] = float(
                    item["combined_score"]
                )

            current["rrf_score"] += (
                weight
                / (RRF_K + float(rank))
            )

            current["coverage_weight"] += weight
            current["coverage_count"] += 1

    fused: list[dict] = []

    for current in fused_by_id.values():
        normalized_rrf = (
            current["rrf_score"]
            / max_rrf_score
            if max_rrf_score > 0
            else 0.0
        )

        coverage_ratio = min(
            current["coverage_weight"]
            / total_weight,
            1.0,
        )

        fusion_score = (
            current["best_combined_score"]
            * FUSION_COMBINED_WEIGHT
            + normalized_rrf
            * FUSION_RRF_WEIGHT
            + coverage_ratio
            * FUSION_COVERAGE_WEIGHT
        )

        representative = dict(
            current["representative"]
        )

        representative[
            "fusion_score"
        ] = fusion_score

        representative[
            "coverage_count"
        ] = current["coverage_count"]

        fused.append(
            representative
        )

    fused.sort(
        key=lambda item: (
            item.get(
                "fusion_score",
                item["combined_score"],
            ),
            item["combined_score"],
            item["semantic_score"],
        ),
        reverse=True,
    )

    return fused


def select_with_query_coverage(
    fused_results: list[dict],
    primary_ranked_results: list[list[dict]],
    effective_top_k: int,
) -> list[dict]:
    """
    Conserva al menos un candidato fuerte por cada subpregunta
    principal cuando es posible y completa los cupos usando el
    ranking fusionado global.
    """

    if effective_top_k <= 0:
        return []

    required_ids: list[object] = []
    required_seen: set[object] = set()

    for ranked in primary_ranked_results:
        for item in ranked:
            chunk_id = get_chunk_id(
                item["chunk"]
            )

            if chunk_id in required_seen:
                continue

            required_seen.add(
                chunk_id
            )
            required_ids.append(
                chunk_id
            )
            break

        if len(required_ids) >= effective_top_k:
            break

    selected_ids: set[object] = set(
        required_ids
    )

    for item in fused_results:
        if len(selected_ids) >= effective_top_k:
            break

        selected_ids.add(
            get_chunk_id(
                item["chunk"]
            )
        )

    selected = [
        item
        for item in fused_results
        if get_chunk_id(
            item["chunk"]
        ) in selected_ids
    ]

    return selected[
        :effective_top_k
    ]


# ============================================================
# CONSULTAS COMPUESTAS
# ============================================================

def extract_multi_part_queries(
    query: str,
) -> list[str]:
    clean_query = (
        query.strip()
        .rstrip("?")
    )

    pattern = re.compile(
        r"\s+y\s+"
        r"(?="
        r"(?:"
        r"qué|que|"
        r"cómo|como|"
        r"cuánto|cuanto|"
        r"cuánta|cuanta|"
        r"cuántos|cuantos|"
        r"cuántas|cuantas|"
        r"cuál|cual|"
        r"quién|quien|"
        r"dónde|donde|"
        r"cuándo|cuando"
        r")\b"
        r")",
        flags=re.IGNORECASE,
    )

    parts = pattern.split(
        clean_query
    )

    parts = [
        part.strip()
        for part in parts
        if part.strip()
    ]

    if len(parts) <= 1:
        return []

    return parts


def contextualize_subqueries(
    subject: str,
    subqueries: list[str],
) -> list[str]:
    """
    Mantiene el sujeto principal dentro de cada subpregunta.

    Es útil cuando una segunda parte como "cómo se formaliza"
    perdería el contexto si se enviara sola al embedding.
    """

    subject_key = subject.casefold()

    contextualized: list[str] = []

    for subquery in subqueries:
        if subject_key in subquery.casefold():
            contextualized.append(
                subquery
            )
        else:
            contextualized.append(
                f"{subject}: {subquery}"
            )

    return contextualized


def retrieve_multi_part_chunks(
    db: Session,
    query: str,
    allowed_documents: list[str] | None,
    effective_top_k: int,
    retrieval_hints: dict[str, list[str]] | None,
) -> list[dict]:
    subqueries = extract_multi_part_queries(
        query
    )

    if not subqueries:
        return []

    queries = [
        *subqueries,
        query,
    ]

    batch_results = retrieve_query_batch(
        db=db,
        queries=queries,
        allowed_documents=allowed_documents,
        retrieval_hints_list=[
            retrieval_hints
            for _ in queries
        ],
        candidate_ks=[
            30
            for _ in queries
        ],
    )

    weights = [
        LITERAL_SUBQUERY_WEIGHT
        for _ in subqueries
    ] + [
        GENERAL_QUERY_WEIGHT
    ]

    fused = fuse_ranked_results(
        ranked_results=batch_results,
        weights=weights,
    )

    return select_with_query_coverage(
        fused_results=fused,
        primary_ranked_results=(
            batch_results[
                :len(subqueries)
            ]
        ),
        effective_top_k=effective_top_k,
    )


# ============================================================
# CONSULTAS DE COMPARACIÓN
# ============================================================

def extract_comparison_concepts(
    query: str,
) -> list[str]:
    q = (
        query.strip()
        .rstrip("?")
    )

    patterns = [
        (
            r"(?:diferencia|diferencias)\s+"
            r"entre\s+(.+?)\s+y\s+(.+)$"
        ),
        (
            r"(?:comparar|comparación|comparacion)\s+"
            r"(?:entre\s+)?(.+?)\s+y\s+(.+)$"
        ),
        (
            r"(.+?)\s+(?:vs\.?|versus)\s+(.+)$"
        ),
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            q,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        concepts = [
            match.group(1).strip(),
            match.group(2).strip(),
        ]

        concepts = [
            concept
            for concept in concepts
            if len(
                concept.split()
            ) <= 10
        ]

        if len(concepts) == 2:
            return concepts

    return []


def retrieve_comparison_chunks(
    db: Session,
    query: str,
    allowed_documents: list[str] | None,
    effective_top_k: int,
    retrieval_hints: dict[str, list[str]] | None,
) -> list[dict]:
    concepts = extract_comparison_concepts(
        query
    )

    if len(concepts) != 2:
        ranked = retrieve_for_subquery(
            db=db,
            subquery=query,
            allowed_documents=allowed_documents,
            retrieval_hints=retrieval_hints,
            candidate_k=max(
                effective_top_k * 6,
                30,
            ),
        )

        return ranked[
            :effective_top_k
        ]

    queries = [
        concepts[0],
        concepts[1],
        query,
    ]

    batch_results = retrieve_query_batch(
        db=db,
        queries=queries,
        allowed_documents=allowed_documents,
        retrieval_hints_list=[
            None,
            None,
            retrieval_hints,
        ],
        candidate_ks=[
            30,
            30,
            35,
        ],
    )

    fused = fuse_ranked_results(
        ranked_results=batch_results,
        weights=[
            1.35,
            1.35,
            GENERAL_QUERY_WEIGHT,
        ],
    )

    return select_with_query_coverage(
        fused_results=fused,
        primary_ranked_results=batch_results[:2],
        effective_top_k=effective_top_k,
    )


# ============================================================
# TRABAJO DIRIGIDO
# ============================================================

TRABAJO_DIRIGIDO_QUERY_PROFILES = (
    {
        "name": "inicio",
        "triggers": (
            "iniciar",
            "inicio",
            "comenzar",
            "empezar",
            "qué necesito",
            "que necesito",
            "requisitos",
            "primer paso",
            "primeros pasos",
        ),
        "expansions": (
            (
                "Trabajo Dirigido propuesta Director Carrera "
                "aprobación tutores convenio"
            ),
            (
                "Trabajo Dirigido definición problema "
                "organización profesión"
            ),
        ),
    },
    {
        "name": "propuesta",
        "triggers": (
            "propuesta",
            "presentar",
            "presento",
            "aprobación",
            "aprobacion",
            "director de carrera",
            "director del programa",
        ),
        "expansions": (
            (
                "Trabajo Dirigido propuesta presentada "
                "Director de la Carrera o Programa"
            ),
            (
                "Trabajo Dirigido propuesta aprobación "
                "comunicada por escrito"
            ),
        ),
    },
    {
        "name": "tutores",
        "triggers": (
            "tutor",
            "tutores",
            "tutoría",
            "tutoria",
            "designa",
            "designación",
            "designacion",
        ),
        "expansions": (
            (
                "Trabajo Dirigido dos tutores uno Universidad "
                "otro empresa institución"
            ),
            (
                "Trabajo Dirigido designación de tutores "
                "Universidad empresa institución"
            ),
        ),
    },
    {
        "name": "convenio",
        "triggers": (
            "convenio",
            "acuerdo",
            "formaliza",
            "formalizar",
            "formalización",
            "formalizacion",
            "condiciones",
            "horarios",
        ),
        "expansions": (
            (
                "Trabajo Dirigido convenio estudiante Universidad "
                "empresa institución horarios condiciones"
            ),
        ),
    },
    {
        "name": "finalizacion",
        "triggers": (
            "finalizar",
            "finalización",
            "finalizacion",
            "culminar",
            "concluir",
            "conclusión",
            "conclusion",
            "terminar",
            "memoria",
            "borrador",
            "informe favorable",
        ),
        "expansions": (
            (
                "Trabajo Dirigido memoria Dirección Carrera "
                "conformidad tutor treinta cincuenta páginas"
            ),
            (
                "Trabajo Dirigido trabajo concluido informe favorable "
                "borrador Director Carrera Programa"
            ),
            (
                "Trabajo Dirigido memoria final formato Carrera Programa"
            ),
        ),
    },
)


def get_trabajo_dirigido_expansions(
    query: str,
) -> list[str]:
    """
    Detecta todos los aspectos presentes en la pregunta.

    No utiliza una cadena if/elif: una misma consulta puede pedir,
    por ejemplo, tutores y convenio al mismo tiempo.
    """

    q = query.casefold()

    expansions: list[str] = []

    for profile in TRABAJO_DIRIGIDO_QUERY_PROFILES:
        if any(
            trigger.casefold() in q
            for trigger in profile["triggers"]
        ):
            expansions.extend(
                profile["expansions"]
            )

    return deduplicate_queries(
        expansions
    )


def retrieve_trabajo_dirigido_procedure(
    db: Session,
    query: str,
    allowed_documents: list[str] | None,
    effective_top_k: int,
    retrieval_hints: dict[str, list[str]] | None,
) -> list[dict]:
    literal_parts = extract_multi_part_queries(
        query
    )

    contextual_parts = contextualize_subqueries(
        subject="Trabajo Dirigido",
        subqueries=literal_parts,
    )

    expansions = get_trabajo_dirigido_expansions(
        query
    )

    queries = deduplicate_queries(
        [
            *contextual_parts,
            *expansions,
            query,
        ]
    )

    if len(queries) == 1:
        ranked = retrieve_for_subquery(
            db=db,
            subquery=query,
            allowed_documents=allowed_documents,
            retrieval_hints=retrieval_hints,
            candidate_k=max(
                effective_top_k * 8,
                40,
            ),
        )

        return ranked[
            :effective_top_k
        ]

    literal_keys = {
        part.casefold()
        for part in contextual_parts
    }

    original_key = query.strip().casefold()

    weights: list[float] = []
    candidate_ks: list[int] = []

    for current_query in queries:
        current_key = (
            current_query
            .strip()
            .casefold()
        )

        if current_key == original_key:
            weights.append(
                GENERAL_QUERY_WEIGHT
            )
            candidate_ks.append(
                40
            )

        elif current_key in literal_keys:
            weights.append(
                LITERAL_SUBQUERY_WEIGHT
            )
            candidate_ks.append(
                35
            )

        else:
            weights.append(
                EXPANSION_QUERY_WEIGHT
            )
            candidate_ks.append(
                30
            )

    batch_results = retrieve_query_batch(
        db=db,
        queries=queries,
        allowed_documents=allowed_documents,
        retrieval_hints_list=[
            retrieval_hints
            for _ in queries
        ],
        candidate_ks=candidate_ks,
    )

    fused = fuse_ranked_results(
        ranked_results=batch_results,
        weights=weights,
    )

    primary_ranked_results: list[list[dict]] = []

    if contextual_parts:
        query_index_by_key = {
            current_query
            .strip()
            .casefold(): index
            for index, current_query in enumerate(
                queries
            )
        }

        for part in contextual_parts:
            index = query_index_by_key.get(
                part.strip().casefold()
            )

            if index is not None:
                primary_ranked_results.append(
                    batch_results[index]
                )

    if primary_ranked_results:
        return select_with_query_coverage(
            fused_results=fused,
            primary_ranked_results=primary_ranked_results,
            effective_top_k=effective_top_k,
        )

    return fused[
        :effective_top_k
    ]


# ============================================================
# RECUPERACIÓN DE PROCEDIMIENTOS
# ============================================================

def has_specialized_procedure_subject(
    query: str,
) -> bool:
    """
    Identifica temas con una estrategia de recuperación propia.

    Esta decisión es independiente del tipo coarse-grained que
    haya asignado el clasificador.
    """

    q = query.casefold()

    return (
        "trabajo dirigido"
        in q
    )


def retrieve_specialized_procedure_chunks(
    db: Session,
    query: str,
    allowed_documents: list[str] | None,
    effective_top_k: int,
    retrieval_hints: dict[str, list[str]] | None,
) -> list[dict]:
    q = query.casefold()

    if "trabajo dirigido" in q:
        return retrieve_trabajo_dirigido_procedure(
            db=db,
            query=query,
            allowed_documents=allowed_documents,
            effective_top_k=effective_top_k,
            retrieval_hints=retrieval_hints,
        )

    return []


def retrieve_procedure_chunks(
    db: Session,
    query: str,
    allowed_documents: list[str] | None,
    effective_top_k: int,
    retrieval_hints: dict[str, list[str]] | None,
) -> list[dict]:
    if has_specialized_procedure_subject(
        query
    ):
        return retrieve_specialized_procedure_chunks(
            db=db,
            query=query,
            allowed_documents=allowed_documents,
            effective_top_k=effective_top_k,
            retrieval_hints=retrieval_hints,
        )

    if extract_multi_part_queries(
        query
    ):
        return retrieve_multi_part_chunks(
            db=db,
            query=query,
            allowed_documents=allowed_documents,
            effective_top_k=effective_top_k,
            retrieval_hints=retrieval_hints,
        )

    ranked = retrieve_for_subquery(
        db=db,
        subquery=query,
        allowed_documents=allowed_documents,
        retrieval_hints=retrieval_hints,
        candidate_k=max(
            effective_top_k * 8,
            40,
        ),
    )

    return ranked[
        :effective_top_k
    ]


# ============================================================
# ENTRADA PRINCIPAL DEL RETRIEVER
# ============================================================

def retrieve_relevant_chunks(
    db: Session,
    query: str,
    top_k: int | None = None,
    allowed_documents: list[str] | None = None,
    query_type: str | None = None,
    retrieval_hints: dict[str, list[str]] | None = None,
):
    if not query or not query.strip():
        return [], []

    effective_top_k = (
        top_k
        or TOP_K
    )

    multi_part_queries = (
        extract_multi_part_queries(
            query
        )
    )

    if query_type == "comparison":
        selected_candidates = (
            retrieve_comparison_chunks(
                db=db,
                query=query,
                allowed_documents=allowed_documents,
                effective_top_k=effective_top_k,
                retrieval_hints=retrieval_hints,
            )
        )

    elif has_specialized_procedure_subject(
        query
    ):
        selected_candidates = (
            retrieve_specialized_procedure_chunks(
                db=db,
                query=query,
                allowed_documents=allowed_documents,
                effective_top_k=effective_top_k,
                retrieval_hints=retrieval_hints,
            )
        )

    elif query_type == "procedure":
        selected_candidates = (
            retrieve_procedure_chunks(
                db=db,
                query=query,
                allowed_documents=allowed_documents,
                effective_top_k=effective_top_k,
                retrieval_hints=retrieval_hints,
            )
        )

    elif multi_part_queries:
        selected_candidates = (
            retrieve_multi_part_chunks(
                db=db,
                query=query,
                allowed_documents=allowed_documents,
                effective_top_k=effective_top_k,
                retrieval_hints=retrieval_hints,
            )
        )

    else:
        candidate_k = max(
            effective_top_k * 5,
            25,
        )

        selected_candidates = (
            retrieve_for_subquery(
                db=db,
                subquery=query,
                allowed_documents=allowed_documents,
                retrieval_hints=retrieval_hints,
                candidate_k=candidate_k,
            )[
                :effective_top_k
            ]
        )

    if not selected_candidates:
        return [], []

    # ========================================================
    # LOG DE DIAGNÓSTICO DEL RETRIEVAL
    # ========================================================

    print(
        "\n[RAG][RETRIEVAL] Consulta:",
        query,
    )

    print(
        "[RAG][RETRIEVAL] Tipo:",
        query_type,
    )

    print(
        "[RAG][RETRIEVAL] Documentos permitidos:",
        allowed_documents,
    )

    if multi_part_queries:
        print(
            "[RAG][RETRIEVAL] Consulta compuesta:",
            multi_part_queries,
        )

    for index, item in enumerate(
        selected_candidates,
        start=1,
    ):
        chunk = item["chunk"]

        print(
            f"[RAG][RETRIEVAL] #{index} | "
            f"doc={get_document_title(chunk)} | "
            f"articulo={chunk.articulo_numero} | "
            f"pagina={chunk.pagina_inicio} | "
            f"distance={item['distance']:.4f} | "
            f"semantic={item['semantic_score']:.4f} | "
            f"lexical={item['lexical_score']:.2f} | "
            f"combined={item['combined_score']:.4f}"
            + (
                f" | fusion={item['fusion_score']:.4f}"
                f" | coverage={item.get('coverage_count', 1)}"
                if "fusion_score" in item
                else ""
            )
        )

    # ========================================================
    # CONSTRUCCIÓN DEL CONTEXTO PARA EL GENERADOR
    # ========================================================

    documents = [
        item["chunk"].contenido
        for item in selected_candidates
    ]

    metadatas: list[dict] = []

    for item in selected_candidates:
        chunk = item["chunk"]

        metadatas.append(
            {
                "document": (
                    get_document_title(
                        chunk
                    )
                    or None
                ),
                "page": (
                    chunk.pagina_inicio
                ),
                "article_number": (
                    chunk.articulo_numero
                ),
                "chunk_strategy": (
                    chunk.estrategia_chunking
                ),
                "section": (
                    chunk.seccion
                ),
                "subsection": (
                    chunk.subseccion
                ),
                "retrieval_score": round(
                    item[
                        "combined_score"
                    ],
                    4,
                ),
            }
        )

    return (
        documents,
        metadatas,
    )
