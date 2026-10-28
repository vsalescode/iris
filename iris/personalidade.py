"""Personalidade da Iris em três camadas:

1. personalidade.md          quem ela é e os limites dela. Só você edita; ela nunca muda isso.
2. Ajustes de 0 a 100%       estilo TARS (Interestelar). Os 6 de base estão em TRACOS; ela pode
                             propor traços novos. Os níveis ficam em configuracao.yaml (seção
                             `personalidade:`): engrenagem ou voz ("Iris, humor em 75%").
3. O jeito aprendido         frases curtas sobre como agir com você, que ela aprende nas conversas.

Ela evolui por PROPOSTAS (jeito novo, mudar um ajuste, traço novo), feitas no fim da conversa ou
durante ela. Nada vale antes do seu "sim" (voz com cartão na tela, ou a gaveta → Personalidade).
Traços criados, jeitos aprovados e propostas ficam em personalidade_aprendida.yaml (dá para editar).
"""

import difflib
import re
import unicodedata
from datetime import datetime

import yaml

from . import ambiente, config

# traço: (nome falado, nível padrão, o que significa em cada faixa: 0-20, 21-40, 41-60, 61-80, 81-100)
TRACOS = {
    "humor": ("Humor", 70, [
        "Totalmente séria: nada de piadas.",
        "Humor raro e discreto.",
        "Humor leve de vez em quando.",
        "Bem-humorada: piadas secas e comentários espirituosos com frequência, sem atrapalhar o que foi pedido.",
        "Muito engraçada: transforma quase tudo em tirada, mas ainda resolve o que foi pedido.",
    ]),
    "sarcasmo": ("Sarcasmo", 40, [
        "Nada de sarcasmo.",
        "Ironia sutil só de vez em quando.",
        "Sarcasmo seco e elegante, estilo mordomo britânico, de vez em quando.",
        "Sarcástica com frequência: provocações afiadas, nunca cruéis.",
        "Sarcasmo no máximo: quase toda resposta vem com uma alfinetada (nunca ofensiva de verdade).",
    ]),
    "franqueza": ("Franqueza", 85, [
        "Muito diplomática: suaviza críticas ao máximo (mas nunca mente sobre fatos ou ações).",
        "Diplomática: aponta problemas com muito tato.",
        "Equilibrada entre tato e sinceridade.",
        "Direta: diz o que pensa com clareza, com um mínimo de tato.",
        "Brutalmente honesta: diz exatamente o que pensa, sem rodeios.",
    ]),
    "formalidade": ("Formalidade", 35, [
        "Totalmente informal, com gírias, como uma amiga próxima.",
        "Informal e natural.",
        "Equilibrada e educada.",
        "Formal e polida, estilo mordomo; chama ele de 'senhor' de vez em quando.",
        "Muito formal: sempre 'senhor', linguagem refinada, estilo JARVIS.",
    ]),
    "detalhe": ("Detalhe", 30, [
        "Respostas mínimas: uma frase curta.",
        "Curta: uma ou duas frases.",
        "Duas ou três frases.",
        "Explica com mais detalhe quando for útil.",
        "Detalhista: explicações completas.",
    ]),
    "iniciativa": ("Iniciativa", 50, [
        "Só responde o que foi perguntado, nada além.",
        "Raramente sugere algo por conta própria.",
        "Sugere algo útil de vez em quando.",
        "Proativa: sugere ideias e antecipa o próximo passo.",
        "Muito proativa: puxa assuntos, sugere e antecipa necessidades o tempo todo.",
    ]),
}

ARQUIVO = config.caminho(ambiente.PERSONALIDADE_ARQUIVO)
LIMITE_JEITO = 200
LIMITE_FAIXA = 150
# o jeito dela nunca pode mexer nos limites: confirmações, permissões, honestidade, segurança
MEXE_EM_LIMITE = re.compile(
    r"confirma|permiss|sem pergunt|nao pergunt|sem aviso|mentir|minta|invent|fingir|engan|apagar|apague|"
    r"deletar|enviar? sozinh|mande sozinh|ignor\w* (as |a )?(regra|limite|instru)|burlar|contornar|"
    r"senha|token|chave|segredo|ofend|humilh|xing",
)


