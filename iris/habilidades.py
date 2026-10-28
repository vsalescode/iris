"""Habilidades da Iris: "manuais" em Markdown (SKILL.md) que ensinam procedimentos a ela.

Cada habilidade é uma pasta com um SKILL.md:

    ---
    nome: organizar-downloads
    descricao: Organiza a pasta Downloads em subpastas por tipo
    quando_usar: quando ele pedir para arrumar ou organizar os downloads
    ferramentas: listar_pasta, mover_arquivo
    autor: voce            # ou iris, quando ela mesma escreveu
    versao: 1
    ---
    # Organizar Downloads
    (passo a passo...)

- habilidades_ativas/     valem agora. No system prompt vai só a lista; o texto inteiro ela lê
                          com usar_habilidade quando precisa (economiza espaço).
- habilidades_propostas/  escritas por ela (propor_habilidade). Só passam a valer depois que
                          você aprovar (gaveta ou voz com confirmação). Recusadas vão para .recusadas/.

Uma habilidade NÃO dá poderes novos: só ensina a usar as ferramentas que já existem, e as
permissões continuam valendo. A Iris nunca edita uma habilidade ativa diretamente.
"""

import re
import shutil
import unicodedata
from datetime import datetime
from pathlib import Path

import yaml

from . import ambiente, config

ATIVAS = config.caminho(ambiente.HABILIDADES_ATIVAS)
PROPOSTAS = config.caminho(ambiente.HABILIDADES_PROPOSTAS)
RECUSADAS = PROPOSTAS / ".recusadas"
ARQUIVO = "SKILL.md"
CABECALHO = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


def _slug(nome: str) -> str:
    """'Organizar Downloads!' -> 'organizar-downloads'"""
    sem_acento = unicodedata.normalize("NFD", nome or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", sem_acento)).strip("-")[:50]


def _ler(pasta: Path) -> dict | None:
    arquivo = pasta / ARQUIVO
    if not arquivo.is_file():
        return None
    texto = arquivo.read_text(encoding="utf-8")
    m = CABECALHO.match(texto)
    try:
        dados = (yaml.safe_load(m.group(1)) if m else {}) or {}
    except yaml.YAMLError:
        dados = {}
    return {
        "nome": str(dados.get("nome") or pasta.name),
        "descricao": str(dados.get("descricao") or ""),
        "quando_usar": str(dados.get("quando_usar") or ""),
        "ferramentas": str(dados.get("ferramentas") or ""),
        "autor": str(dados.get("autor") or ""),
        "versao": dados.get("versao", 1),
        "corpo": (m.group(2) if m else texto).strip(),
    }


def listar(onde: str = "ativas") -> list[dict]:
    base = ATIVAS if onde == "ativas" else PROPOSTAS
    if not base.is_dir():
        return []
    habilidades = [_ler(p) for p in sorted(base.iterdir()) if p.is_dir() and not p.name.startswith((".", "_"))]
    return [h for h in habilidades if h]


def usar(nome: str) -> dict:
    """O manual completo de uma habilidade ativa."""
    h = _ler(ATIVAS / _slug(nome))
    if not h:
        return {"erro": f"não tenho a habilidade '{nome}'. Ativas: {', '.join(x['nome'] for x in listar()) or 'nenhuma'}"}
    return {"habilidade": h["nome"], "ferramentas": h["ferramentas"], "instrucoes": _com_nome(h["corpo"]),
            "lembrete": "Siga o passo a passo; as permissões e confirmações continuam valendo."}


def _com_nome(texto: str) -> str:
    """Troca o marcador {nome_usuario} pelo nome configurado (as habilidades não guardam o nome)."""
    nome = (config.carregar().get("usuario") or {}).get("nome") or "ele"
    return texto.replace("{nome_usuario}", nome)


def _montar(nome: str, descricao: str, quando_usar: str, instrucoes: str, ferramentas: str, versao: int) -> str:
    cabecalho = yaml.safe_dump({
        "nome": nome, "descricao": descricao.strip(), "quando_usar": quando_usar.strip(),
        "ferramentas": ferramentas.strip(), "autor": "iris", "versao": versao,
        "proposta_em": datetime.now().isoformat(timespec="minutes"),
    }, allow_unicode=True, sort_keys=False)
    return f"---\n{cabecalho}---\n{instrucoes.strip()}\n"


def propor(nome: str, descricao: str, quando_usar: str, instrucoes: str, ferramentas: str = "") -> dict:
    """Ela escreve uma habilidade nova (ou uma versão melhor de uma existente). Fica PROPOSTA até você aprovar."""
    slug = _slug(nome)
    if len(slug) < 3:
        return {"erro": "dê um nome curto e claro para a habilidade (ex.: 'briefing-do-dia')"}
    if not descricao.strip() or not instrucoes.strip():
        return {"erro": "faltou a descrição ou o passo a passo"}
    if len(instrucoes) > ambiente.HABILIDADES_LIMITE_TEXTO:
        return {"erro": f"o passo a passo passou de {ambiente.HABILIDADES_LIMITE_TEXTO} caracteres; resuma"}
    atual = _ler(ATIVAS / slug)
    versao = int(atual["versao"]) + 1 if atual and str(atual["versao"]).isdigit() else 1
    pasta = PROPOSTAS / slug
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / ARQUIVO).write_text(_montar(slug, descricao, quando_usar, instrucoes, ferramentas, versao), encoding="utf-8")
    resultado = {"proposta": slug, "versao": versao, "substitui_existente": bool(atual),
                 "obs": "fica proposta até ele aprovar (gaveta ou pedindo para ativar)"}
    encolheu = _encolhimento(slug)
    if encolheu:
        resultado["alerta"] = (
            f"a versão nova tem só {encolheu}% do tamanho da atual: provavelmente perdeu passos que funcionavam. "
            "Melhorar = manter tudo o que funciona e acrescentar/corrigir. Use usar_habilidade para ler a atual "
            "e proponha de novo preservando o conteúdo, ou avise isso a ele."
        )
    return resultado


