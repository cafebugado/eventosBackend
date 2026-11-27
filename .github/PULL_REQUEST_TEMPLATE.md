## O que mudou

<!-- Descreva a mudanca e o motivo (bug corrigido, feature adicionada, etc). -->

## Como testar

<!-- Passos para reproduzir/validar a mudanca localmente. -->

## Checklist

- [ ] `ruff check app tests` sem erros
- [ ] `mypy app` sem erros
- [ ] `pytest --cov=app --cov-report=term-missing` passando
- [ ] Commits seguem Conventional Commits
- [ ] Titulo da PR no padrao Conventional Commits
- [ ] Branch criada no `cafebugado/eventosBackend` (PRs de fork nao sao aceitas)
- [ ] Inclui migracao Alembic, se houve mudanca de schema
- [ ] PR aponta para `develop` (ou `main`, apenas em `hotfix/*`)

## Issue relacionada

<!-- Use `Refs #N` se a PR resolve so parte da issue, ou `Closes #N` se resolve a issue inteira. -->
