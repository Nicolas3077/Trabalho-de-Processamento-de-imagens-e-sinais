const form = document.getElementById("upload-form");
const input = document.getElementById("image-input");
const dropzone = document.getElementById("dropzone");
const filenameLabel = document.getElementById("filename");
const statusEl = document.getElementById("status");
const submitBtn = document.getElementById("submit-btn");
const results = document.getElementById("results");
const originalPreview = document.getElementById("original-preview");
const enhancedPreview = document.getElementById("enhanced-preview");
const verdictEl = document.getElementById("verdict");
const sharpOriginal = document.getElementById("sharp-original");
const sharpEnhanced = document.getElementById("sharp-enhanced");
const improvementEl = document.getElementById("improvement");

function setStatus(message, isError = false) {
  statusEl.hidden = !message;
  statusEl.textContent = message;
  statusEl.classList.toggle("error", isError);
}

function formatNumber(value) {
  return Number(value).toLocaleString("pt-BR", { maximumFractionDigits: 2 });
}

input.addEventListener("change", () => {
  filenameLabel.textContent = input.files[0]
    ? input.files[0].name
    : "Nenhum arquivo selecionado";
});

["dragenter", "dragover"].forEach((eventName) => {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.add("dragover");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.remove("dragover");
  });
});

dropzone.addEventListener("drop", (event) => {
  const files = event.dataTransfer.files;
  if (files.length) {
    input.files = files;
    filenameLabel.textContent = files[0].name;
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!input.files[0]) {
    setStatus("Selecione uma imagem de documento.", true);
    return;
  }

  const data = new FormData();
  data.append("image", input.files[0]);

  submitBtn.disabled = true;
  results.hidden = true;
  setStatus("Processando a imagem. Isso pode levar alguns segundos...");

  try {
    const response = await fetch("/api/process", {
      method: "POST",
      body: data,
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Falha no processamento.");
    }

    originalPreview.src = `data:image/png;base64,${payload.original_image}`;
    enhancedPreview.src = `data:image/png;base64,${payload.enhanced_image}`;

    const metrics = payload.metrics;
    sharpOriginal.textContent = formatNumber(metrics.original.nitidez);
    sharpEnhanced.textContent = formatNumber(metrics.enhanced.nitidez);
    improvementEl.textContent = `${formatNumber(metrics.improvement_percent)}%`;
    verdictEl.textContent = metrics.verdict;
    verdictEl.className = "verdict";
    if (metrics.meets_criterion) {
      verdictEl.classList.add("ok");
    } else if (metrics.improvement_percent > 0) {
      verdictEl.classList.add("warn");
    } else {
      verdictEl.classList.add("bad");
    }

    results.hidden = false;
    setStatus("Processamento concluído.");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    submitBtn.disabled = false;
  }
});
