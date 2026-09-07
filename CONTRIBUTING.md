# Guia de contribuicao

Este documento descreve o fluxo de branches, o padrao de commits e o checklist de
qualidade usados neste repositorio. Vale para qualquer pessoa do time.

## Fluxo de branches

- **`main`** — producao. So recebe merge vindo de `develop` (ou de um `hotfix/*` em caso
  de correcao urgente). Protegida: exige Pull Request + CI verde, sem push direto.
- **`develop`** — integracao. Branch-base para novas features/correcoes. Tambem
  protegida: exige Pull Request + CI verde.
- **`feature/<nome-curto>`** — nova funcionalidade, criada a partir de `develop`.
- **`fix/<nome-curto>`** — correcao de bug, criada a partir de `develop`.
- **`hotfix/<nome-curto>`** — correcao urgente em producao, criada a partir de `main` e
  mergeada de volta em `main` **e** em `develop` (para nao perder a correcao na proxima
  release).
- **`chore/<nome-curto>`** — tarefas de manutencao (CI, dependencias, configuracao).

Fluxo tipico:

```bash
git checkout develop
git pull origin develop
git checkout -b feature/nome-da-feature
# ... commits ...
git push -u origin feature/nome-da-feature
# abrir PR para develop
```

Deploy: a Vercel esta conectada diretamente ao repositorio GitHub. Push em `main` gera
deploy de producao; PRs e outras branches geram preview deployments automaticos. Nao ha
step de deploy no GitHub Actions — o CI cuida apenas do quality gate (lint, type-check,
testes, build da imagem Docker).

## Padrao de commits (Conventional Commits)

Commits devem seguir o formato:

```
tipo(escopo opcional): descricao curta no imperativo
```

Tipos aceitos: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`,
`build`.

Exemplos (o historico do projeto ja segue esse padrao):

```
fix(rotas): corrige ordem de include_router que bloqueava /events/tags-map
feat(events): adiciona endpoints publicos de stats e galeria
chore(ci): adiciona job de validacao de commits
```

O CI valida automaticamente (job `commitlint`) que os commits de um Pull Request seguem
esse padrao, usando o [Commitizen](https://commitizen-tools.github.io/commitizen/).

### Configurando localmente (recomendado)

O extra `dev` do projeto ja inclui `commitizen` e `pre-commit`:

```bash
pip install -e ".[dev]"
pre-commit install --hook-type commit-msg --hook-type pre-commit
```

Isso ativa dois hooks locais:
- `commit-msg`: valida a mensagem do commit antes de aceitar (mesmo padrao do CI).
- `pre-commit`: roda `ruff --fix` nos arquivos alterados.

Para escrever a mensagem de forma guiada (opcional), use `cz commit` no lugar de
`git commit`.

## Checklist antes de abrir um Pull Request

- [ ] `ruff check app tests` sem erros.
- [ ] `mypy app` sem erros.
- [ ] `pytest --cov=app --cov-report=term-missing` passando (cobertura minima: 55%).
- [ ] Se houve mudanca de schema, incluir a revisao Alembic correspondente.
- [ ] Commits seguem Conventional Commits.
- [ ] PR aponta para `develop` (ou `main`, apenas em `hotfix/*`).
- [ ] Descricao do PR explica o que mudou e por que (o template do PR guia isso).

## Configuracao de branch protection (referencia)

As regras abaixo sao aplicadas via GitHub (Settings > Branches), tanto em `main` quanto
em `develop`:

- Exigir Pull Request antes de merge (minimo 1 aprovacao).
- Exigir que os status checks `test`, `docker-build` e `commitlint` estejam verdes.
- Exigir que a branch esteja atualizada com a base antes do merge.
- Bloquear push direto e force-push/delete da branch.

Se precisar aplicar/reconfigurar manualmente (requer permissao de admin no repositorio),
o comando equivalente via GitHub CLI e:

```bash
gh api repos/cafebugado/eventosBackend/branches/main/protection \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  -f required_status_checks[strict]=true \
  -f "required_status_checks[contexts][]=test" \
  -f "required_status_checks[contexts][]=docker-build" \
  -f "required_status_checks[contexts][]=commitlint" \
  -f enforce_admins=true \
  -f "required_pull_request_reviews[required_approving_review_count]=1" \
  -f allow_force_pushes=false \
  -f allow_deletions=false
```

Repita trocando `main` por `develop` no path.
