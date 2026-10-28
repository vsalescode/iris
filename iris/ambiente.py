"""Ajustes TÉCNICOS da Iris, lidos do arquivo .env (cada um com um valor padrão).

Aqui ficam modelos de IA, tempos de espera, limites e portas: coisas de manutenção.
Suas preferências (nome, voz, personalidade) ficam no configuracao.yaml, que a
engrenagem e os comandos de voz editam.

A lista completa, explicada, está no .env.example. Mudou algo no .env? Reinicie a Iris.
"""

import os

from . import config  # noqa: F401  (importar config carrega o .env)


def _texto(nome: str, padrao: str) -> str:
    valor = os.getenv(nome)
    return padrao if valor is None or valor.strip() == "" else valor.strip()


def _inteiro(nome: str, padrao: int) -> int:
    try:
        return int(_texto(nome, str(padrao)))
    except ValueError:
        return padrao


def _decimal(nome: str, padrao: float) -> float:
    try:
        return float(_texto(nome, str(padrao)).replace(",", "."))
    except ValueError:
        return padrao


def _sim_nao(nome: str, padrao: bool) -> bool:
    return _texto(nome, "sim" if padrao else "nao").lower() in ("1", "true", "sim", "yes", "s", "on")


def _lista(nome: str, padrao: list[str]) -> list[str]:
    """Valores separados por vírgula: A,B,C"""
    return [item.strip() for item in _texto(nome, ",".join(padrao)).split(",") if item.strip()]


# ---------- Servidor e janela ----------
HOST = _texto("IRIS_HOST", "127.0.0.1")
PORTA = _inteiro("IRIS_PORTA", 8765)
ABRIR_JANELA = _sim_nao("IRIS_ABRIR_JANELA", True)
CAMINHO_EDGE = _texto("IRIS_CAMINHO_EDGE", "")  # vazio = procura o Edge sozinho
IDIOMA_DATAS = _texto("IRIS_IDIOMA_DATAS", "pt_BR")  # como as datas são escritas (ex.: en_US, es_ES)

# ---------- Ouvir (reconhecimento de voz) ----------
IDIOMA = _texto("OUVIR_IDIOMA", "pt-BR")
PALAVRAS_ATIVACAO = _lista("OUVIR_PALAVRAS_ATIVACAO", ["iris", "íris", "ei iris", "hey iris"])
PAUSA_SEGUNDOS = _decimal("OUVIR_PAUSA_SEGUNDOS", 1.5)               # frase ainda aberta
PAUSA_FINAL_SEGUNDOS = _decimal("OUVIR_PAUSA_FINAL_SEGUNDOS", 0.8)   # frase já fechada
WHISPER_ATIVO = _sim_nao("WHISPER_ATIVO", True)
WHISPER_MODELO = _texto("WHISPER_MODELO", "whisper-large-v3-turbo")
WHISPER_ESPERA_SEGUNDOS = _decimal("WHISPER_ESPERA_SEGUNDOS", 6)

# ---------- Gemini Live (conversa principal) ----------
LIVE_ATIVA = _sim_nao("LIVE_ATIVA", True)
LIVE_MODELOS = _lista("LIVE_MODELOS", ["gemini-3.1-flash-live-preview", "gemini-2.5-flash-native-audio-latest"])
LIVE_VOZ = _texto("LIVE_VOZ", "")  # vazio = usa a voz Gemini escolhida na engrenagem
LIVE_SILENCIO_MS = _inteiro("LIVE_SILENCIO_MS", 600)
LIVE_INTERROMPER_FALANDO = _sim_nao("LIVE_INTERROMPER_FALANDO", True)
LIVE_PESQUISA_GOOGLE = _sim_nao("LIVE_PESQUISA_GOOGLE", False)
LIVE_PESQUISA_BLOQUEADA_HORAS = _decimal("LIVE_PESQUISA_BLOQUEADA_HORAS", 6)
LIVE_ESPERA_CONEXAO_SEGUNDOS = _decimal("LIVE_ESPERA_CONEXAO_SEGUNDOS", 8)
LIVE_BUFFER_SEGUNDOS = _decimal("LIVE_BUFFER_SEGUNDOS", 10)      # áudio guardado enquanto (re)conecta
LIVE_REENVIO_SEGUNDOS = _decimal("LIVE_REENVIO_SEGUNDOS", 15)    # fala reenviada se a conexão cair
LIVE_FALHA_TEMPORARIA_MINUTOS = _decimal("LIVE_FALHA_TEMPORARIA_MINUTOS", 5)  # usa o modo reserva por N min

