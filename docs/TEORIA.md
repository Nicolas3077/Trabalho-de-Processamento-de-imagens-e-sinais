# Teoria acadêmica de processamento de imagens e sinais

Este texto descreve a teoria de processamento de imagens e sinais que fundamenta o projeto de **realce de texto em documentos**. O objeto de estudo é uma imagem digital bidimensional tratada como sinal discreto de intensidade. Não há modelagem tridimensional nem métodos de sombreamento de superfícies (Gouraud, Phong, etc.): o domínio é o realce, a restauração pontual/espacial e a medição de nitidez em imagens de documentos.

Os quatro perfis do sistema (documento impresso, letra cursiva, traço fino e texto grande) compartilham a mesma cadeia teórica. O que muda é o **conjunto de parâmetros** e a presença ou ausência da **binarização**.

---

## 1. A imagem como sinal discreto

Uma imagem digital em tons de cinza é uma função

\[
f: \{0,\ldots,M-1\} \times \{0,\ldots,N-1\} \to \{0,\ldots,L-1\},
\]

em que \(M\) e \(N\) são as dimensões (linhas e colunas) e \(L = 256\) é o número de níveis de quantização (8 bits). O valor \(f(x,y)\) é a **luminância** (intensidade) no pixel \((x,y)\).

Uma imagem colorida no espaço BGR (OpenCV) é um sinal vetorial

\[
\mathbf{f}(x,y) = \bigl(f_B(x,y),\, f_G(x,y),\, f_R(x,y)\bigr).
\]

O processamento deste projeto opera quase inteiramente sobre o canal de luminância. Isso se justifica porque o texto impresso ou manuscrito é, em primeira ordem, um fenômeno de **contraste de intensidade** entre tinta e papel, e não de crominância.

### 1.1 Conversão para escala de cinza

A transformação de cor para cinza usada pelo OpenCV (`COLOR_BGR2GRAY`) é a combinação linear da Recomendação ITU-R BT.601:

\[
Y = 0{,}299\,R + 0{,}587\,G + 0{,}114\,B.
\]

Os pesos refletem a sensibilidade espectral relativa do sistema visual humano: o verde contribui mais para a luminância percebida do que o vermelho, e o azul menos. Se a imagem já possui um único canal, ela já é o sinal \(f\). Se possui canal alfa (BGRA), o canal de transparência é descartado na conversão para cinza.

### 1.2 Polaridade do documento

Documentos seguem o padrão **tinta escura sobre fundo claro**. Se a média espacial das intensidades

\[
\mu = \frac{1}{MN}\sum_{x,y} f(x,y)
\]

é menor que \(127\) (metade da faixa \([0,255]\)), a imagem é tratada como negativo e substitui-se \(f\) pelo **complemento**

\[
f'(x,y) = 255 - f(x,y),
\]

equivalente à operação lógica bit a bit de inversão em imagens binárias de 8 bits. Isso alinha a polaridade ao modelo de documento, sem alterar o conteúdo geométrico do traço.

---

## 2. Histograma como descritor estatístico do sinal

O histograma de uma imagem em cinza com \(L = 256\) níveis é a função

\[
h(k) = \#\bigl\{(x,y): f(x,y) = k\bigr\}, \qquad k = 0,1,\ldots,255.
\]

É a distribuição empírica da intensidade: o eixo horizontal é o nível de cinza (preto \(\to\) branco) e o eixo vertical é a contagem de pixels. A frequência relativa \(p(k) = h(k)/(MN)\) é a função massa de probabilidade do sinal, usada em equalização, limiarização de Otsu e análise de contraste.

Em documentos:

- uma página bem binarizada concentra massa em \(k \approx 0\) (tinta) e \(k \approx 255\) (papel);
- uma foto mal iluminada ou desfocada espalha a massa pelos cinzas intermediários;
- o realce que aumenta o contraste tende a **separar** esses dois modos.

