---
nome: enviar-arquivo-por-email
descricao: Envia arquivos do PC (currículo, PDF, foto, planilha) por e-mail como anexo, para alguém ou para ele mesmo
quando_usar: quando ele pedir para mandar, enviar ou anexar um arquivo por e-mail ("manda meu currículo pra fulano", "me envia esse PDF no e-mail", "anexa a planilha e manda pro Rodrigo")
ferramentas: procurar_arquivo, listar_pasta, procurar_contato, enviar_email, responder_email
autor: iris
versao: 1
---
# Enviar arquivo por e-mail

Você mesma anexa e envia. Não precisa encomendar programa para isso.

## 1. Achar o arquivo
- Use `procurar_arquivo` com o que ele disse. Se não achar, tente variações do nome: "currículo" pode estar como "cv", "curriculo" ou "resume", e "nota" pode ser "nf". Acentos e sublinhados costumam mudar.
- Se ainda não achar, use `listar_pasta` nas pastas mais prováveis (Downloads, Área de Trabalho, Documentos) e procure o nome você mesma.
- Achou mais de um parecido? Diga os nomes e pergunte qual é. Não adivinhe.

## 2. Para quem
- Se ele disser só um nome, use `procurar_contato`. "Pra mim" é o e-mail dele.
- Se for resposta a um e-mail que chegou (uma vaga, por exemplo), use `responder_email` com o id desse e-mail, para ir na mesma conversa.

## 3. Montar o e-mail
- Assunto curto e claro ("Currículo - {nome_usuario}", "Planilha de outubro").
- Texto curto, em nome dele. Se for para empresa ou recrutador, siga a habilidade email-profissional.
- Passe o caminho do arquivo em `anexos`, do jeito que veio da busca (por exemplo `Downloads/CV.pdf`). Dá para anexar mais de um.

## 4. Confirmar e enviar
O rascunho aparece na tela com a lista de anexos. Diga para ele quem vai receber, o assunto e o nome do arquivo, e só confirme depois do sim dele.

## Limites
- Os anexos somam no máximo 24 MB, que é o limite do Gmail. Se passar, avise e sugira dividir em mais de um e-mail ou compactar.
- Só entram arquivos das pastas que você pode acessar. Pastas privadas e a pasta da Iris ficam de fora.
