# Notebooks do Kaggle

Cada notebook clona o repositório numa tag ou commit fixo (`VERSAO`) e roda no Kaggle. Desde a mensagem
final da organização (30/09), o Kaggle **não** é mais o entregável: a nota vem da execução da organização
sobre o repositório (`docs/gerais/regras_envio_final_jusbrasil.md`). Os notebooks ficam como registro de
como cada submissão e cada artefato publicado foi produzido.

| Notebook | `VERSAO` | Situação | Para que serviu |
|---|---|---|---|
| `00_esqueleto.ipynb` | `main` | **histórico** | Primeiro teste do fluxo no Kaggle (esqueleto andante, score 0). Roda `main`, então não reproduz nada fixo. |
| `02_sub-002.ipynb` | `sub-002` | **histórico** | Gerou a `sub-002` (1,08604 no leaderboard). |
| `03_sub-003.ipynb` | `sub-003` | **histórico** | Gerou a `sub-003`. |
| `04_sub-004.ipynb` | `sub-004` | **histórico** | Gerou a `sub-004`. |
| `05_llm_diversifica_sintetico.ipynb` | `379714d` | atual (reprodução) | Gerou a camada 2 do sintético publicado no HF (revisão `0209a853…`). |
| `06_sub-005.ipynb` | `sub-005` | **histórico** | Gerou a `sub-005` (1,100 no leaderboard, 13º). |
| `07_treino_encoder_enc-001.ipynb` | `enc-001` | atual (reprodução) | Treinou os pesos publicados do encoder (revisão `d91d0914…`). |
| `08_sub-006.ipynb` | `sub-006` | **histórico** | Conferiu no Kaggle a `sub-006` (regex + encoder): mesmo CSV da execução local. |

Os notebooks `00`, `02`–`04` e `06` usam o mesmo molde e diferem só em `VERSAO` e no título. Nenhum deles
é o ponto de entrada da solução final.
