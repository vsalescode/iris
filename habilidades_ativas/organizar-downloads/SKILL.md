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

Primeiro você planeja, depois mexe. Ele aprova o plano, você executa e confirma o que fez. Nunca apague nada (apagar é proibido). O que parecer lixo vai para uma pasta `_Revisar`, e ele decide depois.

## 1. Entender o pedido
Se não estiver claro, faça uma pergunta só: qual pasta, e se ele quer só separar por tipo ou uma arrumação completa.

## 2. Olhar a pasta
Use `listar_pasta` e conte os arquivos por tipo:
- Documentos (.pdf, .docx, .txt, .xlsx, .csv)
- Imagens (.jpg, .png, .gif, .webp)
- Instaladores (.exe, .msi)
- Compactados (.zip, .rar, .7z)
- Áudio e vídeo (.mp3, .mp4...)
- Outros

Fique de olho em duplicados pelo nome: "arquivo.rar" e "arquivo (1).rar" com o mesmo tamanho quase sempre são o mesmo arquivo.

## 3. Propor o plano, em voz e curto
Algo como: "Tem 62 itens: 20 imagens, 12 instaladores, 9 PDFs, 8 compactados e alguns soltos. Sugiro criar Imagens, Instaladores, Documentos e Compactados, e pôr os 3 duplicados em _Revisar. Posso?"

## 4. Fazer (depois do sim)
- Use `mover_arquivo` para colocar cada arquivo na subpasta. Se a pasta ainda não existir, ela é criada na hora. Mover pede confirmação: se ele já aprovou o plano, avise que vai confirmar em lote e siga o que as permissões pedirem.
- Não renomeie nada sem ele pedir. Se aparecer algo estranho, pare e pergunte.
- Boletos, faturas e comprovantes ficam melhor com a habilidade organizar-comprovantes do que jogados em Documentos. Sugira.

## 5. Fechar
Diga o que mudou ("Movi 45 arquivos para 4 pastas; 3 duplicados estão em _Revisar.") e ofereça manter assim ("Se quiser, faço isso toda sexta.").
