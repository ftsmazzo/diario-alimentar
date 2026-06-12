# -*- coding: utf-8 -*-
"""Área do paciente: registros (refeição, sono, exercício), histórico
e arquivos recebidos do nutricionista."""
from datetime import datetime, date, timezone
from functools import wraps

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, send_from_directory, current_app, abort)
from flask_login import login_required, current_user

import config
from models import (db, Refeicao, RegistroSono, RegistroExercicio, Arquivo,
                    Usuario, Vinculo, clamp_escala)
from analises import buscar_registros, estatisticas, gerar_insights

bp_paciente = Blueprint("paciente", __name__)


def apenas_paciente(f):
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.eh_paciente:
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return wrapper


# ────────────────────────── helpers ──────────────────────────

def _parse_data_hora(valor, padrao_agora=True):
    """'YYYY-MM-DDTHH:MM' (input datetime-local) → datetime."""
    try:
        return datetime.strptime(valor, "%Y-%m-%dT%H:%M")
    except (TypeError, ValueError):
        return datetime.now() if padrao_agora else None


def _parse_data(valor):
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return date.today()


def _duracao_sono(hora_dormir, hora_acordar):
    """Duração em horas, atravessando a meia-noite quando necessário."""
    try:
        hd = datetime.strptime(hora_dormir, "%H:%M")
        ha = datetime.strptime(hora_acordar, "%H:%M")
        minutos = (ha - hd).seconds // 60 if ha > hd \
            else ((24 * 60) - (hd.hour * 60 + hd.minute)
                  + ha.hour * 60 + ha.minute)
        return round(minutos / 60, 2)
    except (TypeError, ValueError):
        return 0.0


# ────────────────────────── hub de registro ──────────────────────────

@bp_paciente.route("/registrar")
@apenas_paciente
def registrar():
    return render_template("paciente/registrar.html")


# ────────────────────────── dashboard ──────────────────────────

@bp_paciente.route("/")
@apenas_paciente
def dashboard():
    refeicoes, sono, exercicios = buscar_registros(current_user.id, dias=7)
    stats = estatisticas(refeicoes, sono, exercicios)
    insights = gerar_insights(refeicoes, sono, exercicios)
    arquivos_novos = Arquivo.query.filter_by(
        paciente_id=current_user.id, visto_em=None).count()
    nutri = current_user.nutricionista()
    ultimas = sorted(refeicoes, key=lambda r: r.data_hora, reverse=True)[:5]
    return render_template("paciente/dashboard.html", stats=stats,
                           insights=insights, ultimas=ultimas,
                           arquivos_novos=arquivos_novos, nutri=nutri)


# ────────────────────────── refeição ──────────────────────────

@bp_paciente.route("/refeicao/nova", methods=["GET", "POST"])
@apenas_paciente
def nova_refeicao():
    if request.method == "POST":
        f = request.form
        if not f.get("tipo"):
            flash("Escolha o tipo de refeição.", "erro")
        else:
            r = Refeicao(
                usuario_id=current_user.id,
                data_hora=_parse_data_hora(f.get("data_hora")),
                tipo=f.get("tipo"),
                alimentos=(f.get("alimentos") or "").strip(),
                fome_antes=clamp_escala(f.get("fome_antes"), 5),
                saciedade_antes=clamp_escala(f.get("saciedade_antes"), 3),
                fome_depois=clamp_escala(f.get("fome_depois"), 3),
                saciedade_depois=clamp_escala(f.get("saciedade_depois"), 8),
                sentimento_antes=f.get("sentimento_antes") or "",
                sentimento_durante=f.get("sentimento_durante") or "",
                local_refeicao=f.get("local_refeicao") or "",
                companhia=f.get("companhia") or "",
                tempo_refeicao=int(f.get("tempo_refeicao") or 0),
                agua_ml=float(f.get("agua_ml") or 0),
                observacoes=(f.get("observacoes") or "").strip(),
            )
            db.session.add(r)
            db.session.commit()
            flash("Refeição registrada.", "ok")
            return redirect(url_for("paciente.dashboard"))

    agora = datetime.now().strftime("%Y-%m-%dT%H:%M")
    return render_template("paciente/refeicao_form.html", cfg=config, agora=agora)


# ────────────────────────── sono ──────────────────────────

