---
nome: organizar-comprovantes
descricao: Organiza boletos, faturas, comprovantes e notas fiscais em pastas por ano/mês, com nomes padronizados e um resumo em planilha
quando_usar: quando ele pedir para organizar boletos, faturas, comprovantes, notas ou "papelada financeira", ou quando a vigília achar vários desses arquivos
ferramentas: listar_pasta, procurar_arquivo, ler_arquivo, ver_emails, criar_arquivo, mover_arquivo
autor: iris
versao: 1
fonte: adaptado de "invoice-organizer" (github.com/ComposioHQ/awesome-claude-skills, Apache-2.0)
---
# Organizar comprovantes

## 1. Achar os arquivos
Use `procurar_arquivo` com palavras como boleto, fatura, comprovante, nota, nf, recibo, pix e invoice. Quando o nome do arquivo não disser o suficiente, leia o PDF com `ler_arquivo` para descobrir a empresa, a data e o valor. O e-mail que trouxe o arquivo (`ver_emails`) também ajuda. O que não der para identificar fica separado para ele revisar.

## 2. O padrão (proponha, mas ele pode trocar)
- Pastas: `Documentos/Financeiro/AAAA/MM - mês`, por exemplo `Documentos/Financeiro/2026/10 - outubro`.
- Nome: `AAAA-MM-DD Empresa - Tipo - Descrição.pdf`, por exemplo `2026-10-25 InfinitePay - Boleto - Parcelamento.pdf`.
- Sem caracteres especiais além do hífen, nome da empresa com inicial maiúscula e a extensão original mantida.
- O que não foi identificado vai para `Documentos/Financeiro/_Revisar`.

## 3. Mostrar o plano antes
Diga quantos arquivos são e dê dois ou três exemplos de como fica ("antes → depois"). Pergunte se pode seguir.

## 4. Fazer (depois do sim)
Use `mover_arquivo` com o caminho novo. Mover já renomeia, e nada é apagado.

## 5. Resumo em planilha
Crie com `criar_arquivo` o arquivo `Documentos/Financeiro/AAAA/resumo-AAAA-MM.csv`, com as colunas `Data;Empresa;Tipo;Descrição;Valor;Arquivo`. Se não souber o valor, deixe em branco. Não invente.

## 6. Fechar
Conte quantos foram organizados e quantos ficaram para revisar, e ofereça repetir ("Quer que eu faça isso todo mês?").
