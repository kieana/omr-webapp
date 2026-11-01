/* OMR Determinístico — frontend logic */

(function () {
  "use strict";

  // ── DOM refs ──────────────────────────────────────────────────────────────
  const dropZone      = document.getElementById("drop-zone");
  const fileInput     = document.getElementById("file-input");
  const analyzeBtn    = document.getElementById("analyze-btn");
  const newFileBtn    = document.getElementById("new-file-btn");
  const previewSec    = document.getElementById("preview-section");
  const previewImg    = document.getElementById("preview-img");
  const loading       = document.getElementById("loading");
  const errorBox      = document.getElementById("error-box");
  const resultsSec    = document.getElementById("results-section");

  const statNotes     = document.getElementById("stat-notes");
  const statStaff     = document.getElementById("stat-staff");
  const statSpacing   = document.getElementById("stat-spacing");

  const annotatedWrap = document.getElementById("annotated-wrapper");
  const annotatedImg  = document.getElementById("annotated-img");

  const tableWrap     = document.getElementById("table-wrapper");
  const notesTbody    = document.getElementById("notes-tbody");

  const noNotesMsg    = document.getElementById("no-notes-msg");
  const exportStatus  = document.getElementById("export-status");

  let selectedFile = null;
  let lastNotes    = null;    // cache do último /analyze
  let lastHash     = null;    // hash das últimas notas (deduplicidade)

  // ── Helper: show / hide ───────────────────────────────────────────────────
  function show(el) { el.hidden = false; }
  function hide(el) { el.hidden = true;  }

  function showError(msg) {
    errorBox.textContent = "⚠ " + msg;
    show(errorBox);
  }

  function clearError() {
    hide(errorBox);
    errorBox.textContent = "";
  }

  // ── Timestamp para nome de arquivo: YYYYMMDD_HHMMSS ──────────────────────
  function timestamp() {
    const d = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    return (
      d.getFullYear() +
      pad(d.getMonth() + 1) +
      pad(d.getDate()) +
      "_" +
      pad(d.getHours()) +
      pad(d.getMinutes()) +
      pad(d.getSeconds())
    );
  }

  // ── Hash simples das notas (para detecção de duplicidade) ─────────────────
  // Concatena pitch+flags de cada nota em string e faz djb2.
  function hashNotes(notes) {
    const str = notes.map((n) => n.pitch + n.flags).join("|");
    let h = 5381;
    for (let i = 0; i < str.length; i++) {
      h = ((h << 5) + h) ^ str.charCodeAt(i);
      h = h >>> 0; // mantém uint32
    }
    return h.toString(16);
  }

  // ── Download de blob ──────────────────────────────────────────────────────
  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a   = document.createElement("a");
    a.href     = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  // ── Exportação automática ─────────────────────────────────────────────────
  async function autoExport(notes, ts) {
    show(exportStatus);
    exportStatus.className = "export-status running";
    exportStatus.textContent = "⏳ Gerando arquivos MIDI e MusicXML…";

    const body = JSON.stringify({ notes });
    const headers = { "Content-Type": "application/json" };

    try {
      const [midiRes, xmlRes] = await Promise.all([
        fetch("/export/midi",     { method: "POST", headers, body }),
        fetch("/export/musicxml", { method: "POST", headers, body }),
      ]);

      if (!midiRes.ok || !xmlRes.ok) {
        exportStatus.className = "export-status error";
        exportStatus.textContent = "⚠ Erro ao gerar os arquivos de exportação.";
        return;
      }

      const [midiBlob, xmlBlob] = await Promise.all([
        midiRes.blob(),
        xmlRes.blob(),
      ]);

      downloadBlob(midiBlob, `partitura_${ts}.mid`);
      downloadBlob(xmlBlob,  `partitura_${ts}.musicxml`);

      exportStatus.className = "export-status done";
      exportStatus.textContent =
        `✔ Exportados: partitura_${ts}.mid  ·  partitura_${ts}.musicxml`;
    } catch (err) {
      exportStatus.className = "export-status error";
      exportStatus.textContent = "⚠ Falha na exportação: " + err.message;
    }
  }

  // ── Tipos aceitos (extensões + MIME) ──────────────────────────────────────
  const ACCEPTED_EXTS = new Set([
    "pdf","jpg","jpeg","png","webp","bmp","tiff","tif",
    "gif","ppm","pgm","pbm","sr","ras",
  ]);

  function _isAccepted(file) {
    if (file.type === "application/pdf") return true;
    if (file.type.startsWith("image/"))  return true;
    const ext = file.name.split(".").pop().toLowerCase();
    return ACCEPTED_EXTS.has(ext);
  }

  // ── File selection ────────────────────────────────────────────────────────
  function handleFile(file) {
    if (!file || !_isAccepted(file)) {
      showError("Formato não suportado. Use PDF, PNG, JPG, WEBP, BMP, TIFF, GIF ou similares.");
      return;
    }

    selectedFile = file;
    clearError();
    analyzeBtn.disabled = false;

    // PDF não tem preview nativo no <img>; mostra placeholder
    if (file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")) {
      previewImg.src = "";
      previewImg.alt = `📄 PDF selecionado: ${file.name}`;
      show(previewSec);
    } else {
      const reader = new FileReader();
      reader.onload = (e) => {
        previewImg.src = e.target.result;
        previewImg.alt = "Pré-visualização da partitura";
        show(previewSec);
      };
      reader.readAsDataURL(file);
    }

    hide(resultsSec);
  }

  // ── Drag-and-drop ─────────────────────────────────────────────────────────
  dropZone.addEventListener("click", () => fileInput.click());

  dropZone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") fileInput.click();
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) handleFile(fileInput.files[0]);
  });

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    handleFile(e.dataTransfer.files[0]);
  });

  // ── Botão "Nova Partitura" ─────────────────────────────────────────────────
  newFileBtn.addEventListener("click", () => {
    selectedFile = null;
    lastNotes    = null;
    lastHash     = null;
    fileInput.value = "";
    hide(resultsSec);
    hide(previewSec);
    clearError();
    analyzeBtn.disabled = true;
    // Rolar até o topo da área de upload
    document.getElementById("upload-section").scrollIntoView({ behavior: "smooth" });
  });

  // ── Analysis ──────────────────────────────────────────────────────────────
  analyzeBtn.addEventListener("click", async () => {
    if (!selectedFile) return;

    clearError();
    hide(resultsSec);
    hide(previewSec);
    show(loading);
    analyzeBtn.disabled = true;

    const formData = new FormData();
    formData.append("image", selectedFile);

    try {
      const response = await fetch("/analyze", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        showError(data.error || "Erro ao processar a imagem.");
        return;
      }

      renderResults(data);
    } catch (err) {
      showError("Falha na comunicação com o servidor: " + err.message);
    } finally {
      hide(loading);
      show(previewSec);
      analyzeBtn.disabled = false;
    }
  });

  // ── Render results ────────────────────────────────────────────────────────
  function renderResults(data) {
    lastNotes = data.notes || [];

    // Stats
    statNotes.textContent   = data.total_notes ?? 0;
    statStaff.textContent   = data.staff_found ? "✓ Sim" : "✗ Não";
    statSpacing.textContent = data.spacing_px > 0 ? data.spacing_px + " px" : "—";

    // Annotated image
    if (data.annotated_image) {
      annotatedImg.src = "data:image/png;base64," + data.annotated_image;
      show(annotatedWrap);
    } else {
      hide(annotatedWrap);
    }

    // Notes table
    notesTbody.innerHTML = "";
    const notes = data.notes || [];

    if (notes.length === 0) {
      hide(tableWrap);
      show(noNotesMsg);
      hide(exportStatus);
    } else {
      hide(noNotesMsg);
      notes.forEach((note, i) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${i + 1}</td>
          <td>${note.position_x}</td>
          <td>${note.position_y}</td>
          <td><strong>${note.pitch}</strong></td>
          <td>${note.duration}</td>
          <td>${note.flags}</td>
        `;
        notesTbody.appendChild(tr);
      });
      show(tableWrap);

      // ── Verificar duplicidade antes de exportar ───────────────────────────
      const newHash = hashNotes(notes);

      if (newHash === lastHash) {
        show(exportStatus);
        exportStatus.className = "export-status warning";
        exportStatus.textContent =
          "⚠ Esta análise é idêntica à anterior — exportação ignorada para evitar duplicidade.";
      } else {
        lastHash = newHash;
        autoExport(notes, timestamp());
      }
    }

    show(resultsSec);
  }
})();
