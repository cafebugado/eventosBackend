# Guia de contribuicao

Este documento descreve o fluxo de branches, o padrao de commits e o checklist de
qualidade usados neste repositorio. Vale para qualquer pessoa do time.

## Fluxo de branches

- **`main`** — producao. So recebe merge vindo de `develop` (ou de um `hotfix/*` em caso
  de correcao urgente). Protegida: exige Pull Request + CI verde, sem push direto.
- **`develop`** — integracao. Branch-base para novas features/correcoes. Tambem
  protegida: exige Pull Request + CI verde.
Branches de trabalho sao criadas a partir de `develop` e usam um prefixo alinhado aos
tipos do Conventional Commits:

- **`feat/<nome-curto>`** — nova funcionalidade.
- **`fix/<nome-curto>`** — correcao de bug.
- **`refactor/<nome-curto>`** — refatoracao sem mudanca de comportamento.
- **`perf/<nome-curto>`** — melhoria de performance.
- **`test/<nome-curto>`** — criacao ou ajuste de testes.
- **`ci/<nome-curto>`** — pipeline de CI (GitHub Actions).
- **`docs/<nome-curto>`** — documentacao.
- **`chore/<nome-curto>`** — tarefas de manutencao (dependencias, configuracao).
- **`hotfix/<nome-curto>`** — correcao urgente em producao, criada a partir de `main` e
  mergeada de volta em `main` **e** em `develop` (para nao perder a correcao na proxima
  release).

O prefixo oficial para funcionalidades e `feat/`. Branches antigas com `feature/` continuam
validas, mas branches novas devem usar `feat/`.

Fluxo tipico:

```bash
git checkout develop
git pull origin develop
git checkout -b feat/nome-da-feature
# ... commits ...
git push -u origin feat/nome-da-feature
# abrir PR para develop
```

### PRs de fork nao sao aceitas

Contribuicoes sao feitas apenas por membros do time, a partir de branches do proprio
repositorio `cafebugado/eventosBackend`. **PRs abertas a partir de fork nao sao aceitas.**

Motivos:
- todos do time tem acesso de escrita, entao o fork nao e necessario;
- a Vercel nao gera o preview deployment de PRs de fork sem autorizacao manual de um
  membro do time;
- branches no repositorio principal seguem as mesmas regras de CI e de revisao do resto
  do fluxo.

Se o seu clone aponta para um fork, troque o `origin` para o repositorio principal:

```bash
git remote set-url origin https://github.com/cafebugado/eventosBackend.git
git fetch origin
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
- [ ] Branch criada no `cafebugado/eventosBackend` com um dos prefixos acima (nao em fork).
- [ ] Titulo da PR no padrao Conventional Commits (ex.:
      `refactor(tags): injeta services via Depends (T08)`).
- [ ] PR aponta para `develop` (ou `main`, apenas em `hotfix/*`).
- [ ] Descricao do PR explica o que mudou e por que (o template do PR guia isso).
- [ ] Issue referenciada com `Refs #N` quando a PR resolve so parte dela, ou `Closes #N`
      quando resolve a issue inteira.

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
