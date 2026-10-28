# Tudo o que a Iris faz

Este é o guia completo. Para instalar e começar, veja o [README](README.md).

A Iris funciona em camadas. Ela conversa com você, usa ferramentas para agir no PC e no Gmail, guarda memória entre conversas, vigia o que chega enquanto você não está falando com ela e, por último, consegue criar coisas novas para si mesma: habilidades, programas e ajustes no próprio jeito. Tudo que ela cria espera a sua aprovação antes de valer.

## Conversa

- Você chama dizendo "Iris" (ou "ei, Iris"), ou apertando Espaço na janela. Pode falar o pedido junto: "Iris, abre o Spotify".
- Depois de chamada, a conversa fica aberta. Você fala normalmente, sem repetir o nome.
- Ela responde em voz em cerca de um segundo, pela Gemini Live. Dá para interromper falando por cima dela.
- A conversa termina depois de um minuto de silêncio, quando você diz algo como "valeu", "tchau" ou "era só isso", ou quando você aperta Esc.
- A tecla / abre uma caixa para digitar em vez de falar. Ajuda com e-mails, links e nomes difíceis.
- Se a Gemini Live cair, ela continua no modo reserva: o Edge transcreve, o Whisper do Groq confere o texto, o Gemini (ou o Groq) responde e a voz é sintetizada à parte. Nesse modo ela conversa, mas ainda não usa ferramentas.

## Ferramentas

Cada ferramenta tem um nível no `permissoes.yaml`: AUTONOMO (faz direto), PERGUNTAR (só depois do seu sim) ou PROIBIDO. Os níveis abaixo são os que vêm de fábrica. Quando aparece "sempre pergunta", a confirmação é obrigatória mesmo que você mude o arquivo.

### No PC

| O que ela faz | Exemplo | Permissão |
| --- | --- | --- |
| Abrir programas e jogos do Menu Iniciar | "abre o Spotify", "abre o Valorant" | faz direto |
| Abrir sites | "abre o YouTube" | faz direto |
| Listar o que tem numa pasta | "o que tem nos meus Downloads?" | faz direto |
| Procurar arquivos pelo nome | "acha o arquivo do contrato" | faz direto |
| Ler arquivos de texto, código, CSV e PDF (inclusive escaneado) | "lê o PDF do boleto e me diz o vencimento" | faz direto |
| Criar arquivos de texto | "salva esse plano num arquivo" | pergunta antes |
| Mover e renomear arquivos e pastas | "joga as fotos numa pasta Imagens" | pergunta antes |
| Apagar arquivos | | proibido |

Ela só mexe dentro da sua pasta de usuário e das pastas liberadas no `permissoes.yaml`. Nunca entra nas pastas privadas nem na pasta da própria Iris, nunca sobrescreve um arquivo e nunca apaga nada.

PDFs digitais são lidos no seu PC. PDFs escaneados (só imagem) são enviados ao Gemini para leitura, a menos que você desligue com `ARQUIVO_PDF_LEITURA_NUVEM=false`.

### No Gmail

| O que ela faz | Exemplo | Permissão |
| --- | --- | --- |
| Listar e resumir e-mails | "chegou algo importante?", "tem e-mail do banco?" | faz direto |
| Ler um e-mail inteiro | "lê o e-mail da Marina" | faz direto |
| Achar o endereço de alguém pelo nome | "qual o e-mail do Rodrigo?" | faz direto |
| Escrever um e-mail novo | "manda um e-mail pro Rodrigo dizendo que..." | sempre pergunta |
| Responder um e-mail, na mesma conversa | "responde a Marina confirmando" | sempre pergunta |
| Encaminhar um e-mail inteiro, com anexos | "me manda aquele e-mail da vaga" | sempre pergunta |
| Anexar arquivos do PC a um e-mail novo ou a uma resposta | "manda meu currículo pra recrutadora" | sempre pergunta |

Antes de enviar qualquer coisa, o rascunho aparece na tela, com a lista de anexos quando houver, e ela lê para você. Só sai depois do seu "pode enviar". Ela entende nomes falados errado ("Joana Silvia" quando o remetente é "Joana Silva") comparando com quem já te escreveu, e entende endereços ditados ("fulano arroba gmail ponto com").

Os anexos somam até 24 MB (`GMAIL_ANEXOS_LIMITE_MB`) e só podem vir das pastas que ela tem permissão de acessar.

A permissão pedida ao Google é só de ler e enviar. Ela não consegue apagar, arquivar nem marcar e-mails.

### Sobre ela mesma

