---
name: verificar-programa
description: Planeja como provar que um programa da oficina funciona antes de escrever o código, e prova no fim. Use em todo programa novo ou alteração.
---
# Verificar programa

Adaptado de `verification-planning` (github.com/akitaonrails/my-skills), reduzido para programas pequenos, de um usuário só.

## 1. Escreva o que precisa ser verdade
Antes do código, escreva em duas ou três linhas o que o programa tem que fazer ("dado um .md, gera um PDF legível com o título") e o que poderia te enganar ("o PDF existe, mas está vazio", "funciona com o meu exemplo e quebra com acento").

## 2. Escolha como provar
Para cada ponto, pense numa verificação direta. Olhar o resultado de verdade (abrir o PDF gerado com pypdf e conferir o texto, contar as páginas, ler o JSON de saída) vale mais do que só ver que não deu erro. Sempre inclua:
- o caminho normal, com dados realistas (acentos, nomes com espaço, arquivo de várias páginas);
- uma entrada inválida (arquivo que não existe, formato errado), que deve dar `{"erro": ...}` e código 1;
- um arquivo de saída que já existe, que não pode ser sobrescrito.

## 3. Deixe repetível
O `teste.py` cria tudo do zero numa pasta temporária, roda o programa do mesmo jeito que a Iris roda (subprocess, JSON no stdin) e apaga a pasta no fim. Não depende de nenhum arquivo do usuário.

## 4. Prove
Rode o `teste.py` e leia a saída. Se falhar, corrija a causa, não o teste. No relatório final, diga o que foi provado e o que não deu para provar ("não testei com PDF escaneado", por exemplo).
