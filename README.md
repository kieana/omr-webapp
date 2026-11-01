# 🎵 OMR WebApp

> **Optical Music Recognition** — Da foto de uma partitura a um arquivo MIDI ou MusicXML, com visão computacional clássica e zero dependência de IA em tempo de inferência.

---

## 🇧🇷 Português

### A história desta ferramenta

Este projeto nasceu em um **Motorola Moto E22**, rodando **Termux no Android**, guiado pela CLI do **IBM Bob**. Sem GPU, sem servidor, sem IDE — apenas um terminal de bolso e muita determinação. Sessão a sessão, a ferramenta foi evoluindo: detecção de pautas, remoção de linhas, mapeamento de notas, exportação MIDI/MusicXML, correção de falsos positivos (símbolos de acorde confundidos com cabeças de nota, claves reconhecidas como notas…). Cada bug foi diagnosticado com print, histogramas de pixels e visão computacional pura. O código que você lê aqui é o resultado dessa jornada.

### O que faz

Dado um **PDF ou imagem de partitura** (até 64 MB), o OMR WebApp:

1. **Binariza** a imagem com limiarização adaptativa (lida com sombras e iluminação irregular)
2. **Detecta as pautas** via Transformada de Hough + agrupamento por sistema de 5 linhas
3. **Remove as linhas** morfologicamente, deixando apenas as figuras musicais
4. **Detecta as cabeças de nota** por erosão horizontal + filtro de proporção (exclui hastes, barras e símbolos da armadura)
5. **Mapeia a altura** de cada nota para solfejo português (Dó, Ré, Mi… Dó6) usando tabelas de clave de Sol e clave de Fá
6. **Detecta duração** aproximada pelo número de colchetes/hastes (`flags`)
7. **Exporta** para **MIDI** (`.mid`) e **MusicXML** (`.musicxml`) via `music21`

### Estrutura

```
omr-webapp/
├── app.py               # Servidor Flask — rotas /analyze, /export/midi, /export/musicxml
├── omr/
│   ├── pipeline.py      # Pipeline completo de visão computacional
│   └── export.py        # Conversão solfejo PT → music21 → MIDI/MusicXML
├── templates/
│   └── index.html       # Interface web single-page
├── static/
│   ├── app.js           # Lógica do cliente
│   └── style.css        # Estilos
└── requirements.txt
```

### Instalação

```bash
# Clone o repositório
git clone https://github.com/kieana/omr-webapp.git
cd omr-webapp

# Crie um ambiente virtual (recomendado)
python -m venv .venv
source .venv/bin/activate        # Linux/macOS/Termux
.venv\Scripts\activate           # Windows

# Instale as dependências
pip install -r requirements.txt

# Inicie o servidor
python app.py
```

Acesse **http://localhost:5000** no navegador.

> **No Termux (Android):** as dependências são instaladas automaticamente na primeira execução de `python app.py`.

### Dependências

| Pacote | Função |
|---|---|
| `flask >= 3.0` | Servidor web |
| `opencv-python-headless >= 4.9` | Visão computacional |
| `numpy >= 1.26` | Operações matriciais |
| `music21 >= 9.1` | Exportação MIDI / MusicXML |
| `pymupdf >= 1.24` | Conversão PDF → imagem |

### API

| Rota | Método | Descrição |
|---|---|---|
| `/` | `GET` | Interface web |
| `/analyze` | `POST` | Analisa PDF ou imagem → JSON com notas, pautas e imagem anotada |
| `/export/midi` | `POST` | Converte notas detectadas → arquivo `.mid` |
| `/export/musicxml` | `POST` | Converte notas detectadas → arquivo `.musicxml` |

### Limitações conhecidas

- PDFs de múltiplas páginas: apenas a **primeira página** é analisada
- Funciona melhor com partituras corais em **Dó maior / Ré maior** com pautas bem definidas
- Duração das notas é aproximada (baseada em colchetes; mínimas e semibreves não são diferenciadas de semínimas sem informação de feixe)
- Acidentes ocidentais (sustenidos/bemóis individuais) ainda não são detectados

---

## 🇺🇸 English

### The story behind this tool

This project was born on a **Motorola Moto E22**, running **Termux on Android**, guided by the **IBM Bob** CLI. No GPU, no server, no IDE — just a pocket terminal and a lot of determination. Session by session the tool evolved: staff detection, line removal, note mapping, MIDI/MusicXML export, false-positive correction (chord symbols mistaken for noteheads, clef symbols picked up as notes…). Every bug was diagnosed with print statements, pixel histograms, and pure computer vision. The code you read here is the result of that journey.

### What it does

Given a **PDF or image of a music score** (up to 64 MB), OMR WebApp:

1. **Binarizes** the image with adaptive thresholding (handles shadows and uneven lighting)
2. **Detects staves** via Hough Transform + 5-line system grouping
3. **Removes staff lines** morphologically, leaving only musical figures
4. **Detects noteheads** via horizontal erosion + aspect-ratio filter (excludes stems, beams, and key-signature symbols)
5. **Maps each note's pitch** to Portuguese solfège (Dó, Ré, Mi… Dó6) using treble-clef and bass-clef lookup tables
6. **Estimates duration** from the number of flags/beams
7. **Exports** to **MIDI** (`.mid`) and **MusicXML** (`.musicxml`) via `music21`

### Project structure

```
omr-webapp/
├── app.py               # Flask server — routes /analyze, /export/midi, /export/musicxml
├── omr/
│   ├── pipeline.py      # Full computer-vision pipeline
│   └── export.py        # Portuguese solfège → music21 → MIDI/MusicXML
├── templates/
│   └── index.html       # Single-page web UI
├── static/
│   ├── app.js           # Client-side logic
│   └── style.css        # Styles
└── requirements.txt
```

### Installation

```bash
# Clone the repository
git clone https://github.com/kieana/omr-webapp.git
cd omr-webapp

# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate        # Linux / macOS / Termux
.venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Start the server
python app.py
```

Open **http://localhost:5000** in your browser.

> **On Termux (Android):** dependencies are installed automatically on the first run of `python app.py`.

### Dependencies

| Package | Purpose |
|---|---|
| `flask >= 3.0` | Web server |
| `opencv-python-headless >= 4.9` | Computer vision |
| `numpy >= 1.26` | Matrix operations |
| `music21 >= 9.1` | MIDI / MusicXML export |
| `pymupdf >= 1.24` | PDF → image conversion |

### API

| Route | Method | Description |
|---|---|---|
| `/` | `GET` | Web UI |
| `/analyze` | `POST` | Analyze PDF or image → JSON with notes, staves, and annotated image |
| `/export/midi` | `POST` | Convert detected notes → `.mid` file |
| `/export/musicxml` | `POST` | Convert detected notes → `.musicxml` file |

### Known limitations

- Multi-page PDFs: only the **first page** is analysed
- Works best with choral scores in **C major / D major** with well-defined staves
- Note duration is approximate (flag-based; half notes and whole notes are not distinguished from quarter notes without beam information)
- Individual accidentals (sharps/flats) are not yet detected

---

## 🛠️ Tech stack

```
Python 3.11+  ·  Flask  ·  OpenCV  ·  NumPy  ·  music21
Born on: Termux / Android (Moto E22)
Guided by: IBM Bob CLI
```

## 📄 License

MIT — use freely, give credit if you share.
