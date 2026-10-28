"""Entende caminhos falados ("Downloads/nota.txt", "área de trabalho") e decide
onde a Iris pode mexer.

Regras:
- só dentro da sua pasta de usuário ou das zonas_liberadas do permissoes.yaml;
- nunca dentro das zonas_privadas;
- nunca na pasta da própria Iris (código, chaves do .env, permissões).
"""

import ctypes
import unicodedata
import uuid
from ctypes import wintypes
from pathlib import Path

from .. import config, permissoes

# Pastas especiais do Windows (o caminho real muda, ex.: quando o OneDrive as guarda)
_GUIDS = {
    "desktop": "B4BFCC3A-DB2C-424C-B029-7FE99A87C641",
    "documentos": "FDD39AD0-238F-46AF-ADB4-6C85480369C7",
    "downloads": "374DE290-123F-4565-9164-39C4925E467B",
    "imagens": "33E28130-4E1E-4676-835A-98395C3BC3BB",
    "musicas": "4BD8D571-6D19-48D3-BE97-422220080E43",
    "videos": "18989B1D-99B5-455B-841C-AB7C74E4DDFC",
}
_APELIDOS = {
    "area de trabalho": "desktop", "desktop": "desktop", "areadetrabalho": "desktop",
    "documentos": "documentos", "meus documentos": "documentos", "documents": "documentos",
    "downloads": "downloads", "download": "downloads",
    "imagens": "imagens", "fotos": "imagens", "pictures": "imagens",
    "musicas": "musicas", "musica": "musicas", "music": "musicas",
    "videos": "videos", "video": "videos",
}


class AcessoNegado(Exception):
    pass


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode()
    return " ".join(sem_acento.lower().split())


def _pasta_do_windows(guid: str) -> Path:
    class GUID(ctypes.Structure):
        _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

    u = uuid.UUID(guid)
    g = GUID(u.time_low, u.time_mid, u.time_hi_version, (ctypes.c_ubyte * 8).from_buffer_copy(u.bytes[8:]))
    ponteiro = ctypes.c_wchar_p()
    if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None, ctypes.byref(ponteiro)) != 0:
        raise OSError("pasta especial não encontrada")
    try:
        return Path(ponteiro.value)
    finally:
        ctypes.windll.ole32.CoTaskMemFree(ponteiro)


def pasta_especial(nome: str) -> Path:
    try:
        return _pasta_do_windows(_GUIDS[nome])
    except Exception:
        return Path.home() / {"desktop": "Desktop", "documentos": "Documents", "downloads": "Downloads",
                              "imagens": "Pictures", "musicas": "Music", "videos": "Videos"}[nome]


def pastas_principais() -> list[Path]:
    return [pasta_especial(n) for n in ("desktop", "documentos", "downloads")]


def resolver(caminho: str) -> Path:
    """Transforma o que a IA pediu num caminho real. Relativo = a partir da Área de Trabalho."""
    texto = (caminho or "").strip().strip('"').replace("\\", "/")
    if not texto:
        return pasta_especial("desktop")
    caminho_path = Path(texto).expanduser()
    if not caminho_path.is_absolute():
        primeiro, _, resto = texto.partition("/")
        apelido = _APELIDOS.get(normalizar(primeiro))
        if apelido:
            caminho_path = pasta_especial(apelido) / resto
        else:
            caminho_path = pasta_especial("desktop") / texto
    return caminho_path.resolve()


def _dentro(caminho: Path, pasta: Path) -> bool:
    try:
        caminho.relative_to(pasta)
        return True
    except ValueError:
        return False


def verificar(caminho: Path) -> Path:
    """Levanta AcessoNegado se a Iris não pode mexer neste caminho."""
    if _dentro(caminho, config.RAIZ.resolve()):
        raise AcessoNegado("essa é a pasta da própria Iris; ela não mexe nos próprios arquivos")
    for privada in permissoes.zonas("zonas_privadas"):
        if _dentro(caminho, privada):
            raise AcessoNegado("essa pasta está marcada como privada")
    permitidas = [Path.home().resolve(), *permissoes.zonas("zonas_liberadas")]
    if not any(_dentro(caminho, p) for p in permitidas):
        raise AcessoNegado("fora da pasta do usuário e das zonas liberadas")
    return caminho


def amigavel(caminho: Path) -> str:
    """Caminho curto para falar/mostrar (ex.: "Downloads\\nota.txt")."""
    for nome, rotulo in (("desktop", "Área de Trabalho"), ("documentos", "Documentos"), ("downloads", "Downloads"),
                         ("imagens", "Imagens"), ("musicas", "Músicas"), ("videos", "Vídeos")):
        base = pasta_especial(nome)
        if _dentro(caminho, base):
            resto = caminho.relative_to(base)
            return rotulo if str(resto) == "." else f"{rotulo}\\{resto}"
    return str(caminho)
