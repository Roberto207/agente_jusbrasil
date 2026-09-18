# Imagem pública do Kaggle, tag fixa (ADR-014). Release v170 em 2026-06-29.
# A imagem tem vários GB — `docker build` não faz parte do fluxo diário; ver README.
FROM gcr.io/kaggle-gpu-images/python:v170
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN pip install --no-cache-dir --no-deps -e .
ENTRYPOINT ["python", "-m", "verificador"]