O projeto calcula \(h(k)\) na original convertida para cinza e na imagem realçada, para evidenciar essa mudança de distribuição.

---

## 3. Correção de inclinação (deskew)

A inclinação do papel na captura é uma **rotação rígida** no plano da imagem. O método usado estima o ângulo a partir da geometria dos pixels de texto e aplica uma transformação afim.

### 3.1 Binarização global de Otsu (somente para estimar o ângulo)

Sobre o negativo da imagem em cinza aplica-se o limiar de **Otsu** (1979). Otsu escolhe o limiar \(t^\ast\) que maximiza a **variância entre classes** do histograma, equivalentemente minimiza a variância intra-classe.

Sejam duas classes \(C_0 = \{0,\ldots,t\}\) e \(C_1 = \{t+1,\ldots,255\}\), com pesos \(w_0(t)\), \(w_1(t)\) e médias \(\mu_0(t)\), \(\mu_1(t)\). A variância entre classes é

\[
\sigma_B^2(t) = w_0(t)\,w_1(t)\,\bigl(\mu_0(t) - \mu_1(t)\bigr)^2.
\]

O limiar ótimo é \(t^\ast = \arg\max_t \sigma_B^2(t)\). O resultado é uma máscara binária dos pixels de tinta (após a inversão).

Essa binarização **não** é a saída do pipeline; serve apenas para obter o conjunto de pontos de texto.

### 3.2 Retângulo de área mínima

Os pixels não nulos formam um conjunto de pontos no plano. O **retângulo de área mínima** (mínimo retângulo delimitador rotacionado) envolve esse conjunto. O ângulo desse retângulo é uma estimativa da orientação dominante da mancha de texto.

O ângulo retornado pelo retângulo mínimo vive, por convenção, em um intervalo que pode cruzar \(\pm 45^\circ\). A correção

\[
\theta \leftarrow
\begin{cases}
\theta + 90^\circ, & \theta < -45^\circ, \\
\theta - 90^\circ, & \theta > 45^\circ, \\
\theta, & \text{caso contrário},
\end{cases}
\]

traz \(\theta\) para a faixa de pequenas rotações de documento (quase horizontal). Se \(|\theta| < 0{,}4^\circ\), a rotação é desprezada: o ganho geométrico seria menor que o custo de reamostrar a imagem.

### 3.3 Transformação afim de rotação

A correção é a isometria

\[
\begin{pmatrix} x' \\ y' \end{pmatrix}
=
\begin{pmatrix}
\cos\theta & \sin\theta \\
-\sin\theta & \cos\theta
\end{pmatrix}
\begin{pmatrix} x - c_x \\ y - c_y \end{pmatrix}
+
\begin{pmatrix} c_x \\ c_y \end{pmatrix},
\]

com centro \(c = (N/2,\, M/2)\). Na malha discreta, \((x',y')\) em geral não cai em um pixel inteiro. A reamostragem usa **interpolação bicúbica** (kernel cúbico de Keys), que aproxima a função sinc de Whittaker–Shannon com suporte \(4\times 4\). Nas bordas, o modo **replicate** estende o valor do pixel de borda (continuação constante), evitando faixas pretas artificiais.

---

## 4. Redução de ruído

O ruído de captura (sensor, compressão, granulação) é modelado como perturbação aditiva ou como flutuações locais de intensidade. O projeto usa dois filtros **não lineares** de preservação de borda, nunca um passa-baixas gaussiano isolado nesta etapa (o gaussiano aparece depois, no unsharp).

### 4.1 Médias não locais (Non-Local Means)

O algoritmo **NL-Means** (Buades, Coll e Morel, 2005) estima cada pixel como média ponderada de outros pixels cuja **vizinhança** (patch) é semelhante, não apenas os vizinhos espaciais imediatos.

\[
\hat{f}(x) = \frac{1}{Z(x)} \sum_{y \in \Omega(x)} w(x,y)\, f(y),
\]

com

