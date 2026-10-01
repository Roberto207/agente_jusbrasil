#!/usr/bin/env bash
# Mesmo que run.sh, só com regex: sem pesos, sem torch.
#   bash run_sem_encoder.sh <caminho_db> <pasta_txt> <arquivo_saida>
set -euo pipefail
exec bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run.sh" --sem-encoder "$@"
