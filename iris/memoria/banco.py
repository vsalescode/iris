"""Memória de longo prazo da Iris, num banco SQLite local (dados/iris.db).

Tabelas:
  fatos      -> o que ela sabe sobre você (fatos e preferências)
  conversas  -> um resumo de cada conversa
  assuntos   -> assuntos em aberto, para ela retomar depois ("e aí, deu certo?")
A coluna `vetor` (vazia por enquanto) fica pronta para busca por significado no futuro.
"""

import re
import sqlite3
import unicodedata
from contextlib import closing
from datetime import date, datetime

from .. import config

ARQUIVO = config.PASTA_DADOS / "iris.db"
CATEGORIAS = ["pessoal", "preferencia", "trabalho", "estudos", "rotina", "saude", "pessoas", "projetos", "outro"]

ESQUEMA = """
CREATE TABLE IF NOT EXISTS fatos (
    id          INTEGER PRIMARY KEY,
    texto       TEXT NOT NULL,
    categoria   TEXT NOT NULL DEFAULT 'outro',
    importancia INTEGER NOT NULL DEFAULT 3,      -- 1 (detalhe) a 5 (essencial)
    criado      TEXT NOT NULL,
    atualizado  TEXT NOT NULL,
    origem      TEXT NOT NULL DEFAULT 'conversa', -- 'voz' (pediu para lembrar) ou 'conversa' (resumo automático)
    ativo       INTEGER NOT NULL DEFAULT 1,
    vetor       BLOB                               -- futuro: busca por significado
);
CREATE TABLE IF NOT EXISTS conversas (
    id          INTEGER PRIMARY KEY,
    inicio      TEXT NOT NULL,
    fim         TEXT NOT NULL,
    resumo      TEXT NOT NULL,
    transcricao TEXT NOT NULL,                     -- guardada só aqui, no seu PC
    vetor       BLOB
);
CREATE TABLE IF NOT EXISTS assuntos (
    id          INTEGER PRIMARY KEY,
    assunto     TEXT NOT NULL,
    detalhe     TEXT NOT NULL DEFAULT '',
    retomar_em  TEXT,                              -- AAAA-MM-DD: a partir de quando vale perguntar
    status      TEXT NOT NULL DEFAULT 'aberto',    -- 'aberto' ou 'fechado'
    desfecho    TEXT NOT NULL DEFAULT '',
    criado      TEXT NOT NULL,
    atualizado  TEXT NOT NULL,
    vetor       BLOB
);
"""


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _conectar() -> sqlite3.Connection:
    """Uma conexão nova por operação (simples e seguro entre threads)."""
    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(ARQUIVO)
    conexao.row_factory = sqlite3.Row
    conexao.executescript(ESQUEMA)
    return conexao


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", sem_acento.lower())).strip()


def _parecidos(a: str, b: str) -> float:
    """Quanto dois textos dividem palavras (0 a 1), em relação ao menor. Bom para buscar."""
    pa, pb = set(_normalizar(a).split()), set(_normalizar(b).split())
    return len(pa & pb) / max(1, min(len(pa), len(pb)))


def _quase_iguais(a: str, b: str) -> bool:
    """Dizem praticamente a mesma coisa (para não guardar duplicado)."""
    pa, pb = set(_normalizar(a).split()), set(_normalizar(b).split())
    return len(pa & pb) / max(1, len(pa | pb)) >= 0.75


# ---------- Fatos ----------

def lembrar(texto: str, categoria: str = "outro", importancia: int = 3, origem: str = "conversa") -> dict:
    texto = (texto or "").strip()
    if not texto:
        return {"erro": "faltou o que lembrar"}
    categoria = categoria if categoria in CATEGORIAS else "outro"
    importancia = max(1, min(5, int(importancia or 3)))
    with closing(_conectar()) as c, c:
        # quase igual a um fato que já existe: atualiza em vez de duplicar
        for f in c.execute("SELECT id, texto FROM fatos WHERE ativo = 1"):
            if _quase_iguais(f["texto"], texto):
                c.execute("UPDATE fatos SET texto = ?, categoria = ?, importancia = MAX(importancia, ?), atualizado = ? "
                          "WHERE id = ?", (texto, categoria, importancia, _agora(), f["id"]))
                return {"lembrado": texto, "id": f["id"], "obs": "atualizei uma lembrança parecida"}
        cur = c.execute("INSERT INTO fatos (texto, categoria, importancia, criado, atualizado, origem) "
                        "VALUES (?, ?, ?, ?, ?, ?)", (texto, categoria, importancia, _agora(), _agora(), origem))
        return {"lembrado": texto, "id": cur.lastrowid}


def atualizar_fato(id_: int, texto: str) -> None:
    with closing(_conectar()) as c, c:
        c.execute("UPDATE fatos SET texto = ?, atualizado = ? WHERE id = ? AND ativo = 1", (texto, _agora(), id_))


