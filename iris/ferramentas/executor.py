"""Executa as ferramentas que a IA pede, sempre passando pelas permissões.

- AUTONOMO: executa e registra na auditoria.
- PERGUNTAR: não executa; guarda como pendente e devolve um id. A IA pergunta
  ao usuário e, se ele disser sim, chama confirmar_acao(id). O executor CONFERE
  na transcrição que o usuário realmente disse sim num turno depois da pergunta
  (a IA não consegue "se autoconfirmar").
- PROIBIDO: recusa.
Ações irreversíveis (enviar e-mail) sempre pedem confirmação, mesmo marcadas como AUTONOMO,
e o rascunho aparece na tela antes. Só UMA delas é confirmada por fala sua: um "sim" não
vale para cinco e-mails ou cinco habilidades de uma vez.
"""

import asyncio
import itertools
import re
import time
from dataclasses import dataclass
from typing import Awaitable, Callable

from .. import ambiente, permissoes
from . import IRREVERSIVEIS, POR_FUNCAO
from .pastas import AcessoNegado, normalizar, resolver, verificar

VALIDADE_PENDENTE = ambiente.CONFIRMACAO_VALIDADE_SEGUNDOS
SIM = re.compile(r"\b(sim|pode|confirm\w*|manda|vai la|ok|okay|beleza|isso|claro|faz|faca|fechou|positivo|com certeza|bora|autoriz\w*)\b")
NAO = re.compile(r"\b(nao|cancela\w*|espera|deixa pra la|deixa quieto|melhor nao|negativo)\b")


@dataclass
class Pendente:
    funcao: str
    args: dict
    turno: int
    criado: float
    previa: dict | None = None


