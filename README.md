# IRIS – assistente pessoal de voz

Uma assistente de voz para Windows no estilo JARVIS/TARS: conversa em tempo real, tem personalidade
ajustável, mexe nos seus arquivos e no seu Gmail (sempre com permissões), lembra de você entre conversas,
vigia o que chega e avisa o que importa. O cérebro roda na nuvem, nos planos gratuitos do Gemini e do Groq;
nada de modelo pesado no seu PC.

## Requisitos
- Windows 10 ou 11, com o Microsoft Edge (já vem no Windows).
- Python 3.12 (https://www.python.org/downloads/; marque "Add python.exe to PATH" na instalação).
- Chaves grátis do Gemini e do Groq (abaixo). Gmail e Oficina são opcionais.

## Como ligar
Dê dois cliques em **`iniciar.bat`**. Na primeira vez ele cria o ambiente Python (`.venv`) e instala tudo; depois só liga.
Abre uma janela do Edge sem barra de endereço com a interface. Para desligar, feche a janela preta do terminal.

## Chaves de API (grátis)
As chaves ficam no arquivo `.env` (criado automaticamente a partir do `.env.example`). Nunca compartilhe esse arquivo.

**Gemini (cérebro principal)**
1. Acesse https://aistudio.google.com/apikey e entre com sua conta Google.
2. Clique em **Create API key** e copie a chave.
3. No `.env`, cole depois de `GEMINI_API_KEY=`.

**Groq (reserva automática)**
1. Acesse https://console.groq.com/keys e crie uma conta.
2. Clique em **Create API Key**, dê um nome (ex.: iris) e copie.
3. No `.env`, cole depois de `GROQ_API_KEY=`.

> No plano gratuito, os provedores podem usar o que você envia para melhorar os modelos. Evite mandar dados sensíveis.

## Arquivos que você pode editar
| Arquivo | Para quê |
| --- | --- |
| `.env` | chaves de API **e todos os ajustes técnicos**: modelos de IA, tempos, limites, porta (lista explicada no `.env.example`; reinicie a Iris depois de mudar) |
| `configuracao.yaml` | suas preferências: nome, voz, personalidade, tempo de conversa (a engrenagem e a voz editam) |
| `personalidade.md` | o jeito da Iris (`{{NOME}}` vira o seu nome) |
| `personalidade_aprendida.yaml` | o que ela aprendeu do seu jeito (aprovado por você) e propostas esperando |
| `permissoes.yaml` | o que ela pode fazer sozinha |

## Estrutura
```
iris/
  __main__.py     liga o servidor e abre a janela
  ambiente.py     ajustes técnicos lidos do .env (com valor padrão)
  config.py       caminhos, .env e configuracao.yaml
  servidor.py     FastAPI + WebSocket (fala com a interface)
  personalidade.py  ajustes de personalidade (TARS)
  cerebro/        Gemini Live e o cérebro do modo reserva
  voz/            voz e transcrição do modo reserva
  ferramentas/    PC, e-mail, memória e ajustes (com permissões)
  emails/         Gmail
  memoria/        memória de longo prazo (SQLite)
  permissoes/     permissoes.yaml e auditoria
  interface/      HTML/CSS/JS
  proatividade/   vigília e pendências
```

## Como falar com ela
- Chame **uma vez**: diga "Iris" (com ou sem o pedido junto) ou aperte Espaço.
- A partir daí ela fica **em conversa**: tudo que você fala é com ela, sem repetir o nome. Depois de ~1,5 s de silêncio ela responde e volta a ouvir.
- A conversa termina com 60 s de silêncio, com "valeu" / "tchau" / "era só isso", ou com **Esc**. Depois disso, chame "Iris" de novo.

## Atalhos na janela
- **Espaço** em IDLE: ativa a Iris sem falar o nome.
- **Espaço** ouvindo: envia na hora o que você já falou.
- **Espaço** pensando/falando: interrompe (continua em conversa).
- **Esc**: encerra a conversa (ou fecha a gaveta / a caixa de texto, se estiverem abertas).
- **/** (ou o ícone ⌨): abre uma caixa para **digitar** em vez de falar (bom para e-mails, links e nomes difíceis). Enter envia; ela responde em voz normalmente.
- **Tab** (ou ☰): abre a gaveta com memória, registro e status do sistema.

## Habilidades (SKILL.md)
"Manuais" em Markdown que ensinam procedimentos a ela. Cada habilidade é uma pasta com um `SKILL.md`:
```
---
nome: organizar-downloads
descricao: o que faz, numa frase
quando_usar: em que situações (é isso que a faz lembrar de usar)
ferramentas: listar_pasta, mover_arquivo
---
# passo a passo em Markdown
```
- **`habilidades_ativas/`**: valem agora. Nas instruções dela vai só a lista; o manual inteiro ela lê na hora (`usar_habilidade`).
- **`habilidades_propostas/`**: escritas por ela ("Iris, aprende a fazer X"). **Só valem depois da sua aprovação**: na gaveta (Tab → Habilidades → Ver / Aprovar / Recusar) ou por voz ("pode ativar"), com o texto na tela antes. Ao melhorar uma existente, a versão antiga fica como backup (`SKILL.v….md`).
- **Proteções:** se a "melhoria" ficar bem menor que a versão atual (menos de 60%, `HABILIDADES_ALERTA_ENCOLHIMENTO`), aparece um ⚠ no cartão: provavelmente perdeu passos. E um "sim" ativa **uma** habilidade por vez (o mesmo vale para enviar e-mails): se ela propôs cinco, você confirma cada uma.
- Use `{nome_usuario}` no texto para o seu nome (vem do `configuracao.yaml`).
- Habilidades **não dão poderes novos**: só ensinam a usar as ferramentas que existem; as permissões continuam valendo.
- Você pode escrever as suas também: crie a pasta e o `SKILL.md` em `habilidades_ativas/` e reinicie a conversa.

Já vêm com ela: `briefing-do-dia`, `organizar-downloads`, `organizar-comprovantes`, `email-profissional`, `pensar-junto`, `texto-natural` e `criar-habilidade` (as de organizar, pensar junto, texto natural e criar habilidade adaptadas de [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills), [obra/superpowers](https://github.com/obra/superpowers), [akitaonrails/my-skills](https://github.com/akitaonrails/my-skills) e [anthropics/skills](https://github.com/anthropics/skills)).

## Oficina (programas novos, feitos pelo Claude Code)
A Iris não escreve código. Quando você pede uma capacidade nova, ela encomenda um programa ao
**Claude Code**, que trabalha só dentro de `oficina/`:
- `oficina/CLAUDE.md`: as regras (formato do programa, nunca apagar/sobrescrever, sem internet, não mexer na Iris).
- `oficina/.claude/skills/`: `verificar-programa`, `seguranca-programa` e `simplificar`, adaptadas das skills do Akita.
- `oficina/programas/<nome>/`: cada programa com `programa.py`, o manual `PROGRAMA.md` e `teste.py`.
- `oficina/.venv`: ambiente Python separado do da Iris.

Por voz: "Iris, encomenda um programa que…". Ela mostra o pedido na tela e só começa depois do seu
"sim" (um por vez). O Claude Code trabalha em segundo plano (de 1 a ~20 min); quando termina, vira uma
pendência na gaveta e ela avisa. "Iris, como está a encomenda?" mostra o andamento e o relatório.
Pronto o programa, ela conta o que ele faz ("Iris, mostra o programa X") e você aprova por voz
("pode aprovar", com o resumo na tela). Só programas aprovados rodam (`usar_programa`), com tempo máximo
(`OFICINA_PROGRAMA_SEGUNDOS`) e só com arquivos das suas pastas liberadas. Se o programa mudar depois,
precisa aprovar de novo. **Programas nunca recebem senhas, tokens ou acesso às suas contas**: um programa
que peça isso é bloqueado na aprovação. Ajustes `OFICINA_*` no `.env`.

Precisa do Claude Code instalado no terminal (`irm https://claude.ai/install.ps1 | iex` no PowerShell e
depois `claude` uma vez para entrar na conta). Usa o seu plano do Claude: não é grátis.

## Vigília – modo proativo
A cada 5 minutos ela faz uma ronda em segundo plano:
1. **Sem IA (barato):** chegou e-mail novo no Gmail? apareceu arquivo novo nas `zonas_liberadas` do `permissoes.yaml` (hoje: Downloads e Área de Trabalho)? De arquivo ela vê só **nome, tamanho e data**, nunca o conteúdo. Na 1ª ronda ela só memoriza o que já existe.
2. **Só se algo mudou:** a IA separa o que importa (boletos, prazos, alguém esperando resposta) do que é propaganda e cria **pendências** com prioridade.
3. **Urgente:** ela **fala sozinha** e já abre a conversa para você responder. Não fala das 23h às 7h, nem mais de uma vez a cada 20 min (ajustes `VIGIA_*` no `.env`).
4. Quando você chamar, ela começa pela pendência mais importante; quando você decidir, ela tira da fila.

Na gaveta (**Tab**): **Pendências** (com × para descartar) e **Pensamentos** (o que a vigília está fazendo, ao vivo).
Para vigiar outra pasta, coloque em `zonas_liberadas` no `permissoes.yaml`; para nunca olhar uma pasta, em `zonas_privadas`.

## Memória
Ela lembra de você entre conversas, num banco local (`dados/iris.db`, só no seu PC):
- **Fatos e preferências** ("trabalha com backend", "alérgico a camarão", "namorada Ana").
- **Resumo de cada conversa**, feito automaticamente quando a conversa termina.
- **Assuntos em aberto**: ela puxa no momento certo ("e aí, como foi a entrevista?") e fecha quando você conta o desfecho. O quanto ela puxa assunto segue o ajuste de **iniciativa**.

Por voz: "lembra que…", "esquece aquilo de…", "o que você sabe sobre mim?".
Na gaveta (**Tab**), seção **Memória**: tudo o que ela sabe, com **×** para apagar qualquer item.
Ela não guarda senhas, cartões nem documentos; na transcrição salva, números perto dessas palavras ficam `[oculto]`.

## Personalidade (estilo JARVIS / TARS)
- O jeito dela está em `personalidade.md` (edite à vontade; vale na próxima conversa).
- Ajustes de 0 a 100%, como o TARS de Interestelar: **humor, sarcasmo, franqueza, formalidade, detalhe e iniciativa**. Mude **por voz** ("Iris, humor em 80%", "menos sarcasmo", "seja mais formal") ou pela engrenagem. Ficam salvos em `configuracao.yaml`.
- Também por voz: trocar a voz dela ("usa a voz Kore"), o seu nome e o tempo de silêncio que encerra a conversa.

### Personalidade que evolui (sempre com o seu "sim")
- **No fim de cada conversa** ela procura sinais claros do jeito que você gosta (riu de um tipo de piada,
  reclamou de resposta longa, pediu algo de novo) e faz **no máximo uma proposta**:
  - **jeito aprendido**, uma frase: "Quando ele está programando, menos piadas e mais direto";
  - **mudar um ajuste** de leve (até 25 pontos): "Humor de 40% para 55%";
  - **ajuste novo** de 0 a 100%, com 5 faixas: "Nerdice", "Empatia"… Aparece sozinho na engrenagem.
- Ela também propõe durante a conversa, ou quando você pede ("cria um ajuste de nerdice").
- **Nada vale antes do seu sim:** por voz (cartão na tela, um "sim" por proposta) ou na gaveta
  (Tab → **Personalidade** → Ver / Aprovar / Recusar). O × num jeito aprendido faz ela esquecer.
- Recusou? Ela não propõe a mesma coisa de novo. Propostas que mexam em confirmações, permissões,
  honestidade ou segurança são barradas: `personalidade.md` e os limites dela nunca mudam.
- Tudo fica em `personalidade_aprendida.yaml` (dá para ler e editar). Apagar a memória não apaga isso.
  Ajustes `PERSONALIDADE_*` no `.env` (`PERSONALIDADE_EVOLUIR=false` desliga as propostas automáticas).

## Interface
- O orbe no centro é ela: respira em espera, se acende ao ouvir, gira em espiral ao pensar e ondula quando fala.
- A fala aparece como legenda embaixo, no ritmo da voz. Ações aparecem como avisos rápidos no canto.
- **Tab** (ou ☰) abre a gaveta com o registro e o status do sistema; **Esc**, × ou clicar fora fecha.

## Gemini Live (modo principal)
- Depois do "Iris" (ou Espaço), o microfone vai direto para a **Gemini Live**, que ouve, pensa e responde em voz em ~1 s. O "Iris" em si continua sendo detectado no seu PC, pelo Edge: fora de uma conversa, nada do microfone vai para a nuvem.
- **Pode falar por cima dela**: ela para e te escuta. Se ela se cortar sozinha (ouvindo a própria voz pela caixa de som), use fone ou mude `LIVE_INTERROMPER_FALANDO=false` no `.env` (aí o Espaço corta a fala dela).
- Usa as vozes Gemini da engrenagem (Edge não funciona na Live; nesse caso ela usa a Aoede).
- Plano grátis: sem limite diário. A conexão é renovada sozinha a cada ~10 min, sem perder a conversa.
- Se a Live falhar, a Iris usa sozinha o **modo clássico** (abaixo) por 5 minutos e avisa no log.

## Ferramentas no PC
Na conversa Live ela pode:
- **abrir programas e jogos** do Menu Iniciar ("abre o Spotify") e **sites** ("abre o YouTube");
- **listar pastas**, **procurar** e **ler** arquivos de texto e **PDF** (currículos, boletos, contratos). PDF digital é lido no seu PC; PDF escaneado (só imagem) é lido pelo Gemini, a menos que `ARQUIVO_PDF_LEITURA_NUVEM=false`;
- **criar** arquivos de texto e **mover/renomear** arquivos (pede sua confirmação antes).

Regras (no `permissoes.yaml`, que só você edita e vale na hora):
- `AUTONOMO` faz direto · `PERGUNTAR` ela pergunta e só faz depois do seu "sim" falado (o servidor confere na transcrição que você disse sim) · `PROIBIDO` nunca. Ação não listada = PERGUNTAR.
- Só mexe dentro da sua pasta de usuário (e das `zonas_liberadas`); nunca nas `zonas_privadas` nem na pasta da própria Iris. Nunca apaga nem sobrescreve.
- Tudo o que ela fez fica em `dados/auditoria.jsonl` (hora, ação, resultado), para você revisar.
- No modo clássico (reserva) ela ainda não usa ferramentas.

## E-mail – Gmail
- **Ler:** lista e resume seus e-mails ("Iris, chegou algo importante?", "tem e-mail do banco?", "lê o e-mail da Ana"). Nomes falados errado ("Infinity Pay") ela acerta pelo remetente mais parecido.
- **Escrever e responder:** "manda um e-mail pro Rodrigo dizendo que…", "responde a InfinitePay pedindo o comprovante". Ela redige, **mostra o rascunho na tela e lê para você**, e só envia depois do seu "pode enviar". Essa confirmação é obrigatória mesmo se o `permissoes.yaml` disser AUTONOMO.
- **Encaminhar:** "me manda aquele e-mail da vaga", "encaminha pro Rodrigo o boleto da Claro". Vai o e-mail **original inteiro, com anexos** (ela não redigita), com um recado opcional seu em cima. Também pede confirmação.
- Permissões pedidas ao Google: `gmail.readonly` (ler) e `gmail.send` (só enviar). Ela não consegue apagar, arquivar nem marcar e-mails.

**Configuração (uma vez só, ~10 min):**
1. Entre em https://console.cloud.google.com com a sua conta Google e crie um projeto (ex.: `Iris`).
2. Menu **APIs e serviços → Biblioteca** → procure **Gmail API** → **Ativar**.
3. Menu **Google Auth Platform** (ou "Tela de permissão OAuth") → **Começar**:
   nome do app `Iris`, seu e-mail de suporte, público **Externo**, seu e-mail de contato → criar.
4. Em **Público-alvo** → **Usuários de teste** → **Adicionar usuários** → coloque o seu Gmail.
5. Em **Clientes** → **Criar cliente** → tipo **App para computador** → criar → **Baixar JSON**.
6. Renomeie o arquivo baixado para `gmail_credenciais.json` e coloque na pasta `dados\` da Iris.
7. Dê dois cliques em **`autorizar_gmail.bat`** → o navegador abre → escolha sua conta →
   em "O Google não verificou este app", clique **Continuar** (o app é seu) → permita.

Pronto: o token fica em `dados\gmail_token.json`. Para revogar o acesso: https://myaccount.google.com/permissions

> Com o app em modo "Teste", o Google expira a autorização a cada **7 dias**; aí é só rodar o `autorizar_gmail.bat` de novo (ela avisa). Para não expirar, em **Público-alvo** clique **Publicar app** (continua sendo só seu).

## Ouvido (modo clássico)
- O texto ao vivo na tela vem do reconhecimento do Edge (instantâneo).
- Quando você termina de falar, o áudio do pedido vai para o **Whisper do Groq**, bem mais preciso, e é esse texto que vai para o cérebro (+~0,5 s). Se o Whisper falhar, ela usa o texto do Edge.
- Para desligar: `WHISPER_ATIVO=false` no `.env`.

## Cérebro
- **Gemini** responde primeiro; se falhar, travar (>8 s) ou estourar o limite, o **Groq** assume sozinho e o log avisa. A barra de baixo mostra quem está respondendo (verde = principal, amarelo = reserva).
- Modelos e ordem ficam no `.env` (`CEREBRO_ORDEM`, `GEMINI_MODELO_TEXTO`, `GROQ_MODELO_TEXTO`). A personalidade (`personalidade.md`) é relida a cada resposta: edite e teste na hora.

## Vozes
- **Gemini** (padrão): a mais natural, usa a mesma `GEMINI_API_KEY`. O plano grátis dá só ~10 falas por dia **por modelo**; ela faz rodízio entre 4 modelos (~40 falas/dia) e, quando todos esgotam, usa a voz **reserva** (edge-tts) até liberar.
- **Edge**: instantânea e sem limite, porém mais robótica.
- **Groq (Orpheus)**: só inglês, sotaque forte. Antes de usar, aceite os termos em https://console.groq.com/playground?model=canopylabs%2Forpheus-v1-english
- Escolha e ouça cada uma na engrenagem. Modelos de voz, estilo e voz reserva ficam no `.env` (`TTS_GEMINI_MODELOS`, `TTS_ESTILO`, `VOZ_RESERVA`).

## Problemas comuns
- **Ela não ouve:** na primeira vez o Edge pede permissão do microfone; aceite. Se negou, clique no ícone de câmera/cadeado da janela, libere e aperte F5.
- **Reconhecimento e voz precisam de internet** (são serviços online da Microsoft, grátis).
