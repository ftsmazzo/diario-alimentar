# -*- coding: utf-8 -*-
"""Modelos de dados — schema portado do app desktop, com multiusuário.

Núcleo preservado: as 4 ESCALAS da refeição (fome/saciedade × antes/depois).
Novidades web: Usuario (paciente/nutricionista), Vinculo e Arquivo.
"""
import secrets
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


def agora():
    return datetime.now(timezone.utc)


def clamp_escala(valor, padrao=5):
    """Garante escala 1–10. Nunca lança exceção (portado do desktop)."""
    try:
        return max(1, min(10, int(valor)))
    except (TypeError, ValueError):
        return padrao


# ════════════════════════════════════════════════════════════════
#  USUÁRIOS E VÍNCULOS
# ════════════════════════════════════════════════════════════════

class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(256), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'paciente' | 'nutricionista'
    # Código que o nutricionista compartilha para o paciente se vincular
    codigo_convite = db.Column(db.String(10), unique=True, index=True)
    # LGPD: consentimento explícito para tratamento de dados de saúde
    aceitou_termos_em = db.Column(db.DateTime, nullable=False, default=agora)
    criado_em = db.Column(db.DateTime, default=agora)

    refeicoes = db.relationship("Refeicao", backref="usuario", lazy="dynamic",
                                cascade="all, delete-orphan")
    sonos = db.relationship("RegistroSono", backref="usuario", lazy="dynamic",
                            cascade="all, delete-orphan")
    exercicios = db.relationship("RegistroExercicio", backref="usuario",
                                 lazy="dynamic", cascade="all, delete-orphan")

    # ---- senha ----
    def definir_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

    # ---- papéis ----
    @property
    def eh_nutricionista(self):
        return self.tipo == "nutricionista"

    @property
    def eh_paciente(self):
        return self.tipo == "paciente"

    # ---- convite ----
    @staticmethod
    def gerar_codigo():
        """Código curto e legível (sem 0/O, 1/I) para o convite."""
        alfabeto = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        while True:
            codigo = "".join(secrets.choice(alfabeto) for _ in range(6))
            if not Usuario.query.filter_by(codigo_convite=codigo).first():
                return codigo

    # ---- vínculos ----
    def pacientes(self):
        """Pacientes vinculados a este nutricionista (lista)."""
        if not self.eh_nutricionista:
            return []
        return (Usuario.query
                .join(Vinculo, Vinculo.paciente_id == Usuario.id)
                .filter(Vinculo.nutricionista_id == self.id)
                .order_by(Usuario.nome).all())

    def nutricionista(self):
        """Nutricionista vinculado a este paciente (ou None)."""
        if not self.eh_paciente:
            return None
        v = Vinculo.query.filter_by(paciente_id=self.id).first()
        return Usuario.query.get(v.nutricionista_id) if v else None

    def atende(self, paciente_id):
        """True se este nutricionista atende o paciente informado."""
        return Vinculo.query.filter_by(
            nutricionista_id=self.id, paciente_id=paciente_id).first() is not None


class Vinculo(db.Model):
    __tablename__ = "vinculos"
    __table_args__ = (db.UniqueConstraint("nutricionista_id", "paciente_id"),)

    id = db.Column(db.Integer, primary_key=True)
    nutricionista_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"),
                                 nullable=False, index=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"),
                            nullable=False, index=True)
    criado_em = db.Column(db.DateTime, default=agora)


# ════════════════════════════════════════════════════════════════
#  REGISTROS DO PACIENTE (schema do desktop + usuario_id)
# ════════════════════════════════════════════════════════════════

class Refeicao(db.Model):
    """Refeição com as 4 escalas obrigatórias (1–10)."""
    __tablename__ = "refeicoes"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"),
                           nullable=False, index=True)
    data_hora = db.Column(db.DateTime, nullable=False, index=True)
    tipo = db.Column(db.String(40), nullable=False)
    alimentos = db.Column(db.Text, default="")

    fome_antes = db.Column(db.Integer, nullable=False, default=5)
    saciedade_antes = db.Column(db.Integer, nullable=False, default=3)
    fome_depois = db.Column(db.Integer, nullable=False, default=3)
    saciedade_depois = db.Column(db.Integer, nullable=False, default=8)

    sentimento_antes = db.Column(db.String(40), default="")
    sentimento_durante = db.Column(db.String(40), default="")
    local_refeicao = db.Column(db.String(40), default="")
    companhia = db.Column(db.String(40), default="")
    tempo_refeicao = db.Column(db.Integer, default=0)   # minutos
    agua_ml = db.Column(db.Float, default=0.0)
    observacoes = db.Column(db.Text, default="")
    criado_em = db.Column(db.DateTime, default=agora)

    @property
    def efetividade(self):
        """Média entre redução de fome e aumento de saciedade → 0–100%.
        (Fórmula idêntica à versão desktop.)"""
        reducao_fome = self.fome_antes - self.fome_depois
        aumento_sac = self.saciedade_depois - self.saciedade_antes
        score = (reducao_fome + aumento_sac) / 2.0
        return max(0.0, min(100.0, (score + 9) / 18 * 100))


class RegistroSono(db.Model):
    __tablename__ = "sono"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"),
                           nullable=False, index=True)
    data = db.Column(db.Date, nullable=False, index=True)
    hora_dormir = db.Column(db.String(5), nullable=False)   # "HH:MM"
    hora_acordar = db.Column(db.String(5), nullable=False)
    duracao_horas = db.Column(db.Float, default=0.0)
    qualidade = db.Column(db.Integer, default=7)            # 1–10
    como_acordou = db.Column(db.String(40), default="")
    interrupcoes = db.Column(db.Integer, default=0)
    observacoes = db.Column(db.Text, default="")
    criado_em = db.Column(db.DateTime, default=agora)


class RegistroExercicio(db.Model):
    __tablename__ = "exercicios"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"),
                           nullable=False, index=True)
    data = db.Column(db.Date, nullable=False, index=True)
    tipo = db.Column(db.String(50), nullable=False)
    atividade = db.Column(db.String(80), default="")
    duracao_minutos = db.Column(db.Float, nullable=False, default=0)
    intensidade = db.Column(db.Integer, default=5)          # 1–10
    sentimento_apos = db.Column(db.String(40), default="")
    observacoes = db.Column(db.Text, default="")
    criado_em = db.Column(db.DateTime, default=agora)


# ════════════════════════════════════════════════════════════════
#  ARQUIVOS (nutricionista → paciente)
# ════════════════════════════════════════════════════════════════

class Arquivo(db.Model):
    """Cardápios, pedidos de exames e planos enviados pelo nutricionista."""
    __tablename__ = "arquivos"

    id = db.Column(db.Integer, primary_key=True)
    nutricionista_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"),
                                 nullable=False, index=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"),
                            nullable=False, index=True)
    categoria = db.Column(db.String(50), nullable=False)
    nome_original = db.Column(db.String(255), nullable=False)
    nome_armazenado = db.Column(db.String(255), nullable=False, unique=True)
    descricao = db.Column(db.Text, default="")
    enviado_em = db.Column(db.DateTime, default=agora)
    visto_em = db.Column(db.DateTime, nullable=True)

    nutricionista = db.relationship("Usuario", foreign_keys=[nutricionista_id])
    paciente = db.relationship("Usuario", foreign_keys=[paciente_id])
