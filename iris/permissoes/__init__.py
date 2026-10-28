"""Sistema de permissões, lido do permissoes.yaml a cada consulta (suas edições valem na hora).

Níveis: AUTONOMO, PERGUNTAR, PROIBIDO. Ação não listada = PERGUNTAR.
Tudo que a Iris executa fica registrado em dados/auditoria.jsonl.
"""

import json
from datetime import datetime
from pathlib import Path

import yaml

from .. import config

ARQUIVO = config.RAIZ / "permissoes.yaml"
AUDITORIA = config.PASTA_DADOS / "auditoria.jsonl"

AUTONOMO, PERGUNTAR, PROIBIDO = "AUTONOMO", "PERGUNTAR", "PROIBIDO"


def _carregar() -> dict:
    try:
        with open(ARQUIVO, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def nivel(acao: str) -> str:
    valor = str((_carregar().get("acoes") or {}).get(acao, PERGUNTAR)).upper()
    return valor if valor in (AUTONOMO, PERGUNTAR, PROIBIDO) else PERGUNTAR


def zonas(tipo: str) -> list[Path]:
    """tipo: "zonas_liberadas" ou "zonas_privadas". Aceita apelidos ("Downloads", "Área de Trabalho")."""
    from ..ferramentas.pastas import resolver  # aqui dentro: pastas também importa este módulo

    return [resolver(str(p)) for p in (_carregar().get(tipo) or [])]


def _resumo(resultado: dict) -> dict:
    """Não guarda conteúdo de arquivos nem listas inteiras: só o essencial."""
    saida = {}
    for chave, valor in resultado.items():
        if chave in ("conteudo", "aviso"):
            continue
        saida[chave] = f"{len(valor)} itens" if isinstance(valor, list) else valor
    return saida


def auditar(acao: str, args: dict, nivel_usado: str, resultado: dict):
    """Registra uma ação executada (uma linha JSON por ação)."""
    AUDITORIA.parent.mkdir(parents=True, exist_ok=True)
    linha = {
        "hora": datetime.now().isoformat(timespec="seconds"),
        "acao": acao,
        "args": args,
        "nivel": nivel_usado,
        "ok": "erro" not in resultado,
        "resultado": _resumo(resultado),
    }
    with open(AUDITORIA, "a", encoding="utf-8") as f:
        f.write(json.dumps(linha, ensure_ascii=False, default=str) + "\n")