\[
w(x,y) = \exp\left( -\frac{\lVert P(x) - P(y) \rVert_{2,a}^2}{h^2} \right),
\]

em que \(P(x)\) é o patch centrado em \(x\) (janela de template), \(\lVert\cdot\rVert_{2,a}\) é uma distância \(L^2\) com peso gaussiano espacial, \(\Omega(x)\) é a janela de busca e \(h > 0\) controla o grau de suavização. \(Z(x)\) normaliza os pesos.

Interpretação: em um documento, muitos trechos de papel (e de traço) se repetem. Pixels com patches semelhantes são média dos “iguais”, o que reduz ruído **sem** borrar tanto as bordas quanto um filtro espacial clássico de mesmo suporte.

Parâmetros do projeto:

| Perfil | \(h\) | Template | Busca |
| --- | --- | --- | --- |
| Documento impresso | \(7\) | \(7\times 7\) | \(21\times 21\) |
| Traço fino | \(3\) | \(7\times 7\) | \(21\times 21\) |
| Texto grande | \(10\) | \(7\times 7\) | \(21\times 21\) |

\(h\) maior admite diferenças maiores entre patches e, portanto, suaviza mais. Traço fino usa \(h\) menor para não apagar tinta de pouca largura.

### 4.2 Filtro bilateral

O **filtro bilateral** (Tomasi e Manduchi, 1998) é uma média ponderada local com **dois** núcleos gaussianos: um no domínio espacial e outro no domínio da intensidade.

\[
\hat{f}(x) = \frac{1}{W(x)} \sum_{y \in \mathcal{N}_d(x)}
f(y)\,
G_{\sigma_s}(\lVert y-x\rVert)\,
G_{\sigma_r}\bigl(\lvert f(y)-f(x)\rvert\bigr).
\]

- \(G_{\sigma_s}\) (sigma espacial) penaliza vizinhos distantes.
- \(G_{\sigma_r}\) (sigma de cor/intensidade) penaliza vizinhos com cinza muito diferente, o que **preserva descontinuidades** (bordas do traço).
- O diâmetro \(d\) limita a vizinhança \(\mathcal{N}_d\).

No perfil de letra cursiva: \(d = 5\), \(\sigma_r = 20\), \(\sigma_s = 20\). O traço manuscrito varia de espessura e de densidade de tinta; um limiar duro depois destruiria essa variação, e o bilateral reduz ruído mantendo a borda do calígrafo.

---

## 5. Reamostragem (interpolação) como operação sobre o sinal

Quando o perfil permite e o maior lado da imagem é no máximo \(2500\) pixels, o sinal é interpolado por fator \(2\) em cada eixo **antes** do realce de contraste e da nitidez, e depois reduzido ao tamanho original.

### 5.1 Ampliação bicúbica

A interpolação bicúbica reconstrói valores em posições intermediárias com um polinômio cúbico por partes (kernel de Keys, parâmetro \(a = -0{,}75\) na implementação típica do OpenCV). No domínio da amostragem, isso equivale a um **passa-baixas** mais seletivo que o bilinear, com melhor preservação de bordas do que a interpolação de ordem \(1\). O objetivo teórico é aumentar a malha sobre a qual atuam o CLAHE e o unsharp, para que o traço ocupe mais amostras.

Letra cursiva **não** amplia: o fator \(2\) interpolado pode criar cinzas artificiais no traço irregular e prejudicar a leitura.

### 5.2 Redução por área (`INTER_AREA`)

A volta ao tamanho original usa reamostragem por **média de área** (box filter adaptado à razão de escala). Cada pixel de saída é a média dos pixels de entrada que recaem no seu suporte. Isso é o dual de um **filtro passa-baixas anti-aliasing** antes da subamostragem, coerente com o teorema da amostragem: reduzir resolução sem filtrar geraria aliasing (serrilhado, moiré).

---

## 6. Realce de contraste local: CLAHE

A **equalização de histograma** clássica aplica a função de distribuição acumulada empírica

