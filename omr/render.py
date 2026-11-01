"""
Score Renderer — converte a lista notes[] do pipeline em um SVG de partitura
reconstruída.  Zero dependências externas: tudo é geometria pura.

Layout por sistema:
  • Uma pauta de 5 linhas (clave de Sol) para cada "faixa" de notas.
  • Notas ordenadas por position_x (= ordem temporal detectada).
  • Cada nota é desenhada como cabeça oval + haste + colchetes conforme flags.
  • Cores: semínima/mínima → preto  colcheia → azul  semicolcheia → laranja
           fusa → vermelho  notas fora de alcance → cinza tracejado
  • Label de pitch abaixo de cada cabeça.
  • Barra de compasso inferida a cada NOTE_PER_BAR notas (configurável).
"""

from __future__ import annotations

# ── Constantes de layout ───────────────────────────────────────────────────────
STAFF_SPACE   = 10          # px entre linhas da pauta (half-step = STAFF_SPACE/2)
HEAD_RX       = 5           # semi-eixo horizontal da cabeça de nota
HEAD_RY       = 4           # semi-eixo vertical
STEM_HEIGHT   = 30          # comprimento da haste em px
COL_STEP      = 22          # largura de cada "slot" de nota em px
LEFT_MARGIN   = 48          # margem esquerda (espaço para clave)
TOP_MARGIN    = 20          # margem acima da 1ª linha
BOTTOM_MARGIN = 40          # margem abaixo da linha do label
NOTES_PER_ROW = 20          # notas por sistema (linha de pauta)
LEDGER_EXTRA  = 3           # linhas suplementares renderizadas acima/abaixo

# ── Tabelas de posição (mesmas do pipeline, invertidas) ───────────────────────
# Índice 0 = linha de baixo da pauta; cada passo = meio espaço (diatônico)
_TREBLE = [
    "Mi4","Fá4","Sol4","Lá4","Si4","Dó5","Ré5","Mi5",
    "Fá5","Sol5","Lá5","Si5","Dó6","Ré6","Mi6",
]
_BASS = [
    "Sol2","Lá2","Si2","Dó3","Ré3","Mi3","Fá3","Sol3",
    "Lá3","Si3","Dó4","Ré4","Mi4",
]

# Lookup rápido: pitch_name → (table_index, is_bass)
_PITCH_INDEX: dict[str, tuple[int, bool]] = {}
for _i, _p in enumerate(_TREBLE):
    _PITCH_INDEX[_p] = (_i, False)
for _i, _p in enumerate(_BASS):
    if _p not in _PITCH_INDEX:          # Mi4 duplicado — treble tem prioridade
        _PITCH_INDEX[_p] = (_i, True)

# ── Cores por duração ─────────────────────────────────────────────────────────
_DURATION_COLOR = {
    "Semínima/Mínima": "#1a1a1a",
    "Colcheia":        "#1a6bb5",
    "Semicolcheia":    "#c47c00",
    "Fusa":            "#c0392b",
    "Semifusa":        "#7b2fa8",
}
_DEFAULT_COLOR = "#888888"


# ── Helpers SVG ───────────────────────────────────────────────────────────────

