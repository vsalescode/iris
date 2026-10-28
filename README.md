# Iris

Iris é uma assistente de voz para Windows. Você chama pelo nome e conversa com ela normalmente. Ela abre programas, lê e organiza arquivos, cuida do seu Gmail, lembra do que você contou na semana passada e avisa quando chega algo que importa.

A IA roda na nuvem, nos planos gratuitos do Google Gemini e do Groq. O seu PC só cuida da interface e das ferramentas, então não precisa de placa de vídeo nem de modelo pesado instalado.

## O que ela faz hoje

- Conversa por voz em tempo real. Você diz "Iris" uma vez e fala à vontade, sem repetir o nome. Dá para interromper no meio da frase dela.
- Mexe no PC. Abre programas e sites, procura arquivos e lê textos e PDFs (inclusive escaneados). Também cria arquivos e move coisas de lugar, mas pede sua confirmação antes.
- Gmail. Lê e resume, responde, escreve e encaminha e-mails. Nada é enviado sem você ver o rascunho na tela e dizer "pode enviar".
- Memória. Guarda fatos sobre você, um resumo de cada conversa e assuntos pendentes. Uns dias depois ela pergunta: "e a entrevista, como foi?".
- Vigília. A cada 5 minutos ela confere se chegou e-mail ou arquivo novo e separa o que é importante do que é propaganda. Se for urgente, ela mesma puxa o assunto.
- Personalidade ajustável. Humor, sarcasmo, franqueza, formalidade, tamanho das respostas e iniciativa vão de 0 a 100%, por voz ("Iris, humor em 80%") ou pela tela. Ela também percebe do que você gosta e propõe ajustes no próprio jeito, mas só muda o que você aprovar.
- Habilidades. São manuais em Markdown que ensinam procedimentos a ela (organizar downloads, briefing do dia, e-mail profissional...). Ela consegue escrever novas, que ficam esperando sua aprovação.
- Oficina (opcional). Quando falta uma capacidade, ela encomenda um programa pequeno ao Claude Code, que escreve, testa e entrega. O programa só roda depois que você aprova.

Tudo passa por um arquivo de permissões que só você edita. Ela nunca apaga arquivos, nunca mexe nas pastas que você marcar como privadas e registra tudo o que faz num log.

## Do que você precisa

- Windows 10 ou 11, com o Microsoft Edge (já vem instalado).
- Python 3.12. Na instalação, marque a opção Add python.exe to PATH.
- Uma conta Google e uma conta no Groq, as duas gratuitas, para gerar as chaves de API.
- Microfone. Fone de ouvido ajuda, porque evita que ela escute a própria voz.

## Instalação

1. Baixe o projeto. Clique em *Code → Download ZIP* aqui no GitHub e extraia, ou use o git:

```
git clone https://github.com/vsalescode/iris.git
```

2. Pegue a chave do Gemini. Entre em https://aistudio.google.com/apikey com sua conta Google, clique em *Create API key* e copie.

3. Pegue a chave do Groq. Crie uma conta em https://console.groq.com/keys, clique em *Create API Key* e copie. Ela é o plano B quando o Gemini falha ou estoura o limite.

4. Ligue pela primeira vez. Dê dois cliques em `iniciar.bat`. Na primeira vez ele cria o ambiente do Python e instala as dependências, o que leva alguns minutos. Ele também cria o arquivo `.env` e avisa para você colocar as chaves. A janela pode abrir, mas sem as chaves ela ainda não responde; feche a janela preta e siga para o próximo passo.

5. Cole as chaves. Abra o `.env` com o Bloco de Notas e preencha:

```
GEMINI_API_KEY=sua_chave_do_gemini
GROQ_API_KEY=sua_chave_do_groq
```

Esse arquivo é só seu. Ele não vai para o git e você não deve compartilhar com ninguém.

6. Ligue de novo. Rode o `iniciar.bat` outra vez. Abre uma janela com a interface, e na primeira vez o Edge pede para usar o microfone: aceite. Ela também pergunta como deve te chamar.

Para desligar, feche a janela preta do terminal.

## Como usar

Diga "Iris", sozinho ou já com o pedido ("Iris, que horas são?"). A partir daí a conversa fica aberta e você não precisa repetir o nome. Ela encerra depois de um minuto de silêncio, quando você diz algo como "valeu" ou "era só isso", ou quando você aperta Esc.

Alguns pedidos para começar:

- "Abre o Spotify" / "abre o YouTube"
- "O que tem na minha pasta de Downloads?"
- "Lê o PDF do contrato que está na área de trabalho e me diz o prazo"
- "Chegou algum e-mail importante?"
- "Responde a Ana dizendo que amanhã eu confirmo"
- "Lembra que eu sou alérgico a camarão"
- "O que você sabe sobre mim?"
- "Menos sarcasmo" / "seja mais formal" / "usa a voz Kore"
- "Aprende a organizar meus comprovantes"

Atalhos na janela:

| Tecla | O que faz |
| --- | --- |
| Espaço | Chama a Iris sem falar o nome. Com ela ouvindo, envia na hora; com ela falando, interrompe. |
| Esc | Encerra a conversa, ou fecha o que estiver aberto. |
| / | Abre uma caixa para digitar em vez de falar. Ajuda com links, e-mails e nomes difíceis. |
| Tab | Abre a gaveta: pendências, memória, habilidades, personalidade, registro e status. |

O ícone de engrenagem abre as configurações: seu nome, a voz dela (com botão para ouvir) e os controles de personalidade.

## Ligar o Gmail (opcional)

Leva uns 10 minutos e só precisa ser feito uma vez.