\[
s_k = (L-1) \sum_{j=0}^{k} p(j)
\]

a toda a imagem. Isso globaliza o contraste e, em documentos com iluminação desigual, **estoura** regiões já claras ou afoga regiões já escuras.

A **equalização adaptativa de histograma** (AHE) calcula um histograma por **lajota** (tile) e interpola bilinearmente os mapeamentos nas fronteiras das lajotas, de modo que o contraste se ajuste ao contexto local.

O **CLAHE** (Contrast Limited Adaptive Histogram Equalization; Pizer et al.; formulação de clipagem em Zuiderveld, 1994) limita o contraste: valores do histograma acima de um **clip limit** são redistribuídos uniformemente pelos demais níveis. Isso evita a amplificação de ruído em regiões homogêneas (o papel).

Parâmetros do projeto: lajota \(8\times 8\); clip limit \(2{,}0\) (impresso e texto grande), \(1{,}8\) (traço fino), \(1{,}5\) (cursiva). Clip menor = menos amplificação de contraste = menos risco de romper o traço manuscrito ou miúdo.

---

## 7. Realce de nitidez: unsharp masking

O **unsharp mask** é um realce clássico de altas frequências. A versão contínua é

\[
f_{\text{sharp}} = f + \lambda \,(f - f_{\sigma}),
\]

em que \(f_{\sigma} = f * G_{\sigma}\) é a imagem filtrada por um **núcleo gaussiano** e \(\lambda\) (amount) é o ganho das altas frequências. Equivalentemente,

\[
f_{\text{sharp}} = (1+\lambda)\,f - \lambda\, f_{\sigma}.
\]

Essa é exatamente a combinação linear usada: peso \(1+\lambda\) na original e peso \(-\lambda\) na suavizada.

### 7.1 Núcleo gaussiano

O filtro gaussiano bidimensional (separável) é

\[
G_{\sigma}(x,y) = \frac{1}{2\pi\sigma^2}
\exp\left( -\frac{x^2+y^2}{2\sigma^2} \right).
\]

É o núcleo passa-baixas isotrópico de referência: minimiza o produto incerteza espaço–frequência e não introduz novos extremos ao longo de escalas (propriedade ligada à equação do calor). A diferença \(f - f_{\sigma}\) é portanto um **passa-altas**: realça transições (bordas das letras).

No OpenCV, máscara \((0,0)\) com \(\sigma\) dado significa que o tamanho do kernel discreto é derivado de \(\sigma\) (suporte proporcional a \(\sigma\)).

Parâmetros: \(\lambda \in \{0{,}8,\, 0{,}35,\, 0{,}5,\, 0{,}6\}\) e \(\sigma \in \{1{,}0,\, 0{,}8\}\) conforme o perfil. Cursiva usa \(\lambda\) menor para não criar halos no traço contínuo.

O resultado é saturado na faixa \([0,255]\) (clipping), o que é a quantização de volta ao intervalo do sinal de 8 bits.

---

## 8. Binarização adaptativa gaussiana

Três perfis (impresso, traço fino, texto grande) convertem o sinal em **dois níveis**. Letra cursiva permanece em cinza: um limiar destruiria a continuidade de traços de tinta irregular.

### 8.1 Limiar adaptativo

Em vez de um único \(t\) global (Otsu), cada pixel recebe um limiar local

\[
T(x,y) = m_G(x,y) - C,
\]

em que \(m_G(x,y)\) é a **média ponderada gaussiana** da vizinhança de lado `blockSize` (ímpar) e \(C\) é uma constante subtraída. A decisão é

\[
g(x,y) =
\begin{cases}
255, & f(x,y) > T(x,y), \\
0, & \text{caso contrário}
\end{cases}
\]

(`THRESH_BINARY`). O peso gaussiano na janela privilegia vizinhos próximos, o que aproxima um fundo local suave (sombra, vinheta, iluminação não uniforme da folha).

