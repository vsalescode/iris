"""Ponto de partida: `python -m iris` sobe o servidor e abre a janela da Iris."""

import shutil
import subprocess
import threading
import webbrowser
from pathlib import Path

import uvicorn

from . import ambiente, config

CAMINHOS_EDGE = [
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
]


def abrir_janela(url: str):
    """Abre o Edge em modo app (sem barra de endereço). Usa um perfil próprio
    para o Edge lembrar a permissão do microfone."""
    caminhos = [Path(ambiente.CAMINHO_EDGE)] if ambiente.CAMINHO_EDGE else CAMINHOS_EDGE
    edge = next((str(p) for p in caminhos if p.exists()), None) or shutil.which("msedge")
    if not edge:
        webbrowser.open(url)
        return
    perfil = config.PASTA_DADOS / "edge-perfil"
    perfil.mkdir(parents=True, exist_ok=True)
    subprocess.Popen([
        edge,
        f"--app={url}",
        f"--user-data-dir={perfil}",
        "--window-size=1440,880",
        "--no-first-run",
        "--autoplay-policy=no-user-gesture-required",
    ])


def main():
    host, porta = ambiente.HOST, ambiente.PORTA
    url = f"http://{host}:{porta}"

    print(f"\n  IRIS online em {url}  (feche esta janela para desligar)\n")
    if ambiente.ABRIR_JANELA:
        # espera o servidor subir antes de abrir a janela
        threading.Timer(1.5, abrir_janela, args=(url,)).start()

    uvicorn.run("iris.servidor:app", host=host, port=porta, log_level="warning")


if __name__ == "__main__":
    main()