# ---------- Cérebro do modo reserva (clássico) ----------
CEREBRO_ORDEM = _lista("CEREBRO_ORDEM", ["groq", "gemini"])
GEMINI_MODELO_TEXTO = _texto("GEMINI_MODELO_TEXTO", "gemini-3.5-flash-lite")
GEMINI_PENSAMENTO = _texto("GEMINI_PENSAMENTO", "minimal")
GROQ_MODELO_TEXTO = _texto("GROQ_MODELO_TEXTO", "openai/gpt-oss-120b")
TEMPERATURA = _decimal("CEREBRO_TEMPERATURA", 0.7)
MAX_HISTORICO = _inteiro("CEREBRO_MAX_HISTORICO", 30)
ESPERA_PRIMEIRA_PALAVRA = _decimal("CEREBRO_ESPERA_PRIMEIRA_PALAVRA", 8)
ESPERA_ENTRE_PEDACOS = _decimal("CEREBRO_ESPERA_ENTRE_PEDACOS", 20)
DESCANSO_PROVEDOR_SEGUNDOS = _decimal("CEREBRO_DESCANSO_SEGUNDOS", 120)

# ---------- Voz do modo reserva (TTS) ----------
TTS_GEMINI_MODELOS = _lista("TTS_GEMINI_MODELOS", [
    "gemini-3.8-flash-tts", "gemini-3.8-flash-lite-tts", "gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts",
])
TTS_ESTILO = _texto("TTS_ESTILO", "")  # vazio: instruções junto do texto às vezes são lidas em voz alta
VOZ_RESERVA = _texto("VOZ_RESERVA", "pt-BR-ThalitaMultilingualNeural")
VOZ_EDGE_ESTAVEL = _texto("VOZ_EDGE_ESTAVEL", "pt-BR-FranciscaNeural")
TTS_DESCANSO_SEGUNDOS = _decimal("TTS_DESCANSO_SEGUNDOS", 180)
TTS_ESGOTADO_DIA_HORAS = _decimal("TTS_ESGOTADO_DIA_HORAS", 3)
GROQ_TTS_MODELO = _texto("GROQ_TTS_MODELO", "canopylabs/orpheus-v1-english")

# ---------- Memória ----------
MEMORIA_FATOS_NO_PROMPT = _inteiro("MEMORIA_FATOS_NO_PROMPT", 40)
MEMORIA_CONVERSAS_NO_PROMPT = _inteiro("MEMORIA_CONVERSAS_NO_PROMPT", 4)
MEMORIA_ASSUNTOS_NO_PROMPT = _inteiro("MEMORIA_ASSUNTOS_NO_PROMPT", 15)

# ---------- Vigília (modo proativo) ----------
VIGIA_ATIVA = _sim_nao("VIGIA_ATIVA", True)
VIGIA_INTERVALO_MINUTOS = _decimal("VIGIA_INTERVALO_MINUTOS", 5)
VIGIA_GMAIL = _sim_nao("VIGIA_GMAIL", True)
VIGIA_GMAIL_BUSCA = _texto("VIGIA_GMAIL_BUSCA", "in:inbox newer_than:2d")
VIGIA_FALAR_SOZINHA = _sim_nao("VIGIA_FALAR_SOZINHA", True)          # urgente: ela fala sem ser chamada
VIGIA_SILENCIO_NOTURNO = _texto("VIGIA_SILENCIO_NOTURNO", "23-7")    # horas em que ela não fala sozinha
VIGIA_INTERVALO_ENTRE_FALAS_MINUTOS = _decimal("VIGIA_INTERVALO_ENTRE_FALAS_MINUTOS", 20)
VIGIA_MAX_IA_POR_DIA = _inteiro("VIGIA_MAX_IA_POR_DIA", 100)          # triagens com IA por dia (limite grátis)
VIGIA_PENDENCIAS_NO_PROMPT = _inteiro("VIGIA_PENDENCIAS_NO_PROMPT", 8)

