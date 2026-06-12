# -*- coding: utf-8 -*-
"""Análises e insights — lógica portada da versão desktop.

Princípio mantido: este sistema REGISTRA, não diagnostica. Os alertas
apontam padrões e sugerem conversa com o profissional, nunca rotulam.
"""
from datetime import date, datetime, timedelta

from models import Refeicao, RegistroSono, RegistroExercicio


def _media(valores):
    valores = [v for v in valores if v is not None]
    return sum(valores) / len(valores) if valores else 0.0


def periodo(dias):
    fim = datetime.now()
    inicio = fim - timedelta(days=dias)
    return inicio, fim


def buscar_registros(usuario_id, dias=30, somente_enviados=False):
    """Refeições, sono e exercícios do período, mais antigos primeiro."""
    inicio, _ = periodo(dias)
    q_ref = (Refeicao.query
             .filter(Refeicao.usuario_id == usuario_id,
                     Refeicao.data_hora >= inicio))
    if somente_enviados:
        q_ref = q_ref.filter(Refeicao.enviado_nutri_em.isnot(None))
    refeicoes = q_ref.order_by(Refeicao.data_hora.asc()).all()

    q_sono = (RegistroSono.query
              .filter(RegistroSono.usuario_id == usuario_id,
                      RegistroSono.data >= inicio.date()))
    if somente_enviados:
        q_sono = q_sono.filter(RegistroSono.enviado_nutri_em.isnot(None))
    sono = q_sono.order_by(RegistroSono.data.asc()).all()

    q_exe = (RegistroExercicio.query
             .filter(RegistroExercicio.usuario_id == usuario_id,
                     RegistroExercicio.data >= inicio.date()))
    if somente_enviados:
        q_exe = q_exe.filter(RegistroExercicio.enviado_nutri_em.isnot(None))
    exercicios = q_exe.order_by(RegistroExercicio.data.asc()).all()
    return refeicoes, sono, exercicios


def estatisticas(refeicoes, sono, exercicios):
    """Cards do dashboard (mesmos indicadores da versão desktop)."""
    return {
        "refeicoes": {
            "total": len(refeicoes),
            "fome_antes_media": _media([r.fome_antes for r in refeicoes]),
            "sac_depois_media": _media([r.saciedade_depois for r in refeicoes]),
            "efetividade_media": _media([r.efetividade for r in refeicoes]),
        },
        "sono": {
            "total": len(sono),
            "duracao_media": _media([s.duracao_horas for s in sono]),
            "qualidade_media": _media([s.qualidade for s in sono]),
            "interrupcoes_media": _media([s.interrupcoes for s in sono]),
        },
        "exercicios": {
            "total": len(exercicios),
            "minutos_total": sum(e.duracao_minutos or 0 for e in exercicios),
            "intensidade_media": _media([e.intensidade for e in exercicios]),
        },
    }


def gerar_insights(refeicoes, sono, exercicios):
    """Observações descritivas sobre o período (portado do desktop)."""
    insights = []

    if refeicoes:
        efet = _media([r.efetividade for r in refeicoes])
        if efet >= 70:
            insights.append("As refeições estão cumprindo bem o papel: "
                            "boa redução de fome e ganho de saciedade.")
        elif efet < 45:
            insights.append("A efetividade média das refeições está baixa — "
                            "pode valer observar composição e ritmo das refeições.")

        fome_alta = [r for r in refeicoes if r.fome_antes >= 8]
        if len(fome_alta) >= max(3, len(refeicoes) * 0.4):
            insights.append("Em boa parte das refeições a fome chega muito alta (8+). "
                            "Intervalos longos entre refeições podem estar contribuindo.")

        rapidas = [r for r in refeicoes if 0 < (r.tempo_refeicao or 0) <= 10]
        if len(rapidas) >= 3:
            insights.append(f"{len(rapidas)} refeições duraram 10 minutos ou menos. "
                            "Comer devagar tende a melhorar a percepção de saciedade.")

        # padrão temporal: tipo mais frequente
        tipos = {}
        for r in refeicoes:
            tipos[r.tipo] = tipos.get(r.tipo, 0) + 1
        if tipos.get("Beliscada", 0) >= 4:
            insights.append("Há beliscadas frequentes no período — registrar "
                            "o sentimento antes pode ajudar a entender o gatilho.")

    if sono:
        dur = _media([s.duracao_horas for s in sono])
        if dur and dur < 6.5:
            insights.append(f"O sono médio está em {dur:.1f}h. Noites curtas "
                            "costumam aumentar a fome no dia seguinte.")
        qual = _media([s.qualidade for s in sono])
        if qual and qual >= 8:
            insights.append("A qualidade do sono está consistentemente boa no período.")

    if exercicios:
        minutos = sum(e.duracao_minutos or 0 for e in exercicios)
        if minutos >= 150:
            insights.append("Meta de 150 min/semana de atividade física vem "
                            "sendo alcançada — ótimo sinal.")
    elif refeicoes or sono:
        insights.append("Sem exercícios registrados no período.")

    if not insights:
        insights.append("Ainda há poucos dados para gerar observações — "
                        "siga registrando para enxergar padrões.")
    return insights


def alertas_bem_estar(refeicoes):
    """Padrões que merecem atenção. Linguagem responsável: aponta o padrão
    e sugere conversa com profissional — nunca diagnostica."""
    alertas = []
    if len(refeicoes) < 5:
        return alertas

    negativos_durante = {"Culpado", "Ansioso"}
    com_culpa = [r for r in refeicoes if r.sentimento_durante in negativos_durante]
    if len(com_culpa) >= max(3, len(refeicoes) * 0.35):
        alertas.append("Sentimentos difíceis (culpa/ansiedade) aparecem com "
                       "frequência durante as refeições no período.")

    fome_sempre_baixa = all(r.fome_antes <= 2 for r in refeicoes[-7:]) \
        if len(refeicoes) >= 7 else False
    if fome_sempre_baixa:
        alertas.append("A fome registrada antes das refeições está muito baixa "
                       "de forma consistente nos últimos registros.")

    # dias com 1 refeição ou menos
    por_dia = {}
    for r in refeicoes:
        d = r.data_hora.date()
        por_dia[d] = por_dia.get(d, 0) + 1
    dias_escassos = [d for d, n in por_dia.items() if n <= 1]
    if len(dias_escassos) >= 3 and len(por_dia) >= 5:
        alertas.append("Há vários dias com apenas uma refeição registrada — "
                       "pode ser falta de registro ou padrão alimentar irregular.")

    return alertas


def series_para_graficos(refeicoes, sono, exercicios):
    """Dados prontos para o Chart.js no painel do nutricionista."""
    return {
        "refeicoes": {
            "labels": [r.data_hora.strftime("%d/%m %H:%M") for r in refeicoes],
            "fome_antes": [r.fome_antes for r in refeicoes],
            "fome_depois": [r.fome_depois for r in refeicoes],
            "sac_antes": [r.saciedade_antes for r in refeicoes],
            "sac_depois": [r.saciedade_depois for r in refeicoes],
            "efetividade": [round(r.efetividade) for r in refeicoes],
        },
        "sono": {
            "labels": [s.data.strftime("%d/%m") for s in sono],
            "duracao": [s.duracao_horas for s in sono],
            "qualidade": [s.qualidade for s in sono],
        },
        "exercicios": {
            "labels": [e.data.strftime("%d/%m") for e in exercicios],
            "minutos": [e.duracao_minutos for e in exercicios],
            "intensidade": [e.intensidade for e in exercicios],
        },
    }
