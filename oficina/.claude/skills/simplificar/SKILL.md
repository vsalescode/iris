---
name: simplificar
description: Deixa o programa mais fácil de ler sem mudar o comportamento. Use no fim, com os testes passando.
---
# Simplificar

Adaptado de `simplify` (github.com/akitaonrails/my-skills, que por sua vez vem de addyosmani/agent-skills).

O objetivo não é ter menos linhas. É alguém iniciante conseguir abrir o `programa.py` e entender o que acontece.

1. O comportamento fica idêntico: mesma saída, mesmos erros, mesmos arquivos gerados. Na dúvida, não mexa.
2. Clareza vale mais que esperteza. Use nomes que dizem o que a coisa é e funções curtas, cada uma com uma responsabilidade. Evite expressões compactas que obrigam a parar para decifrar.
3. Não crie abstração à toa. Programa pequeno não precisa de classes, camadas ou configurações que ninguém pediu.
4. Tire o que sobrou: código sem uso, print esquecido, comentário que só repete o código. Mantenha os comentários que explicam o porquê.
5. Faça uma mudança de cada vez e rode o `teste.py` depois de cada uma.
