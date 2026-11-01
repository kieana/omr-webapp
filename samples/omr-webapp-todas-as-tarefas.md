# OMR WebApp — Histórico Completo de Tarefas

> Exportado em 01/11/2026 · Todas as sessões IBM Bob CLI (Termux/Android → Windows 10)

---

## Índice

1. [Tarefa 1 — Criação inicial do webapp (73064a)](#tarefa-1)
2. [Tarefa 2 — Complemento com pipeline.py e app.js (9dad2c)](#tarefa-2)
3. [Tarefa 3 — Exportação MIDI e MusicXML via music21 (cc45d1)](#tarefa-3)
4. [Tarefa 4 — Como usar o webapp (5612bd)](#tarefa-4)
5. [Tarefa 5 — Sessão de teste inicial (b10ad8)](#tarefa-5)
6. [Tarefa 6 — Correção da "acuidade" do OMR (0e384a) — SESSÃO PRINCIPAL](#tarefa-6)
7. [Sessão Windows 10 — 01/11/2026](#sessao-windows)

---

## Tarefa 1 — Criação inicial do webapp {#tarefa-1}

**ID:** `73064a6b561ec4a64332fb8805d2771c`
**Data:** 2026-10-31 · **Status:** error (interrompida por falta de armazenamento)
**Dispositivo:** Termux / Moto E22

### Prompt
```
cat req.txt | bob run "Analise os requisitos deste arquivo e crie o webapp"
```

### O que foi feito
- Leu `req.txt` com os requisitos do sistema OMR
- Planejou arquitetura: `app.py` (Flask), `omr/pipeline.py`, `templates/index.html`, `static/style.css`, `requirements.txt`
- Criou estrutura de diretórios
- Escreveu `omr/__init__.py`, versão inicial de `omr/pipeline.py`, `app.py`, `requirements.txt`
- Escreveu `templates/index.html` com interface de upload
- **Parou antes de criar `static/app.js` e `static/style.css`** (erro/interrupção)

### Arquitetura definida
```
omr-webapp/
├── app.py              ← Flask backend, endpoint /analyze POST
├── omr/pipeline.py     ← Pipeline determinístico OMR (sem IA)
├── templates/index.html
├── static/style.css
└── requirements.txt    ← flask, opencv-python-headless, numpy
```

### Pipeline inicial (req.txt → código)
| Etapa | Técnica |
|---|---|
| Binarização | `adaptiveThreshold` |
| Alinhamento | Transformada de Hough |
| Remoção de pauta | Morfologia Matemática |
| Detecção de duração | Projeção de perfil vertical (conta colchetes) |
| Detecção de altura | Projeção de perfil horizontal (5 linhas) |
| Identificação de nota | Clave de Sol como referência geométrica |

---

## Tarefa 2 — Complemento com pipeline.py e app.js {#tarefa-2}

**ID:** `9dad2c137bfea8ba3dfdeb7c87c91914`
**Data:** 2026-10-31 · **Status:** running (continuação da Tarefa 1)
**Dispositivo:** Termux / Moto E22

### Prompt
```
Por favor, leia o arquivo req.txt que está na pasta home e conclua o webapp
criando os arquivos omr/pipeline.py e static/app.js que faltaram devido ao erro anterior.
```

### O que foi feito
- Leu `req.txt` e o estado atual do projeto
- Constatou que `omr/pipeline.py` já existia e estava completo
- Criou `static/style.css` (tema escuro, layout responsivo)
- Criou `static/app.js` (lógica de upload, drag-and-drop, fetch para /analyze, renderização de resultados)
- Validou sintaxe com `python -c "import app; print('OK')"`

### Resultado
Webapp funcional com:
- Upload drag-and-drop de imagem
- Chamada ao `/analyze` via fetch
- Exibição da imagem anotada (base64)
- Tabela de notas detectadas

---

## Tarefa 3 — Exportação MIDI e MusicXML via music21 {#tarefa-3}

**ID:** `cc45d10e8d0fde72ef581873cff0b12a`
**Data:** 2026-10-31 · **Status:** active
**Dispositivo:** Termux / Moto E22

### Prompt
```
Complemente o app.py com a capacidade de exportar MIDI e XMLMusic via music21
```

### O que foi feito

**Novos arquivos:**
- `omr/export.py` — converte lista `notes[]` do pipeline para `music21.stream.Score` e exporta MIDI/MusicXML bytes

**Arquivos modificados:**
- `requirements.txt` — adicionado `music21>=9.1`
- `app.py` — novas rotas `/export/midi` e `/export/musicxml`
- `templates/index.html` — botões de exportação
- `static/app.js` — lógica de export (reutiliza notas do último `/analyze` em cache)
- `static/style.css` — estilos dos botões de exportação

### Mapeamento implementado em export.py
```python
_PITCH_MAP = {
    "Dó": "C", "Ré": "D", "Mi": "E", "Fá": "F",
    "Sol": "G", "Lá": "A", "Si": "B",
}
_DURATION_MAP = { 0: 1.0, 1: 0.5, 2: 0.25, 3: 0.125, 4: 0.0625 }
# flags=0 → semínima, flags=1 → colcheia, flags=2 → semicolcheia...
```

### Fluxo de exportação
```
/analyze → notes[] cacheado no browser
  ↓
POST /export/midi  { "notes": [...] }  →  partitura.mid
POST /export/musicxml { "notes": [...] } →  partitura.musicxml
```

---

## Tarefa 4 — Como usar o webapp {#tarefa-4}

**ID:** `5612bdb6acd62a635b4020fb90f3d8ad`
**Data:** 2026-10-31 · **Status:** active
**Dispositivo:** Termux / Moto E22

### Prompt
```
baseado no req.txt e logs das sessoes anteriores, todo desenvolvimento foi concluido, como usar?
```

### Guia de uso produzido

**Passo 1 — Instalar dependências**
```bash
cd ~/omr-webapp
pip install -r requirements.txt
```

**Passo 2 — Iniciar servidor**
```bash
python app.py
# Sobe em http://0.0.0.0:5000
```

**Passo 3 — Usar no browser**
```
http://localhost:5000
# ou pela IP local: http://192.168.x.x:5000
```

**Fluxo:** Upload foto da partitura → Analisar → ver notas detectadas + imagem anotada → Exportar MIDI/XML

**Passo 4 — API curl**
```bash
curl -X POST http://localhost:5000/analyze \
  -F "image=@/caminho/para/partitura.jpg"
```

---

## Tarefa 5 — Sessão de teste inicial {#tarefa-5}

**ID:** `b10ad865e2bc221aea3a792e22e35757`
**Data:** 2026-10-30 · **Status:** error
**Dispositivo:** Termux / Moto E22

### Prompt
```
oi
```
(Teste de conexão — sessão encerrada manualmente)

---

## Tarefa 6 — Correção da "acuidade" do OMR {#tarefa-6}

**ID:** `0e384a5b1ba40eda7acb08ed7d07e616`
**Data:** 2026-11-01 · **Status:** active
**Dispositivo:** Termux / Moto E22 → Windows 10

### Prompt
```
Como corrigir a "acuidade" visual do OMR? Compare os arquivos jpg2mid.*
das dezenas de notas, a maioria virou pausas...
```

### Diagnóstico — 5 bugs simultâneos

| # | Bug | Efeito |
|---|---|---|
| 1 | `_map_staff_lines` retornava `staff_y[:5]` — apenas a **1ª pauta** | Notas dos sistemas 2–4 sem mapeamento → "Desconhecida" → pausa |
| 2 | Detecção baseada em **haste** (`kernel (1,20)`) | Só encontrava 3–10 hastes; notas brancas invisíveis |
| 3 | Kernel `(1,20)` a 18px de espaçamento = 1,1 espaços | Barras de compasso (h=440px!) passavam como "hastes" |
| 4 | Cabeça de nota estimada como `y + h` da haste | Coordenada errada → pitch fora da gama |
| 5 | Sem tabela de clave de fá | Staves ímpares usavam tabela treble → pitches errados |

### Processo de diagnóstico (nas sessões do Termux)
- Análise de histogramas de pixels com `np.sum(img, axis=1)`
- Comparação de coordenadas Y de notas detectadas vs. posições reais na partitura
- Identificação dos padrões de falso positivo: símbolos de acorde (letras "D", "G") reconhecidos como cabeças de nota por serem blobs ovais
- Medição de espaçamento real: 18.5px entre linhas
- Iteração de parâmetros: margem acima da pauta de 3 espaços → 2.5 → 2.0 espaços

### Correções implementadas em `omr/pipeline.py`

1. **`_detect_staves()`** — nova função: detecta **todas as pautas da página** por clustering do perfil de projeção horizontal (gap > 30px separa pautas)
2. **`_detect_note_heads()`** — estratégia por **erosão horizontal**: erode com kernel `(min_head_w, 1)` — mata hastes (1-2px) mas mantém cabeças (≥7px); dilata de volta e faz interseção
3. **`_assign_staff()`** — associa cabeça à pauta mais próxima com margem de **2.0 espaços** (≈2 linhas ledger), excluindo símbolos de acorde
4. **`_note_pitch()`** + **`_NOTES_BASS`** — tabela separada para clave de fá; staves índice ímpar usam-na automaticamente
5. **`_find_note_x_start()`** — detecta margem esquerda por densidade de coluna (exclui clave + armadura + fórmula de compasso)
6. **`_dedup_note_heads()`** — remove cabeças duplicadas dentro de 8×8 px

### Tabelas de notas implementadas
```python
# Clave de Sol — linha de baixo = E4
_NOTES_TREBLE = ["Mi4","Fá4","Sol4","Lá4","Si4","Dó5","Ré5","Mi5",
                 "Fá5","Sol5","Lá5","Si5","Dó6","Ré6","Mi6"]

# Clave de Fá — linha de baixo = G2
_NOTES_BASS   = ["Sol2","Lá2","Si2","Dó3","Ré3","Mi3","Fá3","Sol3",
                 "Lá3","Si3","Dó4","Ré4","Mi4"]
```

### Resultado antes × depois

| Métrica | Antes | Depois |
|---|---|---|
| Pautas detectadas | 1 de 8 | **8 de 8** |
| Notas detectadas | ~3 | **221** |
| Pausas no MusicXML | ~90% | **0%** |
| Pitches fora de gama | maioria | **0** |
| Clave de fá | ✗ | **✓** |

### Recursos do dispositivo (medidos)
| Recurso | Valor |
|---|---|
| CPU | ARMv7 quad-core (32-bit) |
| RAM disponível | ~640 MB |
| Armazenamento livre | 1.3 GB (95% cheio) ⚠️ |
| Tempo de análise | **~4 segundos** por imagem |

---

## Sessão Windows 10 — 01/11/2026 {#sessao-windows}

**Contexto:** Projeto transferido do Termux para o Windows 10 e sincronizado com GitHub.
**Repositório:** https://github.com/kieana/omr-webapp

### Commit 1 — `docs: add bilingual README (PT/EN)`
- Criado `README.md` completo em 🇧🇷 PT e 🇺🇸 EN
- História do projeto, pipeline técnico, estrutura, instalação, API, dependências, limitações

### Commit 2 — `feat: accept PDF and all image formats — 64 MB limit`

| Arquivo | Mudança |
|---|---|
| `requirements.txt` | `pymupdf >= 1.24` adicionado |
| `app.py` | Limite 16 MB → 64 MB; `_file_to_image_bytes()` converte PDF (1ª pág, 200 DPI) antes do pipeline |
| `templates/index.html` | `accept` expandido; hint: PDF · PNG · JPG · WEBP · BMP · TIFF · GIF e mais |
| `static/app.js` | Validação por MIME + extensão; preview de PDF mostra nome do arquivo |
| `README.md` | PT/EN atualizados |

### Commit 3 — `feat: reconstructed score SVG renderer`

**Novo arquivo: `omr/render.py`** — motor SVG puro (zero dependências):

| O que desenha | Como |
|---|---|
| 5 linhas da pauta por sistema | geometria direta |
| Clave de Sol (𝄞) | caractere Unicode |
| Cabeça de nota oval inclinada | `<ellipse rotate(-15)>` |
| Haste (direção automática por altura) | `<line>` |
| Colchetes por `flags` | curva quadrática `<path Q>` |
| Linhas suplementares | detectadas automaticamente |
| Label de pitch | `<text>` 7px |
| Número de ordem | para rastrear na tabela |
| Barras de compasso | configurável (3/4, 4/4…) |
| Legenda de cores | semínima=preto · colcheia=azul · semicolcheia=laranja · fusa=vermelho |

**Novas rotas:**
- `GET /render` — POST JSON `{notes, notes_per_bar}` → SVG
- `/analyze` — agora embute `score_svg` na resposta (sem round-trip extra)

**Interface:** nova seção "Partitura Reconstruída" com controle de notas/compasso e botão de download SVG.

### Commit 4 — `feat: step-by-step visual debug page`

**Novo arquivo: `templates/debug.html`** — página de diagnóstico visual.

**`omr/pipeline.py` — modo debug:**
- `analyze_image_debug()` chama `_run_pipeline(debug=True)`
- Captura PNG anotado em cada etapa via `snap(label, description, img)`

**As 9 etapas fotografadas:**

| # | Etapa | Marcação visual |
|---|---|---|
| 1 | Original (grayscale) | — |
| 2 | Alinhamento (deskew) | — |
| 3 | Binarização | preto e branco puro |
| 4 | Pautas detectadas | linhas **verdes** |
| 5 | Linhas removidas | só figuras musicais |
| 6 | Margem esquerda | linha **vermelha** vertical |
| 7 | Candidatos pré-filtro | círculos **laranjas** |
| 8 | Após deduplicação | círculos **azuis** |
| 9 | Notas aceitas | 🟢verde=aceita · ×cinza=margem · ×vermelho=sem pauta · ▲amarelo=pitch fora |

**Novas rotas:**
- `GET /debug-view` — serve `debug.html`
- `POST /debug` — mesma imagem do `/analyze`, retorna `{result, steps[]}`

**Link adicionado no header do `index.html`:** `🔬 Diagnóstico do Pipeline`

---

## Estado atual do repositório

```
omr-webapp/  (github.com/kieana/omr-webapp)
├── app.py               # Flask — /, /analyze, /render, /debug, /debug-view,
│                        #         /export/midi, /export/musicxml
├── omr/
│   ├── pipeline.py      # Pipeline CV + modo debug (9 etapas fotografadas)
│   ├── render.py        # Gerador de SVG de partitura reconstruída
│   └── export.py        # solfejo PT → music21 → MIDI/MusicXML
├── templates/
│   ├── index.html       # Interface principal
│   └── debug.html       # Página de diagnóstico visual passo a passo
├── static/
│   ├── app.js
│   └── style.css
└── requirements.txt     # flask, opencv-python-headless, numpy, music21, pymupdf
```

### Dependências
| Pacote | Versão mín. | Função |
|---|---|---|
| `flask` | 3.0 | Servidor web |
| `opencv-python-headless` | 4.9 | Visão computacional |
| `numpy` | 1.26 | Operações matriciais |
| `music21` | 9.1 | Exportação MIDI / MusicXML |
| `pymupdf` | 1.24 | Conversão PDF → imagem |

### Rotas da API
| Rota | Método | Descrição |
|---|---|---|
| `/` | GET | Interface principal |
| `/debug-view` | GET | Página de diagnóstico |
| `/analyze` | POST | Analisa imagem/PDF → JSON (notas + SVG + imagem anotada) |
| `/render` | POST | Re-renderiza SVG com notas/compasso configuráveis |
| `/debug` | POST | Análise completa com 9 etapas fotografadas |
| `/export/midi` | POST | Notas → `.mid` |
| `/export/musicxml` | POST | Notas → `.musicxml` |

---

## Próximos passos identificados

1. **Teste com pauta simples** (2 pautas, ~5 notas) via `/debug-view` — observar etapas 4 e 9
2. **Ajuste fino de parâmetros** com base no diagnóstico visual:
   - Espaçamento de detecção de cabeças
   - Margem esquerda (x_cutoff)
   - Limiar de filtro de proporção (aspect ratio)
3. **Detecção de acidentes** (sustenidos/bemóis individuais)
4. **Diferenciação de mínimas/semibreves** de semínimas (via preenchimento da cabeça)
5. **Suporte a múltiplas páginas** de PDF
6. **Comparador MIDI** — diff entre MIDI produzido e MIDI de referência (métrica de precisão/recall por nota)
7. **Integração do `compositor-midi-v2.html`** (Claude) como editor/player no browser — permitir corrigir notas erradas manualmente

---

*Gerado pelo IBM Bob · github.com/kieana/omr-webapp*