@bp_paciente.route("/sono/novo", methods=["GET", "POST"])
@apenas_paciente
def novo_sono():
    if request.method == "POST":
        f = request.form
        hd, ha = f.get("hora_dormir") or "", f.get("hora_acordar") or ""
        if not hd or not ha:
            flash("Informe os horários de dormir e acordar.", "erro")
        else:
            s = RegistroSono(
                usuario_id=current_user.id,
                data=_parse_data(f.get("data")),
                hora_dormir=hd, hora_acordar=ha,
                duracao_horas=_duracao_sono(hd, ha),
                qualidade=clamp_escala(f.get("qualidade"), 7),
                como_acordou=f.get("como_acordou") or "",
                interrupcoes=int(f.get("interrupcoes") or 0),
                observacoes=(f.get("observacoes") or "").strip(),
            )
            db.session.add(s)
            db.session.commit()
            flash(f"Sono registrado ({s.duracao_horas:.1f}h).", "ok")
            return redirect(url_for("paciente.dashboard"))

    hoje = date.today().strftime("%Y-%m-%d")
    return render_template("paciente/sono_form.html", cfg=config, hoje=hoje)


# ────────────────────────── exercício ──────────────────────────

@bp_paciente.route("/exercicio/novo", methods=["GET", "POST"])
@apenas_paciente
def novo_exercicio():
    if request.method == "POST":
        f = request.form
        if not f.get("tipo") or not f.get("duracao_minutos"):
            flash("Informe o tipo e a duração do exercício.", "erro")
        else:
            e = RegistroExercicio(
                usuario_id=current_user.id,
                data=_parse_data(f.get("data")),
                tipo=f.get("tipo"),
                atividade=(f.get("atividade") or "").strip(),
                duracao_minutos=float(f.get("duracao_minutos") or 0),
                intensidade=clamp_escala(f.get("intensidade"), 5),
                sentimento_apos=f.get("sentimento_apos") or "",
                observacoes=(f.get("observacoes") or "").strip(),
            )
            db.session.add(e)
            db.session.commit()
            flash("Exercício registrado.", "ok")
            return redirect(url_for("paciente.dashboard"))

    hoje = date.today().strftime("%Y-%m-%d")
    return render_template("paciente/exercicio_form.html", cfg=config, hoje=hoje)


# ────────────────────────── histórico ──────────────────────────

@bp_paciente.route("/historico")
@apenas_paciente
def historico():
    dias = request.args.get("dias", 30, type=int)
    dias = max(1, min(365, dias))
    refeicoes, sono, exercicios = buscar_registros(current_user.id, dias=dias)
    refeicoes = sorted(refeicoes, key=lambda r: r.data_hora, reverse=True)
    sono = sorted(sono, key=lambda s: s.data, reverse=True)
    exercicios = sorted(exercicios, key=lambda e: e.data, reverse=True)
    return render_template("paciente/historico.html", refeicoes=refeicoes,
                           sono=sono, exercicios=exercicios, dias=dias)


# ────────────────────────── vínculo ──────────────────────────

@bp_paciente.route("/vincular", methods=["POST"])
@apenas_paciente
def vincular():
    codigo = (request.form.get("codigo_convite") or "").strip().upper()
    nutri = Usuario.query.filter_by(codigo_convite=codigo,
                                    tipo="nutricionista").first()
    if not nutri:
        flash("Código não encontrado. Confira com seu nutricionista.", "erro")
    elif current_user.nutricionista():
        flash("Você já está vinculado a um nutricionista.", "info")
    else:
        db.session.add(Vinculo(nutricionista_id=nutri.id,
                               paciente_id=current_user.id))
        db.session.commit()
        flash(f"Vínculo criado com {nutri.nome}.", "ok")
    return redirect(url_for("paciente.dashboard"))


# ────────────────────────── arquivos ──────────────────────────

@bp_paciente.route("/arquivos")
@apenas_paciente
def arquivos():
    lista = (Arquivo.query.filter_by(paciente_id=current_user.id)
             .order_by(Arquivo.enviado_em.desc()).all())
    return render_template("paciente/arquivos.html", arquivos=lista)


@bp_paciente.route("/arquivos/<int:arquivo_id>/baixar")
@apenas_paciente
def baixar_arquivo(arquivo_id):
    arq = db.session.get(Arquivo, arquivo_id)
    if not arq or arq.paciente_id != current_user.id:
        abort(404)
    if arq.visto_em is None:
        arq.visto_em = datetime.now(timezone.utc)
        db.session.commit()
    return send_from_directory(current_app.config["UPLOAD_FOLDER"],
                               arq.nome_armazenado, as_attachment=True,
                               download_name=arq.nome_original)
