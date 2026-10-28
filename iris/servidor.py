"""Servidor da Iris: entrega a interface e conversa com ela por WebSocket.

Há dois modos de conversa:
- Live (principal): o áudio do microfone vai direto para a Gemini Live, que
  ouve, pensa e responde em voz.
- Clássico (reserva): a interface transcreve e manda texto; o cérebro (Groq/
  Gemini) responde em texto e a voz é sintetizada à parte.

Mensagens que chegam da interface (JSON):
  {"tipo": "live_iniciar"} / {"tipo": "live_encerrar"}  -> abre/fecha a conversa Live
  {"tipo": "mensagem", "texto": "..."}          -> (clássico) algo que o usuário falou
  {"tipo": "interromper"}                        -> (clássico) parar a resposta atual
  {"tipo": "salvar_config", "nome": "...", "voz": "..."}
E mensagens binárias: áudio do microfone (PCM 16 bits, 16 kHz) durante a conversa Live.

Mensagens que o servidor envia (JSON):
  estado, token, resposta_inicio, resposta_fim, audio_fim, status, config, erro
  live_status, voce_parcial, voce_final, interrompido, turno_fim (Live)
  sistema (aviso para o log de missão, ex.: ações das ferramentas)
E mensagens binárias com o áudio, na ordem. O 1º byte diz o formato:
  1 = arquivo completo MP3/WAV (edge-tts, Groq) · 2 = pedaço PCM 16 bits 24 kHz (Gemini)
"""

import asyncio
import contextlib
import io
import json
import wave
from collections import deque
from datetime import datetime

import psutil
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import ambiente, config, habilidades, oficina, permissoes
from . import personalidade as ajustes
from .cerebro.cerebro import Cerebro, montar_sistema
from .cerebro.live import ConversaLive, LiveIndisponivel
from .cerebro.live import preparar as live_preparar
from .emails import gmail
from .ferramentas import programas
from .memoria import banco, consolidar
from .proatividade import banco as pendencias
from .proatividade.vigia import Vigia
from .ferramentas.executor import Executor
from .voz import fala, falante, gemini_tts, transcricao

app = FastAPI(title="IRIS")


@app.on_event("startup")
async def _preparar():
    # em segundo plano, para a 1ª conversa não esperar: lista os programas do Menu Iniciar
    # e cria o cliente da Gemini Live
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, programas.carregar_apps)
    loop.run_in_executor(None, live_preparar)
    loop.run_in_executor(None, _buscar_meu_email)
    # a vigília roda o tempo todo, uma só para o programa inteiro
    global _tarefa_vigia
    _tarefa_vigia = asyncio.create_task(Vigia(EventosDaVigia()).rodar())
    # encomenda da oficina terminou (roda numa thread): avisa como uma pendência da vigília
    oficina.avisar = lambda pendencia: asyncio.run_coroutine_threadsafe(_oficina_terminou(pendencia), loop)


async def _oficina_terminou(pendencia: dict):
    eventos = EventosDaVigia()
    await eventos.pensamento(pendencia["resumo"] + ".")
    await eventos.pendencias_mudaram()
    await eventos.alerta(pendencia)


def _buscar_meu_email():
    """O e-mail da conta Gmail autorizada entra no system prompt ("manda pra mim")."""
    if gmail.configurado():
        try:
            gmail.meu_email()
        except Exception:
            pass  # sem internet ou autorização expirada: ela só não saberá o endereço de cabeça


# ---------- Vigília: avisa todas as janelas abertas ----------

SESSOES: set["Sessao"] = set()
PENSAMENTOS: deque[dict] = deque(maxlen=40)  # o que a vigília "pensou" por último (painel Pensamentos)
_tarefa_vigia: asyncio.Task | None = None


async def _para_todas(funcao):
    for sessao in list(SESSOES):
        with contextlib.suppress(Exception):  # janela fechando: ignora
            await funcao(sessao)


