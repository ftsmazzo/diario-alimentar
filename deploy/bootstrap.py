# -*- coding: utf-8 -*-
"""Cria o primeiro nutricionista (admin de bootstrap) se o banco estiver vazio.

Variáveis de ambiente:
  ADMIN_EMAIL     — e-mail do primeiro usuário (obrigatório para bootstrap)
  ADMIN_PASSWORD  — senha (mín. 8 caracteres)
  ADMIN_NAME      — nome exibido (opcional, padrão: Administrador)
"""
import os
import sys


def ensure_admin():
    email = (os.environ.get("ADMIN_EMAIL") or "").strip().lower()
    password = os.environ.get("ADMIN_PASSWORD") or ""
    nome = (os.environ.get("ADMIN_NAME") or "Administrador").strip()

    if not email or not password:
        print("Bootstrap: ADMIN_EMAIL/ADMIN_PASSWORD não definidos — ignorado.")
        return

    if len(password) < 8:
        print("Bootstrap: ADMIN_PASSWORD precisa de pelo menos 8 caracteres — ignorado.",
              file=sys.stderr)
        return

    from app import create_app
    from models import db, Usuario

    app = create_app()
    with app.app_context():
        if Usuario.query.first():
            print("Bootstrap: banco já possui usuários — ignorado.")
            return

        usuario = Usuario(nome=nome, email=email, tipo="nutricionista")
        usuario.definir_senha(password)
        usuario.codigo_convite = Usuario.gerar_codigo()
        db.session.add(usuario)
        db.session.commit()
        print(f"Bootstrap: nutricionista criado ({email}).")
        print(f"Bootstrap: código de convite = {usuario.codigo_convite}")


if __name__ == "__main__":
    ensure_admin()
