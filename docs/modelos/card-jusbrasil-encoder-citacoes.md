---
license: mit
language:
- pt
library_name: transformers
pipeline_tag: token-classification
base_model: neuralmind/bert-base-portuguese-cased
tags:
- legal
- ner
- citations
- token-classification
datasets:
- Roberto2799/jusbrasil-sintetico-diversificado
---

# Encoder de citações jurídicas — Desafio Jusbrasil BRACIS 2026

Marcador de trechos de **citação jurídica** em texto em português (NER com rótulos BIO): `JUR`
(jurisprudência: acórdãos e súmulas) e `LEI` (artigo de lei com a lei identificada). Ajustado a
partir do [BERTimbau-base](https://huggingface.co/neuralmind/bert-base-portuguese-cased) (MIT).

É um componente de um verificador de citações feito para o Desafio Jusbrasil × BRACIS 2026. No
sistema, ele é uma **rede de segurança** ao lado de regras escritas à mão: só acrescenta trechos
onde as regras não acharam nada, e cada trecho passa por filtros antes de virar citação. **Não foi
feito para ser usado sozinho.**

## Rótulos

`O`, `B-JUR`, `I-JUR`, `B-LEI`, `I-LEI` (em `config.json`, `id2label`).

## Treino

- **Modelo-base:** `neuralmind/bert-base-portuguese-cased`, revisão `94d69c95f98f7d5b2a8700c420230ae10def0baa`.
  O `transformers` carregou os pesos da conversão automática para safetensors do Hugging Face
  (revisão `4a78cfbf83c9c97533dd6d6694ca4323029ff061`), que tem o mesmo conteúdo do
  `pytorch_model.bin` da revisão fixada.
- **Dados** (spans por caractere convertidos em BIO por token, janela de 510 tokens com sobreposição de 128):
  - sintético da equipe, camadas 1 e 2 — [`Roberto2799/jusbrasil-sintetico-diversificado`](https://huggingface.co/datasets/Roberto2799/jusbrasil-sintetico-diversificado)
    @ `0209a853e6e59b263b138200963b579105baca24`, divisão `treino` (160 documentos por camada);
  - [LeNER-Br](https://github.com/peluz/lener-br) @ `4999cb7f63191f1d6904206f312eeca8f5b45c5a`,
    divisão `train` (50 documentos), convertido para a convenção do desafio: só jurisprudência de
    STF, STJ, TST, TSE e STM vira `JUR`; número do próprio processo e casos ambíguos ficam fora da
    perda; `LEGISLACAO` só vira `LEI` com "art." e dígito;
  - 14 documentos da amostra de desenvolvimento do desafio (dados da competição, **não
    redistribuídos** aqui).
- **Mistura:** toda janela com citação; 1/3 das janelas só com `O` do LeNER-Br; amostra repetida 4×.
  Total de 1.227 janelas por época.
- **Hiperparâmetros:** AdamW, lr 5e-5, 5 épocas (385 passos), lote 16, aquecimento 10%, decaimento
  0,01, fp16, semente 0. GPU T4, 168 s, pico de 5,05 GB de VRAM.
- **Dataset exato:** sha256 `ec98c4ea5a96d1333e16085fe1f6dccb504e67300c1160112c643e263a16c9ba`
  (detalhes em `manifesto_treino.json`).

## Avaliação

O encoder **sozinho**, IoU ≥ 0,5 por trecho:

| Conjunto | JUR | precisão JUR | LEI | precisão LEI |
|---|---|---|---|---|
| LeNER-Br `dev` | 15/22 | 0,714 | 120/127 | 0,856 |
| sintético, controle (as duas camadas) | 164/164 | 1,0 | 46/46 | 1,0 |
| amostra do desafio, controle | 76/76 | 0,987 | 15/15 | 1,0 |

Dentro do sistema (regras + encoder, com os filtros), no `test` do LeNER-Br, que não foi usado para
ajustar nada:

| | Só regras | Regras + encoder |
|---|---|---|
| Jurisprudência de STF/STJ/TST/TSE/STM | 58/74 | 64/74 |
| Artigos de lei | 115/202 | 173/202 |

## Uso previsto e limitações

- Feito para os documentos do desafio (pareceres jurídicos em português, com ruído de OCR) e para
  as citações que o acervo do desafio cobre. Fora disso, o desempenho não foi medido.
- Os rótulos seguem a convenção do desafio, que difere da do LeNER-Br: por exemplo, o número do
  próprio processo não é citação.
- A inferência no sistema roda em CPU, para dar a mesma saída em execuções repetidas.

## Licença

MIT, a mesma do modelo-base (BERTimbau, MIT, © NeuralMind). O aviso de licença do modelo-base
se aplica a este modelo derivado.
