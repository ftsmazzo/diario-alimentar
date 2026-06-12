# -*- coding: utf-8 -*-
"""Área do paciente: registros (refeição, sono, exercício), histórico
e arquivos recebidos do nutricionista."""
from datetime import datetime, date, timezone
from functools import wraps

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, send_from_directory, current_app, abort, jsonify,
                   session)
from flask_login import login_required, current_user

import config
from models import (db, Refeicao, RegistroSono, RegistroExercicio, Arquivo,
                    Usuario, Vinculo, clamp_escala)
from analises import buscar_registros, estatisticas, gerar_insights
from registros_svc import salvar_refeicao, salvar_sono, salvar_exercicio, salvar_por_tipo
import ai_registro

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


def _rascunho_ia():
    return session.pop("ia_rascunho", None)


def _guardar_rascunho_ia(tipo, dados):
    session["ia_rascunho"] = {"tipo": tipo, "dados": dados}


def _url_formulario(tipo):
    return {
        "refeicao": "paciente.nova_refeicao",
        "sono": "paciente.novo_sono",
        "exercicio": "paciente.novo_exercicio",
    }.get(tipo, "paciente.registrar")


def _extensao(nome):
    if not nome or "." not in nome:
        return ""
    return nome.rsplit(".", 1)[1].lower()


def _ia_ativa():
    return bool(current_app.config.get("OPENAI_API_KEY"))


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
            salvar_refeicao(current_user.id, {
                "data_hora": f.get("data_hora"),
                "tipo": f.get("tipo"),
                "alimentos": f.get("alimentos"),
                "fome_antes": f.get("fome_antes"),
                "saciedade_antes": f.get("saciedade_antes"),
                "fome_depois": f.get("fome_depois"),
                "saciedade_depois": f.get("saciedade_depois"),
                "sentimento_antes": f.get("sentimento_antes"),
                "sentimento_durante": f.get("sentimento_durante"),
                "local_refeicao": f.get("local_refeicao"),
                "companhia": f.get("companhia"),
                "tempo_refeicao": f.get("tempo_refeicao"),
                "agua_ml": f.get("agua_ml"),
                "observacoes": f.get("observacoes"),
            })
            flash("Refeição registrada.", "ok")
            return redirect(url_for("paciente.dashboard"))

    agora = datetime.now().strftime("%Y-%m-%dT%H:%M")
    rascunho = _rascunho_ia()
    prefill = rascunho["dados"] if rascunho and rascunho.get("tipo") == "refeicao" else {}
    if prefill.get("data_hora"):
        try:
            agora = datetime.fromisoformat(str(prefill["data_hora"])).strftime("%Y-%m-%dT%H:%M")
        except (TypeError, ValueError):
            pass
    return render_template("paciente/refeicao_form.html", cfg=config, agora=agora,
                           prefill=prefill)


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
            s = salvar_sono(current_user.id, {
                "data": f.get("data"),
                "hora_dormir": hd,
                "hora_acordar": ha,
                "qualidade": f.get("qualidade"),
                "como_acordou": f.get("como_acordou"),
                "interrupcoes": f.get("interrupcoes"),
                "observacoes": f.get("observacoes"),
            })
            flash(f"Sono registrado ({s.duracao_horas:.1f}h).", "ok")
            return redirect(url_for("paciente.dashboard"))

    hoje = date.today().strftime("%Y-%m-%d")
    rascunho = _rascunho_ia()
    prefill = rascunho["dados"] if rascunho and rascunho.get("tipo") == "sono" else {}
    if prefill.get("data"):
        hoje = str(prefill["data"])[:10]
    return render_template("paciente/sono_form.html", cfg=config, hoje=hoje,
                           prefill=prefill)


# ────────────────────────── exercício ──────────────────────────

