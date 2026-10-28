---
nome: organizar-comprovantes
descricao: Organiza boletos, faturas, comprovantes e notas fiscais em pastas por ano/mês, com nomes padronizados e um resumo em planilha
quando_usar: quando ele pedir para organizar boletos, faturas, comprovantes, notas ou "papelada financeira", ou quando a vigília achar vários desses arquivos
ferramentas: listar_pasta, procurar_arquivo, ver_emails, criar_arquivo, mover_arquivo
autor: iris
versao: 1
fonte: adaptado de "invoice-organizer" (github.com/ComposioHQ/awesome-claude-skills, Apache-2.0)
---
# Organizar comprovantes

## 1. Achar os arquivos
`procurar_arquivo` por palavras como: boleto, fatura, comprovante, nota, nf, recibo, pix, invoice.
Você NÃO consegue ler o conteúdo de PDFs: use o nome do arquivo, a data dele e, se ajudar, o e-mail
que trouxe o arquivo (`ver_emails`). O que não der para identificar fica marcado para ele revisar.

## 2. Padrão (proponha; ele pode trocar)
- Pastas: `Documentos/Financeiro/AAAA/MM - mês` (ex.: `Documentos/Financeiro/2026/10 - outubro`)
- Nome: `AAAA-MM-DD Empresa - Tipo - Descrição.pdf`
  (ex.: `2026-10-25 InfinitePay - Boleto - Parcelamento.pdf`)
- Sem caracteres especiais além de hífen; empresa com letra maiúscula; mantenha a extensão original.
- Não identificado: `Documentos/Financeiro/_Revisar`.

## 3. Mostrar o plano antes
Fale 2 ou 3 exemplos de "antes → depois" e quantos arquivos são. Pergunte se pode seguir.

## 4. Executar (depois do sim)
`mover_arquivo` com o novo caminho (mover já renomeia). Nada é apagado.

## 5. Resumo em planilha
Crie com `criar_arquivo` um `Documentos/Financeiro/AAAA/resumo-AAAA-MM.csv` com as colunas:
`Data;Empresa;Tipo;Descrição;Valor;Arquivo` (valor vazio se você não souber: não invente).

## 6. Fechar
Quantos foram organizados, quantos ficaram para revisar e uma sugestão ("Quer que eu faça isso todo mês?").
