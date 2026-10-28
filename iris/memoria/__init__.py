"""Memória de longo prazo, em SQLite (dados/iris.db).

- banco.py       guarda fatos, resumos de conversas e assuntos em aberto
- consolidar.py  ao fim de cada conversa, extrai o que vale lembrar
- contexto()     o trecho do system prompt com o que ela sabe sobre você
"""

from datetime import date

from .. import ambiente, datas
from . import banco


def contexto() -> str:
    """O que ela lembra, para o system prompt (só o mais importante, para caber)."""
    try:
        fatos = banco.fatos(ambiente.MEMORIA_FATOS_NO_PROMPT)
        conversas = banco.conversas_recentes(ambiente.MEMORIA_CONVERSAS_NO_PROMPT)
        assuntos = banco.assuntos_abertos(ambiente.MEMORIA_ASSUNTOS_NO_PROMPT)
    except Exception:
        return ""
    hoje = date.today().isoformat()
    partes = ["\n## Sua memória (o que você lembra dele, de conversas anteriores)"]
    if fatos:
        partes.append("O que você sabe sobre ele:")
        partes += [f"- {f['texto']}" for f in fatos]
    else:
        partes.append("- Você ainda não sabe quase nada sobre ele: é o começo da convivência.")
    if conversas:
        partes.append("Conversas recentes:")
        for c in conversas:
            d = date.fromisoformat(c["inicio"][:10])
            quando = "hoje" if d.isoformat() == hoje else datas.curta(d)
            partes.append(f"- {quando}: {c['resumo']}")
    if assuntos:
        partes.append("Assuntos em aberto (id: assunto):")
        for a in assuntos:
            prazo = ""
            if a["retomar_em"]:
                prazo = " — JÁ VALE PERGUNTAR" if a["retomar_em"] <= hoje else f" — perguntar a partir de {a['retomar_em']}"
            partes.append(f"- {a['id']}: {a['assunto']}{' (' + a['detalhe'] + ')' if a['detalhe'] else ''}{prazo}")
    partes.append(
        "Como usar a memória:\n"
        "- Use naturalmente, como quem conhece a pessoa; não fique anunciando 'eu lembro que...'.\n"
        "- Se tiver um assunto em aberto que já vale perguntar, puxe no começo da conversa, de leve\n"
        "  ('e aí, como foi a entrevista?'), conforme seu nível de iniciativa. Um por conversa.\n"
        "- Quando ele contar como terminou, use fechar_assunto. Se ele pedir para lembrar ou esquecer\n"
        "  algo, use lembrar/esquecer. Para algo antigo que não está aqui, use buscar_memoria.\n"
        "- Sua memória é SÓ o que está acima. Nunca invente lembranças."
    )
    return "\n".join(partes) + "\n"
