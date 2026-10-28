"""Fala da Iris com edge-tts (vozes neurais da Microsoft, grátis, precisa de internet).

A resposta chega aos pedaços; o DivisorFrases junta os pedaços e libera uma
frase completa por vez. Cada frase vira um MP3 que a interface toca na hora,
assim ela começa a falar antes de a resposta inteira ficar pronta.
"""

import re

import edge_tts

# Vozes oferecidas na engrenagem. As "Multilingual" são de geração mais nova e
# soam mais naturais; as que não são pt-BR falam português, mas podem ter leve sotaque.
VOZES = [
    ("pt-BR-ThalitaMultilingualNeural", "Thalita · BR · feminina (multilíngue)"),
    ("pt-BR-FranciscaNeural", "Francisca · BR · feminina"),
    ("pt-BR-AntonioNeural", "Antonio · BR · masculina"),
    ("en-US-AvaMultilingualNeural", "Ava · feminina expressiva (multilíngue)"),
    ("en-US-EmmaMultilingualNeural", "Emma · feminina conversacional (multilíngue)"),
    ("fr-FR-VivienneMultilingualNeural", "Vivienne · feminina (multilíngue)"),
    ("de-DE-SeraphinaMultilingualNeural", "Seraphina · feminina (multilíngue)"),
    ("en-US-AndrewMultilingualNeural", "Andrew · masculina calorosa (multilíngue)"),
    ("en-US-BrianMultilingualNeural", "Brian · masculina casual (multilíngue)"),
    ("fr-FR-RemyMultilingualNeural", "Remy · masculina (multilíngue)"),
    ("it-IT-GiuseppeMultilingualNeural", "Giuseppe · masculina (multilíngue)"),
    ("pt-PT-RaquelNeural", "Raquel · Portugal · feminina"),
    ("pt-PT-DuarteNeural", "Duarte · Portugal · masculina"),
]

# fim de frase: . ! ? … (seguidos de aspas/parênteses opcionais) e depois um espaço
FIM_DE_FRASE = re.compile(r"[.!?…]+[\"'”)\]]*\s")
# frases muito longas sem pontuação são cortadas numa vírgula para não atrasar a fala
LIMITE_SEM_PONTO = 220


class DivisorFrases:
    def __init__(self):
        self.buffer = ""

    def adicionar(self, pedaco: str) -> list[str]:
        """Recebe um pedaço de texto e devolve as frases que ficaram completas."""
        self.buffer += pedaco
        frases = []
        while m := FIM_DE_FRASE.search(self.buffer):
            frases.append(self.buffer[: m.end()].strip())
            self.buffer = self.buffer[m.end():]
        if len(self.buffer) > LIMITE_SEM_PONTO and (corte := self.buffer.rfind(", ")) > 0:
            frases.append(self.buffer[: corte + 1].strip())
            self.buffer = self.buffer[corte + 2:]
        return [f for f in frases if f]

    def restante(self) -> str:
        """O que sobrou no fim da resposta (última frase sem ponto final)."""
        resto, self.buffer = self.buffer.strip(), ""
        return resto


def limpar_para_fala(texto: str) -> str:
    """Tira marcações de markdown que soariam estranhas faladas (*, #, `)."""
    texto = re.sub(r"[*_`#>]+", "", texto)
    texto = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", texto)  # [link](url) -> link
    return texto.strip()


async def sintetizar(texto: str, voz: str, velocidade: str = "+0%", tom: str = "+0Hz") -> bytes:
    """Transforma texto em áudio MP3. velocidade ex.: "+10%"; tom ex.: "-5Hz"."""
    texto = limpar_para_fala(texto)
    if not texto:
        return b""
    comunicador = edge_tts.Communicate(texto, voz, rate=velocidade, pitch=tom)
    audio = bytearray()
    async for parte in comunicador.stream():
        if parte["type"] == "audio":
            audio += parte["data"]
    return bytes(audio)
