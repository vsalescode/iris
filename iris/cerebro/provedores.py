"""Provedores de IA na nuvem. Todos têm o mesmo jeito de usar:

    async for pedaco in provedor.gerar(sistema, historico):
        ...

`historico` é uma lista de {"papel": "usuario" | "iris", "texto": "..."}.
"""

from google import genai
from google.genai import errors, types
from groq import AsyncGroq

from .. import ambiente, config


class ProvedorGemini:
    nome = "Gemini"

    def __init__(self):
        self.modelo = ambiente.GEMINI_MODELO_TEXTO
        self.pensamento = ambiente.GEMINI_PENSAMENTO or None
        self.temperatura = ambiente.TEMPERATURA
        self._cliente = None

    def disponivel(self) -> bool:
        return bool(config.chave("GEMINI_API_KEY"))

    def _config(self, sistema: str, com_pensamento: bool):
        pensar = types.ThinkingConfig(thinking_level=self.pensamento) if com_pensamento and self.pensamento else None
        return types.GenerateContentConfig(
            system_instruction=sistema, temperature=self.temperatura, thinking_config=pensar
        )

    async def gerar(self, sistema: str, historico: list[dict]):
        if self._cliente is None:
            self._cliente = genai.Client(api_key=config.chave("GEMINI_API_KEY"))
        conteudos = [
            types.Content(role="user" if m["papel"] == "usuario" else "model", parts=[types.Part(text=m["texto"])])
            for m in historico
        ]
        async def fluxo(com_pensamento: bool):
            resposta = await self._cliente.aio.models.generate_content_stream(
                model=self.modelo, contents=conteudos, config=self._config(sistema, com_pensamento)
            )
            async for pedaco in resposta:
                if pedaco.text:
                    yield pedaco.text

        enviou = False
        try:
            async for texto in fluxo(True):
                enviou = True
                yield texto
        except errors.ClientError as erro:
            # alguns modelos não aceitam o nível de pensamento configurado: tenta sem ele
            if enviou or "thinking" not in str(erro).lower():
                raise
            self.pensamento = None
            async for texto in fluxo(False):
                yield texto


class ProvedorGroq:
    nome = "Groq"

    def __init__(self):
        self.modelo = ambiente.GROQ_MODELO_TEXTO
        self.temperatura = ambiente.TEMPERATURA
        self._cliente = None

    def disponivel(self) -> bool:
        return bool(config.chave("GROQ_API_KEY"))

    async def gerar(self, sistema: str, historico: list[dict]):
        if self._cliente is None:
            self._cliente = AsyncGroq(api_key=config.chave("GROQ_API_KEY"))
        mensagens = [{"role": "system", "content": sistema}] + [
            {"role": "user" if m["papel"] == "usuario" else "assistant", "content": m["texto"]} for m in historico
        ]
        extras = {"reasoning_effort": "low"} if "gpt-oss" in self.modelo else {}
        fluxo = await self._cliente.chat.completions.create(
            model=self.modelo, messages=mensagens, temperature=self.temperatura, stream=True, **extras
        )
        async for pedaco in fluxo:
            texto = pedaco.choices[0].delta.content if pedaco.choices else None
            if texto:
                yield texto


PROVEDORES = {"gemini": ProvedorGemini, "groq": ProvedorGroq}
