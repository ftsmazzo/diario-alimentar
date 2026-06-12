# -*- coding: utf-8 -*-
"""Interpretação de áudio e imagem para registro rápido (OpenAI).

Requer OPENAI_API_KEY no ambiente. Não diagnostica — apenas estrutura o que
o paciente relatou para preencher o diário.
"""
import base64
import json
import re
from datetime import datetime

import config

SCHEMA_INSTRUCOES = """
Você estrutura relatos de pacientes em um diário alimentar brasileiro.
Responda APENAS com JSON válido (sem markdown).

Detecte o tipo do registro:
- "refeicao": alimentação / beliscada / café / almoço / jantar etc.
- "sono": sono, dormir, acordar, noite mal dormida etc.
- "exercicio": atividade física, treino, caminhada, academia etc.

Campos por tipo (use null se não mencionado; infira valores razoáveis quando óbvio):

refeicao:
  data_hora (ISO "YYYY-MM-DDTHH:MM", use agora se não disser),
  tipo (um de: {tipos_refeicao}),
  alimentos (texto livre),
  fome_antes, saciedade_antes, fome_depois, saciedade_depois (inteiros 1-10),
  sentimento_antes (um de: {sentimentos_antes} ou null),
  sentimento_durante (um de: {sentimentos_durante} ou null),
  local_refeicao (um de: {locais} ou null),
  companhia (um de: {companias} ou null),
  tempo_refeicao (minutos int), agua_ml (float), observacoes (texto)

sono:
  data ("YYYY-MM-DD", noite de — ontem se disse "ontem à noite"),
  hora_dormir ("HH:MM"), hora_acordar ("HH:MM"),
  qualidade (1-10), como_acordou (um de: {como_acordou} ou null),
  interrupcoes (int), observacoes (texto)

exercicio:
  data ("YYYY-MM-DD"),
  tipo (um de: {tipos_exercicio}),
  atividade (texto), duracao_minutos (float),
  intensidade (1-10), sentimento_apos (um de: {sentimentos_pos} ou null),
  observacoes (texto)

Inclua sempre:
  "tipo": "refeicao"|"sono"|"exercicio",
  "confianca": 0.0-1.0,
  "resumo": frase curta em português do que entendeu,
  "dados": {{ ...campos do tipo... }}
"""


def ia_disponivel():
    from flask import current_app
    return bool(current_app.config.get("OPENAI_API_KEY"))


def _cliente():
    from openai import OpenAI
    from flask import current_app
    chave = current_app.config.get("OPENAI_API_KEY")
    if not chave:
        raise RuntimeError("IA não configurada. Defina OPENAI_API_KEY no servidor.")
    return OpenAI(api_key=chave)


def _prompt_sistema():
    agora = datetime.now().strftime("%Y-%m-%d %H:%M")
    base = SCHEMA_INSTRUCOES.format(
        tipos_refeicao=", ".join(config.TIPOS_REFEICAO),
        tipos_exercicio=", ".join(config.TIPOS_EXERCICIO),
        sentimentos_antes=", ".join(config.SENTIMENTOS_ANTES),
        sentimentos_durante=", ".join(config.SENTIMENTOS_DURANTE),
        locais=", ".join(config.LOCAIS),
        companias=", ".join(config.COMPANHIAS),
        como_acordou=", ".join(config.COMO_ACORDOU),
        sentimentos_pos=", ".join(config.SENTIMENTOS_POS_EXERCICIO),
    )
    return f"{base}\n\nData/hora atual de referência: {agora} (fuso do servidor)."


def _extrair_json(texto):
    texto = (texto or "").strip()
    if texto.startswith("```"):
        texto = re.sub(r"^```(?:json)?\s*", "", texto)
        texto = re.sub(r"\s*```$", "", texto)
    return json.loads(texto)


def _estruturar_texto(texto, contexto=""):
    from flask import current_app
    cliente = _cliente()
    modelo = current_app.config.get("OPENAI_MODEL", "gpt-4o-mini")
    mensagem_usuario = texto
    if contexto:
        mensagem_usuario = f"[Contexto: {contexto}]\n\n{texto}"

    resposta = cliente.chat.completions.create(
        model=modelo,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _prompt_sistema()},
            {"role": "user", "content": mensagem_usuario},
        ],
        temperature=0.2,
    )
    return _extrair_json(resposta.choices[0].message.content)


def interpretar_audio(dados_binarios, nome_arquivo="audio.webm"):
    from flask import current_app
    cliente = _cliente()
    modelo_whisper = current_app.config.get("OPENAI_WHISPER_MODEL", "whisper-1")

    transcricao = cliente.audio.transcriptions.create(
        model=modelo_whisper,
        file=(nome_arquivo, dados_binarios),
        language="pt",
    )
    texto = transcricao.text.strip()
    if not texto:
        raise ValueError("Não foi possível entender o áudio. Tente falar mais perto do microfone.")

    resultado = _estruturar_texto(texto, contexto="Entrada por áudio do paciente.")
    resultado["transcricao"] = texto
    return resultado


def interpretar_imagem(dados_binarios, mime="image/jpeg"):
    from flask import current_app
    cliente = _cliente()
    modelo = current_app.config.get("OPENAI_MODEL", "gpt-4o-mini")
    b64 = base64.standard_b64encode(dados_binarios).decode("ascii")

    resposta = cliente.chat.completions.create(
        model=modelo,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _prompt_sistema()},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "O paciente enviou uma FOTO relacionada ao diário. "
                            "Se for comida/prato, registre como refeicao listando alimentos visíveis. "
                            "Estime escalas de fome/saciedade apenas se houver pistas; senão use "
                            "valores moderados (fome_antes 6, saciedade_depois 7). "
                            "Se a imagem não for de refeição, tente sono ou exercício apenas se "
                            "for óbvio; caso contrário use refeicao com observacoes explicando a foto."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                ],
            },
        ],
        temperature=0.2,
    )
    resultado = _extrair_json(resposta.choices[0].message.content)
    resultado["transcricao"] = resultado.get("resumo", "Análise da imagem.")
    return resultado
