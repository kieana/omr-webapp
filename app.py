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
import cv2
import numpy as np

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max upload


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

    image_bytes = file.read()
    result = analyze_image(image_bytes)

    if "error" in result:
        return jsonify(result), 422

    # Generate annotated image
    annotated_b64 = _build_annotated_image(image_bytes, result)
    result["annotated_image"] = annotated_b64

    return jsonify(result)


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

    result = analyze_image(file.read())
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
