"""Pruebas del proveedor textual: sin red, SQL ni carga de embeddings."""
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
from uuid import uuid4

import httpx
from fastapi import HTTPException
from groq import APITimeoutError, APIConnectionError, RateLimitError, AuthenticationError, APIStatusError

from app.services.rag import llm_client as llm
from app.services.rag.generator import generate_answer
from app.services.rag.query_classifier import classify_query
from app.services.chat.query_rewrite_service import rewrite_question_with_history


class GroqRagTests(unittest.TestCase):
    def setUp(self):
        self.client = Mock()
        self.call = self.client.chat.completions.create
        self.call.return_value = NS(choices=[NS(message=NS(content=' Respuesta válida '))])
        self.patcher = patch.object(llm, 'get_client', return_value=self.client)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_generacion_parametros_y_contexto(self):
        self.assertEqual(generate_answer('Pregunta', ['Fragmento seleccionado']), 'Respuesta válida')
        args = self.call.call_args.kwargs
        self.assertEqual(args['model'], 'openai/gpt-oss-120b')
        self.assertEqual(args['temperature'], 0.2)
        self.assertEqual(args['max_completion_tokens'], 1024)
        self.assertEqual(args['reasoning_effort'], 'low')
        self.assertFalse(args['include_reasoning'])
        self.assertFalse(args['stream'])
        self.assertNotIn('reasoning_format', args)
        self.assertNotIn('tools', args)
        self.assertIn('Fragmento seleccionado', args['messages'][0]['content'])
        self.call.assert_called_once()

    def test_respuestas_incompletas(self):
        for value in (None, NS(), NS(choices=None), NS(choices=[]),
                      NS(choices=[None]), NS(choices=[NS(message=None)]),
                      NS(choices=[NS(message=NS())]), NS(choices=[NS(message=NS(content=None))]),
                      NS(choices=[NS(message=NS(content='  '))])):
            with self.subTest(value=value):
                self.call.return_value = value
                with self.assertRaises(llm.LLMUnavailableError):
                    generate_answer('Pregunta', ['Contexto'])

    def test_errores_sdk_controlados_sin_detalles(self):
        request = httpx.Request('POST', 'https://example.invalid')
        errors = [APITimeoutError(request=request), APIConnectionError(request=request), RuntimeError('detalle interno')]
        for cls, status in ((RateLimitError, 429), (AuthenticationError, 401), (APIStatusError, 500)):
            errors.append(cls('detalle interno', response=httpx.Response(status, request=request), body=None))
        for error in errors:
            with self.subTest(error=type(error).__name__):
                self.call.side_effect = error
                with self.assertRaises(llm.LLMUnavailableError) as caught:
                    generate_answer('Pregunta', ['Contexto'])
                self.assertEqual(str(caught.exception), llm.UNAVAILABLE_MESSAGE)

    def test_clasificacion_local_no_llama(self):
        self.assertEqual(classify_query('¿Cuáles son los requisitos para solicitar el diploma?'), 'procedure')
        self.call.assert_not_called()

    def test_clasificacion_fallback(self):
        self.call.return_value = NS(choices=[NS(message=NS(content='general'))])
        self.assertEqual(classify_query('Necesito información académica adicional'), 'general')
        self.assertEqual(self.call.call_args.kwargs['max_completion_tokens'], 64)

    def test_reformulacion_condicional(self):
        self.assertEqual(rewrite_question_with_history('Pregunta'), 'Pregunta')
        self.assertEqual(rewrite_question_with_history('Pregunta', [{'role': 'user', 'content': ''}]), 'Pregunta')
        self.call.assert_not_called()
        self.call.return_value = NS(choices=[NS(message=NS(content='Pregunta autónoma: Consulta completa'))])
        self.assertEqual(rewrite_question_with_history('¿Y eso?', [{'role': 'user', 'content': 'Tema previo'}]), 'Consulta completa')
        self.assertEqual(self.call.call_args.kwargs['max_completion_tokens'], 256)

    def test_fallo_auxiliar_no_se_oculta(self):
        self.call.side_effect = RuntimeError('detalle interno')
        with self.assertRaises(llm.LLMUnavailableError):
            classify_query('Necesito información académica adicional')
        with self.assertRaises(llm.LLMUnavailableError):
            rewrite_question_with_history('¿Y eso?', [{'role': 'user', 'content': 'Tema'}])


class ClientAndEndpointTests(unittest.TestCase):
    def test_health_y_ready_no_consultan_llm(self):
        from app.main import health, ready
        with patch.object(llm, 'get_client') as client:
            self.assertEqual(health(), {'status': 'ok'})
            self.assertIn('rag_ready', ready())
            client.assert_not_called()

    def test_cliente_compartido_configurado_sin_llamada(self):
        llm.get_client.cache_clear()
        self.addCleanup(llm.get_client.cache_clear)
        with patch.object(llm, 'Groq') as constructor:
            self.assertIs(llm.get_client(), llm.get_client())
            constructor.assert_called_once()
            self.assertEqual(constructor.call_args.kwargs['timeout'], 30)
            self.assertEqual(constructor.call_args.kwargs['max_retries'], 2)
            constructor.return_value.chat.completions.create.assert_not_called()

    def test_endpoint_no_guarda_fallo_o_vacio_y_conserva_exito(self):
        from app.api.routes import rag
        from app.schemas.chat.chat import RagChatQueryRequest
        session_id = uuid4()
        with patch.object(rag, 'get_or_create_chat_session', return_value=NS(id_session=session_id)), \
             patch.object(rag, 'build_conversation_history', return_value=[]), \
             patch.object(rag, 'save_chat_message') as save, \
             patch.object(rag, 'run_rag_pipeline') as pipeline:
            payload = RagChatQueryRequest(question='Pregunta')
            pipeline.side_effect = llm.LLMUnavailableError()
            with self.assertRaises(HTTPException) as caught:
                rag.query_rag(payload, db=Mock())
            self.assertEqual(caught.exception.status_code, 503)
            self.assertEqual(caught.exception.detail, llm.UNAVAILABLE_MESSAGE)
            save.assert_not_called()
            pipeline.side_effect = None
            pipeline.return_value = {'answer': '  '}
            with self.assertRaises(HTTPException): rag.query_rag(payload, db=Mock())
            save.assert_not_called()
            pipeline.return_value = {'question': 'Pregunta', 'answer': 'Respuesta', 'sources': [{'document': 'Documento'}]}
            response = rag.query_rag(payload, db=Mock())
            self.assertEqual(response.session_id, session_id)
            self.assertEqual(response.sources[0].document, 'Documento')
            self.assertEqual(save.call_count, 2)


if __name__ == '__main__':
    unittest.main()
