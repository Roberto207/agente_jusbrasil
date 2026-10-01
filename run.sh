#!/usr/bin/env bash
# Ponto de entrada único da avaliação final (regras da Jusbrasil, 30/09):
#   bash run.sh <caminho_db> <pasta_txt> <arquivo_saida>
# Modo padrão: regex + encoder (configuração em verificador.toml). Execução offline: os pesos do encoder
# precisam estar no cache local antes (ver README). Só regex: bash run_sem_encoder.sh <mesmos argumentos>.
set -euo pipefail

FLAGS=()
if [ "${1:-}" = "--sem-encoder" ]; then  # uso interno do run_sem_encoder.sh
    FLAGS+=(--sem-encoder)
    shift
fi
if [ "$#" -ne 3 ]; then
    echo "uso: bash run.sh <caminho_db> <pasta_txt> <arquivo_saida>" >&2
    exit 2
fi

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Nada de rede: se faltar peso no cache, falha na hora em vez de tentar baixar.
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1
export PYTHONHASHSEED=0
# A configuração é a do repositório; variáveis VERIFICADOR_* do ambiente não a sobrescrevem.
for var in $(env | grep -o '^VERIFICADOR_[A-Z_]*' || true); do unset "$var"; done
export VERIFICADOR_CONFIG="$RAIZ/verificador.toml"
export PYTHONPATH="$RAIZ/src${PYTHONPATH:+:$PYTHONPATH}"

exec "${PYTHON:-python}" -m verificador executar "$1" "$2" "$3" "${FLAGS[@]+"${FLAGS[@]}"}"
