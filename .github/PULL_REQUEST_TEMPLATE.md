## O que mudou

<!-- Descreva a mudanca e o motivo (bug corrigido, feature adicionada, etc). -->

## Como testar

<!-- Passos para reproduzir/validar a mudanca localmente. -->

## Checklist

- [ ] `ruff check app tests` sem erros
- [ ] `mypy app` sem erros
- [ ] `pytest --cov=app --cov-report=term-missing` passando
- [ ] Commits seguem Conventional Commits
- [ ] Inclui migracao Alembic, se houve mudanca de schema
- [ ] PR aponta para `develop` (ou `main`, apenas em `hotfix/*`)

## Issue relacionada

<!-- Ex: Closes #123 -->