@bp_paciente.route("/exercicio/novo", methods=["GET", "POST"])
@apenas_paciente
def novo_exercicio():
    if request.method == "POST":
        f = request.form
        if not f.get("tipo") or not f.get("duracao_minutos"):
            flash("Informe o tipo e a duração do exercício.", "erro")
        else:
            salvar_exercicio(current_user.id, {
                "data": f.get("data"),
                "tipo": f.get("tipo"),
                "atividade": f.get("atividade"),
                "duracao_minutos": f.get("duracao_minutos"),
                "intensidade": f.get("intensidade"),
                "sentimento_apos": f.get("sentimento_apos"),
                "observacoes": f.get("observacoes"),
            })
            flash("Exercício registrado.", "ok")
            return redirect(url_for("paciente.dashboard"))

    hoje = date.today().strftime("%Y-%m-%d")
    rascunho = _rascunho_ia()
    prefill = rascunho["dados"] if rascunho and rascunho.get("tipo") == "exercicio" else {}
    if prefill.get("data"):
        hoje = str(prefill["data"])[:10]
    return render_template("paciente/exercicio_form.html", cfg=config, hoje=hoje,
                           prefill=prefill)


# ────────────────────────── IA — registro rápido ──────────────────────────

@bp_paciente.route("/api/ia/audio", methods=["POST"])
@apenas_paciente
def ia_audio():
    if not _ia_ativa():
        return jsonify({"ok": False, "erro": "Registro por voz não está disponível no momento."}), 503

    arquivo = request.files.get("audio")
    if not arquivo or not arquivo.filename:
        return jsonify({"ok": False, "erro": "Envie um áudio."}), 400

    ext = _extensao(arquivo.filename)
    if ext not in current_app.config["IA_FORMATOS_AUDIO"]:
        return jsonify({"ok": False, "erro": "Formato de áudio não suportado."}), 400

    limite = current_app.config["IA_MAX_AUDIO_MB"] * 1024 * 1024
    dados = arquivo.read()
    if len(dados) > limite:
        return jsonify({"ok": False, "erro": f"Áudio muito grande (máx. {current_app.config['IA_MAX_AUDIO_MB']} MB)."}), 400

    try:
        resultado = ai_registro.interpretar_audio(dados, arquivo.filename)
        return jsonify({"ok": True, **resultado})
    except Exception as exc:
        current_app.logger.exception("IA áudio")
        return jsonify({"ok": False, "erro": str(exc)}), 500


@bp_paciente.route("/api/ia/imagem", methods=["POST"])
@apenas_paciente
def ia_imagem():
    if not _ia_ativa():
        return jsonify({"ok": False, "erro": "Registro por foto não está disponível no momento."}), 503

    arquivo = request.files.get("imagem")
    if not arquivo or not arquivo.filename:
        return jsonify({"ok": False, "erro": "Envie uma imagem."}), 400

    ext = _extensao(arquivo.filename)
    if ext not in current_app.config["IA_FORMATOS_IMAGEM"]:
        return jsonify({"ok": False, "erro": "Use JPG, PNG ou WEBP."}), 400

    dados = arquivo.read()
    if len(dados) > current_app.config["MAX_CONTENT_LENGTH"]:
        return jsonify({"ok": False, "erro": "Imagem muito grande."}), 400

    mime = arquivo.mimetype or f"image/{'jpeg' if ext in ('jpg', 'jpeg') else ext}"
    try:
        resultado = ai_registro.interpretar_imagem(dados, mime)
        return jsonify({"ok": True, **resultado})
    except Exception as exc:
        current_app.logger.exception("IA imagem")
        return jsonify({"ok": False, "erro": str(exc)}), 500


@bp_paciente.route("/api/ia/salvar", methods=["POST"])
@apenas_paciente
def ia_salvar():
    payload = request.get_json(silent=True) or {}
    tipo = payload.get("tipo")
    dados = payload.get("dados") or {}
    if tipo not in ("refeicao", "sono", "exercicio"):
        return jsonify({"ok": False, "erro": "Tipo de registro inválido."}), 400
    try:
        salvar_por_tipo(current_user.id, tipo, dados)
        return jsonify({"ok": True, "redirect": url_for("paciente.dashboard")})
    except ValueError as exc:
        return jsonify({"ok": False, "erro": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("IA salvar")
        return jsonify({"ok": False, "erro": "Não foi possível salvar o registro."}), 500


@bp_paciente.route("/api/ia/editar", methods=["POST"])
@apenas_paciente
def ia_editar():
    payload = request.get_json(silent=True) or {}
    tipo = payload.get("tipo")
    dados = payload.get("dados") or {}
    if tipo not in ("refeicao", "sono", "exercicio"):
        return jsonify({"ok": False, "erro": "Tipo inválido."}), 400
    _guardar_rascunho_ia(tipo, dados)
    return jsonify({"ok": True, "redirect": url_for(_url_formulario(tipo))})


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
