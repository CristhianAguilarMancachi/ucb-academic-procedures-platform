"""Pruebas aisladas del módulo RAG actual.

No utilizan red real, PostgreSQL real ni proveedores externos.
"""

import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
from uuid import uuid4

import httpx

from groq import (
    APITimeoutError,
    APIConnectionError,
    RateLimitError,
    AuthenticationError,
    APIStatusError,
)

from app.services.rag import generator
from app.services.rag import llm_client as llm
from app.services.rag.query_classifier import classify_query
from app.services.chat.query_rewrite_service import (
    rewrite_question_with_history,
)


class GroqRagTests(unittest.TestCase):

    def setUp(self):
        self.client = Mock()
        self.call = self.client.chat.completions.create

        self.call.return_value = NS(
            choices=[
                NS(
                    message=NS(
                        content="Respuesta válida"
                    ),
                    finish_reason="stop",
                )
            ],
            usage=None,
        )

        self.patcher = patch.object(
            llm,
            "get_client",
            return_value=self.client,
        )

        self.patcher.start()
        self.addCleanup(
            self.patcher.stop
        )

    def test_generacion_general_usa_metadata_y_parametros_actuales(self):
        documentos = [
            "Fragmento seleccionado"
        ]

        metadatas = [
            {
                "titulo": "Reglamento",
                "pagina_inicio": 1,
                "pagina_fin": 1,
            }
        ]

        with (
            patch.object(
                generator,
                "build_rag_prompt",
                return_value="PROMPT",
            ) as prompt,
            patch.object(
                generator,
                "complete_text",
                return_value="Respuesta válida",
            ) as complete,
            patch.object(
                generator,
                "validate_grounded_answer",
                return_value="Respuesta válida",
            ) as validate,
        ):
            resultado = generator.generate_answer(
                question="Pregunta",
                documents=documentos,
                metadatas=metadatas,
            )

        self.assertEqual(
            resultado,
            "Respuesta válida",
        )

        prompt.assert_called_once_with(
            question="Pregunta",
            documents=documentos,
            metadatas=metadatas,
            query_type="general",
        )

        complete.assert_called_once_with(
            "PROMPT",
            temperature=0.0,
            max_completion_tokens=900,
            reasoning_effort="low",
            task="generation",
        )

        validate.assert_called_once_with(
            question="Pregunta",
            answer="Respuesta válida",
            documents=documentos,
        )

    def test_procedimiento_usa_presupuesto_ampliado(self):
        with (
            patch.object(
                generator,
                "build_rag_prompt",
                return_value="PROMPT",
            ),
            patch.object(
                generator,
                "complete_text",
                return_value="Respuesta",
            ) as complete,
            patch.object(
                generator,
                "validate_grounded_answer",
                return_value="Respuesta",
            ),
        ):
            resultado = generator.generate_answer(
                question="¿Qué debo hacer?",
                documents=["Contexto"],
                metadatas=[
                    {
                        "titulo": "Documento"
                    }
                ],
                query_type="procedure",
            )

        self.assertEqual(
            resultado,
            "Respuesta",
        )

        complete.assert_called_once_with(
            "PROMPT",
            temperature=0.0,
            max_completion_tokens=1600,
            reasoning_effort="medium",
            task="generation",
        )

    def test_respuestas_incompletas_del_proveedor_son_controladas(self):
        valores = (
            None,
            NS(),
            NS(
                choices=None
            ),
            NS(
                choices=[]
            ),
            NS(
                choices=[
                    None
                ]
            ),
            NS(
                choices=[
                    NS(
                        message=None
                    )
                ]
            ),
            NS(
                choices=[
                    NS(
                        message=NS()
                    )
                ]
            ),
            NS(
                choices=[
                    NS(
                        message=NS(
                            content=None
                        )
                    )
                ]
            ),
            NS(
                choices=[
                    NS(
                        message=NS(
                            content="   "
                        )
                    )
                ]
            ),
        )

        for valor in valores:
            with self.subTest(
                valor=valor
            ):
                self.call.side_effect = None
                self.call.return_value = valor

                with self.assertRaises(
                    llm.LLMUnavailableError
                ):
                    llm.complete_text(
                        "Prompt"
                    )

    def test_errores_sdk_son_transformados_en_error_controlado(self):
        request = httpx.Request(
            "POST",
            "https://example.invalid",
        )

        errores = [
            APITimeoutError(
                request=request
            ),
            APIConnectionError(
                request=request
            ),
            RuntimeError(
                "detalle interno"
            ),
        ]

        for cls, status in (
            (
                RateLimitError,
                429,
            ),
            (
                AuthenticationError,
                401,
            ),
            (
                APIStatusError,
                500,
            ),
        ):
            errores.append(
                cls(
                    "detalle interno",
                    response=httpx.Response(
                        status,
                        request=request,
                    ),
                    body=None,
                )
            )

        for error in errores:
            with self.subTest(
                error=type(error).__name__
            ):
                self.call.side_effect = error

                with self.assertRaises(
                    llm.LLMUnavailableError
                ) as caught:
                    llm.complete_text(
                        "Prompt"
                    )

                self.assertEqual(
                    str(
                        caught.exception
                    ),
                    llm.UNAVAILABLE_MESSAGE,
                )

    def test_clasificacion_local_no_llama_groq(self):
        resultado = classify_query(
            "¿Cuáles son los requisitos "
            "para solicitar el diploma?"
        )

        self.assertEqual(
            resultado,
            "procedure",
        )

        self.call.assert_not_called()

    def test_clasificacion_fallback_usa_32_tokens(self):
        self.call.return_value = NS(
            choices=[
                NS(
                    message=NS(
                        content="general"
                    ),
                    finish_reason="stop",
                )
            ],
            usage=None,
        )

        resultado = classify_query(
            "Necesito información "
            "académica adicional"
        )

        self.assertEqual(
            resultado,
            "general",
        )

        argumentos = (
            self.call
            .call_args
            .kwargs
        )

        self.assertEqual(
            argumentos[
                "max_completion_tokens"
            ],
            32,
        )

        self.assertEqual(
            argumentos[
                "reasoning_effort"
            ],
            "low",
        )

    def test_reformulacion_solo_se_realiza_con_historial_util(self):
        self.assertEqual(
            rewrite_question_with_history(
                "Pregunta"
            ),
            "Pregunta",
        )

        self.call.assert_not_called()

        self.call.return_value = NS(
            choices=[
                NS(
                    message=NS(
                        content=(
                            "Pregunta autónoma: "
                            "Consulta completa"
                        )
                    ),
                    finish_reason="stop",
                )
            ],
            usage=None,
        )

        resultado = (
            rewrite_question_with_history(
                "¿Y eso?",
                [
                    {
                        "role": "user",
                        "content": "Tema previo",
                    }
                ],
            )
        )

        self.assertEqual(
            resultado,
            "Consulta completa",
        )

        argumentos = (
            self.call
            .call_args
            .kwargs
        )

        self.assertEqual(
            argumentos[
                "max_completion_tokens"
            ],
            128,
        )

    def test_fallo_auxiliar_tiene_fallback_seguro(self):
        self.call.side_effect = RuntimeError(
            "fallo"
        )

        self.assertEqual(
            classify_query(
                "Necesito información "
                "académica adicional"
            ),
            "general",
        )

        pregunta = "¿Y eso?"

        self.assertEqual(
            rewrite_question_with_history(
                pregunta,
                [
                    {
                        "role": "user",
                        "content": "Tema",
                    }
                ],
            ),
            pregunta,
        )