def esquecer(id_: int | None = None, termo: str = "") -> dict:
    """Esquece um fato pelo id ou pelo fato mais parecido com o termo."""
    with closing(_conectar()) as c, c:
        if id_ is None:
            candidatos = [(_parecidos(f["texto"], termo), f) for f in c.execute("SELECT id, texto FROM fatos WHERE ativo = 1")]
            candidatos = [x for x in candidatos if x[0] >= 0.5]
            if not candidatos:
                return {"erro": f"não achei nenhuma lembrança sobre '{termo}'"}
            id_ = max(candidatos, key=lambda x: x[0])[1]["id"]
        linha = c.execute("SELECT texto FROM fatos WHERE id = ? AND ativo = 1", (id_,)).fetchone()
        if not linha:
            return {"erro": "essa lembrança não existe (ou já foi esquecida)"}
        c.execute("UPDATE fatos SET ativo = 0, atualizado = ? WHERE id = ?", (_agora(), id_))
        return {"esquecido": linha["texto"]}


def fatos(limite: int = 300) -> list[dict]:
    with closing(_conectar()) as c:
        return [dict(f) for f in c.execute(
            "SELECT id, texto, categoria, importancia, atualizado FROM fatos WHERE ativo = 1 "
            "ORDER BY importancia DESC, atualizado DESC LIMIT ?", (limite,))]


# ---------- Conversas ----------

def salvar_conversa(inicio: str, resumo: str, transcricao: str) -> int:
    with closing(_conectar()) as c, c:
        return c.execute("INSERT INTO conversas (inicio, fim, resumo, transcricao) VALUES (?, ?, ?, ?)",
                         (inicio, _agora(), resumo, transcricao)).lastrowid


def conversas_recentes(limite: int = 4) -> list[dict]:
    with closing(_conectar()) as c:
        return [dict(x) for x in c.execute(
            "SELECT id, inicio, resumo FROM conversas ORDER BY inicio DESC LIMIT ?", (limite,))]


# ---------- Assuntos em aberto ----------

def abrir_assunto(assunto: str, detalhe: str = "", retomar_em: str | None = None) -> dict:
    assunto = (assunto or "").strip()
    if not assunto:
        return {"erro": "faltou o assunto"}
    if retomar_em:
        try:
            retomar_em = date.fromisoformat(retomar_em).isoformat()
        except ValueError:
            retomar_em = None
    with closing(_conectar()) as c, c:
        for a in c.execute("SELECT id, assunto FROM assuntos WHERE status = 'aberto'"):
            if _quase_iguais(a["assunto"], assunto):
                c.execute("UPDATE assuntos SET detalhe = ?, retomar_em = COALESCE(?, retomar_em), atualizado = ? "
                          "WHERE id = ?", (detalhe, retomar_em, _agora(), a["id"]))
                return {"assunto": assunto, "id": a["id"], "obs": "atualizei um assunto parecido"}
        cur = c.execute("INSERT INTO assuntos (assunto, detalhe, retomar_em, criado, atualizado) VALUES (?, ?, ?, ?, ?)",
                        (assunto, detalhe, retomar_em, _agora(), _agora()))
        return {"assunto": assunto, "id": cur.lastrowid}


def fechar_assunto(id_: int, desfecho: str = "") -> dict:
    with closing(_conectar()) as c, c:
        linha = c.execute("SELECT assunto FROM assuntos WHERE id = ? AND status = 'aberto'", (id_,)).fetchone()
        if not linha:
            return {"erro": "esse assunto não está em aberto"}
        c.execute("UPDATE assuntos SET status = 'fechado', desfecho = ?, atualizado = ? WHERE id = ?",
                  (desfecho, _agora(), id_))
        return {"fechado": linha["assunto"], "desfecho": desfecho}


def assuntos_abertos(limite: int = 20) -> list[dict]:
    with closing(_conectar()) as c:
        return [dict(a) for a in c.execute(
            "SELECT id, assunto, detalhe, retomar_em, criado FROM assuntos WHERE status = 'aberto' "
            "ORDER BY COALESCE(retomar_em, criado) LIMIT ?", (limite,))]


# ---------- Busca ----------

def buscar(termo: str, limite: int = 8) -> dict:
    """Procura em fatos, assuntos e resumos de conversas antigas (por palavras em comum)."""
    with closing(_conectar()) as c:
        achados = []
        for f in c.execute("SELECT id, texto FROM fatos WHERE ativo = 1"):
            achados.append((_parecidos(f["texto"], termo), "fato", f["texto"], f["id"]))
        for a in c.execute("SELECT id, assunto, detalhe, status, desfecho FROM assuntos"):
            texto = f"{a['assunto']} ({a['status']}) {a['detalhe']} {a['desfecho']}".strip()
            achados.append((_parecidos(texto, termo), "assunto", texto, a["id"]))
        for v in c.execute("SELECT id, inicio, resumo FROM conversas"):
            achados.append((_parecidos(v["resumo"], termo), "conversa", f"{v['inicio'][:10]}: {v['resumo']}", v["id"]))
    achados = sorted([a for a in achados if a[0] > 0], reverse=True)[:limite]
    return {"resultados": [{"tipo": t, "texto": x, "id": i} for _, t, x, i in achados]}
