from __future__ import annotations

from verificador.contratos import Candidata
from verificador.extracao import extrair, ler_campos
from verificador.extracao.sobreposicao import iou, resolver
from verificador.texto import preparar
from tests.helpers import iou_offsets, trecho_gabarito


def test_recall_de_spans_iou(textos, gabarito) -> None:
    perdidas: list[str] = []
    for doc_id, texto in textos.items():
        prep = preparar(texto)
        candidatas = extrair(prep)
        golds = [row for row in gabarito if row["documento_id"] == doc_id]
        usados: set[int] = set()
        for row in golds:
            esperado = (int(row["inicio"]), int(row["fim"]))
            melhor = 0.0
            melhor_i = None
            for i, cand in enumerate(candidatas):
                if i in usados:
                    continue
                v = iou_offsets(esperado, (cand.inicio, cand.fim))
                if v > melhor:
                    melhor = v
                    melhor_i = i
            if melhor < 0.5:
                perdidas.append(
                    f"{doc_id} {row['citacao_id']} {trecho_gabarito(row['trecho'])!r} melhor={melhor:.2f}"
                )
            elif melhor_i is not None:
                usados.add(melhor_i)
    assert not perdidas, "spans sem par (IoU < 0,5):\n" + "\n".join(perdidas)


def test_r4_sobreposição_parcial_nao_fica_abaixo_de_meio(textos, gabarito) -> None:
    for doc_id, texto in textos.items():
        prep = preparar(texto)
        candidatas = extrair(prep)
        golds = [
            (int(row["inicio"]), int(row["fim"]))
            for row in gabarito
            if row["documento_id"] == doc_id
        ]
        for cand in candidatas:
            for g in golds:
                inter = max(0, min(cand.fim, g[1]) - max(cand.inicio, g[0]))
                if inter == 0:
                    continue
                assert iou_offsets((cand.inicio, cand.fim), g) >= 0.5


def test_r3_sem_par_com_iou_alto(textos) -> None:
    for texto in textos.values():
        candidatas = extrair(preparar(texto))
        for i, a in enumerate(candidatas):
            for b in candidatas[i + 1 :]:
                assert iou(a, b) < 0.5


def test_r33_referencia_vaga_conhecida_nao_vira_candidata(textos) -> None:
    marcas = (
        "jurisprudência pacífica",
        "entendimento sumulado",
        "artigo correspondente",
        "orientação jurisprudencial da Corte Superior",
    )
    for texto in textos.values():
        prep = preparar(texto)
        candidatas = extrair(prep)
        for marca in marcas:
            pos = texto.lower().find(marca)
            if pos < 0:
                continue
            fim = pos + len(marca)
            for cand in candidatas:
                if cand.inicio <= pos and cand.fim >= fim:
                    raise AssertionError(f"referência vaga capturada: {cand.trecho!r}")


def test_referencia_vaga_vira_candidata_so_com_a_flag_ligada(monkeypatch) -> None:
    """Espelho do R33 acima: as mesmas frases conhecidas continuam invisíveis com a flag
    desligada (default), e viram candidata `forma="referencia_vaga"` só quando ligada
    (ADR-005) — nunca por acidente."""
    marcas = (
        "jurisprudência pacífica",
        "entendimento sumulado",
        "artigo correspondente",
        "orientação jurisprudencial da Corte Superior",
    )
    for marca in marcas:
        texto = f"Trata-se de parecer.\n\nSegundo a {marca} desta Corte, a tese não merece acolhimento."
        pos = texto.lower().find(marca.lower())
        fim = pos + len(marca)

        desligada = extrair(preparar(texto))
        assert not any(c.inicio <= pos and c.fim >= fim for c in desligada), (
            f"referência vaga capturada com a flag desligada (default): {marca!r}"
        )

        monkeypatch.setenv("VERIFICADOR_EXTRAIR_REFERENCIA_VAGA", "1")
        ligada = extrair(preparar(texto))
        monkeypatch.delenv("VERIFICADOR_EXTRAIR_REFERENCIA_VAGA")
        achou = [c for c in ligada if c.inicio <= pos and c.fim >= fim]
        assert achou, f"referência vaga não virou candidata com a flag ligada: {marca!r}"
        assert achou[0].forma == "referencia_vaga"


