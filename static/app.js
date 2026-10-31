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
const histogramOriginal = document.getElementById("histogram-original");
const histogramEnhanced = document.getElementById("histogram-enhanced");
const appliedFilter = document.getElementById("applied-filter");

let lastHistograms = null;

function setStatus(message, isError = false) {
  statusEl.hidden = !message;
  statusEl.textContent = message;
  statusEl.classList.toggle("error", isError);
}

function formatNumber(value) {
  return Number(value).toLocaleString("pt-BR", { maximumFractionDigits: 2 });
}

function formatCount(value) {
  return Number(value).toLocaleString("pt-BR", { maximumFractionDigits: 0 });
}

function drawHistogram(canvas, counts) {
  const bins = Array.isArray(counts) ? counts : [];
  const dpr = window.devicePixelRatio || 1;
  const cssWidth = Math.max(canvas.clientWidth || 0, 280);
  const cssHeight = 240;
  canvas.width = Math.round(cssWidth * dpr);
  canvas.height = Math.round(cssHeight * dpr);

  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssWidth, cssHeight);

  const styles = getComputedStyle(document.documentElement);
  const ink = styles.getPropertyValue("--ink").trim() || "#1c1915";
  const muted = styles.getPropertyValue("--muted").trim() || "#5d574e";
  const accent = styles.getPropertyValue("--accent").trim() || "#8c2f1b";
  const line = styles.getPropertyValue("--line").trim() || "#d9d0c3";

  const padding = { top: 16, right: 14, bottom: 36, left: 52 };
  const plotWidth = cssWidth - padding.left - padding.right;
  const plotHeight = cssHeight - padding.top - padding.bottom;
  const maxCount = Math.max(...bins, 1);
  const binCount = 256;
  const barWidth = plotWidth / binCount;

  ctx.strokeStyle = line;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(padding.left, padding.top);
  ctx.lineTo(padding.left, padding.top + plotHeight);
  ctx.lineTo(padding.left + plotWidth, padding.top + plotHeight);
  ctx.stroke();

  ctx.fillStyle = accent;
  bins.forEach((count, index) => {
    const barHeight = (count / maxCount) * plotHeight;
    const x = padding.left + index * barWidth;
    const y = padding.top + plotHeight - barHeight;
    ctx.fillRect(x, y, Math.max(barWidth, 1), barHeight);
  });

  ctx.fillStyle = muted;
  ctx.font = "12px IBM Plex Sans, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  ctx.fillText("0", padding.left, padding.top + plotHeight + 8);
  ctx.fillText("255", padding.left + plotWidth, padding.top + plotHeight + 8);
  ctx.fillText(
    "Intensidade",
    padding.left + plotWidth / 2,
    padding.top + plotHeight + 20
  );

  ctx.save();
  ctx.translate(16, padding.top + plotHeight / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText("Pixels", 0, 0);
  ctx.restore();

  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  ctx.fillStyle = ink;
  ctx.fillText(formatCount(maxCount), padding.left - 8, padding.top);
  ctx.fillText("0", padding.left - 8, padding.top + plotHeight);
}

function renderHistograms(histograms) {
  lastHistograms = histograms;
  if (!histograms) {
    return;
  }
  drawHistogram(histogramOriginal, histograms.original);
  drawHistogram(histogramEnhanced, histograms.enhanced);
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

  const selectedFilter = form.querySelector('input[name="filter"]:checked');
  const data = new FormData();
  data.append("image", input.files[0]);
  data.append("filter", selectedFilter ? selectedFilter.value : "documento_impresso");

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
    appliedFilter.textContent = payload.filter?.label || "—";
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
    renderHistograms(metrics.histograms);
    setStatus("Processamento concluído.");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    submitBtn.disabled = false;
  }
});

window.addEventListener("resize", () => {
  if (lastHistograms && !results.hidden) {
    renderHistograms(lastHistograms);
  }
});
