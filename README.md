# Pino

PWA para acompanhar a ficha de treino com o mínimo de atrito, para você e amigos convidados. A ficha é a fonte da verdade: você edita carga/reps direto nela e o histórico de evolução é gerado automaticamente (1 ponto por dia em que algo mudou).

- **Frontend:** Vue 3 + Vite + Pinia + Tailwind + vite-plugin-pwa (`frontend/`)
- **Backend:** FastAPI + SQLAlchemy + Alembic + Postgres (`backend/`)
- **Deploy:** um único serviço no Railway (Dockerfile multi-stage); o FastAPI serve a API em `/api` e o PWA em `/`.

## Rodando localmente

Pré-requisitos: Python 3.12+, Node 22+ e podman (ou Docker) para o Postgres.

```bash
podman compose up -d                     # Postgres 16 em localhost:5432 (usuário/senha/banco: pino)
cp backend/.env.example backend/.env     # ajuste ADMIN_NAME, ADMIN_EMAIL e ADMIN_PASSWORD
cd backend && python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend && npm install && npm run dev   # proxy /api -> :8000
```

Entre com o e-mail e a senha do admin definidos no `backend/.env`.

Testes: `cd backend && .venv/bin/pytest` (usam SQLite em memória, não precisam do Postgres).

## Contas

- O **administrador** vem das variáveis `ADMIN_NAME`, `ADMIN_EMAIL` e `ADMIN_PASSWORD`. A cada inicialização o app cria essa conta ou atualiza nome, senha e permissão para bater com as variáveis. Para trocar a senha do admin, troque a variável.
- Fichas criadas antes de existirem contas ficam com o admin.
- Os demais só entram por **convite**: em Ajustes, o admin gera um link que vale para uma pessoa por 7 dias.
- Senhas são guardadas com Argon2id; a sessão é um cookie `httponly` que dura um ano e pode ser encerrada em "Sair".

## Deploy no Railway

1. Crie um projeto no Railway a partir do repositório (o `railway.toml` já aponta para o Dockerfile).
2. Adicione um serviço **PostgreSQL** ao projeto.
3. No serviço do app, configure as variáveis:
   | Variável | Valor |
   |---|---|
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
   | `ADMIN_NAME` | seu nome |
   | `ADMIN_EMAIL` | seu e-mail de login |
   | `ADMIN_PASSWORD` | senha longa (mín. 8 caracteres) |
   | `APP_TIMEZONE` | `America/Sao_Paulo` (padrão) |

   Sem `ADMIN_EMAIL` e `ADMIN_PASSWORD` o container se recusa a subir (erro no log de deploy).
4. Gere um domínio público em *Settings → Networking*. As migrações rodam sozinhas a cada deploy.
5. No celular, abra o domínio e use **Adicionar à tela inicial**.

## Uso

- **Colar ficha:** cole o texto (ex.: `Supino reto 4x10 40kg`, `Rosca 12,10,8 20kg`, linhas `Treino A` separam fichas) e confira a prévia.
- **Editar:** `−`/`+` ou toque no número; salva sozinho. “Aplicar a todas” replica a série editada.
- **Remover série:** arraste a linha para a esquerda (com desfazer).
- **Acompanhar treino:** toque no número da série para marcá-la como feita (local, zera no dia seguinte).
- **Histórico:** toque no nome do exercício.
- **Offline:** edições ficam numa fila e sincronizam quando a conexão volta.
- **Backup:** Ajustes → Exportar/Restaurar JSON (só as suas fichas).
- **Convidar:** Ajustes → Gerar link de convite (só o admin).
