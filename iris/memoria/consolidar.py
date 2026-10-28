"""Ao fim de cada conversa: um modelo de texto lê a conversa e atualiza a memória
(resumo, fatos novos ou corrigidos, assuntos abertos e resolvidos)."""

import re
from datetime import datetime

from .. import ambiente, config, datas
from .. import personalidade as ajustes
from ..cerebro.texto_json import pedir_json
from . import banco

INSTRUCOES = """Você organiza a memória de longo prazo da Iris, uma assistente pessoal de voz.
Leia a conversa entre o usuário ({nome}) e a Iris e devolva SÓ um JSON neste formato:
{{
  "resumo": "2 a 4 frases sobre o que foi conversado e decidido",
  "fatos_novos": [{{"texto": "...", "categoria": "uma de {categorias}", "importancia": 1-5}}],
  "fatos_corrigidos": [{{"id": 0, "texto": "versão corrigida"}}],
  "assuntos_novos": [{{"assunto": "...", "detalhe": "...", "retomar_em": "AAAA-MM-DD ou null"}}],
  "assuntos_resolvidos": [{{"id": 0, "desfecho": "como terminou"}}],
  "personalidade": null
}}
Regras:
- Fatos: só coisas sobre o usuário que ele disse ou deixou claras (quem é, gostos, rotina, trabalho,
  pessoas próximas, projetos, preferências de como a Iris deve agir). Frases curtas, em terceira pessoa
  ("Trabalha como desenvolvedor"). Nada de suposições, nada sobre a própria Iris, e NUNCA dados
  sensíveis (senhas, números de cartão, documentos, códigos).
- Não repita fatos que já existem (lista abaixo); se um mudou, use fatos_corrigidos com o id.
- Assuntos em aberto: coisas que vão acontecer ou estão pendentes e valem uma pergunta depois
  ("entrevista quinta-feira" -> retomar_em = a sexta). Ignore pedidos já resolvidos na conversa.
- assuntos_resolvidos: só ids da lista de assuntos em aberto que a conversa resolveu.
- Listas vazias quando não houver nada. Hoje é {hoje}.
{regras_personalidade}
Fatos que já existem (id: texto):
{fatos}

Assuntos em aberto (id: assunto):
{assuntos}
"""

REGRAS_PERSONALIDADE = """- personalidade: no MÁXIMO uma proposta para a Iris ajustar o próprio jeito com ele, e só com
  evidência CLARA nesta conversa (ele riu de um tipo de piada, reclamou do tamanho das respostas,
  pediu a mesma coisa de novo, elogiou um jeito). Na dúvida, null. Formatos:
  {{"tipo": "jeito", "texto": "frase curta sobre como agir com ele", "motivo": "o que ele fez/disse"}}
  {{"tipo": "ajuste", "traco": "id do ajuste", "nivel": 0-100, "motivo": "..."}}  (no máximo 25 pontos de diferença)
  {{"tipo": "traco", "rotulo": "nome de um ajuste novo", "faixas": ["0-20%", "21-40%", "41-60%", "61-80%", "81-100%"],
    "nivel": 0-100, "motivo": "..."}}  (raro: só se nenhum ajuste existente cobre)
  Nunca proponha nada sobre confirmações, permissões, honestidade, segurança ou ofender alguém.
  Não repita o que já existe, está pendente ou foi recusado:
{atual}
"""


SENSIVEL = re.compile(
    r"(?i)\b(senha|pin|cart[aã]o|cvv|c[oó]digo|token|cpf|rg|conta|ag[eê]ncia)\b([^\n]{0,40}?)(\d[\d .\-/]{2,}\d)"
)


def censurar(texto: str) -> str:
    """Esconde números que aparecem perto de 'senha', 'cartão', 'CPF'... antes de guardar no disco."""
    return SENSIVEL.sub(lambda m: f"{m.group(1)}{m.group(2)}[oculto]", texto)


def consolidar(turnos: list[dict], inicio: str) -> dict:
    """turnos: [{"papel": "usuario"|"iris", "texto": ...}]. Devolve o que mudou na memória."""
    cfg = config.carregar()
    nome = (cfg.get("usuario") or {}).get("nome") or "usuário"
    transcricao = "\n".join(f"{nome if t['papel'] == 'usuario' else 'Iris'}: {t['texto']}" for t in turnos)
    instrucoes = INSTRUCOES.format(
        nome=nome,
        categorias=", ".join(banco.CATEGORIAS),
        hoje=f"{datetime.now():%Y-%m-%d} ({datas.dia_da_semana(datetime.now())})",
        fatos="\n".join(f"{f['id']}: {f['texto']}" for f in banco.fatos(150)) or "(nenhum)",
        assuntos="\n".join(f"{a['id']}: {a['assunto']}" for a in banco.assuntos_abertos(30)) or "(nenhum)",
        regras_personalidade=REGRAS_PERSONALIDADE.format(atual=ajustes.contexto_consolidacao(cfg))
        if ambiente.PERSONALIDADE_EVOLUIR else "- personalidade: sempre null.\n",
    )
    dados = pedir_json(instrucoes, transcricao)

    mudancas = {"fatos": [], "assuntos": [], "resolvidos": []}
    for f in dados.get("fatos_novos") or []:
        if isinstance(f, dict) and f.get("texto"):
            banco.lembrar(f["texto"], f.get("categoria", "outro"), f.get("importancia", 3), origem="conversa")
            mudancas["fatos"].append(f["texto"])
    for f in dados.get("fatos_corrigidos") or []:
        if isinstance(f, dict) and f.get("id") and f.get("texto"):
            banco.atualizar_fato(int(f["id"]), f["texto"])
            mudancas["fatos"].append(f["texto"])
    for a in dados.get("assuntos_novos") or []:
        if isinstance(a, dict) and a.get("assunto"):
            banco.abrir_assunto(a["assunto"], a.get("detalhe") or "", a.get("retomar_em"))
            mudancas["assuntos"].append(a["assunto"])
    for a in dados.get("assuntos_resolvidos") or []:
        if isinstance(a, dict) and a.get("id"):
            r = banco.fechar_assunto(int(a["id"]), a.get("desfecho") or "")
            if "fechado" in r:
                mudancas["resolvidos"].append(r["fechado"])
    resumo = (dados.get("resumo") or "").strip()
    if resumo:
        banco.salvar_conversa(inicio, censurar(resumo), censurar(transcricao))
    mudancas["resumo"] = resumo
    mudancas["personalidade"] = _propor_personalidade(dados.get("personalidade"), cfg)
    return mudancas


def _propor_personalidade(p, cfg: dict) -> str:
    """A proposta vira pendente (o personalidade.py recusa o que mexer em limite ou repetir)."""
    if not ambiente.PERSONALIDADE_EVOLUIR or not isinstance(p, dict):
        return ""
    tipo = p.get("tipo")
    if tipo == "jeito":
        r = ajustes.propor_jeito(str(p.get("texto", "")), str(p.get("motivo", "")))
    elif tipo == "ajuste":
        r = ajustes.propor_ajuste(str(p.get("traco", "")), p.get("nivel"), str(p.get("motivo", "")), cfg)
    elif tipo == "traco":
        r = ajustes.propor_traco(str(p.get("rotulo", "")), p.get("faixas") or [], p.get("nivel", 50),
                                 str(p.get("motivo", "")))
    else:
        return ""
    return r.get("resumo", "")