# ---------- Habilidades (SKILL.md) ----------
HABILIDADES_ATIVAS = _texto("HABILIDADES_ATIVAS", "habilidades_ativas")        # relativo = pasta da Iris
HABILIDADES_PROPOSTAS = _texto("HABILIDADES_PROPOSTAS", "habilidades_propostas")
HABILIDADES_LIMITE_TEXTO = _inteiro("HABILIDADES_LIMITE_TEXTO", 8000)         # tamanho máximo de um SKILL.md
# "melhoria" menor que esta fração da versão atual gera alerta (provavelmente perdeu passos)
HABILIDADES_ALERTA_ENCOLHIMENTO = _decimal("HABILIDADES_ALERTA_ENCOLHIMENTO", 0.6)

# ---------- Personalidade que evolui (sempre com a sua aprovação) ----------
PERSONALIDADE_EVOLUIR = _sim_nao("PERSONALIDADE_EVOLUIR", True)     # propõe mudanças no fim da conversa
PERSONALIDADE_ARQUIVO = _texto("PERSONALIDADE_ARQUIVO", "personalidade_aprendida.yaml")
PERSONALIDADE_MAX_JEITOS = _inteiro("PERSONALIDADE_MAX_JEITOS", 15)
PERSONALIDADE_MAX_TRACOS = _inteiro("PERSONALIDADE_MAX_TRACOS", 6)  # ajustes criados além dos 6 de base
PERSONALIDADE_PASSO_MAXIMO = _inteiro("PERSONALIDADE_PASSO_MAXIMO", 25)  # quanto um ajuste proposto pode andar

# ---------- Oficina (programas novos feitos pelo Claude Code) ----------
OFICINA_ATIVA = _sim_nao("OFICINA_ATIVA", True)
OFICINA_PASTA = _texto("OFICINA_PASTA", "oficina")
OFICINA_CLAUDE = _texto("OFICINA_CLAUDE", "")              # vazio = procura o claude instalado
OFICINA_MODELO = _texto("OFICINA_MODELO", "sonnet")        # sonnet gasta menos do plano que opus
OFICINA_MAX_TURNOS = _inteiro("OFICINA_MAX_TURNOS", 60)
OFICINA_TEMPO_MINUTOS = _decimal("OFICINA_TEMPO_MINUTOS", 20)
OFICINA_PROGRAMA_SEGUNDOS = _decimal("OFICINA_PROGRAMA_SEGUNDOS", 120)  # tempo máximo de cada uso

# ---------- Ferramentas e e-mail ----------
CONFIRMACAO_VALIDADE_SEGUNDOS = _decimal("CONFIRMACAO_VALIDADE_SEGUNDOS", 120)
ARQUIVO_LIMITE_LEITURA = _inteiro("ARQUIVO_LIMITE_LEITURA", 15000)       # caracteres enviados à IA
ARQUIVO_LIMITE_TAMANHO_MB = _decimal("ARQUIVO_LIMITE_TAMANHO_MB", 2)
ARQUIVO_PDF_LIMITE_MB = _decimal("ARQUIVO_PDF_LIMITE_MB", 20)          # PDFs costumam ser maiores
ARQUIVO_PDF_MAX_PAGINAS = _inteiro("ARQUIVO_PDF_MAX_PAGINAS", 30)
ARQUIVO_PDF_LEITURA_NUVEM = _sim_nao("ARQUIVO_PDF_LEITURA_NUVEM", True)  # PDF escaneado: Gemini lê a imagem
GMAIL_LIMITE_CORPO = _inteiro("GMAIL_LIMITE_CORPO", 8000)               # caracteres do e-mail enviados à IA
GMAIL_TAMANHO_LOTE = _inteiro("GMAIL_TAMANHO_LOTE", 40)                 # o Gmail limita ~50 leituras/s
GMAIL_PERMITIR_ENVIO = _sim_nao("GMAIL_PERMITIR_ENVIO", True)           # false = ela só lê e-mails
GMAIL_ANEXOS_LIMITE_MB = _decimal("GMAIL_ANEXOS_LIMITE_MB", 24)          # soma dos anexos (o Gmail aceita até 25 MB)
GMAIL_CREDENCIAIS = _texto("GMAIL_CREDENCIAIS", "")   # vazio = dados/gmail_credenciais.json
GMAIL_TOKEN = _texto("GMAIL_TOKEN", "")               # vazio = dados/gmail_token.json
