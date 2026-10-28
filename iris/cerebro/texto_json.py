"""Pedido de texto que volta em JSON (usado nas tarefas de bastidor: memória e vigília).
Gemini (texto) primeiro; se falhar, Groq."""

import json

from groq import Groq

from .. import ambiente, config


def pedir_json(instrucoes: str, conteudo: str) -> dict:
    erros = []
    if config.chave("GEMINI_API_KEY"):
        try:
            from google.genai import types

            from .live import _cliente

            resposta = _cliente().models.generate_content(
                model=ambiente.GEMINI_MODELO_TEXTO,
                contents=conteudo,
                config=types.GenerateContentConfig(
                    system_instruction=instrucoes, response_mime_type="application/json", temperature=0.2
                ),
            )
            return json.loads(resposta.text)
        except Exception as erro:
            erros.append(f"Gemini: {erro}")
    if config.chave("GROQ_API_KEY"):
        try:
            resposta = Groq(api_key=config.chave("GROQ_API_KEY")).chat.completions.create(
                model=ambiente.GROQ_MODELO_TEXTO,
                messages=[{"role": "system", "content": instrucoes}, {"role": "user", "content": conteudo}],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            return json.loads(resposta.choices[0].message.content)
        except Exception as erro:
            erros.append(f"Groq: {erro}")
    raise RuntimeError("; ".join(erros) or "sem chave de API")