| O que ela faz | Exemplo | Permissão |
| --- | --- | --- |
| Mudar um ajuste de personalidade | "humor em 80%", "menos sarcasmo" | faz direto |
| Trocar a voz, o seu nome ou o tempo da conversa | "usa a voz Kore", "me chama de Vic" | faz direto |
| Lembrar, esquecer e procurar na memória | "lembra que eu sou alérgico a camarão" | faz direto |
| Anotar e fechar assuntos em aberto | "minha entrevista é quinta" | faz direto |
| Tirar uma pendência da fila | "pode ignorar esse aviso" | faz direto |

## Memória

Fica num banco local (`dados/iris.db`), só no seu PC.

- Fatos e preferências: "trabalha com backend", "prefere respostas curtas de manhã".
- Um resumo de cada conversa, feito sozinho quando a conversa termina.
- Assuntos em aberto, que ela puxa na hora certa ("e a entrevista, como foi?") e fecha quando você conta o desfecho.

Ela não guarda senhas, cartões nem documentos. Na transcrição salva, números perto de palavras como "senha" ou "cartão" viram `[oculto]`. Tudo aparece na gaveta (Tab → Memória), com um × para apagar qualquer item.

## Vigília

A cada 5 minutos, em segundo plano:

1. Sem gastar IA, ela confere se chegou e-mail novo e se apareceu arquivo novo nas pastas liberadas (de arquivo, ela vê só nome, tamanho e data).
2. Só quando algo mudou, a IA separa o que importa (boleto, prazo, alguém esperando resposta) do que é propaganda e cria pendências com prioridade.
3. Se for urgente, ela fala sozinha, mas nunca das 23h às 7h nem mais de uma vez a cada 20 minutos.
4. Quando você chama, ela começa pela pendência mais importante.

O painel Pensamentos, na gaveta, mostra o que a vigília está fazendo ao vivo.

## O que ela cria por conta própria

Esta é a parte em que a Iris cresce. Ela propõe, você decide. Nada que mude o comportamento dela vale antes do seu sim.

### Lembranças e assuntos
- Como nasce: sozinha, no fim de cada conversa, a partir do que você contou. Ou na hora, quando você pede "lembra que...".
- Precisa de aprovação? Não. Mas você vê tudo na gaveta e apaga o que quiser.

### Pendências
- Como nasce: pela vigília, quando chega algo que importa. Também quando uma encomenda da Oficina termina.
- Precisa de aprovação? Não. Você descarta pela gaveta ou dizendo que já resolveu.

### Habilidades
São manuais em Markdown que ensinam um procedimento a ela, como organizar comprovantes ou montar o briefing do dia.
- Como nasce: quando você pede ("aprende a organizar meus comprovantes") ou quando ela percebe que resolveu bem algo que vai se repetir. Ela escreve o passo a passo e propõe.
- Precisa de aprovação? Sim. Por voz (o texto aparece na tela) ou na gaveta (Tab → Habilidades → Ver / Aprovar / Recusar). Cada "sim" aprova uma só.
- Proteções: uma habilidade não dá poder novo, só ensina a usar as ferramentas que já existem. Se uma "melhoria" ficar bem menor que a versão atual, o cartão avisa que podem ter sumido passos. A versão anterior sempre fica guardada como backup.
- Onde fica: `habilidades_propostas/` até a aprovação, depois `habilidades_ativas/`.

### Programas (Oficina)
Quando falta uma capacidade que nenhuma ferramenta cobre, como gerar um PDF formatado ou converter planilhas, ela encomenda um programa ao Claude Code.
- Como nasce: você pede ("encomenda um programa que..."). Ela escreve a especificação e mostra na tela.
- Precisa de aprovação? Duas vezes. Uma para começar a encomenda, que usa o seu plano do Claude, e outra para usar o programa pronto, depois de ver o que ele faz.
- Como é feito: o Claude Code trabalha só dentro da pasta `oficina/`, segue as regras de `oficina/CLAUDE.md`, escreve o programa, o manual e um teste, roda o teste e manda um relatório. Ela avisa quando fica pronto.
- Proteções: o programa roda com tempo máximo, só com arquivos das pastas liberadas, e é bloqueado se pedir senha, token ou acesso às suas contas. Se o código mudar depois da aprovação, precisa aprovar de novo.
- Onde fica: `oficina/programas/<nome>/`.

### Personalidade
Além dos seis ajustes de fábrica (humor, sarcasmo, franqueza, formalidade, detalhe e iniciativa), ela aprende o seu jeito.
- Como nasce: no fim de cada conversa, ela procura sinais claros do que você gosta (riu de um tipo de piada, reclamou de resposta longa, pediu algo de novo) e faz no máximo uma proposta. Também propõe durante a conversa ou quando você pede.
- O que pode propor:
  - um jeito aprendido, numa frase ("quando ele está programando, menos piadas");
  - mudar um ajuste de leve, no máximo 25 pontos por vez;
  - um ajuste novo de 0 a 100%, como "nerdice" ou "empatia", que aparece sozinho na engrenagem.
