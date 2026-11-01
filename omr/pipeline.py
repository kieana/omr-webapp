"""
Deterministic OMR Pipeline
Based on classical computer vision techniques:
  - Hough Transform for staff alignment
  - Morphological operations for staff removal
  - Note-head blob detection (not stem-only) for robust recall
  - Multi-system staff detection (full page)
  - Per-staff pitch mapping (treble + bass clef)
"""

import cv2
import numpy as np


# ── Pitch tables — index 0 = bottom staff line, each step = one diatonic half-space ──
# Treble clef: bottom line = E4
_NOTES_TREBLE = [
    "Mi4",  # 0  — E4 (1st line)
    "Fá4",  # 1  — F4
    "Sol4", # 2  — G4 (2nd line)
    "Lá4",  # 3  — A4
    "Si4",  # 4  — B4 (3rd line)
    "Dó5",  # 5  — C5
    "Ré5",  # 6  — D5 (4th line)
    "Mi5",  # 7  — E5
    "Fá5",  # 8  — F5 (5th/top line)
    "Sol5", # 9  — G5
    "Lá5",  # 10 — A5 (1st ledger above)
    "Si5",  # 11 — B5
    "Dó6",  # 12 — C6 (2nd ledger above)
    "Ré6",  # 13 — D6
    "Mi6",  # 14 — E6 (3rd ledger above)
]

# Bass clef: bottom line = G2
_NOTES_BASS = [
    "Sol2", # 0  — G2 (1st line)
    "Lá2",  # 1  — A2
    "Si2",  # 2  — B2 (2nd line)
    "Dó3",  # 3  — C3
    "Ré3",  # 4  — D3 (3rd line)
    "Mi3",  # 5  — E3
    "Fá3",  # 6  — F3 (4th line)
    "Sol3", # 7  — G3
    "Lá3",  # 8  — A3 (5th/top line)
    "Si3",  # 9  — B3
    "Dó4",  # 10 — C4 (middle C, 1st ledger above)
    "Ré4",  # 11 — D4
    "Mi4",  # 12 — E4 (2nd ledger above)
]


def _binarize(img_gray: np.ndarray) -> np.ndarray:
    """Adaptive threshold — handles shadows and uneven lighting."""
    return cv2.adaptiveThreshold(
        img_gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        15, 8
    )


