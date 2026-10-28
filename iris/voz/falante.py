"""Escolhe o motor de voz e cuida da reserva automática.

A voz configurada pode ser:
  "gemini:<Voz>"  -> Gemini (principal, mais natural, streaming)
  "groq:<voz>"    -> Groq Orpheus (inglês; sotaque forte em português)
  "<nome>"        -> edge-tts (instantânea, sem limite)
Se o Gemini ou o Groq falharem (sem internet, limite grátis, termos não
aceitos), a frase sai pela voz de reserva do edge-tts e aquele motor descansa
alguns minutos antes de ser tentado de novo.
"""

import time

from .. import ambiente
from . import fala, gemini_tts, groq_tts

PREFIXO_GEMINI = "gemini:"
PREFIXO_GROQ = "groq:"
DESCANSO_SEGUNDOS = ambiente.TTS_DESCANSO_SEGUNDOS
# o plano grátis dá ~10 pedidos/dia de voz POR MODELO; esgotado, o modelo espera horas
ESGOTADO_DIA_SEGUNDOS = ambiente.TTS_ESGOTADO_DIA_HORAS * 3600
ESGOTADO_MINUTO_SEGUNDOS = 60  # limite "por minuto" do Google: libera em 1 minuto

_descansa_ate: dict[str, float] = {}         # por motor (gemini, groq)
_modelo_esgotado_ate: dict[str, float] = {}  # por modelo de voz do Gemini


def lista_vozes() -> list[dict]:
    """Vozes para a engrenagem da interface, agrupadas por motor."""
    vozes = [
        {"id": PREFIXO_GEMINI + nome, "nome": f"{nome} · {desc}", "grupo": "Gemini · mais natural"}
        for nome, desc in gemini_tts.VOZES
    ]
    vozes += [{"id": i, "nome": n, "grupo": "Edge · instantânea, sem limite"} for i, n in fala.VOZES]
    vozes += [
        {"id": PREFIXO_GROQ + nome, "nome": f"{nome.capitalize()} · {desc}", "grupo": "Groq · inglês (sotaque forte)"}
        for nome, desc in groq_tts.VOZES
    ]
    return vozes


def _motor(voz: str) -> str:
    if voz.startswith(PREFIXO_GEMINI):
        return "gemini"
    if voz.startswith(PREFIXO_GROQ):
        return "groq"
    return "edge"


def _descansando(motor: str) -> bool:
    return time.monotonic() < _descansa_ate.get(motor, 0)


def _motivo(erro: Exception) -> str:
    texto = str(erro)
    if "429" in texto or "RESOURCE_EXHAUSTED" in texto:
        return "limite grátis atingido"
    if "terms" in texto:
        return "aceite os termos do modelo em console.groq.com/playground?model=canopylabs%2Forpheus-v1-english"
    return f"erro: {texto[:120]}"


async def falar(texto: str, cfg_voz: dict, voz: str | None = None, amostra: bool = False):
    """Gera o áudio de um trecho. Produz tuplas (tipo, dado):
    ("pcm", bytes) pedaço PCM 24 kHz · ("arquivo", bytes) MP3/WAV completo · ("aviso", str)
    Na amostra da engrenagem o motor é sempre tentado, mesmo descansando.
    """
    voz = voz or cfg_voz["nome"]
    motor = _motor(voz)
    texto_limpo = fala.limpar_para_fala(texto)

    if motor != "edge" and (amostra or not _descansando(motor)):
        try:
            if motor == "gemini":
                falou = False
                async for pcm in _gemini_com_rodizio(texto_limpo, voz.removeprefix(PREFIXO_GEMINI), cfg_voz):
                    falou = True
                    yield "pcm", pcm
                if falou:
                    return
                raise RuntimeError("limite grátis de hoje esgotado em todos os modelos de voz")
            yield "arquivo", await groq_tts.sintetizar(texto_limpo, voz.removeprefix(PREFIXO_GROQ))
            return
        except _FalhouNoMeio:
            return  # já falou parte do trecho: não repete com outra voz
        except Exception as erro:
            if "esgotado" in str(erro):
                _descansa_ate[motor] = min(_modelo_esgotado_ate.values(), default=time.monotonic() + DESCANSO_SEGUNDOS)
                aviso = "Voz do Gemini: limite grátis de hoje acabou. Usando a voz reserva até liberar."
            else:
                _descansa_ate[motor] = time.monotonic() + DESCANSO_SEGUNDOS
                aviso = f"Voz do {motor.capitalize()} indisponível ({_motivo(erro)}). Usando a voz reserva por alguns minutos."
            yield "aviso", aviso

    if motor != "edge":
        voz = ambiente.VOZ_RESERVA
    velocidade, tom = cfg_voz.get("velocidade", "+0%"), cfg_voz.get("tom", "+0Hz")
    # o serviço do Edge às vezes falha numa frase ("No audio was received"):
    # tenta de novo e, se falhar outra vez, usa a Francisca, que é mais estável
    for tentativa in (voz, voz, ambiente.VOZ_EDGE_ESTAVEL):
        try:
            yield "arquivo", await fala.sintetizar(texto, tentativa, velocidade, tom)
            return
        except Exception as erro:
            ultimo_erro = erro
    raise ultimo_erro


class _FalhouNoMeio(Exception):
    pass


async def _gemini_com_rodizio(texto: str, voz: str, cfg_voz: dict):
    """Tenta os modelos de voz do Gemini em ordem, pulando os que esgotaram a cota.
    Não produz nada se todos estiverem esgotados."""
    modelos = ambiente.TTS_GEMINI_MODELOS
    estilo = ambiente.TTS_ESTILO
    for modelo in modelos:
        if time.monotonic() < _modelo_esgotado_ate.get(modelo, 0):
            continue
        enviou = False
        sobra = b""  # cada amostra tem 2 bytes; um pedaço ímpar deixa 1 byte para o próximo
        try:
            async for pcm in gemini_tts.sintetizar_stream(texto, voz, modelo, estilo):
                pcm = sobra + pcm
                corte = len(pcm) - len(pcm) % 2
                sobra = pcm[corte:]
                if corte:
                    enviou = True
                    yield pcm[:corte]
            return
        except Exception as erro:
            if enviou:
                raise _FalhouNoMeio() from erro
            texto_erro = str(erro)
            sumiu = "404" in texto_erro or "NOT_FOUND" in texto_erro  # modelo aposentado pela Google
            if not sumiu and "429" not in texto_erro and "RESOURCE_EXHAUSTED" not in texto_erro:
                raise
            por_dia = sumiu or "PerDay" in texto_erro
            _modelo_esgotado_ate[modelo] = time.monotonic() + (ESGOTADO_DIA_SEGUNDOS if por_dia else ESGOTADO_MINUTO_SEGUNDOS)


def eh_gemini(cfg_voz: dict) -> bool:
    return _motor(cfg_voz["nome"]) == "gemini" and not _descansando("gemini")
