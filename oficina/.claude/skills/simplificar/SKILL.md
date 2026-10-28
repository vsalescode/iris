---
name: simplificar
description: Deixa o programa mais fácil de ler sem mudar o comportamento. Use no fim, com os testes passando.
---

# Simplificar

Adaptado de `simplify` (github.com/akitaonrails/my-skills, que por sua vez vem de
addyosmani/agent-skills).

O objetivo não é ter menos linhas: é um iniciante (o usuário) conseguir abrir o `programa.py` e
entender o que acontece.

1. **Comportamento idêntico.** Mesma saída, mesmos erros, mesmos arquivos gerados. Na dúvida, não mude.
2. **Clareza antes de esperteza.** Nomes que dizem o que a coisa é; funções curtas com uma
   responsabilidade; nada de expressões compactas que exigem parar para decifrar.
3. **Sem abstração à toa.** Programa pequeno não precisa de classes, camadas ou configurações
   que ninguém pediu.
4. **Corte o morto:** código sem uso, prints esquecidos, comentários que repetem o código.
   Mantenha os comentários que explicam o PORQUÊ.
5. **Uma mudança por vez**, rodando o `teste.py` depois de cada uma.