# ---------- Arquivo do que ela aprendeu ----------

def _aprendida() -> dict:
    dados = {}
    if ARQUIVO.is_file():
        try:
            dados = yaml.safe_load(ARQUIVO.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            dados = {}
    dados.setdefault("tracos", {})
    for chave in ("jeitos", "propostas", "recusadas"):
        dados[chave] = dados.get(chave) or []
    dados.setdefault("proximo_id", 1)
    return dados


def _salvar_aprendida(dados: dict) -> None:
    cabecalho = ("# O que a Iris aprendeu sobre o jeito de agir com você (você pode editar).\n"
                 "# tracos: ajustes criados · jeitos: aprovados · propostas: esperando você · recusadas: não repetir\n")
    ARQUIVO.write_text(cabecalho + yaml.safe_dump(dados, allow_unicode=True, sort_keys=False, width=110),
                       encoding="utf-8")


def _novo_id(dados: dict) -> int:
    id_ = int(dados.get("proximo_id", 1))
    dados["proximo_id"] = id_ + 1
    return id_


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFD", texto or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", sem_acento)).strip()


def _slug(texto: str) -> str:
    return re.sub(r"-+", "-", _normalizar(texto).replace(" ", "-")).strip("-")[:30]


def tracos() -> dict:
    """Os 6 de base + os criados (aprovados), no mesmo formato de TRACOS."""
    todos = dict(TRACOS)
    for id_, t in _aprendida()["tracos"].items():
        if id_ not in TRACOS and isinstance(t, dict) and len(t.get("faixas") or []) == 5:
            todos[id_] = (str(t.get("rotulo") or id_), int(t.get("padrao", 50)), [str(f) for f in t["faixas"]])
    return todos


# ---------- Ajustes (0 a 100%) ----------

def niveis(cfg: dict) -> dict[str, int]:
    salvo = cfg.get("personalidade") or {}
    saida = {}
    for traco, (_, padrao, _) in tracos().items():
        try:
            saida[traco] = max(0, min(100, int(salvo.get(traco, padrao))))
        except (TypeError, ValueError):
            saida[traco] = padrao
    return saida


