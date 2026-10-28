"""Fila de pendências e o que a vigília já viu (no mesmo banco da memória, dados/iris.db).

pendencias -> coisas que ela notou e acha que você precisa saber ou decidir
vistos     -> e-mails e arquivos que ela já olhou (para só reagir ao que é novo)
"""

import sqlite3
from contextlib import closing
from datetime import datetime

from ..memoria import banco as memoria

ESQUEMA = """
CREATE TABLE IF NOT EXISTS pendencias (
    id          INTEGER PRIMARY KEY,
    origem      TEXT NOT NULL,                   -- 'email' ou 'arquivo'
    referencia  TEXT NOT NULL DEFAULT '',        -- id do e-mail ou caminho do arquivo
    resumo      TEXT NOT NULL,
    acao        TEXT NOT NULL DEFAULT '',        -- ação sugerida
    prioridade  INTEGER NOT NULL DEFAULT 3,      -- 1 (tanto faz) a 5 (urgente)
    urgente     INTEGER NOT NULL DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'nova',    -- nova, comentada, resolvida, descartada
    nota        TEXT NOT NULL DEFAULT '',
    criado      TEXT NOT NULL,
    atualizado  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS vistos (
    tipo        TEXT NOT NULL,                   -- 'email' ou 'arquivo'
    chave       TEXT NOT NULL,                   -- id do e-mail ou caminho
    marca       TEXT NOT NULL DEFAULT '',        -- arquivo: tamanho+data (muda se o arquivo mudar)
    visto_em    TEXT NOT NULL,
    PRIMARY KEY (tipo, chave)
);
"""


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _conectar() -> sqlite3.Connection:
    memoria.ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(memoria.ARQUIVO)
    conexao.row_factory = sqlite3.Row
    conexao.executescript(ESQUEMA)
    return conexao


# ---------- Vistos ----------

def ja_vistos(tipo: str) -> dict[str, str]:
    """{chave: marca} do que já foi visto."""
    with closing(_conectar()) as c:
        return {r["chave"]: r["marca"] for r in c.execute("SELECT chave, marca FROM vistos WHERE tipo = ?", (tipo,))}


def marcar_vistos(tipo: str, itens: dict[str, str]) -> None:
    with closing(_conectar()) as c, c:
        c.executemany("INSERT OR REPLACE INTO vistos (tipo, chave, marca, visto_em) VALUES (?, ?, ?, ?)",
                      [(tipo, chave, marca, _agora()) for chave, marca in itens.items()])


def nada_visto_ainda(tipo: str) -> bool:
    with closing(_conectar()) as c:
        return c.execute("SELECT COUNT(*) FROM vistos WHERE tipo = ?", (tipo,)).fetchone()[0] == 0


# ---------- Pendências ----------

def criar(origem: str, referencia: str, resumo: str, acao: str = "", prioridade: int = 3, urgente: bool = False) -> int:
    with closing(_conectar()) as c, c:
        return c.execute(
            "INSERT INTO pendencias (origem, referencia, resumo, acao, prioridade, urgente, criado, atualizado) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (origem, referencia, resumo, acao, max(1, min(5, int(prioridade))), int(bool(urgente)), _agora(), _agora()),
        ).lastrowid


def abertas(limite: int = 30) -> list[dict]:
    """Pendências ainda não resolvidas, da mais importante para a menos."""
    with closing(_conectar()) as c:
        return [dict(p) for p in c.execute(
            "SELECT * FROM pendencias WHERE status IN ('nova', 'comentada') "
            "ORDER BY urgente DESC, prioridade DESC, criado DESC LIMIT ?", (limite,))]


def mudar_status(id_: int, status: str, nota: str = "") -> dict:
    with closing(_conectar()) as c, c:
        linha = c.execute("SELECT resumo FROM pendencias WHERE id = ?", (id_,)).fetchone()
        if not linha:
            return {"erro": "pendência não encontrada"}
        c.execute("UPDATE pendencias SET status = ?, nota = ?, atualizado = ? WHERE id = ?", (status, nota, _agora(), id_))
        return {"pendencia": linha["resumo"], "status": status}