def test_referencia_vaga_e_sempre_incompleta_pela_decisao(monkeypatch) -> None:
    """Ponta a ponta (extração + decisão): com a flag ligada, a referência vaga nunca consulta
    o índice e sempre resolve `incompleta` (ADR-005) — usa a função real `decidir`, não hardcode."""
    from verificador.decisao import decidir

    monkeypatch.setenv("VERIFICADOR_EXTRAIR_REFERENCIA_VAGA", "1")
    texto = "Trata-se de parecer.\n\nSegundo a jurisprudência pacífica desta Corte, o pedido procede."
    candidatas = [c for c in extrair(preparar(texto)) if c.forma == "referencia_vaga"]
    assert candidatas, "nenhuma candidata referencia_vaga com a flag ligada"
    campos = ler_campos(candidatas[0])
    assert campos is not None
    resolucao = decidir(campos, candidatas[0].forma, indice=None)  # type: ignore[arg-type]
    assert (resolucao.classificacao, resolucao.id_canonico) == ("incompleta", None)


def test_amostra_tem_recall_e_campos_completos(textos, gabarito) -> None:
    emitidas = 0
    golds = 0
    for doc_id, texto in textos.items():
        candidatas = extrair(preparar(texto))
        emitidas += len(candidatas)
        golds += sum(1 for row in gabarito if row["documento_id"] == doc_id)
        assert all(ler_campos(c) is not None for c in candidatas)
        assert all(c.trecho == texto[c.inicio : c.fim] for c in candidatas)
    assert emitidas == golds == 192


def test_r34_nada_do_cabecalho(textos) -> None:
    for texto in textos.values():
        prep = preparar(texto)
        for cand in extrair(prep):
            assert cand.inicio >= prep.corpo_inicio
            assert cand.trecho == texto[cand.inicio : cand.fim]


def test_padrao_com_numero_positivo_e_negativo() -> None:
    texto = (
        "No mérito aplica-se o AgInt no AREsp nº 9.888.777/GO. "
        "Não se extrai o protocolo 2019.1234567 nem as fls. 10/20."
    )
    cands = extrair(preparar(texto))
    assert any(c.forma == "com_numero" and "9.888.777" in c.trecho for c in cands)
    assert all("2019.1234567" not in c.trecho for c in cands)
    assert all("fls" not in c.trecho.lower() for c in cands)


def test_padrao_sumula_positivo_e_negativo() -> None:
    texto = (
        "A Súmula 83 do STJ, a Súmula n. 331 do TST e a Súmula Vinculante nº 10 resolvem. "
        "O entendimento sumulado não basta."
    )
    cands = extrair(preparar(texto))
    trechos = {c.trecho for c in cands if c.forma == "sumula"}
    assert "Súmula 83 do STJ" in trechos
    assert "Súmula Vinculante nº 10" in trechos
    assert any("Súmula n. 331" in t for t in trechos)
    assert all("sumulado" not in c.trecho.lower() for c in cands)


def test_padrao_lei_positivo_e_negativo() -> None:
    texto = "Vale o art. 12, III, da Constituição Federal, não o artigo correspondente do CPC."
    cands = extrair(preparar(texto))
    leis = [c for c in cands if c.forma == "lei_artigo"]
    assert any("art. 12" in c.trecho for c in leis)
    assert all("artigo correspondente" not in c.trecho for c in leis)


def test_padrao_sem_numero_positivo_e_negativo() -> None:
    texto = (
        "Como o julgado do STF proferido em 2024 pela relatoria de Relator Exemplo. "
        "A jurisprudência pacífica desta Corte não é citação."
    )
    cands = extrair(preparar(texto))
    assert any(c.forma == "sem_numero" for c in cands)
    assert all("pacífica" not in c.trecho for c in cands)


def _tem_sem_numero(texto: str) -> bool:
    return any(c.forma == "sem_numero" for c in extrair(preparar(texto)))


