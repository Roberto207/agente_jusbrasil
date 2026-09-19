"""Frases, cabeçalhos e nomes do gerador sintético (só texto e escolhas; nenhuma lógica).

Escritos sem olhar os regex da frente B (ADR-012): alguns moldes imitam a amostra, outros
são deliberadamente novos, para o relatório mostrar onde a extração não generaliza.
"""

from __future__ import annotations

# Frases com uma citação no lugar de `{c}`.
FRASES_COM_CITACAO = (
    "Nesse sentido, o entendimento firmado em {c} afasta a tese contrária.",
    "Confira-se, por oportunidade, {c}.",
    "A questão já foi apreciada em {c}, cujo raciocínio se aplica ao caso.",
    "Vale registrar a lição extraída de {c}.",
    "Em sentido semelhante: {c}.",
    "Como assentado em {c}, a controvérsia comporta solução diversa.",
    "Invoca-se, ainda, {c}, no ponto em que afasta a exigência combatida.",
    "O raciocínio desenvolvido no acórdão recorrido destoa de {c}.",
    "Na linha do que se decidiu em {c}, impõe-se a reforma.",
    "A tese defensiva encontra amparo em {c}.",
)

# Frases sem citação, incluindo distratores que parecem citação mas não são (R33).
FRASES_SEM_CITACAO = (
    "A questão de fundo comporta solução singela.",
    "Toda a construção defensiva repousa nas normas de regência da matéria.",
    "Registre-se que o tema comporta enfrentamento sob dupla perspectiva.",
    "Segundo a jurisprudência pacífica desta Corte, a tese não merece acolhimento.",
    "O entendimento sumulado não deixa margem a dúvida quanto ao ponto.",
    "Os documentos de fls. 10/20 demonstram a versão dos fatos.",
    "O protocolo 2019.1234567 foi juntado no prazo legal.",
    "Aplica-se, no ponto, o artigo correspondente do diploma processual.",
    "A parte sustenta a nulidade do ato e pede a reforma da decisão.",
    "Assim delimitada a controvérsia, passa-se ao exame do mérito.",
)

TITULOS = (
    "AGRAVO REGIMENTAL EM HABEAS CORPUS",
    "MEMORIAL",
    "RAZÕES DE APELAÇÃO",
    "DECISÃO MONOCRÁTICA",
    "ACÓRDÃO",
    "PARECER",
    "CONTRARRAZÕES",
)

ORGAOS = (
    "EXCELENTÍSSIMO SENHOR MINISTRO RELATOR\nSUPERIOR TRIBUNAL DE JUSTIÇA",
    "DEFENSORIA PÚBLICA DA UNIÃO\nOFÍCIO JUNTO AO SUPERIOR TRIBUNAL MILITAR",
    "MINISTÉRIO PÚBLICO ELEITORAL\nPROCURADORIA-GERAL ELEITORAL",
    "TRIBUNAL SUPERIOR DO TRABALHO\nGABINETE DO RELATOR",
    "SUPREMO TRIBUNAL FEDERAL\nSECRETARIA JUDICIÁRIA",
)

PARTES = ("Impetrante", "Paciente", "Apelante", "Apelado", "Agravante", "Agravado", "Recorrente", "Recorrido")
NOMES = (
    "PAULO HENRIQUE VASCONCELOS", "INDÚSTRIA TÊXTIL ARARAQUARA S.A.", "TRANSPORTES MARAJÓ EIRELI",
    "CARLOS EDUARDO MARQUES", "MARIA APARECIDA SOUZA", "COMERCIAL BOA VISTA LTDA.",
)

# Como cada classe aparece por extenso (a sigla é sempre uma opção).
NOME_LONGO = {
    "REsp": "Recurso Especial", "AREsp": "Agravo em Recurso Especial", "HC": "Habeas Corpus",
    "RHC": "Recurso em Habeas Corpus", "Rcl": "Reclamação", "RE": "Recurso Extraordinário",
    "RMS": "Recurso em Mandado de Segurança", "APL": "Apelação", "AI": "Agravo de Instrumento",
    "AgInt": "Agravo Interno", "AgRg": "Agravo Regimental", "EDcl": "Embargos de Declaração",
    "RR": "Recurso de Revista",
}

# lei_chave → (artigo definido, nome) possíveis.
NOMES_DE_LEI: dict[str, tuple[tuple[str, str], ...]] = {
    "CF-1988": (("da", "Constituição Federal"), ("da", "Constituição da República")),
    "LEI-13105-2015": (("do", "CPC"), ("do", "Código de Processo Civil"), ("da", "Lei nº 13.105/2015")),
    "DL-5452-1943": (("da", "CLT"), ("da", "Consolidação das Leis do Trabalho")),
    "LEI-8078-1990": (("do", "CDC"), ("do", "Código de Defesa do Consumidor"), ("da", "Lei nº 8.078/1990")),
    "DL-1001-1969": (("do", "Código Penal Militar"),),
    "LEI-4737-1965": (("do", "Código Eleitoral"), ("da", "Lei nº 4.737/1965")),
    "LEI-10406-2002": (("do", "Código Civil"), ("da", "Lei nº 10.406/2002")),
    "DL-3689-1941": (("do", "Código de Processo Penal"),),
    "LC-64-1990": (("da", "Lei Complementar nº 64/1990"),),
    "LEI-9504-1997": (("da", "Lei nº 9.504/1997"),),
    "LEI-13467-2017": (("da", "Lei nº 13.467/2017"),),
}

# Molde da forma (d): (tribunal ou classe) + ano + relator, sem número. Os quatro primeiros
# imitam a amostra; os dois últimos são novos de propósito.
MOLDES_SEM_NUMERO = (
    "julgado do {trib} proferido em {ano} pela relatoria de {rel}",
    "precedente do {trib} de {ano}, da relatoria de {rel}",
    "acórdão do {trib} julgado em {ano}, sob relatoria de {rel}",
    "{classe} do {trib}, de {ano}, Rel. Min. {rel}",
    "decisão colegiada do {trib} em {ano}, relatada pelo Ministro {rel}",
    "julgado da Corte ({trib}, {ano}, Min. {rel})",
)

COMPLEMENTOS_DE_ARTIGO = ("", "", ", § 1º", ", I", ", III", ", IX")
