"""Carrega as configurações:
- .env               -> chaves de API e ajustes técnicos (veja ambiente.py)
- configuracao.yaml  -> suas preferências (nome, voz, personalidade), editadas pela engrenagem e por voz
"""

import json
import os
import re
from pathlib import Path

import yaml
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")


def caminho(texto: str | None) -> Path | None:
    """Caminho vindo do .env. Relativo (ex.: dados/token.json) = a partir da pasta da Iris,
    para continuar funcionando se o projeto mudar de lugar. Vazio = None."""
    if not texto or not texto.strip():
        return None
    p = Path(texto.strip()).expanduser()
    return p if p.is_absolute() else RAIZ / p


ARQUIVO_CONFIG = RAIZ / "configuracao.yaml"
ARQUIVO_PERSONALIDADE = RAIZ / "personalidade.md"
PASTA_DADOS = caminho(os.getenv("IRIS_PASTA_DADOS")) or RAIZ / "dados"
PASTA_INTERFACE = Path(__file__).resolve().parent / "interface"


def carregar() -> dict:
    """Lê o configuracao.yaml e devolve um dicionário."""
    with open(ARQUIVO_CONFIG, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def chave(nome: str) -> str:
    """Lê uma chave de API do .env (ex.: chave("GEMINI_API_KEY"))."""
    return os.getenv(nome, "").strip()


def personalidade(cfg: dict) -> str:
    """Lê o personalidade.md e troca {{NOME}} pelo nome configurado."""
    texto = ARQUIVO_PERSONALIDADE.read_text(encoding="utf-8")
    nome = (cfg.get("usuario") or {}).get("nome") or "seu usuário"
    return texto.replace("{{NOME}}", nome)


def salvar_valor(secao: str, campo: str, valor) -> None:
    """Altera um único valor no yaml mantendo os comentários do arquivo.

    Ex.: salvar_valor("usuario", "nome", "João") troca a linha `nome:` dentro de `usuario:`.
    Se o campo (ou a seção) não existir, acrescenta.
    """
    texto = ARQUIVO_CONFIG.read_text(encoding="utf-8")
    # json.dumps gera um valor válido em YAML (texto entre aspas com escapes, ou número)
    valor_yaml = json.dumps(valor, ensure_ascii=False)
    padrao = re.compile(
        rf"(^{re.escape(secao)}:[ \t]*\n(?:[ \t]+.*\n|[ \t]*\n)*?[ \t]+{re.escape(campo)}:[ \t]*)"
        r"(\"[^\"]*\"|'[^']*'|[^\s#]*)",
        re.MULTILINE,
    )
    novo, trocas = padrao.subn(lambda m: m.group(1) + valor_yaml, texto, count=1)
    if not trocas:
        cabecalho = re.search(rf"^{re.escape(secao)}:[ \t]*\n", texto, re.MULTILINE)
        if cabecalho:
            novo = texto[: cabecalho.end()] + f"  {campo}: {valor_yaml}\n" + texto[cabecalho.end():]
        else:
            novo = texto.rstrip("\n") + f"\n\n{secao}:\n  {campo}: {valor_yaml}\n"
    ARQUIVO_CONFIG.write_text(novo, encoding="utf-8")
