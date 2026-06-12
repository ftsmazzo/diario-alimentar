# -*- coding: utf-8 -*-
"""Área do nutricionista: lista de pacientes, painel do paciente com
gráficos e envio de arquivos (cardápio, exames, treinos)."""
import os
import uuid
from functools import wraps

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, jsonify, current_app, abort, send_from_directory)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

import config
from models import db, Usuario, Arquivo, Refeicao
from analises import (buscar_registros, estatisticas, gerar_insights,
                      alertas_bem_estar, series_para_graficos)

bp_nutri = Blueprint("nutri", __name__)


def apenas_nutricionista(f):
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.eh_nutricionista:
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return wrapper


def _paciente_autorizado(paciente_id):
    """Carrega o paciente garantindo o vínculo — barreira de privacidade."""
    if not current_user.atende(paciente_id):
        abort(403)
    paciente = db.session.get(Usuario, paciente_id)
    if not paciente or not paciente.eh_paciente:
        abort(404)
    return paciente


def _extensao_permitida(nome):
    return ("." in nome and
            nome.rsplit(".", 1)[1].lower() in config.Config.EXTENSOES_PERMITIDAS)


# ────────────────────────── dashboard ──────────────────────────

@bp_nutri.route("/")
@apenas_nutricionista
def dashboard():
    pacientes = current_user.pacientes()
    resumo = []
    for p in pacientes:
        ultima = (Refeicao.query.filter_by(usuario_id=p.id)
                  .filter(Refeicao.enviado_nutri_em.isnot(None))
                  .order_by(Refeicao.data_hora.desc()).first())
        total_7d = len(buscar_registros(p.id, dias=7, somente_enviados=True)[0])
        resumo.append({"paciente": p, "ultima": ultima, "refeicoes_7d": total_7d})
    return render_template("nutri/dashboard.html", resumo=resumo,
                           codigo=current_user.codigo_convite)


# ────────────────────────── painel do paciente ──────────────────────────

@bp_nutri.route("/paciente/<int:paciente_id>")
@apenas_nutricionista
def paciente_detalhe(paciente_id):
    paciente = _paciente_autorizado(paciente_id)
    dias = request.args.get("dias", 30, type=int)
    dias = max(7, min(365, dias))

    refeicoes, sono, exercicios = buscar_registros(paciente.id, dias=dias,
                                                   somente_enviados=True)
    stats = estatisticas(refeicoes, sono, exercicios)
    insights = gerar_insights(refeicoes, sono, exercicios)
    alertas = alertas_bem_estar(refeicoes)
    arquivos = (Arquivo.query
                .filter_by(paciente_id=paciente.id,
                           nutricionista_id=current_user.id)
                .order_by(Arquivo.enviado_em.desc()).all())
    refeicoes_recentes = sorted(refeicoes, key=lambda r: r.data_hora,
                                reverse=True)[:20]

    return render_template("nutri/paciente_detalhe.html", paciente=paciente,
                           stats=stats, insights=insights, alertas=alertas,
                           arquivos=arquivos, dias=dias, cfg=config,
                           refeicoes_recentes=refeicoes_recentes)


@bp_nutri.route("/paciente/<int:paciente_id>/dados")
@apenas_nutricionista
def paciente_dados(paciente_id):
    """JSON consumido pelo Chart.js no painel do paciente."""
    paciente = _paciente_autorizado(paciente_id)
    dias = request.args.get("dias", 30, type=int)
    dias = max(7, min(365, dias))
    refeicoes, sono, exercicios = buscar_registros(paciente.id, dias=dias,
                                                   somente_enviados=True)
    return jsonify(series_para_graficos(refeicoes, sono, exercicios))


# ────────────────────────── arquivos ──────────────────────────

@bp_nutri.route("/paciente/<int:paciente_id>/enviar-arquivo", methods=["POST"])
@apenas_nutricionista
def enviar_arquivo(paciente_id):
    paciente = _paciente_autorizado(paciente_id)

    arquivo = request.files.get("arquivo")
    categoria = request.form.get("categoria") or "Outro"
    descricao = (request.form.get("descricao") or "").strip()

    if not arquivo or arquivo.filename == "":
        flash("Selecione um arquivo para enviar.", "erro")
    elif not _extensao_permitida(arquivo.filename):
        flash("Tipo de arquivo não permitido. Use PDF, imagem, "
              "Word, Excel, CSV ou TXT.", "erro")
    elif categoria not in config.CATEGORIAS_ARQUIVO:
        flash("Categoria inválida.", "erro")
    else:
        nome_original = secure_filename(arquivo.filename)
        extensao = nome_original.rsplit(".", 1)[1].lower()
        nome_armazenado = f"{uuid.uuid4().hex}.{extensao}"
        arquivo.save(os.path.join(current_app.config["UPLOAD_FOLDER"],
                                  nome_armazenado))
        db.session.add(Arquivo(
            nutricionista_id=current_user.id, paciente_id=paciente.id,
            categoria=categoria, nome_original=nome_original,
            nome_armazenado=nome_armazenado, descricao=descricao))
        db.session.commit()
        flash(f"Arquivo enviado para {paciente.nome}.", "ok")

    return redirect(url_for("nutri.paciente_detalhe", paciente_id=paciente.id))


@bp_nutri.route("/arquivos/<int:arquivo_id>/baixar")
@apenas_nutricionista
def baixar_arquivo(arquivo_id):
    arq = db.session.get(Arquivo, arquivo_id)
    if not arq or arq.nutricionista_id != current_user.id:
        abort(404)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"],
                               arq.nome_armazenado, as_attachment=True,
                               download_name=arq.nome_original)


@bp_nutri.route("/arquivos/<int:arquivo_id>/excluir", methods=["POST"])
@apenas_nutricionista
def excluir_arquivo(arquivo_id):
    arq = db.session.get(Arquivo, arquivo_id)
    if not arq or arq.nutricionista_id != current_user.id:
        abort(404)
    paciente_id = arq.paciente_id
    caminho = os.path.join(current_app.config["UPLOAD_FOLDER"],
                           arq.nome_armazenado)
    try:
        if os.path.exists(caminho):
            os.remove(caminho)
    except OSError:
        pass  # registro sai do banco mesmo se o arquivo físico falhar
    db.session.delete(arq)
    db.session.commit()
    flash("Arquivo removido.", "ok")
    return redirect(url_for("nutri.paciente_detalhe", paciente_id=paciente_id))
