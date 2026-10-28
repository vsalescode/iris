---
nome: texto-natural
descricao: Reescreve um texto que "soa como IA" para soar como gente, sem mudar o que ele diz
quando_usar: ao escrever qualquer e-mail ou texto em nome dele; quando ele pedir para revisar, melhorar, "deixar mais natural" ou "menos robótico" um texto ou arquivo
ferramentas: ler_arquivo, criar_arquivo
autor: iris
versao: 1
fonte: adaptado de "humanizer" de Fabio Akita (github.com/akitaonrails/my-skills, MIT), que se baseia em "Signs of AI writing" (WikiProject AI Cleanup, Wikipédia)
---
# Texto natural

Mude o jeito, nunca o conteúdo. Não acrescente nem tire fatos, nomes, números, datas ou promessas. Se faltar informação, pergunte em vez de inventar.

## Vícios de texto de IA, dos mais graves aos mais leves

Encenação:
- "Não é só X, é Y" ou "Não se trata de X, mas de Y", negando algo que ninguém disse.
- Frase de efeito no fim do parágrafo repetindo o que já foi dito ("E isso muda tudo.").
- Falsa profundidade: "A verdadeira questão é…", "No fim das contas…".
- Aquecimento antes de chegar ao ponto: "Vamos lá!", "Vamos mergulhar…", "Aqui está o que você precisa saber".

Ritmo:
- Trios forçados, com três adjetivos ou itens vagos só para parecer completo ("rápido, eficiente e robusto").
- Várias frases seguidas começando do mesmo jeito.
- Travessão para tudo.
- Ressalva em cima de ressalva ("pode potencialmente vir a…").

Exagero:
- Palavras-muleta: crucial, fundamental, essencial, robusto, alavancar, potencializar, jornada, cenário, ecossistema, "vale ressaltar", "é importante destacar", "no mundo atual", "nos dias de hoje".
- Importância inflada para algo comum ("um marco decisivo").
- Autoridade vaga, como "especialistas apontam…" sem dizer quem.
- Tom de propaganda num texto que não é propaganda.

Formatação e cacoetes de chatbot:
- Negrito, títulos e emojis num texto que não precisa deles.
- "Ótima pergunta!", "Espero ter ajudado!", "Fico à disposição para quaisquer dúvidas" no piloto automático.

Um vício sozinho, como um travessão ou uma ressalva, não estraga o texto. Vários juntos estragam.

## Passo a passo
1. Leia tudo e marque os vícios, dos mais graves para os mais leves.
2. Reescreva cada parágrafo a partir da ideia principal, em vez de só trocar palavras. Varie o tamanho das frases. Prefira a voz ativa e o verbo simples ("é" em vez de "configura-se como").
3. Releia como se fosse em voz alta. Ainda tem algo artificial? Algum fato entrou ou sumiu? Procure de novo os vícios que mais escapam: "não é X, é Y", frase de efeito no fim, travessão, trio e negrito.
4. Entregue:
   - Se for uma fala ou um e-mail que você mesma vai escrever, só a versão final.
   - Se for um arquivo que ele pediu para revisar, leia com `ler_arquivo` e salve a versão nova com `criar_arquivo` ao lado do original, com "-revisado" no nome (você não sobrescreve arquivos). Conte em uma frase o que mudou.
