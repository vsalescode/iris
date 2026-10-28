"""Voz pelo Gemini (TTS da Google): bem mais natural que o edge-tts.

O áudio chega em streaming como PCM cru (16 bits, 24 kHz, mono), em pedaços
pequenos; a interface toca cada pedaço assim que chega.
"""

from google import genai
from google.genai import types

from .. import config

TAXA_AMOSTRAGEM = 24000

# Vozes pré-prontas do Gemini (falam qualquer idioma; o estilo vem do texto de instrução).
VOZES = [
    ("Aoede", "leve, descontraída"),
    ("Sulafat", "calorosa"),
    ("Leda", "jovem"),
    ("Kore", "firme"),
    ("Zephyr", "animada"),
    ("Despina", "suave"),
    ("Achernar", "macia"),
    ("Vindemiatrix", "gentil"),
    ("Callirrhoe", "tranquila"),
    ("Puck", "masculina, animada"),
    ("Charon", "masculina, informativa"),
    ("Achird", "masculina, amigável"),
]

_cliente: genai.Client | None = None


def _obter_cliente() -> genai.Client:
    global _cliente
    if _cliente is None:
        chave = config.chave("GEMINI_API_KEY")
        if not chave:
            raise RuntimeError("GEMINI_API_KEY não configurada no .env")
        _cliente = genai.Client(api_key=chave)
    return _cliente


async def sintetizar_stream(texto: str, voz: str, modelo: str, estilo: str):
    """Gera pedaços de áudio PCM (bytes) conforme o Gemini vai produzindo."""
    configuracao = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voz))
        ),
    )
    # Sem estilo, manda só o texto: instruções junto do texto às vezes são lidas em voz alta.
    conteudo = f"{estilo}\n\n{texto}" if estilo else texto
    fluxo = await _obter_cliente().aio.models.generate_content_stream(
        model=modelo, contents=conteudo, config=configuracao
    )
    async for pedaco in fluxo:
        conteudo = pedaco.candidates[0].content if pedaco.candidates else None
        for parte in (conteudo.parts or []) if conteudo else []:
            if parte.inline_data and parte.inline_data.data:
                yield parte.inline_data.data
