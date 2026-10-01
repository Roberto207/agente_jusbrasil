# Ambiente declarado da avaliação final (regras da Jusbrasil de 30/09; ADR-014, revisão de 01/10).
# Execução só em CPU e offline: os pesos do encoder entram na imagem no `docker build` (o único passo com
# rede), na revisão fixa do verificador.toml, e são conferidos pelo sha256.
#
#   docker build -t verificador .
#   docker run --rm --network none -v <pasta_dados>:/dados:ro -v <pasta_saida>:/saida verificador \
#       /dados/<base>.db /dados/<pasta_txt> /saida/submission.csv
#
# Só regex (sem encoder): --entrypoint bash ... verificador run_sem_encoder.sh <mesmos argumentos>
ARG IMAGEM_BASE=python:3.13-slim@sha256:7c61056e61ac89e852de05f3dc6fa51a6dd2181797bceed46aa725dd7cb2cd3b
FROM ${IMAGEM_BASE}
ARG IMAGEM_BASE

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/opt/huggingface \
    IMAGEM_DOCKER=${IMAGEM_BASE}

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Pesos do encoder (R45: link público + revisão fixa). Mesmos valores do verificador.toml.
ARG ENCODER_LINK=Roberto2799/jusbrasil-encoder-citacoes
ARG ENCODER_REVISAO=d91d09142fdc2601cad04b8df1d509d87c5a1552
ARG ENCODER_SHA256=4e52bfb66fe10ba9c1802a7205047d777f0766745a92992b0f8973091971a2bc
RUN python -c "import hashlib, pathlib, sys; \
from huggingface_hub import snapshot_download; \
p = pathlib.Path(snapshot_download('${ENCODER_LINK}', revision='${ENCODER_REVISAO}')) / 'model.safetensors'; \
h = hashlib.sha256(p.read_bytes()).hexdigest(); \
sys.exit(0 if h == '${ENCODER_SHA256}' else f'sha256 dos pesos não confere: {h}')"

COPY . .
RUN pip install --no-deps -e .

# A partir daqui, nada de rede (o run.sh também define estas variáveis).
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
ENTRYPOINT ["bash", "run.sh"]
