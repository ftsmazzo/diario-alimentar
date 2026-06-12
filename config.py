# -*- coding: utf-8 -*-
"""Configuração central da aplicação.

Local:     SQLite (zero configuração — basta rodar `flask db upgrade`)
Produção:  defina DATABASE_URL (PostgreSQL), SECRET_KEY e use o
           Dockerfile (migrations + bootstrap no entrypoint).
"""
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    APP_NAME = "Pleno — Diário Alimentar"

    # NUNCA use a chave padrão em produção: defina SECRET_KEY no ambiente.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-trocar-em-producao")

    # Railway/Render fornecem DATABASE_URL automaticamente ao criar um Postgres.
    _db_url = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'diario.db')}")
    # Compatibilidade: SQLAlchemy exige 'postgresql://', alguns hosts dão 'postgres://'
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # Arquivos enviados pelo nutricionista (cardápios, exames, treinos)
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(BASE_DIR, "uploads"))
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB por arquivo
    EXTENSOES_PERMITIDAS = {"pdf", "png", "jpg", "jpeg", "doc", "docx", "xls", "xlsx", "csv", "txt"}

    # Sessão
    REMEMBER_COOKIE_DURATION = 60 * 60 * 24 * 14  # 14 dias

    # IA — registro por áudio/imagem (OpenAI)
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_WHISPER_MODEL = os.environ.get("OPENAI_WHISPER_MODEL", "whisper-1")
    IA_MAX_AUDIO_MB = int(os.environ.get("IA_MAX_AUDIO_MB", "8"))
    IA_FORMATOS_AUDIO = {"webm", "ogg", "mp4", "m4a", "mpeg", "mp3", "wav"}
    IA_FORMATOS_IMAGEM = {"jpg", "jpeg", "png", "webp", "heic", "heif"}


# ── Listas de domínio (portadas do app desktop — manter as 4 escalas!) ──
TIPOS_REFEICAO = ["Café da manhã", "Lanche manhã", "Almoço",
                  "Lanche tarde", "Jantar", "Ceia", "Beliscada"]

TIPOS_EXERCICIO = ["Aeróbico", "Anaeróbico", "Misto (Aeróbico + Anaeróbico)",
                   "Flexibilidade/Alongamento", "Equilíbrio/Coordenação"]

SENTIMENTOS_ANTES = ["Calmo", "Ansioso", "Estressado", "Feliz", "Triste",
                     "Entediado", "Irritado", "Relaxado", "Preocupado",
                     "Eufórico", "Neutro", "Motivado", "Cansado", "Energizado"]

SENTIMENTOS_DURANTE = ["Prazeroso", "Culpado", "Satisfeito", "Automático",
                       "Consciente", "Apressado", "Relaxado", "Social",
                       "Solitário", "Reconfortante", "Neutro", "Distraído",
                       "Focado", "Ansioso"]

LOCAIS = ["Casa", "Trabalho", "Restaurante", "Casa de amigos", "Carro",
          "Rua", "Shopping", "Escola/Faculdade", "Outro"]

COMPANHIAS = ["Sozinho", "Família", "Amigos", "Colegas de trabalho",
              "Parceiro(a)", "Reunião social", "Evento", "Outro"]

COMO_ACORDOU = ["Descansado", "Sonolento", "Cansado", "Revigorado",
                "Irritado", "Confuso", "Alerta", "Preguiçoso",
                "Ansioso", "Tranquilo", "Com dor", "Energizado"]

SENTIMENTOS_POS_EXERCICIO = ["Energizado", "Cansado", "Satisfeito", "Motivado",
                             "Exausto", "Relaxado", "Frustrado", "Realizado",
                             "Dolorido", "Feliz", "Ansioso", "Calmo", "Forte", "Fraco"]

CATEGORIAS_ARQUIVO = ["Sugestão de cardápio", "Pedido de exames",
                      "Planejamento de exercícios", "Material educativo", "Outro"]
