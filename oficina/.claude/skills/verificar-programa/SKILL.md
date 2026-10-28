---
name: verificar-programa
description: Planeja como provar que um programa da oficina funciona antes de escrever o código, e prova no fim. Use em todo programa novo ou alteração.
---

# Verificar programa

Adaptado de `verification-planning` (github.com/akitaonrails/my-skills), reduzido para
programas pequenos de um usuário só.

## 1. Escreva a afirmação
Antes do código, escreva em 2–3 linhas: o que deve ficar verdadeiro ("dado um .md, gera um PDF
legível com o título") e o que poderia enganar você ("o PDF existe mas está vazio", "funciona com
o meu exemplo e quebra com acento").

## 2. Escolha a evidência
Para cada afirmação, qual verificação a estabelece de forma direta? Prefira olhar o resultado
real (abrir o PDF gerado com pypdf e conferir o texto, contar páginas, ler o JSON de saída) a só
checar "não deu erro". Inclua sempre:
- o caminho feliz com dados realistas (acentos, nomes com espaço, arquivo de várias páginas);
- uma entrada inválida (arquivo inexistente, formato errado) → `{"erro": ...}` e código 1;
- o arquivo de saída já existente → não sobrescreve.

## 3. Torne repetível
O `teste.py` cria tudo do zero numa pasta temporária, roda o programa como a Iris roda
(subprocess, JSON no stdin) e apaga a pasta no fim. Nada de depender de arquivos do usuário.

## 4. Prove
Rode o `teste.py` e leia a saída. Se falhar, conserte a causa (não o teste). No relatório final,
diga o que foi provado e o que não deu para provar (ex.: "não testei com PDF escaneado").
