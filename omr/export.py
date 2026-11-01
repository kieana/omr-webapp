"""
Convert pipeline note data to music21 Stream and export MIDI / MusicXML bytes.
"""

import io
import logging
import tempfile
import os

# Silencia a saída verbosa do music21 (conversões, avisos internos)
logging.getLogger("music21").setLevel(logging.WARNING)

from music21 import stream, note, duration, metadata, environment as _m21env

# Desativa o log interno do music21 (usa WARNING em vez de INFO/DEBUG)
_m21env.UserSettings()["warnings"] = 0

# ── Pitch mapping ─────────────────────────────────────────────────────────────
# Pipeline uses Portuguese solfège names (Dó, Ré, Mi…) + octave number.
# music21 uses English letter names (C, D, E…) + octave number.

_PITCH_MAP = {
    "Dó":  "C",
    "Ré":  "D",
    "Mi":  "E",
    "Fá":  "F",
    "Sol": "G",
    "Lá":  "A",
    "Si":  "B",
}

# ── Duration mapping ──────────────────────────────────────────────────────────
# pipeline flags → music21 quarterLength value
# flags=0  → quarter note (1.0)  — we can't distinguish half/whole without beam info
# flags=1  → eighth     (0.5)
# flags=2  → 16th       (0.25)
# flags=3  → 32nd       (0.125)
# flags=4  → 64th       (0.0625)

_DURATION_MAP = {
    0: 1.0,
    1: 0.5,
    2: 0.25,
    3: 0.125,
    4: 0.0625,
}


def _parse_pitch(pitch_str: str) -> str | None:
    """
    Convert Portuguese pitch string like 'Sol5' or 'Dó4' to music21 nameWithOctave
    like 'G5' or 'C4'. Returns None for unparseable/unknown pitches.
    """
    pitch_str = pitch_str.strip()
    for pt_name, en_name in _PITCH_MAP.items():
        if pitch_str.startswith(pt_name):
            octave = pitch_str[len(pt_name):]
            if octave.isdigit():
                return en_name + octave
    return None


def _parse_quarter_length(flags: int) -> float:
    return _DURATION_MAP.get(flags, 1.0)


def notes_to_stream(notes: list[dict]) -> stream.Score:
    """
    Build a music21 Score from the list of note dicts produced by the pipeline.
    Each dict must have at least 'pitch' (str) and 'flags' (int).
    """
    sc = stream.Score()
    sc.metadata = metadata.Metadata()
    sc.metadata.title = "OMR Export"

    part = stream.Part()
    part.id = "P1"

    for n in notes:
        m21_pitch = _parse_pitch(n.get("pitch", ""))
        ql = _parse_quarter_length(n.get("flags", 0))

        if m21_pitch is None:
            # Unrecognised pitch → insert a rest of the same duration
            elem = note.Rest(quarterLength=ql)
        else:
            elem = note.Note(m21_pitch, quarterLength=ql)

        part.append(elem)

    sc.append(part)
    return sc


def stream_to_midi_bytes(sc: stream.Score) -> bytes:
    """Return the MIDI file as raw bytes."""
    with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        sc.write("midi", fp=tmp_path)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp_path)


def stream_to_musicxml_bytes(sc: stream.Score) -> bytes:
    """Return the MusicXML file as raw bytes (UTF-8 encoded)."""
    with tempfile.NamedTemporaryFile(suffix=".musicxml", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        sc.write("musicxml", fp=tmp_path)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp_path)
