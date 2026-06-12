# -*- coding: utf-8 -*-
"""Teste de ponta a ponta com o test client do Flask."""
import io
import re
import os

os.environ["UPLOAD_FOLDER"] = "/tmp/uploads_teste"
import app as modulo_app
from models import db

aplicacao = modulo_app.app
aplicacao.config["WTF_CSRF_ENABLED"] = False  # simplifica o teste

with aplicacao.app_context():
    db.create_all()
falhas = []


def checa(cond, msg):
    print(("OK   " if cond else "FALHA") + " " + msg)
    if not cond:
        falhas.append(msg)


with aplicacao.test_client() as nutri:
    # 1. cadastro nutricionista
    r = nutri.post("/registro", data={
        "nome": "Dra. Ana", "email": "ana@nutri.com", "senha": "senha12345",
        "tipo": "nutricionista", "termos": "on"}, follow_redirects=True)
    checa(r.status_code == 200, "cadastro nutricionista")

    r = nutri.get("/nutri/")
    codigo = re.search(r'codigo-convite">(\w{6})<', r.get_data(as_text=True))
    checa(codigo is not None, "código de convite gerado")
    codigo = codigo.group(1)

with aplicacao.test_client() as pac:
    # 2. cadastro paciente com código → vínculo automático
    r = pac.post("/registro", data={
        "nome": "Hudson Silva", "email": "hudson@ex.com", "senha": "senha12345",
        "tipo": "paciente", "codigo_convite": codigo, "termos": "on"},
        follow_redirects=True)
    checa(r.status_code == 200, "cadastro paciente com convite")

    # 3. registros
    r = pac.post("/paciente/refeicao/nova", data={
        "data_hora": "2026-06-10T12:30", "tipo": "Almoço",
        "alimentos": "Arroz, feijão, frango", "fome_antes": 8,
        "saciedade_antes": 2, "fome_depois": 2, "saciedade_depois": 9,
        "sentimento_antes": "Ansioso", "sentimento_durante": "Satisfeito",
        "local_refeicao": "Casa", "companhia": "Família",
        "tempo_refeicao": 25, "agua_ml": 300}, follow_redirects=True)
    checa("Refeição registrada" in r.get_data(as_text=True), "refeição salva")

    r = pac.post("/paciente/sono/novo", data={
        "data": "2026-06-10", "hora_dormir": "23:00", "hora_acordar": "06:30",
        "qualidade": 8, "como_acordou": "Descansado", "interrupcoes": 1},
        follow_redirects=True)
    checa("7.5h" in r.get_data(as_text=True), "sono salvo (duração 7.5h cruzando meia-noite)")

    r = pac.post("/paciente/exercicio/novo", data={
        "data": "2026-06-10", "tipo": "Aeróbico", "atividade": "Caminhada",
        "duracao_minutos": 40, "intensidade": 6, "sentimento_apos": "Energizado"},
        follow_redirects=True)
    checa("Exercício registrado" in r.get_data(as_text=True), "exercício salvo")

    for rota in ["/paciente/", "/paciente/historico", "/paciente/arquivos"]:
        checa(pac.get(rota).status_code == 200, f"tela paciente {rota}")

    # paciente NÃO acessa área do nutricionista
    r = pac.get("/nutri/", follow_redirects=False)
    checa(r.status_code == 302, "paciente bloqueado na área do nutricionista")

with aplicacao.test_client() as nutri:
    nutri.post("/login", data={"email": "ana@nutri.com", "senha": "senha12345"})

    r = nutri.get("/nutri/")
    checa("Hudson Silva" in r.get_data(as_text=True), "paciente aparece na lista")

    r = nutri.get("/nutri/paciente/2?dias=30")
    html = r.get_data(as_text=True)
    checa(r.status_code == 200, "painel do paciente abre")
    checa("8" in html and "Almoço" in html, "dados da refeição no painel")

    r = nutri.get("/nutri/paciente/2/dados?dias=30")
    j = r.get_json()
    checa(j["refeicoes"]["fome_antes"] == [8], "JSON dos gráficos correto")
    checa(j["refeicoes"]["efetividade"] == [86], "efetividade calculada (8→2, 2→9 = 86%)")

    # 4. envio de arquivo
    r = nutri.post("/nutri/paciente/2/enviar-arquivo", data={
        "categoria": "Sugestão de cardápio", "descricao": "Cardápio da semana",
        "arquivo": (io.BytesIO(b"%PDF-1.4 conteudo"), "cardapio.pdf")},
        content_type="multipart/form-data", follow_redirects=True)
    checa("Arquivo enviado" in r.get_data(as_text=True), "upload do nutricionista")

    # extensão proibida
    r = nutri.post("/nutri/paciente/2/enviar-arquivo", data={
        "categoria": "Outro", "arquivo": (io.BytesIO(b"x"), "virus.exe")},
        content_type="multipart/form-data", follow_redirects=True)
    checa("não permitido" in r.get_data(as_text=True), "extensão .exe bloqueada")

    # nutricionista NÃO acessa paciente de outro profissional
    r = nutri.get("/nutri/paciente/999")
    checa(r.status_code == 403, "acesso a paciente não vinculado → 403")

with aplicacao.test_client() as pac:
    pac.post("/login", data={"email": "hudson@ex.com", "senha": "senha12345"})
    r = pac.get("/paciente/arquivos")
    checa("cardapio.pdf" in r.get_data(as_text=True), "paciente vê o arquivo")
    r = pac.get("/paciente/arquivos/1/baixar")
    checa(r.status_code == 200 and b"%PDF" in r.data, "download do arquivo funciona")
    # marca como visto
    r = pac.get("/paciente/arquivos")
    checa("novo" not in r.get_data(as_text=True).split("cardapio")[0][-200:],
          "arquivo marcado como visto após download")

print()
print("RESULTADO:", "TODOS OS TESTES PASSARAM ✔" if not falhas
      else f"{len(falhas)} falha(s): {falhas}")