Isso é **limiarização local**: o mesmo cinza absoluto pode ser classificado como tinta ou papel conforme o contexto. Documentos fotografados com luz irregular são o caso típico em que o limiar global falha.

| Perfil | `blockSize` | \(C\) |
| --- | --- | --- |
| Documento impresso | \(21\) | \(10\) |
| Traço fino | \(13\) | \(5\) |
| Texto grande | \(35\) | \(15\) |

Janela menor e \(C\) menor (traço fino) tornam o teste mais conservador com a tinta: menos pixels de traço são empurrados para o fundo. Janela maior e \(C\) maior (texto grosso) evitam preencher ocos internos de letras grandes (o “branco” de um “O”).

Não há morfologia matemática (erosão, dilatação, abertura, fechamento) após o limiar.

---

## 9. Medidas de nitidez e contraste

A nitidez, neste projeto, **não** é OCR nem avaliação subjetiva MOS. É um funcional sobre derivadas discretas da imagem: texto nítido produz **gradientes e laplaciano de maior energia**.

### 9.1 Operador de Sobel e Tenengrad

O **gradiente** discreto aproxima \(\nabla f = (f_x, f_y)\). O operador de **Sobel** (máscaras \(3\times 3\)) combina diferenças centrais com um leve suavização perpendicular (média ponderada \([1,2,1]\)):

\[
K_x =
\begin{bmatrix}
-1 & 0 & 1 \\
-2 & 0 & 2 \\
-1 & 0 & 1
\end{bmatrix},
\quad
K_y =
\begin{bmatrix}
-1 & -2 & -1 \\
 0 &  0 &  0 \\
 1 &  2 &  1
\end{bmatrix}.
\]

A medida de **Tenengrad** usada é a energia média do gradiente:

\[
T(f) = \frac{1}{MN} \sum_{x,y} \bigl( (K_x * f)^2 + (K_y * f)^2 \bigr).
\]

É um índice clássico de foco: desfoque óptico (aproximável por convolução gaussiana) reduz a magnitude do gradiente; bordas de letra nítidas a aumentam.

### 9.2 Laplaciano e sua variância

O **laplaciano** \(\nabla^2 f = f_{xx} + f_{yy}\) é um operador passa-altas isotrópico de segunda ordem. Com abertura padrão \(ksize = 1\) no OpenCV, o núcleo é o laplaciano de 4-vizinhos:

\[
K_{\nabla^2} =
\begin{bmatrix}
0 &  1 & 0 \\
1 & -4 & 1 \\
0 &  1 & 0
\end{bmatrix}.
\]

A **variância do laplaciano** (Pech, 2000, e literatura de auto-foco)

\[
V(f) = \mathrm{Var}(\nabla^2 f)
\]

é alta quando há muitas transições fortes (texto nítido) e baixa quando a imagem é suave (desfoque). Diferente da média do \(|\nabla^2 f|\), a variância captura a **dispersão** das respostas de borda.

### 9.3 Contraste RMS

O contraste RMS (raiz da variância, isto é, o **desvio-padrão** das intensidades)

\[
C_{\mathrm{RMS}}(f) = \sqrt{\frac{1}{MN}\sum_{x,y}\bigl(f(x,y)-\mu\bigr)^2}
= \sigma_f
\]

mede o espalhamento global dos cinzas. É o contraste de Michelson generalizado para cenas complexas, no sentido estatístico de energia AC do sinal. Em um documento, aumentar a separação tinta/papel aumenta \(\sigma_f\); uma imagem “lavada” tem \(\sigma_f\) baixo.

Esta métrica é reportada, mas **não** entra no índice combinado de nitidez.

### 9.4 Índice combinado e critério de melhoria

A nitidez combinada é a combinação linear convexa

\[
S(f) = 0{,}6\, V(f) + 0{,}4\, T(f).
\]

Laplaciano (segunda derivada) e Tenengrad (primeira derivada) são complementares: um enfatiza curvatura/pontos de inflexão da borda, o outro a energia de primeira ordem.

