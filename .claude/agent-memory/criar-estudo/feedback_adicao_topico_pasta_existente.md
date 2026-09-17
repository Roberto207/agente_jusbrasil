---
name: feedback-adicao-topico-pasta-existente
description: Como agir quando o pedido é adicionar UM tópico novo a uma pasta de estudos Obsidian já existente e madura, em vez de criar a pasta do zero
metadata:
  type: feedback
---

Quando o usuário pede para adicionar um único conceito novo a uma pasta de estudos já existente (tem `fundamentos/`, `tecnicas_modernas/`, `pratica_ia/`, `html/`, `guia_de_estudos.md` etc.), o trabalho deve ser **cirúrgico**, não uma regeneração do pipeline completo (Fases 1-7 do agente `criar-estudo`).

**Escopo típico de uma tarefa dessas:**
1. Ler 2-4 arquivos de referência já existentes na pasta (para copiar padrão exato: TL;DR em escada, citações inline, mermaid, callouts fixos, CSS/HTML) — nunca inventar um estilo novo.
2. Criar APENAS o(s) arquivo(s) `.md` novo(s) pedido(s), seguindo as mesmas regras didáticas do pipeline completo (mín. 1400 palavras, termos definidos na 1ª ocorrência, intuição antes do formalismo, exemplo-fio-condutor único, callouts fixos `[!example]`/`[!info]`/`[!warning]`).
3. Fazer edições pontuais (`Edit`, nunca reescrever o arquivo inteiro) nos arquivos vizinhos para reencaixar o novo arquivo na cadeia de navegação: linhas `Voltar:`/`Próximo:` dos `.md` vizinhos, e o `guia_de_estudos.md` (item numerado + diagrama mermaid "mapa de dependência de leitura").
4. Gerar o HTML correspondente ao novo `.md`, copiando a estrutura exata de um HTML de conceito já existente na mesma pasta (mesma paleta Catppuccin Mocha, mesmas tabs Rápido/Completo/Cards, mesmo script de flashcards em localStorage).
5. Editar `html/index.html` cirurgicamente (nav sidebar + card na seção certa + contagem de páginas no rodapé).

**Why:** o usuário explicitamente restringe "NÃO recriar estrutura de pastas, NÃO reescrever conteúdo já existente" nesses pedidos — o valor está em preservar 100% do material já validado e só encaixar a peça nova. Reescrever arquivos inteiros desperdiça trabalho e arrisca quebrar padrão já aprovado.

**Extensão útil não pedida explicitamente, mas de baixo risco e alto valor:** quando o `.md` vizinho tem seu rodapé `Voltar:`/`Próximo:` trocado, o HTML **equivalente** desse mesmo arquivo (`.nav-footer` no HTML) fica com link quebrado/desatualizado se não for corrigido também. Vale fazer esse ajuste simétrico no HTML mesmo que não esteja na lista explícita de arquivos a editar, desde que o arquivo não esteja na lista de "não toque". Isso evita links mortos na navegação.

**How to apply:** antes de escrever qualquer coisa, sempre localizar e ler o(s) arquivo(s)-benchmark da própria pasta (não os benchmarks genéricos do agente `criar-estudo`) — cada pasta madura já tem seu próprio padrão consolidado de citação, CSS e navegação que deve ser clonado ao pé da letra.

Ver também: [[projeto-engenharia-de-requisitos]]
