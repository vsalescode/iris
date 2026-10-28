"""Transcrição precisa com o Whisper do Groq (grátis, na nuvem).

O navegador transcreve ao vivo (rápido, mas erra mais); quando você termina
de falar, o áudio gravado passa por aqui e o texto do Whisper é o que vai
para o cérebro.
"""

import re

from groq import AsyncGroq

from .. import ambiente, config

MODELO = ambiente.WHISPER_MODELO

# Frases que o Whisper "inventa" quando ouve silêncio ou ruído (vícios do treino com vídeos)
ALUCINACOES = re.compile(
    r"^(obrigad[oa] por assistir|legendas? (pela|por) .*|inscreva-se.*|tchau,? tchau\.?|"
    r"amara\.org.*|transcri[cç][aã]o .*|\.+|♪.*)$",
    re.IGNORECASE,
)

_cliente: AsyncGroq | None = None


def disponivel() -> bool:
    return bool(config.chave("GROQ_API_KEY"))


async def transcrever(wav: bytes, nome_usuario: str = "") -> str:
    """Devolve o texto falado no áudio WAV, ou "" se não entendeu nada útil."""
    global _cliente
    if _cliente is None:
        _cliente = AsyncGroq(api_key=config.chave("GROQ_API_KEY"))
    # a "dica" ajuda o Whisper a escrever certo nomes que ele não conhece
    dica = f"Conversa em português com a Iris, assistente pessoal{' de ' + nome_usuario if nome_usuario else ''}."
    resposta = await _cliente.audio.transcriptions.create(
        file=("fala.wav", wav), model=MODELO, language="pt", prompt=dica, temperature=0
    )
    texto = (resposta.text or "").strip()
    return "" if ALUCINACOES.match(texto) else texto