class EventosDaVigia:
    async def pensamento(self, texto: str):
        item = {"hora": datetime.now().strftime("%H:%M"), "texto": texto}
        PENSAMENTOS.append(item)
        await _para_todas(lambda s: s.enviar("pensamento", **item))

    async def pendencias_mudaram(self):
        await _para_todas(lambda s: s.enviar_pendencias())

    async def alerta(self, pendencia: dict):
        """Algo urgente: a interface decide se pode falar agora (se está livre)."""
        dados = {k: pendencia.get(k) for k in ("id", "resumo", "acao")}
        await _para_todas(lambda s: s.enviar("alerta_proativo", pendencia=dados))


class Sessao:
    """Uma conexão aberta com a interface."""

    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.cfg = config.carregar()
        self.cerebro = Cerebro(self.cfg)
        self.tarefa_resposta: asyncio.Task | None = None
        self.avisou_voz = False
        # conversa Live
        self.live: ConversaLive | None = None
        self.live_voce = ""          # o que você falou neste turno (transcrição)
        self.live_iris = ""          # o que ela respondeu neste turno
        self.live_respondendo = False
        self.live_sobra = b""        # meia amostra de áudio que ficou para o próximo pedaço
        # memória: o que já foi consolidado do histórico desta sessão
        self.consolidado_ate = 0
        self.inicio_conversa = datetime.now().isoformat(timespec="seconds")
        self.turno = 0               # conta os turnos (o executor confere confirmações por eles)
        self.ultima_fala_iris = ""   # o que ela disse no turno anterior
        self.executor = Executor(
            turno_atual=lambda: self.turno,
            fala_atual=lambda: self.live_voce,
            fala_anterior_iris=lambda: self.ultima_fala_iris,
            avisar=lambda texto: self.enviar("sistema", texto=texto),
            mostrar_previa=lambda dados: self.enviar("rascunho", rascunho=dados),
        )

    async def enviar(self, tipo: str, **dados):
        await self.ws.send_json({"tipo": tipo, **dados})

    def live_habilitada(self) -> bool:
        return bool(ambiente.LIVE_ATIVA and config.chave("GEMINI_API_KEY"))

    async def enviar_config(self):
        voz = self.cfg.get("voz") or {}
        ouvir = self.cfg.get("ouvir") or {}
        await self.enviar(
            "config",
            nome=(self.cfg.get("usuario") or {}).get("nome") or "",
            voz=voz.get("nome", "gemini:Aoede"),
            velocidade=voz.get("velocidade", "+0%"),
            tom=voz.get("tom", "+0Hz"),
            vozes=falante.lista_vozes(),
            personalidade=ajustes.lista_para_interface(self.cfg),
            # ajustes técnicos (.env) + o tempo de conversa (preferência, no configuracao.yaml)
            ouvir={
                "idioma": ambiente.IDIOMA,
                "palavras_ativacao": ambiente.PALAVRAS_ATIVACAO,
                "pausa_segundos": ambiente.PAUSA_SEGUNDOS,
                "pausa_final_segundos": ambiente.PAUSA_FINAL_SEGUNDOS,
                "conversa_segundos": ouvir.get("conversa_segundos", 60),
                "whisper": ambiente.WHISPER_ATIVO and transcricao.disponivel(),
            },
            live={
                "ativo": self.live_habilitada(),
                "interromper_falando": ambiente.LIVE_INTERROMPER_FALANDO,
                "falha_minutos": ambiente.LIVE_FALHA_TEMPORARIA_MINUTOS,
            },
        )

    async def laco_status(self):
        """A cada 2 s manda CPU/RAM e o estado da conexão com a IA."""
        psutil.cpu_percent(None)  # a primeira leitura sempre é 0; descarta
        espera = 0.5  # primeira medição sai rápido, depois a cada 2 s
        while True:
            await asyncio.sleep(espera)
            espera = 2
            if self.live and self.live.modelo:
                provedor = "Gemini Live"
                conexao = "ok" if self.live.indice_modelo == 0 else "reserva"
            else:
                provedor, conexao = self.cerebro.status()
            await self.enviar(
                "status",
                cpu=round(psutil.cpu_percent(None)),
                ram=round(psutil.virtual_memory().percent),
                provedor=provedor,
                conexao=conexao,
            )

    async def gerar_resposta(self, texto: str):
        """Pede a resposta ao cérebro. Se nenhum provedor responder, ela avisa falando."""
        try:
            async for pedaco in self.cerebro.responder(texto):
                for aviso in self.cerebro.pegar_avisos():
                    await self.enviar("erro", texto=aviso)
                yield pedaco
        except RuntimeError as erro:
            await self.enviar("erro", texto=f"Cérebro indisponível: {erro}")
            yield "Opa, perdi a conexão com meu cérebro agora. Tenta de novo daqui a pouquinho?"

    async def responder(self, texto: str):
        """Manda a resposta para a tela (token a token) e, frase a frase, para a voz."""
        await self.enviar("estado", estado="PENSANDO")
        fila_fala: asyncio.Queue[str | None] = asyncio.Queue()
        falar = asyncio.create_task(self.falar(fila_fala))
        divisor = fala.DivisorFrases()
        comecou = False
        try:
            async for pedaco in self.gerar_resposta(texto):
                if not comecou:
                    comecou = True
                    await self.enviar("estado", estado="FALANDO")
                    await self.enviar("resposta_inicio")
                await self.enviar("token", texto=pedaco)
                for frase in divisor.adicionar(pedaco):
                    fila_fala.put_nowait(frase)
            if resto := divisor.restante():
                fila_fala.put_nowait(resto)
            if comecou:
                await self.enviar("resposta_fim")
        except asyncio.CancelledError:
            falar.cancel()
            raise
        except Exception as erro:
            await self.enviar("erro", texto=f"Falha ao responder: {erro}")
        fila_fala.put_nowait(None)  # avisa que não vem mais frase
        await falar

    async def falar(self, fila: asyncio.Queue):
        """Sintetiza as frases em ordem e manda o áudio como mensagens binárias.

        Edge/Groq: uma frase por vez, para começar a falar logo.
        Gemini: a resposta inteira num pedido só, porque o plano grátis dá
        poucos pedidos de voz por dia.
        """
        cfg_voz = self.cfg["voz"]
        guardadas: list[str] = []
        while (frase := await fila.get()) is not None:
            if falante.eh_gemini(cfg_voz):
                guardadas.append(frase)
            else:
                if guardadas:  # o Gemini saiu de cena no meio: fala o que estava guardado
                    await self.falar_trecho(" ".join(guardadas), cfg_voz)
                    guardadas = []
                await self.falar_trecho(frase, cfg_voz)
        if guardadas:
            await self.falar_trecho(" ".join(guardadas), cfg_voz)
        await self.enviar("audio_fim")  # a interface volta ao IDLE quando terminar de tocar

    async def falar_trecho(self, texto: str, cfg_voz: dict):
        try:
            async for tipo, dado in falante.falar(texto, cfg_voz):
                if tipo == "aviso":
                    await self.enviar("erro", texto=dado)
                elif dado:
                    # 1º byte diz o formato: 1 = arquivo completo (MP3/WAV), 2 = pedaço PCM 24 kHz
                    await self.ws.send_bytes((b"\x01" if tipo == "arquivo" else b"\x02") + dado)
        except Exception as erro:
            if not self.avisou_voz:  # avisa uma vez só, não a cada frase
                self.avisou_voz = True
                await self.enviar("erro", texto=f"Voz indisponível ({erro}). Confira a internet.")

    def cancelar_resposta(self):
        if self.tarefa_resposta and not self.tarefa_resposta.done():
            self.tarefa_resposta.cancel()

    # ---------- conversa Live ----------

    async def iniciar_live(self):
        live = self.live
        try:
            await live.iniciar()
        except LiveIndisponivel as erro:
            if self.live is live:
                self.live = None
            await self.enviar("live_status", ativo=False, erro=str(erro))
            return
        await self.enviar("live_status", ativo=True, modelo=live.modelo)

    async def encerrar_live(self):
        live, self.live = self.live, None
        self._live_zerar_turno()
        if live:
            await live.encerrar()
            self.fim_de_conversa()

    # ---------- memória ----------

    def fim_de_conversa(self):
        """A conversa acabou: em segundo plano, a memória é atualizada com o que foi dito."""
        turnos = self.cerebro.historico[self.consolidado_ate:]
        self.consolidado_ate = len(self.cerebro.historico)
        inicio, self.inicio_conversa = self.inicio_conversa, datetime.now().isoformat(timespec="seconds")
        if sum(1 for t in turnos if t["papel"] == "usuario") >= 1 and len(turnos) >= 2:
            asyncio.create_task(self._consolidar(turnos, inicio))

    async def _consolidar(self, turnos: list[dict], inicio: str):
        try:
            mudancas = await asyncio.to_thread(consolidar.consolidar, turnos, inicio)
        except Exception as erro:
            with contextlib.suppress(Exception):
                await self.enviar("erro", texto=f"Não consegui atualizar a memória: {str(erro)[:120]}")
            return
        novos = len(mudancas["fatos"]) + len(mudancas["assuntos"]) + len(mudancas["resolvidos"])
        with contextlib.suppress(Exception):  # a janela pode ter sido fechada
            if novos:
                await self.enviar("sistema", texto=f"Memória atualizada ({novos} {'novidade' if novos == 1 else 'novidades'}).")
            await self.enviar_memoria()
            if mudancas.get("personalidade"):
                await self.enviar("sistema", texto=f"Proposta de personalidade: {mudancas['personalidade']}.")
                await self.enviar_personalidade()

    async def enviar_habilidades(self):
        """Lista da gaveta: habilidades ativas e propostas (esperando sua aprovação)."""
        ativas = await asyncio.to_thread(habilidades.listar, "ativas")
        propostas = await asyncio.to_thread(habilidades.listar, "propostas")
        await self.enviar(
            "habilidades",
            ativas=[{"nome": h["nome"], "descricao": h["descricao"]} for h in ativas],
            propostas=[{"nome": h["nome"], "descricao": h["descricao"], "versao": h["versao"]} for h in propostas],
        )

    async def gaveta_personalidade(self, tipo: str, id_):
        """Botões da gaveta → Personalidade (você mesmo decidiu: não precisa de confirmação por voz)."""
        if tipo == "ver_personalidade":
            with contextlib.suppress(ValueError):
                await self.enviar("rascunho", rascunho={**ajustes.previa(id_), "dica": "Clique fora para fechar"})
            return
        funcao, acao = {"aprovar_personalidade": (ajustes.aprovar, "iris.aprovar_personalidade"),
                        "recusar_personalidade": (ajustes.recusar, "iris.recusar_personalidade"),
                        "esquecer_jeito": (ajustes.esquecer_jeito, "iris.esquecer_jeito")}[tipo]
        resultado = await asyncio.to_thread(funcao, id_)
        permissoes.auditar(acao, {"id": id_}, "VOCÊ (gaveta)", resultado)
        await self.enviar("rascunho", rascunho=None)
        if "erro" in resultado:
            await self.enviar("sistema", texto=resultado["erro"])
        else:
            await self.enviar("sistema", texto={"aprovar_personalidade": "Personalidade atualizada.",
                                                "recusar_personalidade": "Proposta recusada.",
                                                "esquecer_jeito": "Jeito esquecido."}[tipo])
            await self.recarregar_config()
        await self.enviar_personalidade()

    async def enviar_personalidade(self):
        """Gaveta → Personalidade: propostas esperando você e o jeito que ela já aprendeu."""
        propostas = await asyncio.to_thread(ajustes.propostas)
        jeitos = await asyncio.to_thread(ajustes.jeitos)
        await self.enviar("personalidade_aprendida",
                          propostas=[{"id": p["id"], "texto": p["resumo"], "motivo": p.get("motivo", "")} for p in propostas],
                          jeitos=[{"id": j["id"], "texto": j["texto"]} for j in jeitos])

    async def enviar_pendencias(self):
        """Lista da gaveta: pendências que a vigília encontrou (dá para descartar)."""
        lista = await asyncio.to_thread(pendencias.abertas, 30)
        await self.enviar("pendencias", itens=[
            {"id": p["id"], "texto": p["resumo"], "urgente": bool(p["urgente"]), "prioridade": p["prioridade"]}
            for p in lista
        ])

    async def enviar_memoria(self):
        """Lista da gaveta: o que ela lembra (dá para apagar)."""
        fatos = await asyncio.to_thread(banco.fatos, 200)
        assuntos = await asyncio.to_thread(banco.assuntos_abertos, 30)
        await self.enviar(
            "memoria",
            fatos=[{"id": f["id"], "texto": f["texto"]} for f in fatos],
            assuntos=[{"id": a["id"], "texto": a["assunto"], "quando": a["retomar_em"] or ""} for a in assuntos],
        )

    def _live_zerar_turno(self):
        if self.live_iris.strip():
            self.ultima_fala_iris = self.live_iris.strip()
        self.live_voce = self.live_iris = ""
        self.live_respondendo = False
        self.live_sobra = b""

    def _live_guardar_no_historico(self):
        """O cérebro clássico fica sabendo da conversa, caso precise assumir."""
        if self.live_voce.strip():
            self.cerebro.historico.append({"papel": "usuario", "texto": self.live_voce.strip()})
        if self.live_iris.strip():
            self.cerebro.historico.append({"papel": "iris", "texto": self.live_iris.strip()})

    async def _live_comecar_resposta(self):
        if not self.live_respondendo:
            self.live_respondendo = True
            await self.enviar("estado", estado="FALANDO")
            await self.enviar("resposta_inicio")

    # eventos chamados pela ConversaLive
    async def voce_parcial(self, texto: str):
        self.live_voce += texto
        await self.enviar("voce_parcial", texto=self.live_voce.strip())

    async def audio(self, pcm: bytes):
        await self._live_comecar_resposta()
        pcm = self.live_sobra + pcm
        corte = len(pcm) - len(pcm) % 2  # cada amostra tem 2 bytes
        self.live_sobra = pcm[corte:]
        if corte:
            await self.ws.send_bytes(b"\x02" + pcm[:corte])

    async def iris(self, texto: str):
        await self._live_comecar_resposta()
        self.live_iris += texto
        await self.enviar("token", texto=texto)

    async def interrompido(self):
        """Você falou por cima dela: a Live já parou de gerar; a interface para de tocar."""
        if self.live_voce.strip():
            await self.enviar("voce_final", texto=self.live_voce.strip())
        await self.enviar("interrompido", texto=self.live_iris.strip())
        self._live_guardar_no_historico()
        self._live_zerar_turno()
        self.turno += 1

    async def turno_fim(self):
        if self.live_voce.strip():
            await self.enviar("voce_final", texto=self.live_voce.strip())
        if self.live_respondendo:
            await self.enviar("resposta_fim")
        await self.enviar("turno_fim")
        self._live_guardar_no_historico()
        self._live_zerar_turno()
        self.turno += 1

    async def ferramenta(self, nome: str, args: dict) -> dict:
        """A IA pediu uma ferramenta: o executor aplica as permissões."""
        resultado = await self.executor.chamar(nome, args)
        if nome in ("ajustar_personalidade", "ajustar_preferencia", "aprovar_personalidade", "esquecer_jeito") \
                and "erro" not in resultado:
            await self.recarregar_config()
        if nome in ("propor_jeito", "propor_traco", "aprovar_personalidade", "esquecer_jeito"):
            await self.enviar_personalidade()
        if nome in ("lembrar", "esquecer", "anotar_assunto", "fechar_assunto") and "erro" not in resultado:
            await self.enviar_memoria()
        if nome == "tratar_pendencia" and "erro" not in resultado:
            await self.enviar_pendencias()
        if nome in ("propor_habilidade", "ativar_habilidade") and "erro" not in resultado:
            await self.enviar_habilidades()
        return resultado

    async def recarregar_config(self):
        """Releio o configuracao.yaml (algo mudou) e aviso a interface."""
        self.cfg = config.carregar()
        self.cerebro.atualizar_config(self.cfg)
        await self.enviar_config()

    async def caiu(self, motivo: str):
        self.live = None
        self._live_zerar_turno()
        await self.enviar("live_status", ativo=False, erro=motivo)

    async def tratar_audio(self, pcm: bytes):
        if self.live:
            await self.live.enviar_audio(pcm)

    async def tratar(self, msg: dict):
        tipo = msg.get("tipo")
        if tipo == "live_iniciar":
            await self.encerrar_live()
            # o system prompt é montado na hora de (re)conectar, já com os ajustes mais recentes
            self.live = ConversaLive(
                self.cfg, lambda pesquisa: montar_sistema(self.cfg, pesquisa=pesquisa, ferramentas=True), self
            )
            asyncio.create_task(self.iniciar_live())  # não trava: o áudio que chegar já fica guardado
        elif tipo == "live_encerrar":
            await self.encerrar_live()
        elif tipo == "live_aviso":
            # a vigília achou algo urgente: a interface abriu a conversa e pede para ela avisar.
            # Vai como instrução para a Iris, NÃO como algo que você falou.
            texto = (msg.get("texto") or "").strip()
            if texto and self.live:
                with contextlib.suppress(Exception):
                    await self.live.enviar_texto(texto)
        elif tipo == "ver_habilidade":  # botão "Ver" na gaveta: mostra o texto no cartão
            nome = str(msg.get("nome", ""))
            onde = habilidades.PROPOSTAS if msg.get("proposta") else habilidades.ATIVAS
            h = await asyncio.to_thread(habilidades._ler, onde / habilidades._slug(nome))
            if h:
                await self.enviar("rascunho", rascunho={
                    "acao": f"Habilidade{' proposta' if msg.get('proposta') else ''} · v{h['versao']}",
                    "para": h["descricao"], "assunto": h["quando_usar"], "texto": h["corpo"],
                    "rotulos": ["O que faz", "Quando usar"], "dica": "Clique fora para fechar",
                })
        elif tipo in ("aprovar_habilidade", "recusar_habilidade"):  # botões da gaveta (você mesmo decidiu)
            nome = str(msg.get("nome", ""))
            aprovar = tipo == "aprovar_habilidade"
            resultado = await asyncio.to_thread(habilidades.aprovar if aprovar else habilidades.recusar, nome)
            permissoes.auditar("habilidades.ativar" if aprovar else "habilidades.recusar", {"nome": nome},
                               "VOCÊ (gaveta)", resultado)
            await self.enviar("rascunho", rascunho=None)
            await self.enviar("sistema", texto=f"Habilidade {nome} {'ativada' if aprovar else 'recusada'}."
                              if "erro" not in resultado else resultado["erro"])
            await self.enviar_habilidades()
        elif tipo in ("ver_personalidade", "aprovar_personalidade", "recusar_personalidade", "esquecer_jeito"):
            await self.gaveta_personalidade(tipo, msg.get("id"))
        elif tipo == "descartar_pendencia":  # clicou no × de uma pendência na gaveta
            await asyncio.to_thread(pendencias.mudar_status, int(msg.get("id", 0)), "descartada", "pela gaveta")
            await self.enviar_pendencias()
        elif tipo == "conversa_fim":  # conversa do modo clássico terminou
            self.fim_de_conversa()
        elif tipo == "esquecer_fato":  # clicou no × de uma lembrança na gaveta
            await asyncio.to_thread(banco.esquecer, int(msg.get("id", 0)))
            await self.enviar_memoria()
        elif tipo == "fechar_assunto":
            await asyncio.to_thread(banco.fechar_assunto, int(msg.get("id", 0)), "removido pelo usuário")
            await self.enviar_memoria()
        elif tipo == "live_texto":
            texto = (msg.get("texto") or "").strip()
            if texto and self.live:
                # conta como algo que você "disse" neste turno (ex.: digitar "pode enviar" confirma)
                self.live_voce += (" " if self.live_voce else "") + texto
                try:
                    await self.live.enviar_texto(texto)
                except Exception as erro:
                    await self.enviar("erro", texto=f"Não consegui mandar o texto para a Iris: {erro}")
        elif tipo == "mensagem":
            texto = (msg.get("texto") or "").strip()
            if texto:
                self.cancelar_resposta()
                self.tarefa_resposta = asyncio.create_task(self.responder(texto))
        elif tipo == "interromper":
            self.cancelar_resposta()
            await self.enviar("estado", estado="IDLE")
        elif tipo == "salvar_config":
            voz = self.cfg["voz"]
            config.salvar_valor("usuario", "nome", (msg.get("nome") or "").strip())
            config.salvar_valor("voz", "nome", msg.get("voz") or voz["nome"])
            config.salvar_valor("voz", "velocidade", msg.get("velocidade") or voz.get("velocidade", "+0%"))
            config.salvar_valor("voz", "tom", msg.get("tom") or voz.get("tom", "+0Hz"))
            for traco, nivel in (msg.get("personalidade") or {}).items():
                ajustes.ajustar(traco, nivel)
            await self.recarregar_config()


