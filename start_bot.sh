#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Erro: ambiente virtual não encontrado em $PROJECT_DIR/.venv." >&2
  echo "Crie-o e instale as dependências antes de iniciar o bot." >&2
  exit 1
fi

exec "$PYTHON_BIN" -m telegram.bot
