# Pino

PWA pessoal para acompanhar a ficha de treino com o mínimo de atrito. A ficha é a fonte da verdade: você edita carga/reps direto nela e o histórico de evolução é gerado automaticamente (1 ponto por dia em que algo mudou).

- **Frontend:** Vue 3 + Vite + Pinia + Tailwind + vite-plugin-pwa (`frontend/`)
- **Backend:** FastAPI + SQLAlchemy + Alembic + Postgres (`backend/`)
- **Deploy:** um único serviço no Railway (Dockerfile multi-stage); o FastAPI serve a API em `/api` e o PWA em `/`.

## Rodando localmente

```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/alembic upgrade head          # SQLite em ./dev.db por padrão
APP_PASSWORD=teste123 .venv/bin/uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend && npm install && npm run dev   # proxy /api -> :8000
```

Testes: `cd backend && .venv/bin/pytest`

## Deploy no Railway

1. Suba o repositório no GitHub e crie um projeto no Railway a partir dele (o `railway.toml` já aponta para o Dockerfile).
2. Adicione um banco **PostgreSQL** ao projeto.
3. No serviço do app, configure as variáveis:
   | Variável | Valor |
   |---|---|
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
   | `APP_PASSWORD` | sua senha de acesso |
   | `SECRET_KEY` | string aleatória longa (`openssl rand -hex 32`) |
   | `APP_TIMEZONE` | `America/Sao_Paulo` (padrão) |
   Sem `APP_PASSWORD` ou `SECRET_KEY` o container se recusa a subir (erro no log de deploy).
4. Gere um domínio público em *Settings → Networking*. As migrações rodam sozinhas a cada deploy.
5. No celular, abra o domínio e use **Adicionar à tela inicial**.

## Uso

- **Colar ficha:** cole o texto (ex.: `Supino reto 4x10 40kg`, `Rosca 12,10,8 20kg`, linhas `Treino A` separam fichas) e confira a prévia.
- **Editar:** `−`/`+` ou toque no número; salva sozinho. “Aplicar a todas” replica a série editada.
- **Remover série:** arraste a linha para a esquerda (com desfazer).
- **Acompanhar treino:** toque no número da série para marcá-la como feita (local, zera no dia seguinte).
- **Histórico:** toque no nome do exercício.
- **Offline:** edições ficam numa fila e sincronizam quando a conexão volta.
- **Backup:** Ajustes → Exportar/Restaurar JSON.
