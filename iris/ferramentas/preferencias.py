"""Preferências que dá para mudar por voz ("Iris, troca sua voz para Kore")."""

from .. import config
from ..voz import gemini_tts
from .pastas import normalizar

PREFERENCIAS = ["voz", "nome_usuario", "tempo_conversa"]


def ajustar(preferencia: str, valor: str) -> dict:
    valor = str(valor or "").strip()
    if preferencia == "voz":
        vozes = {normalizar(nome): nome for nome, _ in gemini_tts.VOZES}
        nome = vozes.get(normalizar(valor))
        if not nome:
            return {"erro": f"não conheço a voz {valor}. Disponíveis: {', '.join(n for n, _ in gemini_tts.VOZES)}"}
        config.salvar_valor("voz", "nome", f"gemini:{nome}")
        return {"voz": nome, "obs": "a voz muda a partir da próxima conversa (não dá para trocar no meio desta)"}
    if preferencia == "nome_usuario":
        if not valor:
            return {"erro": "faltou o nome"}
        config.salvar_valor("usuario", "nome", valor)
        return {"nome_usuario": valor}
    if preferencia == "tempo_conversa":
        try:
            segundos = max(10, min(900, round(float(valor))))
        except ValueError:
            return {"erro": "o tempo precisa ser um número de segundos"}
        config.salvar_valor("ouvir", "conversa_segundos", segundos)
        return {"tempo_conversa": f"{segundos} segundos de silêncio encerram a conversa"}
    return {"erro": f"preferência desconhecida: {preferencia}"}