class ClientAndEndpointTests(unittest.TestCase):

    def test_health_y_ready_no_consultan_groq(self):
        from app.main import (
            health,
            ready,
        )

        with patch.object(
            llm,
            "get_client",
        ) as client:
            self.assertEqual(
                health(),
                {
                    "status": "ok"
                },
            )

            self.assertIn(
                "rag_ready",
                ready(),
            )

            client.assert_not_called()

    def test_cliente_groq_es_compartido_y_configurado(self):
        llm.get_client.cache_clear()

        self.addCleanup(
            llm.get_client.cache_clear
        )

        with patch.object(
            llm,
            "Groq",
        ) as constructor:
            primero = llm.get_client()
            segundo = llm.get_client()

            self.assertIs(
                primero,
                segundo,
            )

            constructor.assert_called_once()

            argumentos = (
                constructor
                .call_args
                .kwargs
            )

            self.assertEqual(
                argumentos["timeout"],
                llm.GROQ_TIMEOUT_SECONDS,
            )

            self.assertEqual(
                argumentos["max_retries"],
                llm.GROQ_MAX_RETRIES,
            )

            (
                constructor
                .return_value
                .chat
                .completions
                .create
                .assert_not_called()
            )

    def _ejecutar_endpoint(
        self,
        resultado_pipeline,
        *,
        error=None,
    ):
        from app.api.routes import rag
        from app.schemas.chat.chat import (
            RagChatQueryRequest,
        )

        session_id = uuid4()
        message_id = uuid4()

        save = Mock(
            side_effect=[
                NS(
                    id_message=uuid4()
                ),
                NS(
                    id_message=message_id
                ),
            ]
        )

        pipeline = (
            Mock(
                side_effect=error
            )
            if error is not None
            else Mock(
                return_value=resultado_pipeline
            )
        )

        with (
            patch.object(
                rag,
                "read_visitor_id",
                return_value=None,
            ),
            patch.object(
                rag,
                "get_or_create_chat_session",
                return_value=NS(
                    id_session=session_id
                ),
            ),
            patch.object(
                rag,
                "set_visitor_cookie",
            ),
            patch.object(
                rag,
                "build_conversation_history",
                return_value=[],
            ),
            patch.object(
                rag,
                "save_chat_message",
                save,
            ),
            patch.object(
                rag,
                "run_rag_pipeline",
                pipeline,
            ),
        ):
            respuesta = rag.query_rag(
                RagChatQueryRequest(
                    question="Pregunta"
                ),
                request=Mock(),
                response=Mock(),
                db=Mock(),
                usuario=None,
            )

        return (
            respuesta,
            save,
            session_id,
            message_id,
        )

    def test_endpoint_llm_no_disponible_devuelve_respuesta_controlada(self):
        respuesta, save, session_id, message_id = (
            self._ejecutar_endpoint(
                None,
                error=llm.LLMUnavailableError(
                    reason="test"
                ),
            )
        )

        self.assertEqual(
            respuesta.session_id,
            session_id,
        )

        self.assertEqual(
            respuesta.message_id,
            message_id,
        )

        self.assertEqual(
            respuesta.answer,
            llm.UNAVAILABLE_MESSAGE,
        )

        self.assertEqual(
            respuesta.sources,
            [],
        )

        self.assertEqual(
            save.call_count,
            2,
        )

    def test_endpoint_respuesta_vacia_usa_fallback_controlado(self):
        respuesta, save, _, _ = (
            self._ejecutar_endpoint(
                {
                    "question": "Pregunta",
                    "answer": "   ",
                    "sources": [],
                }
            )
        )

        self.assertEqual(
            respuesta.answer,
            llm.UNAVAILABLE_MESSAGE,
        )

        self.assertEqual(
            save.call_count,
            2,
        )

    def test_endpoint_exitoso_conserva_respuesta(self):
        respuesta, save, _, _ = (
            self._ejecutar_endpoint(
                {
                    "question": "Pregunta",
                    "standalone_question": (
                        "Pregunta"
                    ),
                    "answer": "Respuesta",
                    "sources": [],
                }
            )
        )

        self.assertEqual(
            respuesta.answer,
            "Respuesta",
        )

        self.assertEqual(
            respuesta.standalone_question,
            "Pregunta",
        )

        self.assertEqual(
            save.call_count,
            2,
        )


if __name__ == "__main__":
    unittest.main()
