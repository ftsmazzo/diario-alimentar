# -*- coding: utf-8 -*-
"""Configuração central da aplicação.

Local:     SQLite (zero configuração — basta rodar)
Produção:  defina DATABASE_URL (PostgreSQL) e SECRET_KEY como
           variáveis de ambiente no Railway/Render.
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

    # Arquivos enviados pelo nutricionista (cardápios, exames, treinos)
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(BASE_DIR, "uploads"))
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB por arquivo
    EXTENSOES_PERMITIDAS = {"pdf", "png", "jpg", "jpeg", "doc", "docx", "xls", "xlsx", "csv", "txt"}

    # Sessão
    REMEMBER_COOKIE_DURATION = 60 * 60 * 24 * 14  # 14 dias


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