def _encolhimento(slug: str) -> int | None:
    """Se a proposta for bem menor que a versão ativa, devolve o tamanho em % (senão None)."""
    nova, atual = _ler(PROPOSTAS / slug), _ler(ATIVAS / slug)
    if not nova or not atual or not atual["corpo"]:
        return None
    proporcao = len(nova["corpo"]) / len(atual["corpo"])
    return round(proporcao * 100) if proporcao < ambiente.HABILIDADES_ALERTA_ENCOLHIMENTO else None


def previa(nome: str) -> dict:
    """Para o cartão na tela antes de ativar."""
    slug = _slug(nome)
    h = _ler(PROPOSTAS / slug)
    if not h:
        raise ValueError(f"não há habilidade proposta chamada '{nome}'")
    atual = _ler(ATIVAS / slug)
    acao = f"{h['nome']} · v{h['versao']}" + (f" (substitui a v{atual['versao']})" if atual else " (nova)")
    dica = "Diga “pode ativar” ou “cancela”"
    encolheu = _encolhimento(slug)
    if encolheu:
        dica = f"⚠ Tem só {encolheu}% do tamanho da versão atual: pode ter perdido passos. " + dica
    return {"acao": acao, "para": h["descricao"], "assunto": h["quando_usar"],
            "texto": h["corpo"], "rotulos": ["O que faz", "Quando usar"], "dica": dica}


def aprovar(nome: str) -> dict:
    """Move de propostas para ativas (a versão anterior, se houver, fica guardada)."""
    slug = _slug(nome)
    origem = PROPOSTAS / slug
    if not (origem / ARQUIVO).is_file():
        return {"erro": f"não há habilidade proposta chamada '{nome}'"}
    destino = ATIVAS / slug
    destino.mkdir(parents=True, exist_ok=True)
    anterior = destino / ARQUIVO
    if anterior.is_file():
        anterior.replace(destino / f"SKILL.v{datetime.now():%Y%m%d-%H%M}.md")  # backup da versão anterior
    shutil.move(str(origem / ARQUIVO), str(anterior))
    shutil.rmtree(origem, ignore_errors=True)
    return {"ativada": slug}


def recusar(nome: str) -> dict:
    slug = _slug(nome)
    origem = PROPOSTAS / slug
    if not origem.is_dir():
        return {"erro": f"não há habilidade proposta chamada '{nome}'"}
    RECUSADAS.mkdir(parents=True, exist_ok=True)
    shutil.move(str(origem), str(RECUSADAS / f"{slug}-{datetime.now():%Y%m%d-%H%M}"))
    return {"recusada": slug}


def contexto() -> str:
    """Trecho do system prompt: a lista de habilidades (o texto inteiro ela busca quando precisar)."""
    ativas = listar("ativas")
    propostas = listar("propostas")
    linhas = ["\n## Suas habilidades (manuais de procedimentos)"]
    if ativas:
        linhas += [_com_nome(f"- {h['nome']}: {h['descricao']} (use quando: {h['quando_usar'] or '—'})") for h in ativas]
        linhas.append("- Antes de fazer algo que uma habilidade cobre, chame usar_habilidade(nome) e siga o passo a passo.")
    else:
        linhas.append("- Nenhuma ativa ainda.")
    if propostas:
        linhas.append(f"- Esperando a aprovação dele: {', '.join(h['nome'] for h in propostas)}.")
    linhas.append(
        "- Você pode se desenvolver: quando ele pedir ('aprende a fazer X', 'guarda esse jeito de fazer') ou\n"
        "  quando você resolver bem algo que vai se repetir, escreva o passo a passo com propor_habilidade\n"
        "  (curto, em tópicos, citando as ferramentas que usa) e conte a ele que propôs. Para melhorar uma\n"
        "  existente, proponha com o mesmo nome. Ela só vale depois que ele aprovar; para ativar pela voz, use\n"
        "  ativar_habilidade (ele confirma). Habilidades não dão poderes novos: as permissões continuam."
    )
    return "\n".join(linhas) + "\n"