- Precisa de aprovação? Sim, por voz ou na gaveta (Tab → Personalidade).
- Proteções: propostas que mexam em confirmações, permissões, honestidade ou segurança são barradas. O que você recusa ela não propõe de novo. O `personalidade.md` ela nunca altera.
- Onde fica: `personalidade_aprendida.yaml`, que você pode ler e editar.

### Arquivos e rascunhos
- Arquivos de texto (planos, listas, resumos em CSV, versões revisadas de um texto) ela cria quando você pede, depois de confirmar. Nunca por cima de um arquivo existente.
- Rascunhos de e-mail ela escreve sozinha a partir do que você ditou, mas só envia com o seu sim.

## Habilidades que já vêm com ela

| Habilidade | O que faz |
| --- | --- |
| briefing-do-dia | Resumo falado do dia: pendências, e-mails que pedem ação e assuntos que vencem |
| organizar-downloads | Arruma uma pasta bagunçada em subpastas por tipo, sem apagar nada |
| organizar-comprovantes | Organiza boletos e notas em pastas por ano e mês, com nomes padronizados e uma planilha de resumo |
| email-profissional | Escreve e-mails de trabalho no tom certo para recrutador, empresa, suporte ou colega |
| enviar-arquivo-por-email | Acha um arquivo no PC e manda por e-mail como anexo |
| texto-natural | Revisa um texto para soar como gente, sem mudar o conteúdo |
| pensar-junto | Ajuda a transformar uma ideia solta num plano, uma pergunta por vez |
| criar-habilidade | O manual que ela segue para escrever habilidades novas |

## O que ela nunca faz

- Apagar arquivos ou e-mails.
- Fazer pagamentos.
- Enviar e-mail, ativar habilidade, mudar a própria personalidade ou encomendar programa sem o seu sim. E cada sim vale para uma ação só.
- Obedecer ordens escritas dentro de e-mails, arquivos ou páginas. Se aparecer algo assim, ela avisa você.
- Mexer no próprio código, no `permissoes.yaml` ou nas pastas privadas.
- Dizer que fez algo que não fez.

Tudo o que ela faz com ferramentas fica registrado em `dados/auditoria.jsonl`, com hora, ação e resultado.

## Interface

- No centro, a íris de uma lente. Em espera o diafragma respira. Ouvindo, ele abre e o medidor acompanha a sua voz. Pensando, as lâminas fecham e giram e tudo fica violeta. Falando, o medidor pulsa com a voz dela.
- A fala dela aparece embaixo, à esquerda, no ritmo da voz.
- A gaveta (Tab) tem Pendências, Pensamentos, Habilidades, Personalidade, Memória, Registro e o status do sistema.
- A engrenagem tem o seu nome, a voz (com botão para ouvir cada uma) e os controles de personalidade.

## Onde cada coisa fica

| Arquivo ou pasta | O que guarda |
| --- | --- |
| `.env` | Chaves de API e ajustes técnicos |
| `configuracao.yaml` | Seu nome, a voz e os níveis de personalidade |
| `personalidade.md` | O jeito dela, em texto |
| `personalidade_aprendida.yaml` | O que ela aprendeu do seu jeito e as propostas pendentes |
| `permissoes.yaml` | O que ela pode fazer e as pastas liberadas e privadas |
| `habilidades_ativas/` e `habilidades_propostas/` | Habilidades valendo e esperando aprovação |
| `oficina/programas/` | Programas feitos na Oficina |
| `dados/iris.db` | Memória, pendências e o que a vigília já viu |
| `dados/auditoria.jsonl` | Registro de tudo que ela fez |
| `dados/gmail_token.json` | Autorização do Gmail |

## Custos e limites

- Gemini e Groq: planos gratuitos. A conversa pela Gemini Live não tem limite diário.
- Vozes do Gemini fora da Live: cerca de 10 falas por dia por modelo. Ela alterna entre quatro modelos e, quando todos acabam, usa a voz do Edge.
- A vigília usa no máximo 100 análises com IA por dia (`VIGIA_MAX_IA_POR_DIA`).
- A Oficina usa o seu plano do Claude e não é gratuita. Um programa pequeno costuma ficar pronto em poucos minutos.
- No plano gratuito, Google e Groq podem usar o que recebem para melhorar os modelos. Evite ditar senhas e documentos.
