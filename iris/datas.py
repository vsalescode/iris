"""Datas escritas por extenso no idioma configurado (IRIS_IDIOMA_DATAS no .env).

Usa a biblioteca Babel, que já sabe os nomes de dias e meses de cada idioma:
nada de listas de "segunda-feira", "janeiro"... no código.
"""

from datetime import date, datetime

from babel.dates import format_date, format_time

from . import ambiente


def por_extenso(momento: datetime) -> str:
    """'segunda-feira, 26 de outubro de 2026, 14:05' (em inglês: 'Monday, October 26, 2026, 14:05')"""
    dia = format_date(momento, "full", locale=ambiente.IDIOMA_DATAS)  # formato completo de cada idioma
    return f"{dia}, {format_time(momento, 'HH:mm', locale=ambiente.IDIOMA_DATAS)}"


def dia_da_semana(dia: date) -> str:
    """'segunda-feira'"""
    return format_date(dia, "EEEE", locale=ambiente.IDIOMA_DATAS)


def curta(dia: date) -> str:
    """'segunda-feira, 26/10'"""
    return format_date(dia, "EEEE, dd/MM", locale=ambiente.IDIOMA_DATAS)