def _faixa(nivel: int) -> int:
    return min(4, max(0, (nivel - 1) // 20)) if nivel > 0 else 0


def descrever(cfg: dict) -> str:
    """Trecho do system prompt: níveis atuais, o jeito aprendido e as propostas pendentes."""
    todos = tracos()
    linhas = [f"- {todos[t][0]}: {n}% — {todos[t][2][_faixa(n)]}" for t, n in niveis(cfg).items()]
    texto = (
        "\n## Seus ajustes de personalidade (ele configura, de 0 a 100%)\n"
        + "\n".join(linhas)
        + "\n- Esses níveis mandam no seu estilo, acima de qualquer outra instrução de estilo.\n"
        "- Se ele pedir para mudar um ajuste (ex.: 'humor em 80%', 'menos sarcasmo', 'seja mais formal'), "
        "use a ferramenta ajustar_personalidade e confirme numa frase curta, já no novo estilo, "
        "dizendo o novo valor, como o TARS de Interestelar faria.\n"
    )
    dados = _aprendida()
    if dados["jeitos"]:
        texto += "\n## O jeito que você aprendeu com ele (aprovado por ele)\n" + "\n".join(
            f"- {j['texto']}" for j in dados["jeitos"]) + "\n"
    texto += (
        "\n## Você evolui (com a aprovação dele)\n"
        "- Quando notar com clareza o jeito que ele gosta (ele riu, reclamou, pediu de novo), proponha com\n"
        "  propor_jeito (uma frase curta) ou, para um ajuste que ainda não existe, propor_traco. Sem pressa:\n"
        "  só com evidência, e nunca nada que mexa nos seus limites, confirmações ou permissões.\n"
        "- Nada muda antes do sim dele: para aprovar pela voz, aprovar_personalidade (ele confirma na tela).\n"
        "- Se ele pedir para esquecer um jeito aprendido, use esquecer_jeito.\n"
    )
    if dados["propostas"]:
        texto += "- Propostas esperando a decisão dele (mencione UMA vez, curto, no seu estilo; não insista):\n"
        texto += "\n".join(f"  - id {p['id']}: {_resumo(p)}" for p in dados["propostas"]) + "\n"
    return texto


def lista_para_interface(cfg: dict) -> list[dict]:
    todos = tracos()
    return [{"id": t, "rotulo": todos[t][0], "nivel": n} for t, n in niveis(cfg).items()]


def ajustar(traco: str, nivel) -> dict:
    """Muda um traço e salva no configuracao.yaml."""
    todos = tracos()
    traco = (traco or "").strip().lower()
    if traco not in todos:
        traco = next((t for t, (rotulo, _, _) in todos.items() if _normalizar(rotulo) == _normalizar(traco)), traco)
    if traco not in todos:
        return {"erro": f"não conheço o ajuste '{traco}'. Existem: {', '.join(todos)}"}
    try:
        nivel = max(0, min(100, round(float(nivel))))
    except (TypeError, ValueError):
        return {"erro": "o nível precisa ser um número de 0 a 100"}
    config.salvar_valor("personalidade", traco, nivel)
    return {"ajuste": todos[traco][0], "nivel": f"{nivel}%", "efeito": todos[traco][2][_faixa(nivel)],
            "instrucao": "A partir de agora, aja com esse novo nível."}


# ---------- Propostas: ela sugere, você aprova ----------

def _resumo(p: dict) -> str:
    if p["tipo"] == "jeito":
        return f"jeito novo: “{p['texto']}”" + (f" (substitui: “{p['substitui_texto']}”)" if p.get("substitui_texto") else "")
    if p["tipo"] == "ajuste":
        return f"{p['rotulo']} de {p['de']}% para {p['para']}%"
    return f"ajuste novo “{p['rotulo']}” começando em {p['nivel']}%"


def _parecido(a: str, b: str) -> bool:
    return difflib.SequenceMatcher(None, _normalizar(a), _normalizar(b)).ratio() >= 0.8


def _ja_existe(dados: dict, chave: str) -> str | None:
    """Evita repetir algo aprovado, pendente ou que ele já recusou."""
    for j in dados["jeitos"]:
        if _parecido(j["texto"], chave):
            return "isso já está no seu jeito"
    for p in dados["propostas"]:
        if _parecido(_chave(p), chave):
            return "já existe uma proposta parecida esperando ele"
    for r in dados["recusadas"]:
        if _parecido(r, chave):
            return "ele já recusou algo assim; não proponha de novo"
    return None


def _chave(p: dict) -> str:
    return p.get("texto") or p.get("traco") or p.get("id_traco") or ""


def _guardar(dados: dict, proposta: dict) -> dict:
    proposta = {"id": _novo_id(dados), **proposta, "criada_em": datetime.now().isoformat(timespec="minutes")}
    dados["propostas"].append(proposta)
    _salvar_aprendida(dados)
    return {"proposta": proposta["id"], "resumo": _resumo(proposta),
            "obs": "fica proposta até ele aprovar (pela gaveta ou pedindo; aí use aprovar_personalidade)"}


def propor_jeito(texto: str, motivo: str = "", substitui: int | None = None) -> dict:
    texto = re.sub(r"\s+", " ", texto or "").strip()
    if len(texto) < 10 or len(texto) > LIMITE_JEITO:
        return {"erro": f"escreva o jeito numa frase curta (10 a {LIMITE_JEITO} caracteres)"}
    if MEXE_EM_LIMITE.search(_normalizar(texto)):
        return {"erro": "isso mexe nos seus limites (confirmações, permissões, honestidade ou segurança); não é negociável"}
    dados = _aprendida()
    repetido = _ja_existe(dados, texto)
    if repetido:
        return {"erro": repetido}
    proposta = {"tipo": "jeito", "texto": texto, "motivo": (motivo or "").strip()[:200]}
    if substitui:
        alvo = next((j for j in dados["jeitos"] if j["id"] == int(substitui)), None)
        if not alvo:
            return {"erro": f"não há jeito aprovado com id {substitui}"}
        proposta.update(substitui=alvo["id"], substitui_texto=alvo["texto"])
    elif len(dados["jeitos"]) >= ambiente.PERSONALIDADE_MAX_JEITOS:
        lista = "; ".join(f"{j['id']}: {j['texto']}" for j in dados["jeitos"])
        return {"erro": f"já são {len(dados['jeitos'])} jeitos (o máximo). Proponha trocar um deles "
                        f"(parâmetro substitui com o id): {lista}"}
    return _guardar(dados, proposta)


def propor_ajuste(traco: str, nivel, motivo: str, cfg: dict | None = None) -> dict:
    todos = tracos()
    traco = (traco or "").strip().lower()
    if traco not in todos:
        return {"erro": f"não conheço o ajuste '{traco}'. Existem: {', '.join(todos)}"}
    atual = niveis(cfg or config.carregar())[traco]
    try:
        alvo = max(0, min(100, round(float(nivel))))
    except (TypeError, ValueError):
        return {"erro": "o nível precisa ser um número de 0 a 100"}
    passo = ambiente.PERSONALIDADE_PASSO_MAXIMO
    if abs(alvo - atual) > passo:
        return {"erro": f"mude no máximo {passo} pontos por vez (está em {atual}%)"}
    if alvo == atual:
        return {"erro": f"{todos[traco][0]} já está em {atual}%"}
    dados = _aprendida()
    if any(p["tipo"] == "ajuste" and p["traco"] == traco for p in dados["propostas"]):
        return {"erro": "já existe uma proposta para esse ajuste esperando ele"}
    return _guardar(dados, {"tipo": "ajuste", "traco": traco, "rotulo": todos[traco][0], "de": atual, "para": alvo,
                            "motivo": (motivo or "").strip()[:200]})


def propor_traco(rotulo: str, faixas: list, nivel=50, motivo: str = "") -> dict:
    rotulo = re.sub(r"\s+", " ", rotulo or "").strip()[:30]
    id_ = _slug(rotulo)
    if len(id_) < 3:
        return {"erro": "dê um nome curto para o ajuste (ex.: 'Nerdice')"}
    todos = tracos()
    if id_ in todos or any(_normalizar(r) == _normalizar(rotulo) for r, _, _ in todos.values()):
        return {"erro": f"o ajuste '{rotulo}' já existe; use ajustar_personalidade ou proponha um nível"}
    faixas = [re.sub(r"\s+", " ", str(f)).strip() for f in (faixas or [])]
    if len(faixas) != 5 or not all(5 <= len(f) <= LIMITE_FAIXA for f in faixas):
        return {"erro": f"são 5 descrições (0-20, 21-40, 41-60, 61-80, 81-100%), cada uma com até {LIMITE_FAIXA} caracteres"}
    if any(MEXE_EM_LIMITE.search(_normalizar(f"{rotulo} {f}")) for f in faixas):
        return {"erro": "isso mexe nos seus limites (confirmações, permissões, honestidade ou segurança); não é negociável"}
    dados = _aprendida()
    if len(dados["tracos"]) >= ambiente.PERSONALIDADE_MAX_TRACOS:
        return {"erro": f"já existem {len(dados['tracos'])} ajustes criados (o máximo)"}
    repetido = _ja_existe(dados, id_)
    if repetido:
        return {"erro": repetido}
    try:
        nivel = max(0, min(100, round(float(nivel))))
    except (TypeError, ValueError):
        nivel = 50
    return _guardar(dados, {"tipo": "traco", "id_traco": id_, "rotulo": rotulo, "faixas": faixas, "nivel": nivel,
                            "motivo": (motivo or "").strip()[:200]})


def _achar(dados: dict, id_) -> dict | None:
    try:
        id_ = int(id_)
    except (TypeError, ValueError):
        return None
    return next((p for p in dados["propostas"] if p["id"] == id_), None)


def propostas() -> list[dict]:
    return [{**p, "resumo": _resumo(p)} for p in _aprendida()["propostas"]]


def jeitos() -> list[dict]:
    return _aprendida()["jeitos"]


def previa(id_) -> dict:
    """Cartão na tela antes de aprovar."""
    p = _achar(_aprendida(), id_)
    if not p:
        raise ValueError(f"não há proposta de personalidade com id {id_}")
    texto = _resumo(p)
    if p["tipo"] == "traco":
        texto += "\n\n" + "\n".join(f"{faixa}: {d}" for faixa, d in zip(("0-20%", "21-40%", "41-60%", "61-80%", "81-100%"), p["faixas"]))
    titulos = {"jeito": "Jeito novo", "ajuste": "Mudar um ajuste", "traco": "Ajuste novo"}
    return {"acao": f"Personalidade · {titulos[p['tipo']]}", "para": p.get("motivo") or "—",
            "assunto": "só vale depois do seu sim", "texto": texto, "rotulos": ["Por quê", "Quando"],
            "dica": "Diga “pode” ou “cancela”"}


def aprovar(id_) -> dict:
    dados = _aprendida()
    p = _achar(dados, id_)
    if not p:
        return {"erro": f"não há proposta de personalidade com id {id_}"}
    hoje = datetime.now().strftime("%Y-%m-%d")
    if p["tipo"] == "jeito":
        if p.get("substitui"):
            dados["jeitos"] = [j for j in dados["jeitos"] if j["id"] != p["substitui"]]
        dados["jeitos"].append({"id": p["id"], "texto": p["texto"], "motivo": p.get("motivo", ""), "desde": hoje})
    elif p["tipo"] == "traco":
        dados["tracos"][p["id_traco"]] = {"rotulo": p["rotulo"], "padrao": p["nivel"], "faixas": p["faixas"],
                                          "criado_em": hoje, "motivo": p.get("motivo", "")}
    dados["propostas"] = [x for x in dados["propostas"] if x["id"] != p["id"]]
    _salvar_aprendida(dados)
    if p["tipo"] == "ajuste":
        ajustar(p["traco"], p["para"])
    elif p["tipo"] == "traco":
        config.salvar_valor("personalidade", p["id_traco"], p["nivel"])
    return {"aprovado": _resumo(p), "instrucao": "A partir de agora, aja assim."}


def recusar(id_) -> dict:
    dados = _aprendida()
    p = _achar(dados, id_)
    if not p:
        return {"erro": f"não há proposta de personalidade com id {id_}"}
    dados["propostas"] = [x for x in dados["propostas"] if x["id"] != p["id"]]
    dados["recusadas"] = (dados["recusadas"] + [_chave(p)])[-50:]
    _salvar_aprendida(dados)
    return {"recusado": _resumo(p)}


def esquecer_jeito(id_) -> dict:
    dados = _aprendida()
    try:
        id_ = int(id_)
    except (TypeError, ValueError):
        return {"erro": "diga o id do jeito"}
    alvo = next((j for j in dados["jeitos"] if j["id"] == id_), None)
    if not alvo:
        lista = "; ".join(f"{j['id']}: {j['texto']}" for j in dados["jeitos"]) or "nenhum"
        return {"erro": f"não há jeito com id {id_}. Aprovados: {lista}"}
    dados["jeitos"] = [j for j in dados["jeitos"] if j["id"] != id_]
    dados["recusadas"] = (dados["recusadas"] + [alvo["texto"]])[-50:]  # não propor de novo
    _salvar_aprendida(dados)
    return {"esquecido": alvo["texto"]}


def contexto_consolidacao(cfg: dict) -> str:
    """Para a análise do fim da conversa saber o que já existe e não repetir."""
    dados = _aprendida()
    todos = tracos()
    return (
        "Ajustes atuais: " + ", ".join(f"{t} ({todos[t][0]}) {n}%" for t, n in niveis(cfg).items()) + "\n"
        "Jeitos já aprovados: " + ("; ".join(j["texto"] for j in dados["jeitos"]) or "(nenhum)") + "\n"
        "Propostas pendentes: " + ("; ".join(_resumo(p) for p in dados["propostas"]) or "(nenhuma)") + "\n"
        "Já recusados (não repetir): " + ("; ".join(dados["recusadas"][-15:]) or "(nada)")
    )
