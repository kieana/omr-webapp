import subprocess
import sys
import importlib

def _ensure_requirements():
    """Instala as dependências listadas em requirements.txt na primeira execução."""
    import pathlib, os
    req_file = pathlib.Path(__file__).parent / "requirements.txt"
    flag_file = pathlib.Path(__file__).parent / ".deps_installed"

    if flag_file.exists():
        return  # já instalado anteriormente

    print("[OMR] Instalando dependências (primeira execução)…")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-r", str(req_file), "--quiet"],
    )
    flag_file.touch()
    print("[OMR] Dependências instaladas com sucesso.")

_ensure_requirements()

import io
import base64
from flask import Flask, render_template, request, jsonify, send_file
from omr.pipeline import analyze_image
from omr.export import notes_to_stream, stream_to_midi_bytes, stream_to_musicxml_bytes
from omr.render import notes_to_svg
import cv2
import numpy as np

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024  # 64 MB max upload

# ── Tipos de arquivo suportados ────────────────────────────────────────────────
_IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif",
    ".gif", ".ppm", ".pgm", ".pbm", ".sr", ".ras",
}
_PDF_EXTENSION = ".pdf"


def _file_to_image_bytes(file_bytes: bytes, filename: str) -> tuple[bytes, str]:
    """
    Converte qualquer arquivo suportado para bytes de imagem PNG prontos para
    o pipeline do OpenCV.  Retorna (image_bytes, error_str).
    PDF: renderiza a primeira página com DPI=200 via PyMuPDF.
    Imagens: passa direto (OpenCV aceita todos os formatos listados).
    """
    import os
    ext = os.path.splitext(filename.lower())[1]

    if ext == _PDF_EXTENSION:
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            if doc.page_count == 0:
                return b"", "O PDF não contém páginas."
            page = doc.load_page(0)
            mat = fitz.Matrix(200 / 72, 200 / 72)   # 200 DPI
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
            return pix.tobytes("png"), ""
        except Exception as exc:
            return b"", f"Falha ao converter PDF: {exc}"

    if ext not in _IMAGE_EXTENSIONS and not ext:
        # tenta mesmo assim — OpenCV decidirá
        pass

    return file_bytes, ""


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    if "image" not in request.files:
        return jsonify({"error": "Nenhuma imagem enviada."}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Nome de arquivo vazio."}), 400

    image_bytes, err = _file_to_image_bytes(file.read(), file.filename)
    if err:
        return jsonify({"error": err}), 422
    result = analyze_image(image_bytes)

    if "error" in result:
        return jsonify(result), 422

    # Generate annotated image
    annotated_b64 = _build_annotated_image(image_bytes, result)
    result["annotated_image"] = annotated_b64

    # Generate reconstructed score SVG (inline — no extra round-trip needed)
    result["score_svg"] = notes_to_svg(result.get("notes", []))

    return jsonify(result)


@app.route("/render", methods=["POST"])
def render_score():
    """
    POST JSON {"notes": [...], "notes_per_bar": 4}
    Returns the SVG as text/svg+xml — useful for re-rendering after manual edits.
    """
    data = request.get_json(silent=True) or {}
    notes = data.get("notes", [])
    notes_per_bar = int(data.get("notes_per_bar", 4))
    svg = notes_to_svg(notes, notes_per_bar=notes_per_bar)
    return svg, 200, {"Content-Type": "image/svg+xml; charset=utf-8"}


@app.route("/export/midi", methods=["POST"])
def export_midi():
    notes = _extract_notes_from_request()
    if isinstance(notes, tuple):           # error response
        return notes
    sc = notes_to_stream(notes)
    midi_bytes = stream_to_midi_bytes(sc)
    return send_file(
        io.BytesIO(midi_bytes),
        mimetype="audio/midi",
        as_attachment=True,
        download_name="partitura.mid",
    )


@app.route("/export/musicxml", methods=["POST"])
def export_musicxml():
    notes = _extract_notes_from_request()
    if isinstance(notes, tuple):           # error response
        return notes
    sc = notes_to_stream(notes)
    xml_bytes = stream_to_musicxml_bytes(sc)
    return send_file(
        io.BytesIO(xml_bytes),
        mimetype="application/vnd.recordare.musicxml+xml",
        as_attachment=True,
        download_name="partitura.musicxml",
    )


def _extract_notes_from_request():
    """
    Shared helper: accepts a JSON body with a 'notes' list (from a prior /analyze
    call stored client-side) OR re-runs the pipeline on an uploaded image.
    Returns the notes list or a Flask error tuple.
    """
    # Prefer pre-computed notes sent as JSON
    if request.is_json:
        data = request.get_json(silent=True) or {}
        if "notes" in data:
            return data["notes"]

    # Fall back to re-analysing an uploaded image
    if "image" not in request.files:
        return jsonify({"error": "Envie a imagem ou os dados de notas (JSON)."}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Nome de arquivo vazio."}), 400

    image_bytes, err = _file_to_image_bytes(file.read(), file.filename)
    if err:
        return jsonify({"error": err}), 422
    result = analyze_image(image_bytes)
    if "error" in result:
        return jsonify(result), 422

    return result["notes"]


def _build_annotated_image(image_bytes: bytes, result: dict) -> str:
    """Draw bounding boxes / markers on the original image and return as base64 PNG."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return ""

    # Draw staff lines
    for y in result.get("staff_y", []):
        cv2.line(img, (0, y), (img.shape[1], y), (0, 180, 0), 1)

    # Draw note markers
    for note in result.get("notes", []):
        cx = note["position_x"]
        cy = note["position_y"] + 5
        color = (0, 80, 255)
        cv2.circle(img, (cx, cy), 6, color, -1)
        label = f"{note['pitch']} {note['duration']}"
        cv2.putText(img, label, (cx + 8, cy + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1, cv2.LINE_AA)

    _, buf = cv2.imencode(".png", img)
    return base64.b64encode(buf).decode("utf-8")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
