"""Abrir programas (os mesmos do Menu Iniciar, inclusive apps da loja e jogos) e sites."""

import difflib
import json
import os
import subprocess
import webbrowser

from .pastas import normalizar

_apps: list[dict] | None = None


def carregar_apps(forcar: bool = False) -> list[dict]:
    """Lista os programas do Menu Iniciar (nome + ID para abrir). Fica em memória."""
    global _apps
    if _apps is None or forcar:
        comando = "[Console]::OutputEncoding=[Text.Encoding]::UTF8; Get-StartApps | ConvertTo-Json -Compress"
        saida = subprocess.run(
            ["powershell", "-NoProfile", "-Command", comando],
            capture_output=True, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW,
        ).stdout.decode("utf-8", errors="replace")
        dados = json.loads(saida or "[]")
        _apps = [{"nome": a["Name"], "id": a["AppID"]} for a in (dados if isinstance(dados, list) else [dados])]
    return _apps


def _achar(nome: str) -> tuple[dict | None, list[str]]:
    apps = carregar_apps()
    termo = normalizar(nome)
    por_nome = {normalizar(a["nome"]): a for a in apps}
    if termo in por_nome:
        return por_nome[termo], []
    comecam = [a for n, a in por_nome.items() if n.startswith(termo)]
    contem = comecam or [a for n, a in por_nome.items() if termo in n]
    if len(contem) == 1:
        return contem[0], []
    if contem:  # vários: o de nome mais curto costuma ser o principal ("Word" e não "Word 2016 Ajuda")
        contem.sort(key=lambda a: len(a["nome"]))
        return contem[0], [a["nome"] for a in contem[1:5]]
    parecidos = difflib.get_close_matches(termo, list(por_nome), n=3, cutoff=0.6)
    if parecidos:
        return por_nome[parecidos[0]], [por_nome[p]["nome"] for p in parecidos[1:]]
    return None, []


def abrir_programa(nome: str) -> dict:
    app, outros = _achar(nome)
    if not app:
        carregar_apps(forcar=True)  # pode ter sido instalado agora
        app, outros = _achar(nome)
    if not app:
        return {"erro": f"não achei nenhum programa chamado {nome} no Menu Iniciar"}
    if "://" in app["id"]:
        os.startfile(app["id"])  # ex.: jogos da Steam (steam://...)
    else:
        subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{app['id']}"])
    return {"aberto": app["nome"], **({"outros_parecidos": outros} if outros else {})}


def abrir_site(endereco: str) -> dict:
    url = endereco.strip()
    if not url:
        return {"erro": "faltou o endereço"}
    if "://" not in url:
        url = "https://" + url
    if not url.startswith(("http://", "https://")):
        return {"erro": "só abro endereços http/https"}
    webbrowser.open(url)
    return {"aberto": url}