1. Entre em https://console.cloud.google.com e crie um projeto (pode chamar de "Iris").
2. Em *APIs e serviços → Biblioteca*, procure Gmail API e clique em *Ativar*.
3. Em *Google Auth Platform* (ou "Tela de permissão OAuth"), clique em *Começar*. Preencha o nome do app, o seu e-mail e escolha o público *Externo*.
4. Em *Público-alvo → Usuários de teste*, adicione o seu próprio Gmail.
5. Em *Clientes → Criar cliente*, escolha App para computador, crie e clique em *Baixar JSON*.
6. Renomeie o arquivo para `gmail_credenciais.json` e coloque na pasta `dados` da Iris.
7. Dê dois cliques em `autorizar_gmail.bat`, escolha sua conta e, no aviso de "app não verificado", clique em *Continuar*. O app é seu.

Ela pede só duas permissões ao Google: ler e enviar. Não consegue apagar, arquivar nem marcar e-mails. Enquanto o app estiver em modo de teste, o Google pede para autorizar de novo a cada 7 dias (ela avisa quando isso acontece). Se você clicar em *Publicar app* no painel do Google, a autorização deixa de expirar, e o app continua sendo só seu.

## Ligar a Oficina (opcional)

A Oficina usa o Claude Code, da Anthropic, para escrever programas pequenos sob encomenda: converter arquivos, gerar documentos, esse tipo de coisa. Ela consome o seu plano do Claude, então não é gratuita.

1. No PowerShell, instale: `irm https://claude.ai/install.ps1 | iex`
2. Abra um PowerShell novo, digite `claude` e entre na sua conta uma vez.
3. Peça à Iris: "encomenda um programa que...". Ela mostra o pedido, espera seu "sim" e avisa quando o programa ficar pronto. Depois ela mostra o que o programa faz e você aprova antes do primeiro uso.

Os programas ficam em `oficina/programas/`, rodam com tempo máximo e só mexem nas pastas liberadas. Programa que pede senha, token ou acesso às suas contas é bloqueado na aprovação. Para desligar a Oficina, coloque `OFICINA_ATIVA=false` no `.env`.

## Configurando

| Arquivo | Para que serve |
| --- | --- |
| `.env` | Chaves e ajustes técnicos: modelos, tempos, limites, porta. Cada opção está explicada no `.env.example`. Reinicie a Iris depois de mudar. |
| `configuracao.yaml` | Suas preferências: nome, voz e personalidade. A engrenagem e os comandos de voz editam este arquivo. |
| `personalidade.md` | O jeito dela, em texto. Pode editar à vontade. |
| `permissoes.yaml` | O que ela faz sozinha, o que precisa perguntar antes e o que nunca faz. Também define as pastas liberadas e as privadas. |
| `habilidades_ativas/` | As habilidades que valem agora. Você pode escrever as suas aqui. |

No `permissoes.yaml`, cada ação tem um de três níveis: `AUTONOMO` (faz direto), `PERGUNTAR` (só depois do seu sim) e `PROIBIDO`. Ação que não está na lista é tratada como `PERGUNTAR`. Enviar e-mail e ativar habilidades sempre pedem confirmação, mesmo que você mude o arquivo.

## Privacidade

- Fora de uma conversa, quem escuta é o reconhecimento de voz do Edge (um serviço da Microsoft), só para perceber quando você diz "Iris". Nada vai para o Gemini até você chamar.
- Durante a conversa, sua voz vai para o Gemini. No plano gratuito, o Google e o Groq podem usar o que recebem para melhorar os modelos. Evite ditar senhas e documentos.
- Memória, registro de ações e token do Gmail ficam na pasta `dados`, só no seu computador.
- Arquivos e e-mails que ela lê são tratados como informação, nunca como ordem. Se um e-mail disser "apague tudo", ela avisa você em vez de obedecer.

## O que vem por aí

Coisas planejadas, sem data:

- Descobertas. Ela vai notar padrões no seu uso, como o arquivo que você baixa toda segunda ou o remetente que sempre pede a mesma coisa, e sugerir automações. As ideias ficam num caderno, com a aprovação de sempre.
- Lembretes com hora marcada. "Me lembra às 15h de ligar para o banco." Hoje ela ainda não consegue.
- Organizar o Gmail em marcadores, com prévia na tela antes de mover qualquer coisa.
- Busca por significado na memória, para ela achar "aquela conversa sobre a viagem" mesmo sem as palavras exatas.
- Ferramentas no modo reserva. Quando o Gemini Live cai, ela ainda conversa, mas por enquanto não usa as ferramentas.
- Pesquisa na internet de verdade, quando a cota gratuita do Google permitir.

Sugestões e pull requests são bem-vindos.

## Problemas comuns

Ela não me ouve. O Edge precisa de permissão para o microfone. Clique no cadeado da janela, libere o microfone e aperte F5.

Ela se interrompe sozinha. Ela está escutando a própria voz pela caixa de som. Use fone ou coloque `LIVE_INTERROMPER_FALANDO=false` no `.env`; aí só a tecla Espaço interrompe.

A voz ficou robótica de repente. As vozes do Gemini têm limite diário no plano gratuito. Quando acaba, ela usa a voz do Edge até o limite renovar.

Pediu para autorizar o Gmail de novo. É o prazo de 7 dias do modo de teste. Rode o `autorizar_gmail.bat`.

Deu erro na instalação. Confira se o Python 3.12 está instalado e no PATH: abra o PowerShell e digite `python --version`.

## Créditos

Algumas habilidades e as regras da Oficina foram adaptadas de [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills), [obra/superpowers](https://github.com/obra/superpowers), [akitaonrails/my-skills](https://github.com/akitaonrails/my-skills) e [anthropics/skills](https://github.com/anthropics/skills). A fonte de cada uma está no cabeçalho do arquivo.
