# Backend Eventos

API REST em Python (FastAPI) que concentra toda a logica de negocio da agenda de eventos,
usando o Supabase apenas como Postgres (conexao direta), Auth (JWT) e Storage.

## Stack

- FastAPI + Pydantic v2
- SQLAlchemy 2.0 (async) + asyncpg
- Alembic (migrations)
- PyJWT (validacao de JWT do Supabase Auth)
- httpx (integracao GitHub)
- supabase-py (Storage, com Service Role Key)
- Pytest + pytest-asyncio + httpx.AsyncClient
- ruff + mypy
- Docker / docker-compose

## Arquitetura

```
Router (FastAPI) -> Service (regra de negocio) -> Repository (queries) -> Model (SQLAlchemy)
                              |
                          Schema (Pydantic)
```

- `app/routers`: endpoints HTTP, dependencias de auth/RBAC.
- `app/services`: regras de negocio (slug, recomendacoes, RBAC de papeis, etc.).
- `app/repositories`: acesso a dados via SQLAlchemy, sem regra de negocio.
- `app/models`: entidades SQLAlchemy mapeando as 9 tabelas existentes no Supabase.
- `app/schemas`: DTOs Pydantic de entrada/saida.
- `app/rbac`: enum de papeis, matriz de permissoes e dependencies (`require_role`,
  `require_permission`).
- `app/integrations`: Supabase Storage (upload/remocao de imagens) e cliente GitHub
  (com cache em memoria de 5 min).
- `app/utils`: geracao de slug (`slug.py`) e parsing de `data_evento` DD/MM/YYYY
  (`event_date.py`) — compativeis com `src/utils/slug.js` e `src/utils/eventDate.js`
  do frontend.

## Configuracao

Copie `.env.example` para `.env` e preencha:

- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`: usados apenas para Storage (bucket `imagens`).
- `SUPABASE_JWT_SECRET`: usado para validar localmente o JWT emitido pelo Supabase Auth
  (Dashboard > Settings > API > JWT Settings).
- `DATABASE_URL`: conexao direta ao Postgres do Supabase via `asyncpg`.
- `GITHUB_TOKEN`, `GITHUB_REPO`, `GITHUB_REPO_BACKEND`: integracao com a API do GitHub.
- `CORS_ORIGINS`: lista separada por virgula das origens do frontend.

### Obtendo o `.env` rapidamente (devs do time)

As credenciais reais de desenvolvimento ficam centralizadas no repositorio privado
`cafebugado/backendeventos-env` (apenas arquivos `.env`, sem codigo). Pre-requisitos:
acesso de leitura a esse repositorio (peca a quem administra o projeto) e estar logado
no GitHub CLI (`gh auth login`).

Com isso, basta rodar:

```bash
./scripts/fetch-env.ps1   # Windows
./scripts/fetch-env.sh    # Linux/Mac
```

O script clona/atualiza o repo de env e copia `dev.env` para `.env` na raiz do projeto
(perguntando antes de sobrescrever um `.env` local diferente). Use `-Up` (PowerShell) ou
`--up` (Bash) para já subir `docker compose up --build` em seguida. Para atualizar depois
de uma rotacao de credenciais, edite o arquivo `dev.env` no repo `backendeventos-env` e
peca para o time rodar o script novamente.

> Nota de seguranca: versionar segredos em texto puro, mesmo em repositorio privado, nao
> e ideal a longo prazo. Mantenha o acesso restrito a devs ativos e rotacione as
> credenciais (`SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `GITHUB_TOKEN`) sempre
> que alguem sair do time.

## Autenticacao e RBAC

- Login/cadastro continuam via **Supabase Auth** no frontend. O backend apenas valida o
  `access_token` (HS256, `SUPABASE_JWT_SECRET`, audience `authenticated`) e extrai o
  `user_id` (`sub`).
- Papeis (`super_admin` > `admin` > `moderador`, default `moderador`) ficam na tabela
  `user_roles`. Como o backend conecta com credenciais privilegiadas (bypass RLS), toda
  autorizacao e feita em Python (`app/rbac/permissions.py`), via `require_role(...)` e
  `require_permission(...)`.