@app.websocket("/ws")
async def websocket(ws: WebSocket):
    await ws.accept()
    sessao = Sessao(ws)
    await sessao.enviar_config()
    await sessao.enviar("estado", estado="IDLE")
    await sessao.enviar_memoria()
    await sessao.enviar_pendencias()
    await sessao.enviar_habilidades()
    await sessao.enviar_personalidade()
    for item in PENSAMENTOS:  # o que a vigília pensou antes de a janela abrir
        await sessao.enviar("pensamento", **item)
    SESSOES.add(sessao)
    status = asyncio.create_task(sessao.laco_status())
    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            if msg.get("bytes"):
                await sessao.tratar_audio(msg["bytes"])
            elif msg.get("text"):
                await sessao.tratar(json.loads(msg["text"]))
    except WebSocketDisconnect:
        pass
    finally:
        SESSOES.discard(sessao)
        status.cancel()
        sessao.cancelar_resposta()
        await sessao.encerrar_live()
        sessao.fim_de_conversa()  # fechou a janela no meio de uma conversa: a memória guarda mesmo assim
        with contextlib.suppress(asyncio.CancelledError):
            await status


@app.post("/ouvir/transcrever")
async def transcrever(pedido: Request):
    """Recebe o áudio WAV da sua fala e devolve o texto pelo Whisper."""
    if not transcricao.disponivel():
        return JSONResponse({"texto": "", "erro": "GROQ_API_KEY não configurada"}, status_code=503)
    nome = config.carregar()["usuario"].get("nome") or ""
    try:
        texto = await asyncio.wait_for(
            transcricao.transcrever(await pedido.body(), nome), ambiente.WHISPER_ESPERA_SEGUNDOS
        )
    except Exception as erro:
        return JSONResponse({"texto": "", "erro": str(erro)[:200]}, status_code=502)
    return {"texto": texto}


