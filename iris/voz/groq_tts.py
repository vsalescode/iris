"""Voz pelo Groq (modelo Orpheus). Só existe em inglês e árabe: fala português
com sotaque forte. Antes do 1º uso é preciso aceitar os termos do modelo em
https://console.groq.com/playground?model=canopylabs%2Forpheus-v1-english
"""

import inspect

from groq import AsyncGroq

from .. import ambiente, config

MODELO = ambiente.GROQ_TTS_MODELO

VOZES = [
    ("autumn", "feminina"),
    ("diana", "feminina"),
    ("hannah", "feminina"),
    ("austin", "masculina"),
    ("daniel", "masculina"),
    ("troy", "masculina"),
]

_cliente: AsyncGroq | None = None


async def sintetizar(texto: str, voz: str) -> bytes:
    """Devolve um arquivo WAV completo."""
    global _cliente
    if _cliente is None:
        chave = config.chave("GROQ_API_KEY")
        if not chave:
            raise RuntimeError("GROQ_API_KEY não configurada no .env")
        _cliente = AsyncGroq(api_key=chave)
    resposta = await _cliente.audio.speech.create(model=MODELO, voice=voz, input=texto, response_format="wav")
    dados = resposta.read()
    return await dados if inspect.isawaitable(dados) else dados
