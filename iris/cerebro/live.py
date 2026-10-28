"""Conversa por voz com a Gemini Live: um único modelo ouve, pensa e fala.

O áudio do microfone (PCM 16 kHz) entra em tempo real; a resposta sai em
áudio (PCM 24 kHz) já em streaming, junto com a transcrição dos dois lados.
A própria Live percebe quando você terminou de falar e quando você fala por
cima dela (interrupção).

Cuidados com os limites da sessão:
- a conexão dura ~10 min: o servidor avisa antes (GoAway) e reconectamos
  usando o "token de retomada", sem perder a conversa;
- a compressão de contexto deixa a sessão durar o quanto for preciso.
"""

import asyncio
import contextlib
import time

from google import genai
from google.genai import types

from .. import ambiente, config, ferramentas

TAXA_ENTRADA = 16000  # formato exigido pela Live (PCM 16 bits, 16 kHz): não é ajuste
BYTES_POR_SEGUNDO = TAXA_ENTRADA * 2
LIMITE_BUFFER = int(BYTES_POR_SEGUNDO * ambiente.LIVE_BUFFER_SEGUNDOS)     # áudio guardado enquanto (re)conecta
LIMITE_REENVIO = int(BYTES_POR_SEGUNDO * ambiente.LIVE_REENVIO_SEGUNDOS)   # fala reenviada se a conexão cair
PESQUISA_BLOQUEADA_SEGUNDOS = ambiente.LIVE_PESQUISA_BLOQUEADA_HORAS * 3600  # a pesquisa recusou por cota

_cliente_global: genai.Client | None = None
_pesquisa_bloqueada_ate = 0.0


def _cliente() -> genai.Client:
    """Um cliente só para o programa todo (criar leva quase 1 s; fazemos isso uma vez)."""
    global _cliente_global
    if _cliente_global is None:
        _cliente_global = genai.Client(api_key=config.chave("GEMINI_API_KEY"))
    return _cliente_global


def preparar():
    """Chamado quando o servidor liga, para a 1ª conversa não esperar a criação do cliente."""
    if config.chave("GEMINI_API_KEY"):
        _cliente()


class LiveIndisponivel(Exception):
    pass


