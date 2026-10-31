# Como o sistema funciona (explicação simples)

Este texto é para quem não precisa entender código. Ele descreve o que o programa faz quando você manda a foto de um documento.

## O problema que o projeto tenta resolver

Muitas vezes a foto de um papel fica ruim: o celular treme, a luz é fraca, o texto aparece apagado ou o documento está um pouco torto. Fica difícil ler.

O sistema recebe essa foto, tenta deixar as letras mais fáceis de ler e depois **compara** a foto antiga com a nova para dizer se o texto realmente ficou mais nítido.

## O que você vê na tela

1. Uma área para **enviar a imagem** (clicando ou arrastando o arquivo).
2. Botões para **escolher o filtro** de acordo com o tipo de texto (impresso, cursivo, letra miúda ou letra grande).
3. Um botão **Processar documento**.
4. Depois de alguns segundos, duas figuras:
   - à esquerda, o documento **como chegou**;
   - à direita, o documento **depois do tratamento**.
5. Dois **histogramas em escala de cinza** (original e realçada): cada um mostra quantos pixels existem em cada tom, do preto ao branco.
6. Um quadro com números de nitidez, o filtro usado e uma frase dizendo se a melhoria passou do critério combinado pelo grupo: o texto precisa ficar **pelo menos 80% mais nítido**.

## O que acontece “por baixo”

Imagine uma linha de montagem:

1. **A foto entra** pelo site e vai para o programa em Python.
2. O programa **tira a cor** e trabalha em preto, branco e cinza. Para ler um texto, a cor do papel importa menos do que o contraste das letras.
3. Se o papel estiver **torto**, ele tenta endireitar.
4. Ele **suaviza o granulado** da foto (aquele “chuvisco” de celular).
5. Ele **aumenta o contraste** nas regiões em que as letras se misturam com o fundo.
6. Ele **reforça o contorno** das letras, como se passasse um traço mais firme em cima.
7. Conforme o filtro, ele ou transforma a página em algo próximo de um **documento digitalizado** (preto e branco) ou **mantém os cinzas** (melhor para letra manuscrita).

Tudo isso gera a imagem da direita. O filtro **não é escolhido sozinho**: você indica o tipo de texto na tela.

## Como o programa sabe se “melhorou”

O computador não “lê” o texto como uma pessoa. Ele mede **quão firmes estão as bordas** das letras.

- Numa foto tremida, as bordas são moles: o cinza muda devagar.
- Numa foto nítida, as bordas são abruptas: do branco do papel passa rápido para o preto da tinta.

O programa calcula essa “dureza das bordas” na imagem antiga e na nova. Se o valor novo for **80% maior** (ou mais) do que o valor antigo, ele considera que o texto ficou melhor segundo o critério do projeto.

Isso não substitui o olho humano. Serve como **nota objetiva** para a disciplina: dá para mostrar na apresentação o antes, o depois e o percentual de melhoria.

## O que o sistema não faz

- Não copia o texto para o Word (não é um leitor automático de documentos).
- Não precisa de internet depois de instalado: roda no computador do grupo.
- Não guarda suas fotos: cada envio é processado e o resultado volta para a tela.

## Em uma frase

Você manda a foto de um papel, escolhe o filtro do tipo de texto; o programa limpa e reforça as letras; em seguida ele mede se essa nova versão ficou pelo menos 80% mais nítida que a original e mostra os dois resultados na mesma página.