def _deskew(img_gray: np.ndarray) -> np.ndarray:
    """Use Hough Line Transform to detect staff angle and rotate to horizontal."""
    edges = cv2.Canny(img_gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)
    if lines is None:
        return img_gray

    angles = []
    for rho, theta in lines[:, 0]:
        angle_deg = np.degrees(theta) - 90
        if abs(angle_deg) < 10:
            angles.append(angle_deg)

    if not angles:
        return img_gray

    median_angle = float(np.median(angles))
    if abs(median_angle) < 0.3:
        return img_gray

    h, w = img_gray.shape
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    return cv2.warpAffine(
        img_gray, M, (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )


def _detect_staves(img_bin: np.ndarray) -> list[list[int]]:
    """
    Detect all staff groups in the image.

    Returns a list of staves, each a list of exactly 5 Y-coordinates
    (one per staff line), sorted top-to-bottom.

    Strategy:
      1. Horizontal projection profile to find dense rows (staff lines).
      2. Cluster consecutive rows within 4px into single line candidates.
      3. Group line candidates: gaps > 30px separate distinct staves.
      4. Keep only groups with exactly 5 members.
    """
    profile = np.sum(img_bin, axis=1).astype(np.float32)
    max_val = float(np.max(profile))
    if max_val == 0:
        return []

    threshold = max_val * 0.5

    # Cluster rows that exceed threshold into representative Y positions
    raw_ys: list[int] = []
    for y, val in enumerate(profile):
        if val > threshold:
            if not raw_ys or y - raw_ys[-1] > 4:
                raw_ys.append(y)

    if not raw_ys:
        return []

    # Group into staves: a gap > 30px starts a new staff
    staves: list[list[int]] = []
    current: list[int] = [raw_ys[0]]
    for y in raw_ys[1:]:
        if y - current[-1] > 30:
            staves.append(current)
            current = [y]
        else:
            current.append(y)
    staves.append(current)

    # Keep only valid 5-line staves
    return [s for s in staves if len(s) == 5]


def _remove_staff_lines(img_bin: np.ndarray) -> np.ndarray:
    """
    Remove horizontal staff lines via morphological opening.
    Returns the image with staff lines subtracted.
    """
    kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    staff_mask = cv2.morphologyEx(img_bin, cv2.MORPH_OPEN, kernel_h)
    return cv2.subtract(img_bin, staff_mask)


def _estimate_spacing(staves: list[list[int]]) -> float:
    """Compute median inter-line spacing across all detected staves."""
    spacings = []
    for staff in staves:
        sp = (staff[4] - staff[0]) / 4.0
        if sp > 0:
            spacings.append(sp)
    return float(np.median(spacings)) if spacings else 18.0


def _detect_note_heads(notes_only: np.ndarray, spacing: float) -> list[tuple[int, int, int, int]]:
    """
    Detect note heads using a horizontal-erosion isolation strategy.

    Approach:
      1. Horizontal erosion: kills narrow stems (1-2px wide) while keeping
         note heads (≥ 0.4× spacing wide).  Dilate back and intersect with
         the original to restore note-head shapes without re-introducing stems.
      2. Filter resulting contours by size and aspect ratio.

    Returns list of (cx, cy, w, h) tuples for each candidate note head,
    where cx/cy are the center coordinates.
    """
    min_head_w = max(6, int(spacing * 0.40))   # narrow enough to survive erosion

    # Horizontal erosion kills stems; dilate back restores note heads
    kernel_erode_h = cv2.getStructuringElement(cv2.MORPH_RECT, (min_head_w, 1))
    heads_eroded = cv2.erode(notes_only, kernel_erode_h)

    kernel_dilate = cv2.getStructuringElement(cv2.MORPH_RECT, (min_head_w + 4, 3))
    heads_dilated = cv2.dilate(heads_eroded, kernel_dilate)

    # Intersect with original so we don't expand beyond real ink
    heads_img = cv2.bitwise_and(notes_only, heads_dilated)

    contours, _ = cv2.findContours(heads_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Note head size bounds (generous to handle engraving variation):
    # width  ≈ 0.45–2.0 × spacing,  height ≈ 0.25–1.4 × spacing
    min_w = max(6, int(spacing * 0.45))
    max_w = max(35, int(spacing * 2.0))
    min_h = max(4, int(spacing * 0.25))
    max_h = max(22, int(spacing * 1.4))
    min_area = max(25, int(spacing * spacing * 0.08))

    candidates = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        area = cv2.contourArea(c)
        ar = w / h if h > 0 else 99.0
        if (min_w <= w <= max_w and
                min_h <= h <= max_h and
                0.35 <= ar <= 5.0 and
                area >= min_area):
            cx = x + w // 2
            cy = y + h // 2
            candidates.append((cx, cy, w, h))

    return candidates


def _find_note_x_start(
    notes_only: np.ndarray, staves: list[list[int]], spacing: float
) -> int:
    """
    Estimate the X position where actual note content begins (i.e. after the
    clef, key signature, and time signature).

    We scan the column-density profile of the first treble staff zone and look
    for the first gap (≥ 8 consecutive low-density columns) that occurs after
    x = 80. The note content starts immediately after that gap.

    Falls back to 10× spacing if no gap is detected.
    """
    if not staves:
        return int(spacing * 10)

    # Use the first available treble staff (even index 0)
    staff = staves[0]
    margin_px = int(spacing * 1.5)
    y_top = max(0, staff[0] - margin_px)
    y_bot = min(notes_only.shape[0], staff[4] + margin_px)

    roi = notes_only[y_top:y_bot, 80:min(notes_only.shape[1], 450)]
    if roi.size == 0:
        return int(spacing * 10)

    col_sums = np.sum(roi, axis=0).astype(np.float32)
    local_max = float(np.max(col_sums))
    if local_max == 0:
        return int(spacing * 10)

    gap_threshold = local_max * 0.15
    gap_run = 0
    for x in range(len(col_sums)):
        if col_sums[x] < gap_threshold:
            gap_run += 1
            if gap_run >= 8 and (x + 80) > 150:
                # x+80 is absolute position; the gap ends here, notes follow
                return x + 80 + gap_run
        else:
            gap_run = 0

    return int(spacing * 10)


def _dedup_note_heads(
    heads: list[tuple[int, int, int, int]],
    dx: int = 8,
    dy: int = 8,
) -> list[tuple[int, int, int, int]]:
    """
    Remove duplicate note-head detections closer than (dx, dy) pixels.
    When two candidates are within the threshold, keep the one with the
    larger bounding box (more evidence for a real note head).
    """
    if not heads:
        return heads

    # Sort by cx so we only compare nearby candidates
    sorted_heads = sorted(heads, key=lambda t: t[0])
    kept: list[tuple[int, int, int, int]] = []
    used = [False] * len(sorted_heads)

    for i, (cx_i, cy_i, w_i, h_i) in enumerate(sorted_heads):
        if used[i]:
            continue
        # Collect all candidates within the dedup window
        cluster = [(cx_i, cy_i, w_i, h_i)]
        for j in range(i + 1, len(sorted_heads)):
            cx_j, cy_j, w_j, h_j = sorted_heads[j]
            if cx_j - cx_i > dx:
                break  # sorted by x — no more candidates in range
            if abs(cy_j - cy_i) <= dy:
                cluster.append((cx_j, cy_j, w_j, h_j))
                used[j] = True
        # Keep the candidate with the largest area
        best = max(cluster, key=lambda t: t[2] * t[3])
        kept.append(best)

    return kept




def _assign_staff(
    cy: int, staves: list[list[int]], spacing: float
) -> tuple[list[int] | None, int]:
    """
    Return (staff, staff_index) for the nearest staff whose range contains cy.

    The search window extends 2 full staff-spaces (≈ 2 ledger lines) above and
    below the staff.  Chord-symbol text typically sits 2.7+ spaces above the top
    line and is thereby excluded, while notes up to A5/A3 (1st ledger above each
    clef) remain included.
    Returns (None, -1) if no staff is close enough.
    """
    margin = int(spacing * 2.0)
    best: list[int] | None = None
    best_idx = -1
    best_dist = 9999
    for idx, staff in enumerate(staves):
        mid = (staff[0] + staff[4]) / 2.0
        dist = abs(cy - mid)
        if staff[0] - margin <= cy <= staff[4] + margin and dist < best_dist:
            best = staff
            best_idx = idx
            best_dist = dist
    return best, best_idx


def _note_pitch(note_head_cy: int, staff: list[int], staff_idx: int, spacing: float) -> str:
    """
    Map note head center Y to a solfège pitch name.
    Uses treble clef for even-indexed staves, bass clef for odd-indexed.
    """
    if spacing <= 0:
        return "Desconhecida"
    # Distance upward from bottom staff line, in half-spaces (diatonic steps)
    relative = (staff[4] - note_head_cy) / (spacing / 2.0)
    pos = int(round(relative))
    table = _NOTES_BASS if staff_idx % 2 == 1 else _NOTES_TREBLE
    if 0 <= pos < len(table):
        return table[pos]
    if pos < 0:
        return "Abaixo da pauta"
    return "Acima da pauta"


def _count_flags(notes_img: np.ndarray, cx: int, cy: int, w: int, h: int) -> int:
    """
    Count beam/flag groups to the right of the note head center.
    Returns 0 (quarter/half), 1 (eighth), 2 (16th), 3 (32nd), 4 (64th).
    """
    x_start = cx + w // 2
    x_end = min(x_start + 16, notes_img.shape[1])
    y_start = max(0, cy - h)
    y_end = min(notes_img.shape[0], cy + h * 2)

    if x_start >= x_end or y_start >= y_end:
        return 0

    roi = notes_img[y_start:y_end, x_start:x_end]
    if roi.size == 0:
        return 0

    profile = np.sum(roi, axis=1)
    threshold = roi.shape[1] * 255 * 0.25

    peaks = 0
    in_peak = False
    for val in profile:
        if val > threshold:
            if not in_peak:
                peaks += 1
                in_peak = True
        else:
            in_peak = False

    return min(peaks, 4)


def _classify_duration(flags: int) -> str:
    mapping = {
        0: "Semínima/Mínima",
        1: "Colcheia",
        2: "Semicolcheia",
        3: "Fusa",
        4: "Semifusa",
    }
    return mapping.get(flags, f"Desconhecida ({flags} colchetes)")


def analyze_image(image_bytes: bytes) -> dict:
    """
    Full OMR pipeline. Accepts raw image bytes.
    Returns a dict with keys: notes (list), staff_found (bool),
    staff_y (list of all detected line Y positions), spacing_px (float),
    total_notes (int).
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img_gray = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)

    if img_gray is None:
        return {"error": "Não foi possível decodificar a imagem.", "notes": []}

    # 1. Deskew via Hough
    img_gray = _deskew(img_gray)

    # 2. Binarize
    img_bin = _binarize(img_gray)

    # 3. Detect ALL staves on the page (multi-system support)
    staves = _detect_staves(img_bin)

    # Flatten all staff line Y positions for the response / annotation
    all_staff_y: list[int] = [y for staff in staves for y in staff]

    # Estimate median spacing across all staves
    spacing = _estimate_spacing(staves)

    # 4. Compute per-system left-margin cutoff (skip clef + key + time signature area).
    # We detect the first large horizontal gap in column density within each treble staff
    # zone and use it as the note-content start.  Fall back to 10× spacing if not found.
    notes_only = _remove_staff_lines(img_bin)
    x_cutoff = _find_note_x_start(notes_only, staves, spacing)

    # 5. Detect note heads
    note_heads = _detect_note_heads(notes_only, spacing)

    # 6. Deduplicate note heads that are within 8px horizontally and 8px vertically
    #    (artefacts from the close/open operations can produce twin blobs for one head).
    note_heads = _dedup_note_heads(note_heads)

    # 7. Build note list: assign each head to a staff, map pitch and duration
    detected_notes = []
    for cx, cy, w, h in sorted(note_heads, key=lambda t: t[0]):
        # Skip blobs in the left margin (clef / key sig / time sig area)
        if cx < x_cutoff:
            continue

        staff, staff_idx = _assign_staff(cy, staves, spacing)
        if staff is None:
            continue  # blob not near any staff — skip

        staff_spacing = (staff[4] - staff[0]) / 4.0
        pitch = _note_pitch(cy, staff, staff_idx, staff_spacing)
        # Skip notes whose pitch resolved to out-of-range (text blobs above/below)
        if pitch in ("Acima da pauta", "Abaixo da pauta"):
            continue
        flags = _count_flags(notes_only, cx, cy, w, h)
        duration = _classify_duration(flags)

        detected_notes.append({
            "position_x": int(cx),
            "position_y": int(cy),
            "duration": duration,
            "pitch": pitch,
            "flags": int(flags),
        })

    return {
        "notes": detected_notes,
        "staff_found": len(staves) >= 1,
        "staff_y": all_staff_y,
        "spacing_px": round(spacing, 2),
        "total_notes": len(detected_notes),
    }