class Executor:
    def __init__(
        self,
        turno_atual: Callable[[], int],
        fala_atual: Callable[[], str],
        fala_anterior_iris: Callable[[], str],
        avisar: Callable[[str], Awaitable[None]],
        mostrar_previa: Callable[[dict | None], Awaitable[None]] | None = None,
    ):
        """turno_atual(): nº do turno da conversa · fala_atual(): o que o usuário disse no turno atual
        fala_anterior_iris(): o que ela disse no turno anterior · avisar(texto): mostra no log de missão
        mostrar_previa(dados | None): mostra (ou esconde) o rascunho na tela."""
        self.turno_atual = turno_atual
        self.fala_atual = fala_atual
        self.fala_anterior_iris = fala_anterior_iris
        self.avisar = avisar
        self.mostrar_previa = mostrar_previa or (lambda dados: asyncio.sleep(0))
        self.pendentes: dict[str, Pendente] = {}
        self._ids = itertools.count(1)
        self._turno_irreversivel = -1  # turno em que um "sim" já foi gasto numa ação irreversível

    async def chamar(self, funcao: str, args: dict) -> dict:
        try:
            if funcao == "confirmar_acao":
                return await self._confirmar(str(args.get("id", "")))
            if funcao == "cancelar_acao":
                pendente = self.pendentes.pop(str(args.get("id", "")), None)
                if pendente:
                    await self._mostrar_proxima()
                    await self.avisar(f"Cancelado: {POR_FUNCAO[pendente.funcao].resumo(pendente.args)}.")
                return {"cancelado": bool(pendente)}

            ferramenta = POR_FUNCAO.get(funcao)
            if not ferramenta:
                return {"erro": f"ferramenta desconhecida: {funcao}"}
            # confere os caminhos antes de tudo: não adianta pedir confirmação de algo que será negado
            for chave in ("caminho", "origem", "destino", "pasta"):
                if args.get(chave):
                    verificar(resolver(args[chave]))
            nivel = permissoes.nivel(ferramenta.acao)
            if nivel == permissoes.PROIBIDO:
                await self.avisar(f"Bloqueado pelas permissões: {ferramenta.resumo(args)}.")
                return {"erro": "essa ação está PROIBIDA no permissoes.yaml; não insista"}
            irreversivel = ferramenta.acao in IRREVERSIVEIS
            if irreversivel:
                nivel = permissoes.PERGUNTAR  # enviar e-mail etc.: confirmação sempre, seja o que for no yaml
            elif nivel == permissoes.PERGUNTAR and await self._ja_confirmou():
                # ela já perguntou em voz no turno anterior e você respondeu "sim" agora
                return await self._executar(funcao, args, nivel)
            if nivel == permissoes.PERGUNTAR:
                return await self._pedir_confirmacao(ferramenta, args, irreversivel)
            return await self._executar(funcao, args, nivel)
        except AcessoNegado as erro:
            await self.avisar(f"Acesso negado: {erro}.")
            return {"erro": f"acesso negado: {erro}"}
        except KeyError as erro:
            await self.avisar(f"A IA chamou {funcao} sem o parâmetro {erro}.")
            return {"erro": f"faltou o parâmetro {erro}; chame de novo com ele"}
        except Exception as erro:
            await self.avisar(f"Erro em {funcao}: {str(erro)[:120]}")
            return {"erro": str(erro)[:200]}

    async def _pedir_confirmacao(self, ferramenta, args: dict, irreversivel: bool) -> dict:
        """Guarda a ação como pendente e diz à IA como perguntar. Se houver prévia (ex.: rascunho
        do e-mail), ela vai junto, para a IA ler exatamente o que será feito, e aparece na tela."""
        previa = await asyncio.to_thread(ferramenta.previa, args) if ferramenta.previa else None
        id_ = str(next(self._ids))
        self.pendentes[id_] = Pendente(ferramenta.funcao, args, self.turno_atual(), time.monotonic(), previa)
        await self.avisar(f"Aguardando sua confirmação: {ferramenta.resumo(args)}.")
        if previa:
            await self.mostrar_previa({**previa, "id": id_})
            instrucao = ("Leia para o usuário o rascunho (para quem vai, o assunto e o texto, de forma natural) "
                         "e pergunte se pode enviar. Só chame confirmar_acao depois que ele disser que sim. "
                         "Se ele quiser mudar algo, chame cancelar_acao e faça um novo com as mudanças.")
        else:
            instrucao = (f"Pergunte ao usuário, numa frase curta, se pode {ferramenta.resumo(args)}. "
                         "Só chame confirmar_acao depois que ele responder que sim.")
        return {"status": "aguardando_confirmacao", "id": id_, **({"rascunho": previa} if previa else {}),
                "instrucao": instrucao}

    async def _resposta_do_usuario(self) -> str:
        """'sim', 'nao' ou '' para a fala do usuário neste turno.
        A transcrição às vezes chega um pouco depois do pedido da IA: espera até 1,5 s."""
        for _ in range(15):
            fala = normalizar(self.fala_atual())
            if NAO.search(fala):
                return "nao"
            if SIM.search(fala):
                return "sim"
            await asyncio.sleep(0.1)
        return ""

    async def _ja_confirmou(self) -> bool:
        """Ela fez uma pergunta no turno anterior e você respondeu com um "sim" curto agora."""
        if not self.fala_anterior_iris().rstrip().endswith("?"):
            return False
        if len(self.fala_atual().split()) > 6:  # um pedido novo e longo não é confirmação
            return False
        return await self._resposta_do_usuario() == "sim"

    async def _confirmar(self, id_: str) -> dict:
        pendente = self.pendentes.get(id_)
        if not pendente or time.monotonic() - pendente.criado > VALIDADE_PENDENTE:
            self.pendentes.pop(id_, None)
            await self.mostrar_previa(None)
            return {"erro": "não há ação aguardando com esse id (pode ter expirado); peça de novo"}
        if self.turno_atual() <= pendente.turno:
            return {"erro": "o usuário ainda não respondeu; pergunte e espere a resposta dele"}
        resposta = await self._resposta_do_usuario()
        if resposta == "nao":
            return {"erro": "o usuário não confirmou (disse não ou pediu para esperar)"}
        if resposta != "sim":
            return {"erro": "não ouvi o usuário dizer sim; pergunte de novo"}
        irreversivel = POR_FUNCAO[pendente.funcao].acao in IRREVERSIVEIS
        if irreversivel and self._turno_irreversivel == self.turno_atual():
            await self._mostrar(pendente, id_)
            return {"erro": "esse 'sim' já foi usado na ação anterior. Uma confirmação por vez: "
                            "apresente esta (está na tela) e espere ele responder sobre ela"}
        del self.pendentes[id_]
        if irreversivel:
            self._turno_irreversivel = self.turno_atual()
        resultado = await self._executar(pendente.funcao, pendente.args, permissoes.PERGUNTAR)
        await self._mostrar_proxima()
        return resultado

    async def _mostrar(self, pendente: Pendente, id_: str) -> None:
        await self.mostrar_previa({**pendente.previa, "id": id_} if pendente.previa else None)

    async def _mostrar_proxima(self) -> None:
        """Depois de resolver uma, a próxima que ainda espera (se tiver prévia) vai para a tela."""
        agora = time.monotonic()
        validas = [(i, p) for i, p in self.pendentes.items() if agora - p.criado <= VALIDADE_PENDENTE and p.previa]
        if validas:
            await self._mostrar(validas[0][1], validas[0][0])
        else:
            await self.mostrar_previa(None)

    async def _executar(self, funcao: str, args: dict, nivel: str) -> dict:
        ferramenta = POR_FUNCAO[funcao]
        resultado = await asyncio.to_thread(ferramenta.executar, args)
        permissoes.auditar(ferramenta.acao, args, nivel, resultado)
        resumo = ferramenta.resumo(args).rstrip(".")
        if "erro" in resultado:
            await self.avisar(f"Não deu para {resumo}: {resultado['erro']}.")
        else:
            await self.avisar(f"Feito: {resumo}.")
        return resultado