- `admin` so pode atribuir/remover o papel `moderador` e nao pode alterar papeis de
  `admin`/`super_admin`. `super_admin` gerencia qualquer papel.

## Decisoes registradas

- **`data_evento` permanece `TEXT` (formato `DD/MM/YYYY`)** na v1, para compatibilidade
  com os dados existentes. Validado via regex no Pydantic. Migracao para `DATE` nativo
  pode ser feita depois via Alembic + backfill.
- **Auditoria via triggers SQL existentes**: `audit_log` continua sendo populada pelos
  triggers do Postgres (migrations 001-018 do Supabase). O backend expoe apenas leitura
  (`GET /audit-logs`, `GET /audit-logs/users`).
- **Fallback de coluna `status` ausente** (presente no JS antigo) **nao foi portado** —
  a tabela `eventos` ja possui a coluna `status` (migration 016).
- **OG tags e sitemap**: implementados em `/og` e `/sitemap.xml` consultando o backend
  diretamente (substituem `api/og.ts`/`api/sitemap.ts`, que podem ser mantidos como proxy
  fino na Vercel Edge se desejado).
- **Schema do banco**: as tabelas ja existem no Supabase (criadas pelas migrations SQL
  001-018). A revisao Alembic `0001_baseline` nao executa DDL; apos configurar
  `DATABASE_URL`, rode `alembic stamp 0001` para sincronizar o historico sem recriar
  tabelas. Novas evolucoes de schema devem ser criadas como revisoes a partir da
  baseline.

## Rodando localmente

### Com Docker

```bash
docker compose up --build
```

A API sobe em `http://localhost:8000` (`/docs` para o Swagger UI) e um Postgres local em
`localhost:5432` (para desenvolvimento; em produção `DATABASE_URL` aponta para o Postgres
do Supabase).

### Sem Docker

```bash
python -m venv .venv
.venv/Scripts/activate  # ou source .venv/bin/activate no Linux/Mac
pip install -e ".[dev]"
cp .env.example .env  # preencha as variaveis
uvicorn app.main:app --reload
```

## Testes

```bash
pytest
ruff check app tests
mypy app
```

Os testes de integracao usam SQLite em memoria (via `aiosqlite`) e um
`SUPABASE_JWT_SECRET` de teste para gerar tokens validos sem depender do Supabase real.

## Endpoints principais

Consulte `/docs` (Swagger) apos subir a API. Resumo por dominio:

| Dominio | Prefixo | RBAC |
|---|---|---|
| Eventos | `/events` | leitura publica (`/published`, `/upcoming`, `/slug/*`, `/by-period/*`, `/recommended`); escrita exige papel autenticado |
| Tags | `/tags`, `/events/{id}/tags`, `/events/tags-map` | leitura publica; escrita exige `canManageTags`/`canDeleteTags` |
| Usuarios/Papeis | `/users/*` | `/me/*` autenticado; listagem/atribuicao exige `admin`/`super_admin` |
| Comunidades | `/communities` | leitura publica; escrita autenticada |
| Galeria | `/gallery/albums`, `/gallery/photos` | leitura publica; escrita exige `canUploadImages` |
| Contribuidores | `/contributors` | leitura publica; escrita exige `canManageContributors` |
| Auditoria | `/audit-logs` | `admin`/`super_admin` |
| GitHub | `/github/*` | publico, com rate limit (30/min) e cache de 5 min |
| Meta | `/health`, `/og`, `/sitemap.xml` | publico |

## Migracao incremental do frontend

O frontend deve passar a consumir esta API no lugar de `@supabase/supabase-js` para
operacoes de negocio, mantendo o Supabase apenas para login/sessao (`authService.js`).
Recomenda-se uma feature flag (`VITE_USE_PYTHON_BACKEND`) para alternar gradualmente cada
servico, permitindo rollback rapido por dominio.