A melhoria relativa é

\[
\Delta = \frac{S(f_{\text{realçada}}) - S(f_{\text{original}})}{S(f_{\text{original}})} \times 100\%,
\]

com o caso degenerado \(S(f_{\text{original}}) \approx 0\) tratado à parte. O critério da disciplina é \(\Delta \ge 80\%\).

Esse critério é um **limiar sobre um funcional de alta frequência**, não uma garantia de legibilidade humana. Binarização, em particular, pode inflar \(V\) e \(T\) ao criar bordas em degrau unitário mesmo quando o resultado visual for discutível.

---

## 10. Síntese: cadeia de operações no domínio da teoria

Ordem conceitual do processamento, comum aos perfis:

1. **Projeção para luminância** — descarta crominância; o sinal passa a ser escalar.
2. **Estimação de orientação + rotação afim** — corrige o modelo geométrico de captura (rotação no plano), com limiar de Otsu só como detector de suporte do texto.
3. **Estimação não local ou bilateral** — reduz a componente de ruído preservando descontinuidades.
4. **Mudança de taxa de amostragem** (quando aplicável) — interpolação bicúbica / média de área, ligada ao teorema da amostragem.
5. **Equalização adaptativa limitada** — redistribui o histograma **localmente**, realçando contraste tinta–papel sob iluminação não uniforme.
6. **Ênfase de altas frequências (unsharp)** — soma um múltiplo do resíduo passa-altas gaussiano.
7. **Quantização a dois níveis** (exceto cursiva) — decisão bayesiana simplificada com limiar local gaussiano.
8. **Ajuste de polaridade** — complemento se o fundo for escuro.
9. **Descritores** — histograma \(h(k)\); \(\sigma_f\); energia de Sobel; variância do laplaciano.

Os “filtros” da interface não são núcleos isolados: são **perfis de parâmetros** da mesma teoria, ajustados à escala e à regularidade do traço (impresso vs. manuscrito, fino vs. grosso).

---

## 11. O que este projeto não emprega

Para delimitar o conteúdo teórico efetivo:

- não há **sombreamento 3D** (modelos de iluminação de superfície);
- não há **morfologia matemática** após a binarização;
- não há **OCR** nem reconhecimento de padrões de caracteres;
- não há **transformada de Fourier** explícita na implementação (os filtros gaussianos e o unsharp são equivalentes a operações passa-baixas/passa-altas no domínio da frequência, mas são realizados no domínio espacial);
- não há **restauração cega de desfoque** (deconvolução, filtro de Wiener).

---

## Referências clássicas (teoria dos métodos utilizados)

- Gonzalez, R. C.; Woods, R. E. *Digital Image Processing*. Equalização, histograma, filtragem espacial, unsharp, limiarização, geometria.
- Otsu, N. A threshold selection method from gray-level histograms. *IEEE Trans. SMC*, 1979.
- Buades, A.; Coll, B.; Morel, J.-M. A non-local algorithm for image denoising. *CVPR*, 2005.
- Tomasi, C.; Manduchi, R. Bilateral filtering for gray and color images. *ICCV*, 1998.
- Zuiderveld, K. Contrast limited adaptive histogram equalization. *Graphics Gems IV*, 1994.
- Pizer, S. M. et al. Adaptive histogram equalization and its variations. *Computer Vision, Graphics, and Image Processing*, 1987.
- Pech-Pacheco, J. L. et al. Diatom autofocusing in brightfield microscopy: a comparative study. *ICPR*, 2000. (variância do laplaciano como medida de foco.)
- Sobel, I.; Feldman, G. A 3×3 isotropic gradient operator for image processing. Comunicação histórica, 1968; máscaras de Sobel.
- Keys, R. Cubic convolution interpolation for digital image processing. *IEEE Trans. Acoustics, Speech, and Signal Processing*, 1981.
- ITU-R BT.601. Pesos de luminância da conversão RGB → Y.
