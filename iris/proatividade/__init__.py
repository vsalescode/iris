"""Modo proativo e, depois, curiosidade/descoberta.

- vigia.py   ronda em segundo plano (Gmail e zonas liberadas) e triagem com IA
- banco.py   fila de pendências e o que já foi visto
- contexto() trecho do system prompt com as pendências abertas
"""

from .. import ambiente
from . import banco


def contexto() -> str:
    try:
        pendencias = banco.abertas(ambiente.VIGIA_PENDENCIAS_NO_PROMPT)
    except Exception:
        return ""
    if not pendencias:
        return ""
    linhas = ["\n## Pendências (o que sua vigília notou enquanto ele não estava conversando)"]
    for p in pendencias:
        marcas = []
        if p["urgente"]:
            marcas.append("URGENTE")
        if p["status"] == "comentada":
            marcas.append("você já avisou")
        if p["origem"] == "email" and p["referencia"]:
            marcas.append(f"e-mail id {p['referencia']}: ler_email para os detalhes")
        extra = f" [{', '.join(marcas)}]" if marcas else ""
        linhas.append(f"- {p['id']}: {p['resumo']} (sugestão: {p['acao'] or '—'}; prioridade {p['prioridade']}){extra}")
    linhas.append(
        "Como usar:\n"
        "- Logo no começo da conversa, puxe a pendência mais importante que você ainda não comentou, de forma\n"
        "  natural e curta, e pergunte o que ele quer fazer. Uma de cada vez; as menores só se ele quiser.\n"
        "- Quando ele decidir (fazer, ignorar, lembrar depois), faça o que for preciso com suas ferramentas,\n"
        "  confirme o resultado e use tratar_pendencia para tirá-la da fila.\n"
        "- 'Lembrar depois': anote com anotar_assunto (com a data) e trate a pendência como resolvida."
    )
    return "\n".join(linhas) + "\n"