def test_forma_d_cobre_ligacoes_nao_enumeradas() -> None:
    """ADR-015: o padrão ancora em gatilho/tribunal/ano/relator, não nas conjunções.

    Nenhuma destas frases existe na amostra oficial; se alguma falhar, o padrão voltou a depender
    das palavras de ligação.
    """
    for frase in (
        "aresto do STJ datado de 2021, tendo como relator o Ministro Assusete Magalhaes",
        "acórdão prolatado pelo STF em 2019 sob a condução do Ministro Celso De Mello",
        "decisão do TSE — 2016 — Rel. Henrique Neves",
        "precedente firmado em 2021 pelo STM, relator o Ministro Artur Vidigal",
        "julgado do TST (Rel. Min. Morgana Richa, 2025)",
    ):
        assert _tem_sem_numero(frase), frase


def test_forma_d_nao_usa_entendimento_como_gatilho() -> None:
    """Falha conhecida e deliberada (ADR-015).

    Admitir `entendimento` como gatilho estendia o span à esquerda num documento real da amostra
    (`gen_n1_007`), e nas 31 citações reais o gatilho nunca é essa palavra. Vale mais proteger o dado
    oficial do que cobrir um molde de estresse que a própria equipe escreveu.
    """
    assert not _tem_sem_numero(
        "entendimento do STJ assentado em 2021 pela relatora Ministra Nancy Andrighi"
    )


def test_forma_d_exige_ano_e_relator_e_nao_pega_referencia_vaga() -> None:
    """R33 — o que protege contra referência vaga é exigir ano **e** relator, não o vocabulário."""
    for frase in (
        "a jurisprudência pacífica desta Corte",
        "o entendimento sumulado sobre a matéria",
        "o entendimento do STJ sobre o tema",
        "julgado do STF sem mais dados",
    ):
        assert not _tem_sem_numero(frase), frase


def test_forma_d_nao_atravessa_fim_de_frase_nem_engole_numero() -> None:
    """O enchimento entre âncoras não pode cruzar ponto final nem conter dígito.

    Sem isso, o span uniria trechos sem relação e expulsaria a citação numerada na resolução de
    sobreposição, onde o candidato maior substitui o menor.
    """
    assert not _tem_sem_numero("O STF decidiu em 2024. O Ministro Fulano afirmou o contrário.")

    texto = "Confira-se o AgRg no REsp 1.234.567/SP, Rel. Min. Nancy Andrighi, de 2021."
    cands = extrair(preparar(texto))
    assert any(c.forma == "com_numero" for c in cands)
    assert all(c.forma != "sem_numero" for c in cands)


def test_resolver_descarta_contida() -> None:
    longa = Candidata(10, 40, "x" * 30, "jurisprudencia", "com_numero", "a", frozenset({"regex"}))
    curta = Candidata(12, 20, "x" * 8, "jurisprudencia", "com_numero", "a", frozenset({"regex"}))
    saida = resolver([longa, curta])
    assert saida == [longa]


def test_edv_nao_captura_prosa_comum() -> None:
    """O alias `EDv` já teve um padrão `divergência em` que pegava prosa corrente.

    Era redundante — nenhum dos 11 registros da base com "Embargos de Divergência" dependia dele —
    e abria três modos de falha: duas citações falsas e a corrupção da cadeia de uma citação real.
    """
    for frase in (
        "houve divergência em 2024 sobre o tema",
        "a divergência em 1.234.567 casos analisados",
        "não há divergência em relação ao voto do relator",
    ):
        assert not any(c.forma == "com_numero" for c in extrair(preparar(frase))), frase


def test_edv_reconhecido_mesmo_colado_no_conector() -> None:
    """O cabeçalho da base vem sem espaço em 4 registros (`AgInt nosEMBARGOS DE DIVERGÊNCIA`).

    O guarda `(?<![A-Za-z])` do padrão de classe barra `EMBARGOS` quando ele encosta em `nos`, então
    o alias precisa tolerar o prefixo. Sem isso o registro é indexado como `REsp` puro e volta a
    empatar com o `AgInt no REsp` de mesmo número (`gen_n2_010`).
    """
    from verificador.extracao.campos import _classes_no_texto

    for cabecalho in (
        "AgInt nosEMBARGOS DE DIVERGÊNCIA EM RESP Nº 1597443 - PR",
        "AgInt nos EMBARGOS DE DIVERGÊNCIA EM RESP Nº 1597443 - PR",
    ):
        assert "EDv" in _classes_no_texto(cabecalho), cabecalho
