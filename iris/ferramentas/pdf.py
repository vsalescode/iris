"""Leitura de PDFs.

1. No seu PC, com a biblioteca pypdf (PDFs "digitais": currículos, boletos, notas, contratos).
2. Se o PDF for escaneado (só imagem, quase sem texto), o Gemini lê as páginas
   (ARQUIVO_PDF_LEITURA_NUVEM=false no .env desliga isso: aí o arquivo nunca sai do PC).
"""

import re
from pathlib import Path

from .. import ambiente, config

MINIMO_TEXTO_POR_PAGINA = 40  # menos que isso (em média) = provavelmente escaneado
LIMITE_NUVEM_MB = 19          # a API aceita até ~20 MB por arquivo enviado direto
PEDIDO_TRANSCRICAO = (
    "Transcreva fielmente TODO o texto deste PDF, página por página, marcando cada uma como [página N]. "
    "Mantenha números, datas e valores exatamente como estão. Não resuma, não comente, não traduza."
)


def extrair(caminho: Path) -> dict:
    """{"texto", "paginas", "lidas", "metodo"} ou {"erro"}."""
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        leitor = PdfReader(str(caminho))
        if leitor.is_encrypted and not leitor.decrypt(""):
            return {"erro": "o PDF tem senha; abra e salve sem senha para eu conseguir ler"}
        total = len(leitor.pages)
        lidas = min(total, ambiente.ARQUIVO_PDF_MAX_PAGINAS)
        partes = []
        for i in range(lidas):
            texto = (leitor.pages[i].extract_text() or "").strip()
            partes.append(f"[página {i + 1}]\n{texto}")
    except PdfReadError as erro:
        return {"erro": f"não consegui abrir o PDF (arquivo corrompido?): {erro}"}

    texto = "\n\n".join(partes)
    util = len(re.sub(r"\[página \d+\]|\s", "", texto))
    if util >= MINIMO_TEXTO_POR_PAGINA * max(1, lidas) * 0.5:
        return {"texto": texto, "paginas": total, "lidas": lidas, "metodo": "texto do PDF (no seu PC)"}

    # quase sem texto: provavelmente escaneado (foto, documento digitalizado)
    if not ambiente.ARQUIVO_PDF_LEITURA_NUVEM:
        return {"erro": "o PDF parece escaneado (só imagem) e a leitura pela nuvem está desligada no .env"}
    if caminho.stat().st_size > LIMITE_NUVEM_MB * 1024**2:
        return {"erro": "o PDF escaneado é grande demais para eu ler"}
    try:
        return {"texto": _ler_na_nuvem(caminho), "paginas": total, "lidas": total,
                "metodo": "PDF escaneado, lido pelo Gemini (o arquivo foi enviado ao Google)"}
    except Exception as erro:
        return {"erro": f"o PDF parece escaneado e não consegui ler a imagem: {str(erro)[:150]}"}


def _ler_na_nuvem(caminho: Path) -> str:
    if not config.chave("GEMINI_API_KEY"):
        raise RuntimeError("sem GEMINI_API_KEY")
    from google.genai import types

    from ..cerebro.live import _cliente

    resposta = _cliente().models.generate_content(
        model=ambiente.GEMINI_MODELO_TEXTO,
        contents=[types.Part.from_bytes(data=caminho.read_bytes(), mime_type="application/pdf"), PEDIDO_TRANSCRICAO],
        config=types.GenerateContentConfig(temperature=0),
    )
    return (resposta.text or "").strip()
