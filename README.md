# Pleno — Diário Alimentar (versão web)

Aplicação web com dois perfis de usuário:

- **Paciente** — registra refeições (com as 4 escalas de fome/saciedade,
  antes e depois), sono e exercícios; recebe arquivos do nutricionista.
- **Nutricionista** — acompanha pacientes vinculados com gráficos e
  estatísticas; envia cardápios, pedidos de exames e planos de treino.

O vínculo é feito por **código de convite**: cada nutricionista tem um
código de 6 caracteres que o paciente **precisa informar no cadastro**.

## Rodar localmente

```bash
pip install -r requirements.txt
export FLASK_APP=app:app   # Windows: set FLASK_APP=app:app
flask db upgrade
python app.py
# → http://localhost:5000
```

Banco SQLite em `instance/diario.db` (criado pela migration).
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
deploy/             wait_db, bootstrap do primeiro usuário
entrypoint.sh       migrations + bootstrap + gunicorn (deploy)
Dockerfile          build de produção
migrations/         Alembic / Flask-Migrate
templates/          Jinja2 — base, auth, paciente, nutri
static/             CSS (identidade visual) e JS leve
uploads/            arquivos enviados (volume persistente em produção)
```

## Deploy com Docker (EasyPanel)

### Serviços no projeto EasyPanel

| Serviço | Obrigatório |
|---------|-------------|
| **PostgreSQL** | Sim — criar **antes** do App |
| **App** (GitHub + Dockerfile) | Sim |
| Redis, MySQL, etc. | Não |

### 1. PostgreSQL

- **+ Service → PostgreSQL**
- Anote host interno, usuário, senha e nome do banco

### 2. App

- **+ Service → App**
- Source: GitHub → `ftsmazzo/diario-alimentar`
- Build: **Dockerfile** (caminho: `Dockerfile`)
- **Domains & Proxy → Port:** `8000`

### 3. Variáveis de ambiente

| Variável | Descrição |
|----------|-----------|
| `SECRET_KEY` | Chave longa aleatória |
| `DATABASE_URL` | `postgresql://user:pass@HOST_POSTGRES:5432/banco` |
| `PORT` | `8000` (padrão do container) |
| `UPLOAD_FOLDER` | `/app/uploads` |
| `ADMIN_EMAIL` | E-mail do primeiro nutricionista (bootstrap) |
| `ADMIN_PASSWORD` | Senha (mín. 8 caracteres) |
| `ADMIN_NAME` | Nome (opcional) |

O bootstrap só roda se o banco **não tiver usuários**. O primeiro login
é um **nutricionista** (perfil profissional do sistema). O código de
convite aparece nos logs do deploy.

### 4. Volume de uploads (recomendado)

App → **Mounts → Volume**

- `mountPath`: `/app/uploads`

Sem volume, arquivos enviados pelo nutricionista se perdem em redeploy.

### 5. O que acontece em cada deploy

O `entrypoint.sh` executa automaticamente:

1. Aguarda o PostgreSQL ficar disponível
2. `flask db upgrade` — aplica migrations pendentes
3. Bootstrap do primeiro nutricionista (se `ADMIN_*` definidos e banco vazio)
4. Inicia Gunicorn na porta `8000`

### Nova migration (desenvolvimento)

```bash
export FLASK_APP=app:app
flask db migrate -m "descricao da mudanca"
flask db upgrade
git add migrations/ && git commit && git push
```

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
