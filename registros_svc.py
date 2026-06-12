# -*- coding: utf-8 -*-
"""Persistência de registros a partir de formulário ou dados estruturados pela IA."""
from datetime import datetime, date

import config
from models import db, Refeicao, RegistroSono, RegistroExercicio, clamp_escala


def _parse_data_hora(valor):
    if isinstance(valor, datetime):
        return valor
    try:
        return datetime.strptime(str(valor), "%Y-%m-%dT%H:%M")
    except (TypeError, ValueError):
        try:
            return datetime.fromisoformat(str(valor))
        except (TypeError, ValueError):
            return datetime.now()


def _parse_data(valor):
    if isinstance(valor, date):
        return valor
    try:
        return datetime.strptime(str(valor), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return date.today()


def _duracao_sono(hora_dormir, hora_acordar):
    try:
        hd = datetime.strptime(hora_dormir, "%H:%M")
        ha = datetime.strptime(hora_acordar, "%H:%M")
        minutos = (ha - hd).seconds // 60 if ha > hd \
            else ((24 * 60) - (hd.hour * 60 + hd.minute) + ha.hour * 60 + ha.minute)
        return round(minutos / 60, 2)
    except (TypeError, ValueError):
        return 0.0


def _escolher(valor, opcoes, padrao=""):
    if valor in opcoes:
        return valor
    return padrao


def salvar_refeicao(usuario_id, dados):
    d = dados or {}
    tipo = _escolher(d.get("tipo"), config.TIPOS_REFEICAO)
    if not tipo:
        raise ValueError("Tipo de refeição não identificado.")

    r = Refeicao(
        usuario_id=usuario_id,
        data_hora=_parse_data_hora(d.get("data_hora")),
        tipo=tipo,
        alimentos=(d.get("alimentos") or "").strip(),
        fome_antes=clamp_escala(d.get("fome_antes"), 5),
        saciedade_antes=clamp_escala(d.get("saciedade_antes"), 3),
        fome_depois=clamp_escala(d.get("fome_depois"), 3),
        saciedade_depois=clamp_escala(d.get("saciedade_depois"), 8),
        sentimento_antes=_escolher(d.get("sentimento_antes"), config.SENTIMENTOS_ANTES),
        sentimento_durante=_escolher(d.get("sentimento_durante"), config.SENTIMENTOS_DURANTE),
        local_refeicao=_escolher(d.get("local_refeicao"), config.LOCAIS),
        companhia=_escolher(d.get("companhia"), config.COMPANHIAS),
        tempo_refeicao=int(d.get("tempo_refeicao") or 0),
        agua_ml=float(d.get("agua_ml") or 0),
        observacoes=(d.get("observacoes") or "").strip(),
    )
    db.session.add(r)
    db.session.commit()
    return r


def salvar_sono(usuario_id, dados):
    d = dados or {}
    hd = d.get("hora_dormir") or ""
    ha = d.get("hora_acordar") or ""
    if not hd or not ha:
        raise ValueError("Horários de sono não identificados.")

    s = RegistroSono(
        usuario_id=usuario_id,
        data=_parse_data(d.get("data")),
        hora_dormir=hd,
        hora_acordar=ha,
        duracao_horas=_duracao_sono(hd, ha),
        qualidade=clamp_escala(d.get("qualidade"), 7),
        como_acordou=_escolher(d.get("como_acordou"), config.COMO_ACORDOU),
        interrupcoes=int(d.get("interrupcoes") or 0),
        observacoes=(d.get("observacoes") or "").strip(),
    )
    db.session.add(s)
    db.session.commit()
    return s


def salvar_exercicio(usuario_id, dados):
    d = dados or {}
    tipo = _escolher(d.get("tipo"), config.TIPOS_EXERCICIO)
    duracao = float(d.get("duracao_minutos") or 0)
    if not tipo or duracao <= 0:
        raise ValueError("Tipo e duração do exercício são obrigatórios.")

    e = RegistroExercicio(
        usuario_id=usuario_id,
        data=_parse_data(d.get("data")),
        tipo=tipo,
        atividade=(d.get("atividade") or "").strip(),
        duracao_minutos=duracao,
        intensidade=clamp_escala(d.get("intensidade"), 5),
        sentimento_apos=_escolher(d.get("sentimento_apos"), config.SENTIMENTOS_POS_EXERCICIO),
        observacoes=(d.get("observacoes") or "").strip(),
    )
    db.session.add(e)
    db.session.commit()
    return e


def salvar_por_tipo(usuario_id, tipo, dados):
    if tipo == "refeicao":
        return salvar_refeicao(usuario_id, dados)
    if tipo == "sono":
        return salvar_sono(usuario_id, dados)
    if tipo == "exercicio":
        return salvar_exercicio(usuario_id, dados)
    raise ValueError("Tipo de registro desconhecido.")