class ConversaLive:
    """Uma conversa aberta com a Live.

    `eventos` recebe as chamadas (todas async):
      voce_parcial(texto)  · audio(pcm)  · iris(texto)  · interrompido()
      turno_fim()  · caiu(motivo)  · ferramenta(nome, args) -> dict
    """

    def __init__(self, cfg: dict, montar_sistema, eventos):
        """`montar_sistema(pesquisa: bool) -> str` monta o system prompt (muda se a pesquisa estiver ligada)."""
        self.modelos = ambiente.LIVE_MODELOS
        self.voz = _voz_live(cfg)
        self.silencio_ms = ambiente.LIVE_SILENCIO_MS
        self.pesquisa = ambiente.LIVE_PESQUISA_GOOGLE and time.monotonic() >= _pesquisa_bloqueada_ate
        self.montar_sistema = montar_sistema
        self.eventos = eventos

        self.modelo: str | None = None
        self.indice_modelo = 0
        self._sessao = None
        self._handle: str | None = None   # token para retomar a sessão em nova conexão
        self._buffer = bytearray()        # áudio esperando a conexão
        self._audio_turno = bytearray()   # sua fala no turno atual (para reenviar se a conexão cair)
        self._respondendo = False         # ela já começou a responder este turno
        self._reenviar = False            # a conexão caiu: reenvia a fala do turno
        self._parar = asyncio.Event()
        self._pronto: asyncio.Future = asyncio.get_running_loop().create_future()
        self._tarefa: asyncio.Task | None = None

    # ---------- uso externo ----------

    async def iniciar(self):
        """Conecta (tentando os modelos em ordem). Levanta LiveIndisponivel se nenhum funcionar."""
        self._tarefa = asyncio.create_task(self._rodar())
        try:
            await asyncio.wait_for(asyncio.shield(self._pronto), ambiente.LIVE_ESPERA_CONEXAO_SEGUNDOS)
        except Exception as erro:
            await self.encerrar()
            raise LiveIndisponivel(_resumir(erro)) from erro

    async def enviar_audio(self, pcm: bytes):
        """Áudio do microfone (PCM 16 bits, 16 kHz, mono)."""
        self._audio_turno += pcm
        del self._audio_turno[: max(0, len(self._audio_turno) - LIMITE_REENVIO)]
        await self._enviar(pcm)

    async def enviar_texto(self, texto: str):
        """Algo que você digitou (em vez de falar): ela responde em voz do mesmo jeito."""
        await asyncio.wait_for(asyncio.shield(self._pronto), ambiente.LIVE_ESPERA_CONEXAO_SEGUNDOS)
        for _ in range(30):  # se estiver reconectando, espera a sessão voltar (até 3 s)
            if self._sessao is not None:
                break
            await asyncio.sleep(0.1)
        await self._sessao.send_client_content(
            turns=types.Content(role="user", parts=[types.Part(text=texto)]), turn_complete=True
        )

    async def _enviar(self, pcm: bytes):
        if self._sessao is None:
            self._buffer += pcm
            del self._buffer[: max(0, len(self._buffer) - LIMITE_BUFFER)]
            return
        try:
            await self._sessao.send_realtime_input(
                audio=types.Blob(data=pcm, mime_type=f"audio/pcm;rate={TAXA_ENTRADA}")
            )
        except Exception:
            self._buffer += pcm  # caiu no meio: guarda para mandar depois de reconectar

    async def encerrar(self):
        self._parar.set()
        if self._sessao is not None:
            with contextlib.suppress(Exception):
                await self._sessao.close()
        if self._tarefa and self._tarefa is not asyncio.current_task():
            with contextlib.suppress(Exception, asyncio.CancelledError):
                await asyncio.wait_for(self._tarefa, 3)

    # ---------- interno ----------

    def _config(self) -> types.LiveConnectConfig:
        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=self.montar_sistema(self.pesquisa),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=self.voz))
            ),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    silence_duration_ms=self.silencio_ms,
                    end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
                )
            ),
            context_window_compression=types.ContextWindowCompressionConfig(sliding_window=types.SlidingWindow()),
            session_resumption=types.SessionResumptionConfig(handle=self._handle),
            tools=self._ferramentas(),
        )

    def _ferramentas(self) -> list[types.Tool]:
        funcoes = [types.FunctionDeclaration(**d) for d in ferramentas.declaracoes()]
        lista = [types.Tool(function_declarations=funcoes)]
        if self.pesquisa:
            lista.append(types.Tool(google_search=types.GoogleSearch()))
        return lista

    async def _rodar(self):
        falhas_seguidas = 0
        while not self._parar.is_set():
            modelo = self.modelos[self.indice_modelo]
            try:
                async with _cliente().aio.live.connect(model=modelo, config=self._config()) as sessao:
                    self._sessao = sessao
                    self.modelo = modelo
                    falhas_seguidas = 0
                    if not self._pronto.done():
                        self._pronto.set_result(modelo)
                    if self._reenviar and self._audio_turno and not self._respondendo:
                        # a conexão anterior caiu antes de ela responder: manda sua fala de novo
                        pendente = bytes(self._audio_turno)
                    else:
                        pendente = bytes(self._buffer)
                    self._buffer, self._reenviar = bytearray(), False
                    if pendente:
                        await self._enviar(pendente)
                    await self._receber(sessao)
            except Exception as erro:
                if self._parar.is_set():
                    break
                self._reenviar = True
                if self.pesquisa and "quota" in str(erro).lower():
                    # a cota grátis da pesquisa no Google acabou: conecta sem ela (e não tenta por umas horas)
                    global _pesquisa_bloqueada_ate
                    _pesquisa_bloqueada_ate = time.monotonic() + PESQUISA_BLOQUEADA_SEGUNDOS
                    self.pesquisa = False
                    continue
                if not self._pronto.done():
                    # nunca conectou com este modelo: tenta o próximo da lista
                    self.indice_modelo += 1
                    if self.indice_modelo >= len(self.modelos):
                        self._pronto.set_exception(erro)
                        break
                    continue
                falhas_seguidas += 1
                if falhas_seguidas > 2:
                    await self.eventos.caiu(_resumir(erro))
                    break
                await asyncio.sleep(0.5)
            finally:
                self._sessao = None
        self._parar.set()

    async def _receber(self, sessao):
        """Lê as mensagens turno a turno. Volta para reconectar quando o servidor avisa (GoAway)."""
        trocar_conexao = False
        while not self._parar.is_set():
            recebeu = False
            async for msg in sessao.receive():
                recebeu = True
                if msg.session_resumption_update and msg.session_resumption_update.new_handle:
                    self._handle = msg.session_resumption_update.new_handle
                if msg.go_away is not None:
                    trocar_conexao = True  # termina este turno e reconecta
                if msg.tool_call:
                    await self._ferramenta(sessao, msg.tool_call)
                if msg.server_content:
                    await self._conteudo(msg.server_content)
            if not recebeu:
                raise ConnectionError("conexão com a Live fechada")
            if trocar_conexao:
                return

    async def _ferramenta(self, sessao, pedido: types.LiveServerToolCall):
        """A IA pediu para usar ferramentas: executa (via permissões) e devolve o resultado."""
        respostas = []
        for chamada in pedido.function_calls or []:
            resultado = await self.eventos.ferramenta(chamada.name, dict(chamada.args or {}))
            respostas.append(types.FunctionResponse(id=chamada.id, name=chamada.name, response=resultado))
        if respostas:
            await sessao.send_tool_response(function_responses=respostas)

    def _comecou_a_responder(self):
        if not self._respondendo:
            self._respondendo = True
            self._audio_turno.clear()  # sua fala já foi entendida: não precisa mais reenviar

    async def _conteudo(self, sc: types.LiveServerContent):
        if sc.interrupted:
            self._respondendo = False
            await self.eventos.interrompido()
        if sc.input_transcription and sc.input_transcription.text:
            await self.eventos.voce_parcial(sc.input_transcription.text)
        if sc.model_turn:
            for parte in sc.model_turn.parts or []:
                if parte.inline_data and parte.inline_data.data and not parte.thought:
                    self._comecou_a_responder()
                    await self.eventos.audio(parte.inline_data.data)
        if sc.output_transcription and sc.output_transcription.text:
            self._comecou_a_responder()
            await self.eventos.iris(sc.output_transcription.text)
        if sc.turn_complete:
            self._respondendo = False
            self._audio_turno.clear()
            await self.eventos.turno_fim()


def _voz_live(cfg: dict) -> str:
    """A Live só fala com as vozes do Gemini: usa a escolhida na engrenagem se for uma delas."""
    if ambiente.LIVE_VOZ:
        return ambiente.LIVE_VOZ
    nome = (cfg.get("voz") or {}).get("nome", "")
    return nome.removeprefix("gemini:") if nome.startswith("gemini:") else "Aoede"


def _resumir(erro: Exception) -> str:
    texto = str(erro) or type(erro).__name__
    if "429" in texto or "RESOURCE_EXHAUSTED" in texto:
        return "limite grátis atingido"
    if isinstance(erro, TimeoutError):
        return "demorou demais para conectar"
    return texto[:160]
