# -*- coding: utf-8 -*-
"""Autenticação: cadastro (2 perfis), login, logout.

Vínculo nutricionista ↔ paciente: o nutricionista possui um código de
convite; o paciente precisa informar esse código no cadastro para criar
a conta vinculada.
"""
import re

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from models import db, Usuario, Vinculo

bp_auth = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@bp_auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        senha = request.form.get("senha") or ""
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario and usuario.verificar_senha(senha):
            login_user(usuario, remember=bool(request.form.get("lembrar")))
            return redirect(url_for("index"))
        flash("E-mail ou senha incorretos.", "erro")

    return render_template("auth/login.html")


@bp_auth.route("/registro", methods=["GET", "POST"])
def registro():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        senha = request.form.get("senha") or ""
        tipo = request.form.get("tipo") or ""
        codigo = (request.form.get("codigo_convite") or "").strip().upper()
        aceitou = request.form.get("termos")

        # ---- validações ----
        erros = []
        if len(nome) < 2:
            erros.append("Informe seu nome.")
        if not EMAIL_RE.match(email):
            erros.append("E-mail inválido.")
        if len(senha) < 8:
            erros.append("A senha precisa de pelo menos 8 caracteres.")
        if tipo not in ("paciente", "nutricionista"):
            erros.append("Escolha o tipo de conta.")
        if not aceitou:
            erros.append("É preciso aceitar o termo de consentimento (LGPD).")
        if Usuario.query.filter_by(email=email).first():
            erros.append("Este e-mail já está cadastrado.")

        nutri_convite = None
        if tipo == "paciente":
            if not codigo:
                erros.append("Informe o código do seu nutricionista.")
            else:
                nutri_convite = Usuario.query.filter_by(
                    codigo_convite=codigo, tipo="nutricionista").first()
                if not nutri_convite:
                    erros.append("Código de convite não encontrado. "
                                 "Confira com seu nutricionista.")

        if erros:
            for e in erros:
                flash(e, "erro")
            return render_template("auth/registro.html", form=request.form)

        # ---- criação ----
        usuario = Usuario(nome=nome, email=email, tipo=tipo)
        usuario.definir_senha(senha)
        if tipo == "nutricionista":
            usuario.codigo_convite = Usuario.gerar_codigo()
        db.session.add(usuario)
        db.session.flush()  # garante usuario.id antes do vínculo

        if tipo == "paciente":
            db.session.add(Vinculo(nutricionista_id=nutri_convite.id,
                                   paciente_id=usuario.id))
        db.session.commit()

        login_user(usuario)
        flash(f"Bem-vindo(a), {nome}!", "ok")
        return redirect(url_for("index"))

    return render_template("auth/registro.html", form={})


@bp_auth.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("auth.login"))
