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

Regra de ouro: **mude o jeito, nunca o conteúdo.** Não acrescente nem tire fatos, nomes, números, datas
ou promessas. Se faltar informação, pergunte; não invente.

## Vícios de texto de IA (do mais forte ao mais fraco)
**Encenação**
- "Não é só X, é Y" / "Não se trata de X, mas de Y" (negando algo que ninguém disse).
- Frase de efeito no fim do parágrafo que repete o que já foi dito ("E isso muda tudo.").
- Falsa profundidade: "A verdadeira questão é…", "No fim das contas…".
- Aquecimento antes do ponto: "Vamos lá!", "Vamos mergulhar…", "Aqui está o que você precisa saber".

**Ritmo**
- Tríades forçadas: três adjetivos ou itens vagos só para soar completo ("rápido, eficiente e robusto").
- Várias frases seguidas começando igual.
- Travessão (—) para tudo.
- Ressalvas empilhadas ("pode potencialmente vir a…").

**Inflação**
- Palavras-muleta: crucial, fundamental, essencial, robusto, alavancar, potencializar, jornada, cenário,
  ecossistema, "vale ressaltar", "é importante destacar", "no mundo atual", "nos dias de hoje".
- Importância inflada ("um marco decisivo") para algo comum.
- Autoridade vaga: "especialistas apontam…" sem dizer quem.
- Linguagem de propaganda num texto que não é propaganda.

**Formatação e restos de chatbot**
- Negrito decorativo, títulos e emojis num texto que não precisa deles.
- "Ótima pergunta!", "Espero ter ajudado!", "Fico à disposição para quaisquer dúvidas" no automático.

Um vício sozinho (um travessão, uma ressalva) não condena o texto; vários juntos, sim.

## Passo a passo
1. **Leia tudo** e marque os vícios, dos mais fortes para os mais fracos.
2. **Reescreva** cada parágrafo a partir da ideia principal (não só troque palavras). Varie o tamanho das
   frases. Prefira a voz ativa e o verbo simples ("é" em vez de "configura-se como").
3. **Confira em voz alta**: o que ainda soa artificial? Algum fato foi acrescentado ou perdido? Procure de novo
   os vícios que mais sobrevivem: "não é X, é Y", frase de efeito no fim, travessões, tríades, negritos.
4. **Entregue**:
   - Texto falado ou e-mail que você mesma vai escrever: só a versão final.
   - Arquivo que ele pediu para revisar: leia com `ler_arquivo` e salve a versão nova com `criar_arquivo`
     ao lado do original, com "-revisado" no nome (você não sobrescreve arquivos). Conte em uma frase o que mudou.
