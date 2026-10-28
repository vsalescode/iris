---
nome: organizar-downloads
descricao: Organiza uma pasta bagunçada (normalmente Downloads) em subpastas por tipo, sem apagar nada
quando_usar: quando ele pedir para arrumar, organizar ou limpar os Downloads, a Área de Trabalho ou outra pasta
ferramentas: listar_pasta, procurar_arquivo, criar_arquivo, mover_arquivo
autor: iris
versao: 1
fonte: adaptado de "file-organizer" (github.com/ComposioHQ/awesome-claude-skills, Apache-2.0)
---
# Organizar uma pasta

Princípio: **planejar antes de mexer**. Ele aprova o plano; você executa e confirma. Nunca apague nada
(apagar é proibido): o que parecer lixo vai para uma pasta `_Revisar` para ele decidir depois.

## 1. Entender o pedido
Se não estiver claro, pergunte uma coisa só: qual pasta e o quanto ele quer mexer
("só separar por tipo" ou "arrumação completa").

## 2. Olhar a pasta
`listar_pasta` na pasta pedida. Conte por tipo:
- Documentos (.pdf, .docx, .txt, .xlsx, .csv)
- Imagens (.jpg, .png, .gif, .webp)
- Instaladores (.exe, .msi)
- Compactados (.zip, .rar, .7z)
- Áudio e vídeo (.mp3, .mp4, ...)
- Outros

Repare em **duplicados pelo nome**: "arquivo.rar" e "arquivo (1).rar", com o mesmo tamanho, são quase certamente iguais.

## 3. Propor o plano (em voz, curto)
Ex.: "Tem 62 itens: 20 imagens, 12 instaladores, 9 PDFs, 8 compactados e alguns soltos. Sugiro criar
Imagens, Instaladores, Documentos e Compactados, e pôr os 3 duplicados em _Revisar. Faço?"

## 4. Executar (depois do sim)
- `mover_arquivo` para cada arquivo, para dentro da subpasta (mover para uma pasta que não existe
  cria a pasta). Mover pede confirmação: se ele já disse sim ao plano, avise que vai confirmar em lote
  e siga o que as permissões pedirem.
- Não renomeie nada sem ele pedir. Se algo estranho aparecer, pare e pergunte.
- Comprovantes, boletos e faturas: sugira a habilidade organizar-comprovantes em vez de jogar em Documentos.

## 5. Fechar
Diga o que mudou ("Movi 45 arquivos para 4 pastas; 3 duplicados estão em _Revisar.") e dê uma dica de
manutenção ("Se quiser, posso fazer isso toda sexta.").
