# -*- coding: utf-8 -*-
"""Pleno — Diário Alimentar (versão web)

Dois perfis de usuário:
  • Paciente:       registra refeições (4 escalas), sono e exercícios
  • Nutricionista:  acompanha pacientes com gráficos e envia arquivos

Execução local:
    pip install -r requirements.txt
    python app.py            →  http://localhost:5000

Produção (Railway/Render):
    gunicorn app:app         (defina SECRET_KEY e DATABASE_URL no ambiente)
"""
import os

from flask import Flask, redirect, url_for
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect

from config import Config
from models import db, Usuario

csrf = CSRFProtect()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "instance"), exist_ok=True)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Entre para acessar esta página."
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def carregar_usuario(user_id):
        return db.session.get(Usuario, int(user_id))

    # Blueprints
    from auth import bp_auth
    from paciente import bp_paciente
    from nutricionista import bp_nutri
    app.register_blueprint(bp_auth)
    app.register_blueprint(bp_paciente, url_prefix="/paciente")
    app.register_blueprint(bp_nutri, url_prefix="/nutri")

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            destino = "nutri.dashboard" if current_user.eh_nutricionista \
                else "paciente.dashboard"
            return redirect(url_for(destino))
        return redirect(url_for("auth.login"))

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