_amostras: dict[tuple, Response] = {}  # amostras já geradas (poupa a cota diária do Gemini)


@app.get("/voz/amostra")
async def amostra_voz(voz: str, velocidade: str = "+0%", tom: str = "+0Hz"):
    """Fala uma frase de exemplo para você comparar vozes na engrenagem."""
    cfg = config.carregar()
    nome = cfg["usuario"].get("nome") or "tudo bem"
    chave = (voz, velocidade, tom, nome)
    if chave not in _amostras:
        resposta = await _gerar_amostra(voz, velocidade, tom, nome, cfg)
        if resposta.status_code != 200:
            return resposta
        _amostras[chave] = resposta
    return _amostras[chave]


async def _gerar_amostra(voz: str, velocidade: str, tom: str, nome: str, cfg: dict) -> Response:
    texto = f"Oi, {nome}! Eu sou a Iris. É assim que eu vou soar daqui pra frente. Gostou, ou quer testar outra?"
    cfg_voz = {**cfg["voz"], "velocidade": velocidade, "tom": tom}
    arquivo, pcm, aviso = b"", bytearray(), ""
    try:
        async for tipo, dado in falante.falar(texto, cfg_voz, voz=voz, amostra=True):
            if tipo == "arquivo":
                arquivo = dado
            elif tipo == "pcm":
                pcm += dado
            else:
                aviso = dado
    except Exception as erro:
        return Response(f"Voz indisponível: {erro}", status_code=502)
    if aviso:  # na amostra, tocar a voz reserva no lugar enganaria a comparação
        return Response(aviso, status_code=502)
    if pcm:
        # PCM cru não toca sozinho no navegador; embrulhamos num WAV
        saida = io.BytesIO()
        with wave.open(saida, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(gemini_tts.TAXA_AMOSTRAGEM)
            w.writeframes(bytes(pcm))
        return Response(saida.getvalue(), media_type="audio/wav")
    return Response(arquivo, media_type="audio/wav" if arquivo[:4] == b"RIFF" else "audio/mpeg")


# Tudo que não é /ws é arquivo da interface (index.html, css, js).
app.mount("/", StaticFiles(directory=config.PASTA_INTERFACE, html=True), name="interface")
