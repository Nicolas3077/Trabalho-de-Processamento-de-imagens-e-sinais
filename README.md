# Realce de texto em documentos

Sistema web local para a disciplina de **processamento de imagens e sinais**. Recebe a imagem de um documento, aplica o **filtro escolhido pelo usuário** para realçar o texto e compara a nitidez da imagem original com a imagem gerada.

O critério de avaliação adotado no backend considera a imagem **melhor** quando o texto fica **pelo menos 80% mais nítido**.

## Arquitetura

| Camada | Tecnologia | Papel |
| --- | --- | --- |
| Front-end | HTML, CSS e JavaScript | Escolha do filtro, upload da imagem, estado de processamento, imagens lado a lado e histogramas em tons de cinza |
| Back-end | Python 3, Flask, OpenCV, NumPy, Pillow | Pipeline de realce, métricas de nitidez, histogramas de cinza e API JSON |
| Entrega | Execução local em `http://127.0.0.1:5000` | Demonstração em aula sem deploy na nuvem |

```
.
├── app.py                      # API Flask e página inicial
├── processing/
│   ├── enhancement.py          # Pipelines de realce (filtros nomeados)
│   └── metrics.py              # Nitidez (critério de 80%) e histogramas de cinza
├── templates/index.html
├── static/style.css
├── static/app.js
├── requirements.txt
├── README.md                   # Este arquivo (visão técnica)
└── COMO_FUNCIONA.md            # Explicação para quem não é da área
```

## Filtros disponíveis

O usuário escolhe o filtro na página. Cada perfil usa o tom (cinza ou binário) e os parâmetros mais adequados ao tipo de texto. Se o campo `filter` não for enviado, o backend usa `documento_impresso`.

- **Documento impresso** (`documento_impresso`) — texto digitado, formulário, comprovante. Denoise NLMeans (`h=7`), CLAHE `2.0`, unsharp `0.8`, limiar adaptativo `blockSize=21` e `C=10`. **Saída binária.**
- **Letra cursiva** (`letra_cursiva`) — manuscrito e tinta irregular. Filtro bilateral (preserva borda), CLAHE `1.5`, unsharp leve (`0.35`), **sem limiar duro**. **Saída em tons de cinza.**
- **Traço fino e letra miúda** (`traco_fino`) — corpo pequeno e linhas finas. NLMeans mais fraco (`h=3`), CLAHE `1.8`, unsharp `0.5`, limiar `blockSize=13` e `C=5`. **Saída binária**, mais conservadora com a tinta.
- **Texto grande e traço grosso** (`texto_grande`) — títulos e letra grande. NLMeans `h=10`, CLAHE `2.0`, unsharp `0.6`, limiar `blockSize=35` e `C=15`. **Saída binária**, para não preencher ocos.

## Pipeline de processamento

Etapas comuns a todos os filtros; os números e a binarização vêm do perfil escolhido.

1. **Decodificação** — a imagem enviada é lida com Pillow e convertida para BGR (OpenCV).
2. **Tons de cinza** — o texto é tratado como variação de luminância, não de cor.
3. **Deskew** — correção de pequena inclinação pelo ângulo do retângulo mínimo dos pixels de texto.
4. **Redução de ruído** — NLMeans ou bilateral, conforme o filtro.
5. **Ampliação 2x** — quando o perfil permite e o maior lado é `<= 2500`, para o traço miúdo ter mais pixels (a letra cursiva não amplia).
6. **Contraste local (CLAHE)** — equalização adaptativa com `clipLimit` do perfil.
7. **Nitidez (unsharp mask)** — `amount` do perfil.
8. **Binarização adaptativa** — só nos filtros de documento impresso, traço fino e texto grande. Sem morfologia.
9. **Polaridade** — texto escuro em fundo claro.
10. **Redução com antialias** — se houve upscale, volta ao tamanho original com `INTER_AREA`.
11. **Métricas** — Laplaciano + Tenengrad no original e no resultado; percentual de melhoria.
12. **Histogramas** — contagem de pixels por intensidade 0–255 na original convertida para cinza e na imagem realçada.
13. **Resposta** — as duas imagens em PNG Base64, o filtro aplicado, os histogramas e o veredito do critério de 80%.

## Fluxo da requisição

```mermaid
flowchart TD
    A[Usuário escolhe a imagem e o filtro] --> B[JavaScript envia POST /api/process<br/>multipart campos image e filter]
    B --> C{Flask valida tipo e tamanho}
    C -->|inválido| D[JSON de erro 400/413]
    D --> E[Front exibe mensagem de falha]
    C -->|válido| F[Pillow + OpenCV decodificam a imagem]
    F --> G[Pipeline de realce em processing/enhancement.py]
    G --> H[Comparação de nitidez em processing/metrics.py]
    H --> I{Melhoria >= 80%?}
    I -->|sim| J[meets_criterion = true]
    I -->|não| K[meets_criterion = false]
    J --> L[JSON: original_image, enhanced_image, metrics, filter]
    K --> L
    L --> M[Front desenha as duas imagens, os histogramas de cinza e o painel de métricas]
```

### Contrato da API

`POST /api/process`

- **Entrada:** arquivo no campo `image` e id do filtro no campo `filter` (`documento_impresso`, `letra_cursiva`, `traco_fino` ou `texto_grande`).
- **Saída de sucesso:**

```json
{
  "filename": "documento.jpg",
  "filter": {
    "id": "documento_impresso",
    "label": "Documento impresso",
    "description": "Texto digitado, formulário ou comprovante. Saída em preto e branco."
  },
  "original_image": "<png em base64>",
  "enhanced_image": "<png em base64>",
  "metrics": {
    "original": { "laplacian": 0, "tenengrad": 0, "contraste_rms": 0, "nitidez": 0 },
    "enhanced": { "laplacian": 0, "tenengrad": 0, "contraste_rms": 0, "nitidez": 0 },
    "improvement_percent": 0,
    "threshold_percent": 80,
    "meets_criterion": true,
    "histograms": {
      "original": [0, 0, 0],
      "enhanced": [0, 0, 0]
    },
    "verdict": "O texto ficou pelo menos 80% mais nítido."
  }
}
```

A **nitidez combinada** é `0,6 × variância do Laplaciano + 0,4 × Tenengrad`. A melhoria percentual é:

```
melhoria = ((nitidez_realçada − nitidez_original) / nitidez_original) × 100
```

Se `melhoria >= 80`, o backend classifica o resultado como texto pelo menos 80% mais nítido.

`metrics.histograms.original` e `metrics.histograms.enhanced` são listas de 256 inteiros: o índice é a intensidade (0 = preto, 255 = branco) e o valor é a quantidade de pixels. A original usa a mesma conversão `BGR → cinza` do restante das métricas.

## Como executar o projeto

Requisitos: **Python 3.10 ou superior** e pip.

No PowerShell, dentro da pasta do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

No prompt do Windows (cmd):

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
python app.py
```

Abra o navegador em [http://127.0.0.1:5000](http://127.0.0.1:5000), escolha o filtro, envie a foto de um documento e aguarde o par original / realçado.

Para encerrar o servidor, use `Ctrl+C` no terminal.

### Problemas comuns

- **`Activate.ps1` bloqueado:** execute `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` ou use o `activate.bat` do cmd.
- **`python` não reconhecido:** tente `py -3` no lugar de `python`.
- **Foto muito grande:** o limite é 12 MB.

## Escopo da entrega

Página simples para rodar na máquina do grupo. Não há autenticação, banco de dados nem OCR: o objetivo é o **processamento da imagem** e a **comparação objetiva de nitidez**.
