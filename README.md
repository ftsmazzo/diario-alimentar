# Pleno — Diário Alimentar (versão web)

Aplicação web com dois perfis de usuário:

- **Paciente** — registra refeições (com as 4 escalas de fome/saciedade,
  antes e depois), sono e exercícios; recebe arquivos do nutricionista.
- **Nutricionista** — acompanha pacientes vinculados com gráficos e
  estatísticas; envia cardápios, pedidos de exames e planos de treino.

O vínculo é feito por **código de convite**: cada nutricionista tem um
código de 6 caracteres que o paciente informa no cadastro (ou depois,
no painel).

## Rodar localmente

```bash
pip install -r requirements.txt
python app.py
# → http://localhost:5000
```

Banco SQLite criado automaticamente em `instance/diario.db`.
Para testar, crie uma conta de nutricionista, copie o código de convite
e crie uma conta de paciente usando esse código (use outro navegador ou
janela anônima para manter as duas sessões).

Teste automatizado de ponta a ponta: `python teste_e2e.py`

## Estrutura

```
app.py              fábrica Flask, login, blueprints
config.py           configurações + listas de domínio (4 escalas preservadas)
models.py           Usuario, Vinculo, Refeicao, RegistroSono,
                    RegistroExercicio, Arquivo
analises.py         estatísticas, insights e alertas (portados do desktop)
auth.py             cadastro (LGPD), login, logout
paciente.py         rotas do paciente
nutricionista.py    rotas do nutricionista (gráficos via JSON + Chart.js)
templates/          Jinja2 — base, auth, paciente, nutri
static/             CSS (identidade visual) e JS leve
uploads/            arquivos enviados (em produção, ver nota abaixo)
```

## Deploy em produção (Railway) com domínio próprio

1. Suba o código para um repositório GitHub.
2. No [Railway](https://railway.app): **New Project → Deploy from GitHub**.
3. Adicione um banco: **New → Database → PostgreSQL**
   (a variável `DATABASE_URL` é injetada automaticamente).
4. Em *Variables* do serviço web, defina:
   - `SECRET_KEY` → string longa e aleatória
     (`python -c "import secrets; print(secrets.token_hex(32))"`)
5. Descomente `psycopg2-binary` no `requirements.txt`.
6. Comando de start (Procfile já incluído): `gunicorn app:app`
7. Em *Settings → Networking → Custom Domain*, adicione seu domínio e
   crie o registro CNAME no seu provedor (Registro.br, GoDaddy etc.).
   O HTTPS é emitido automaticamente.

**Arquivos enviados:** o disco do Railway/Render é efêmero — em produção
real, migre os uploads para um storage externo (Cloudflare R2 ou AWS S3).
Está no roadmap da Fase 2; localmente e em testes a pasta `uploads/` basta.

## LGPD — pontos já implementados

- Consentimento explícito no cadastro (Art. 11 — dados de saúde),
  com data registrada (`aceitou_termos_em`).
- Senhas com hash (Werkzeug/scrypt), nunca em texto puro.
- Isolamento de dados: nutricionista só acessa pacientes vinculados
  (HTTP 403 caso contrário); paciente só baixa arquivos destinados a ele.
- Proteção CSRF em todos os formulários.

Pendências para operação comercial: página de Política de Privacidade,
fluxo de exclusão de conta/dados a pedido do titular, e registro das
operações de tratamento.

## Roadmap

- **Fase 2 (comercial):** convite por e-mail, assinatura do nutricionista
  (Stripe/Mercado Pago), storage externo de arquivos, política de
  privacidade e exclusão de conta.
- **Fase 3:** PWA instalável no celular, lembretes de registro,
  exportação de relatório em PDF para o nutricionista.

---

*Pleno registra a rotina — não substitui avaliação médica ou nutricional.*