def _esc(s: str) -> str:
    """Escape minimal XML entities."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _staff_lines_svg(x0: int, x1: int, y_top: int) -> list[str]:
    """5 linhas horizontais da pauta."""
    lines = []
    for i in range(5):
        y = y_top + i * STAFF_SPACE
        lines.append(
            f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" '
            f'stroke="#333" stroke-width="0.8"/>'
        )
    return lines


def _clef_svg(x: int, y_top: int) -> list[str]:
    """Símbolo de clave de Sol simplificado como texto SVG."""
    cy = y_top + STAFF_SPACE * 3          # entre 2ª e 3ª linha de baixo
    return [
        f'<text x="{x}" y="{cy + 4}" font-family="serif" font-size="32" '
        f'fill="#333" dominant-baseline="middle">𝄞</text>'
    ]


def _pitch_to_y(pitch: str, y_bottom_line: int) -> int | None:
    """
    Converte nome de pitch para coordenada Y no SVG.
    y_bottom_line = Y da 1ª linha (linha de baixo) da pauta.
    """
    entry = _PITCH_INDEX.get(pitch)
    if entry is None:
        return None
    idx, _ = entry
    # idx 0 = linha de baixo → y_bottom_line
    # cada incremento de idx sobe meio espaço (STAFF_SPACE/2)
    return y_bottom_line - int(idx * STAFF_SPACE / 2)


def _note_svg(
    x: int,
    y: int,
    y_bottom_line: int,
    y_top_line: int,
    pitch: str,
    duration: str,
    flags: int,
    index: int,
) -> list[str]:
    """
    Retorna lista de strings SVG para uma nota: cabeça, haste, colchetes, label,
    linhas suplementares se necessário.
    """
    color = _DURATION_COLOR.get(duration, _DEFAULT_COLOR)
    parts: list[str] = []

    # ── Linhas suplementares ───────────────────────────────────────────────────
    # Abaixo da pauta
    below_start = y_bottom_line + STAFF_SPACE        # 1ª linha suplementar abaixo
    if y >= below_start:
        ledger_y = below_start
        while ledger_y <= y + 2:
            parts.append(
                f'<line x1="{x - HEAD_RX - 3}" y1="{ledger_y}" '
                f'x2="{x + HEAD_RX + 3}" y2="{ledger_y}" '
                f'stroke="#555" stroke-width="0.9"/>'
            )
            ledger_y += STAFF_SPACE
    # Acima da pauta
    above_start = y_top_line - STAFF_SPACE           # 1ª linha suplementar acima
    if y <= above_start:
        ledger_y = above_start
        while ledger_y >= y - 2:
            parts.append(
                f'<line x1="{x - HEAD_RX - 3}" y1="{ledger_y}" '
                f'x2="{x + HEAD_RX + 3}" y2="{ledger_y}" '
                f'stroke="#555" stroke-width="0.9"/>'
            )
            ledger_y -= STAFF_SPACE

    # ── Cabeça de nota ────────────────────────────────────────────────────────
    fill = color if flags == 0 else color      # sempre preenchida por ora
    parts.append(
        f'<ellipse cx="{x}" cy="{y}" rx="{HEAD_RX}" ry="{HEAD_RY}" '
        f'fill="{fill}" stroke="{color}" stroke-width="0.8" '
        f'transform="rotate(-15,{x},{y})"/>'
    )

    # ── Haste (para cima se nota abaixo da linha central, para baixo se acima) ─
    mid_line_y = y_bottom_line + STAFF_SPACE * 2    # 3ª linha = linha do meio
    if y >= mid_line_y:
        # haste para cima
        parts.append(
            f'<line x1="{x + HEAD_RX - 1}" y1="{y}" '
            f'x2="{x + HEAD_RX - 1}" y2="{y - STEM_HEIGHT}" '
            f'stroke="{color}" stroke-width="1.2"/>'
        )
        stem_tip_y = y - STEM_HEIGHT
        stem_x    = x + HEAD_RX - 1
        flag_dir  = -1         # colchetes crescem para baixo a partir do topo
    else:
        # haste para baixo
        parts.append(
            f'<line x1="{x - HEAD_RX + 1}" y1="{y}" '
            f'x2="{x - HEAD_RX + 1}" y2="{y + STEM_HEIGHT}" '
            f'stroke="{color}" stroke-width="1.2"/>'
        )
        stem_tip_y = y + STEM_HEIGHT
        stem_x    = x - HEAD_RX + 1
        flag_dir  = 1          # colchetes crescem para cima a partir da base

    # ── Colchetes (flags) ─────────────────────────────────────────────────────
    for f_i in range(flags):
        fy = stem_tip_y + flag_dir * f_i * 5
        fx2 = stem_x + 10
        fy2 = fy + flag_dir * 8
        parts.append(
            f'<path d="M{stem_x},{fy} Q{fx2},{fy} {fx2},{fy2}" '
            f'fill="none" stroke="{color}" stroke-width="1.2"/>'
        )

    # ── Label de pitch ────────────────────────────────────────────────────────
    label_y = y_bottom_line + STAFF_SPACE * 4 + 14  # abaixo da linha de baixo
    parts.append(
        f'<text x="{x}" y="{label_y}" text-anchor="middle" '
        f'font-family="system-ui,sans-serif" font-size="7" fill="{color}">'
        f'{_esc(pitch)}</text>'
    )

    # ── Número de ordem (pequeno, cinza) ──────────────────────────────────────
    parts.append(
        f'<text x="{x}" y="{y_bottom_line - STAFF_SPACE * 4 - 4}" '
        f'text-anchor="middle" font-family="system-ui,sans-serif" '
        f'font-size="6" fill="#aaa">{index + 1}</text>'
    )

    return parts


def _barline_svg(x: int, y_top: int) -> str:
    y_bot = y_top + STAFF_SPACE * 4
    return (
        f'<line x1="{x}" y1="{y_top}" x2="{x}" y2="{y_bot}" '
        f'stroke="#555" stroke-width="0.9"/>'
    )


# ── API pública ───────────────────────────────────────────────────────────────

def notes_to_svg(
    notes: list[dict],
    notes_per_bar: int = 4,
    notes_per_row: int = NOTES_PER_ROW,
) -> str:
    """
    Converte a lista notes[] do pipeline em SVG de partitura reconstruída.

    Parâmetros:
        notes        — lista de dicts com keys: pitch, duration, flags,
                       position_x, position_y
        notes_per_bar — quantas notas por compasso (default 4 = 4/4)
        notes_per_row — notas por sistema/linha (default 20)

    Retorna string SVG completa (sem DOCTYPE, pronto para <img src="data:…">).
    """
    if not notes:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="60">'
            '<text x="20" y="35" font-family="system-ui" font-size="14" fill="#888">'
            'Nenhuma nota detectada.</text></svg>'
        )

    # Divide em linhas (sistemas)
    rows: list[list[dict]] = []
    for i in range(0, len(notes), notes_per_row):
        rows.append(notes[i : i + notes_per_row])

    # Dimensões
    row_width  = LEFT_MARGIN + notes_per_row * COL_STEP + 20
    # Altura de um sistema: 4 espaços de pauta + margens + labels
    row_height = TOP_MARGIN + STAFF_SPACE * 4 + BOTTOM_MARGIN + 24
    total_h    = len(rows) * row_height + 20

    svgs: list[str] = []
    svgs.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{row_width}" height="{total_h}" '
        f'style="background:#fafafa;font-family:system-ui,sans-serif;">'
    )

    # ── Legenda de cores ───────────────────────────────────────────────────────
    legend_items = [
        ("Semínima/Mínima", _DURATION_COLOR["Semínima/Mínima"]),
        ("Colcheia",        _DURATION_COLOR["Colcheia"]),
        ("Semicolcheia",    _DURATION_COLOR["Semicolcheia"]),
        ("Fusa",            _DURATION_COLOR["Fusa"]),
    ]
    lx = LEFT_MARGIN
    ly = 12
    svgs.append(
        f'<text x="{lx - 40}" y="{ly}" font-size="8" fill="#555">Duração:</text>'
    )
    for label, col in legend_items:
        svgs.append(
            f'<rect x="{lx}" y="{ly - 7}" width="8" height="8" fill="{col}"/>'
            f'<text x="{lx + 11}" y="{ly}" font-size="8" fill="{col}">{label}</text>'
        )
        lx += len(label) * 5 + 24

    # ── Sistemas ───────────────────────────────────────────────────────────────
    for row_idx, row_notes in enumerate(rows):
        y_offset   = 16 + row_idx * row_height    # deslocamento vertical do sistema
        y_top_line = y_offset + TOP_MARGIN                       # 5ª linha (topo)
        y_bot_line = y_top_line + STAFF_SPACE * 4               # 1ª linha (base)

        actual_width = LEFT_MARGIN + len(row_notes) * COL_STEP + 10

        # Linhas da pauta
        svgs.extend(_staff_lines_svg(LEFT_MARGIN - 4, actual_width, y_top_line))

        # Clave de Sol
        svgs.extend(_clef_svg(4, y_top_line))

        # Número do sistema
        svgs.append(
            f'<text x="4" y="{y_top_line - 4}" font-size="8" fill="#aaa">'
            f'Sistema {row_idx + 1}</text>'
        )

        # Notas
        global_offset = row_idx * notes_per_row
        for local_i, note in enumerate(row_notes):
            global_i = global_offset + local_i
            x = LEFT_MARGIN + local_i * COL_STEP

            # Barra de compasso antes da nota que inicia um compasso (exceto a 1ª)
            if global_i > 0 and global_i % notes_per_bar == 0:
                svgs.append(_barline_svg(x - COL_STEP // 2, y_top_line))

            y = _pitch_to_y(note.get("pitch", ""), y_bot_line)
            if y is None:
                # Nota fora de alcance — desenha X cinza
                svgs.append(
                    f'<text x="{x}" y="{y_bot_line - STAFF_SPACE * 2}" '
                    f'text-anchor="middle" font-size="10" fill="#ccc">×</text>'
                )
                continue

            svgs.extend(
                _note_svg(
                    x=x,
                    y=y,
                    y_bottom_line=y_bot_line,
                    y_top_line=y_top_line,
                    pitch=note.get("pitch", ""),
                    duration=note.get("duration", ""),
                    flags=note.get("flags", 0),
                    index=global_i,
                )
            )

        # Linha de fechamento do sistema
        svgs.append(_barline_svg(actual_width, y_top_line))

    svgs.append("</svg>")
    return "\n".join(svgs)
