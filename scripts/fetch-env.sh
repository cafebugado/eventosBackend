#!/usr/bin/env bash
# Baixa o .env do repositorio privado cafebugado/backendeventos-env e copia para a raiz do projeto.
#
# Uso:
#   ./scripts/fetch-env.sh [environment] [--up]
#
# environment: nome do arquivo "<environment>.env" no repo de env (default: dev)
# --up: roda "docker compose up --build" apos configurar o .env

set -euo pipefail

ENV_REPO="cafebugado/backendeventos-env"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_ENV_FILE="$PROJECT_ROOT/.env"
CLONE_DIR="${TMPDIR:-/tmp}/backendeventos-env"

ENVIRONMENT="dev"
UP=false
for arg in "$@"; do
    case "$arg" in
        --up) UP=true ;;
        *) ENVIRONMENT="$arg" ;;
    esac
done

if ! gh auth status >/dev/null 2>&1; then
    echo "Voce nao esta autenticado no GitHub CLI. Rode 'gh auth login' e tente novamente." >&2
    exit 1
fi

if [ -d "$CLONE_DIR" ]; then
    echo "Atualizando repositorio de env existente..."
    if ! git -C "$CLONE_DIR" pull --quiet; then
        echo "Falha ao atualizar '$ENV_REPO'. Verifique se voce ainda tem acesso a ele." >&2
        exit 1
    fi
else
    echo "Clonando '$ENV_REPO'..."
    if ! gh repo clone "$ENV_REPO" "$CLONE_DIR" >/dev/null 2>&1; then
        echo "Nao foi possivel clonar '$ENV_REPO'. Peca acesso a esse repositorio a quem administra o projeto." >&2
        exit 1
    fi
fi

SOURCE_ENV_FILE="$CLONE_DIR/$ENVIRONMENT.env"
if [ ! -f "$SOURCE_ENV_FILE" ]; then
    echo "Arquivo '$ENVIRONMENT.env' nao encontrado em '$ENV_REPO'." >&2
    exit 1
fi

if [ -f "$TARGET_ENV_FILE" ] && ! cmp -s "$TARGET_ENV_FILE" "$SOURCE_ENV_FILE"; then
    read -r -p "Já existe um .env local diferente do remoto. Sobrescrever? (s/N) " answer
    if [[ ! "$answer" =~ ^[sS]$ ]]; then
        echo "Operacao cancelada. .env local mantido."
        exit 0
    fi
fi

cp "$SOURCE_ENV_FILE" "$TARGET_ENV_FILE"
echo "'.env' atualizado a partir de '$ENVIRONMENT.env' ($ENV_REPO)."

if [ "$UP" = true ]; then
    docker compose up --build
fi
