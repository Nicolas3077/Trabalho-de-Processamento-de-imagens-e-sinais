"""Servidor Flask: recebe a imagem, processa e devolve original + realçada + métricas."""

from __future__ import annotations

import base64
import io

import cv2
import numpy as np
from flask import Flask, jsonify, render_template, request
from PIL import Image, UnidentifiedImageError

from processing.enhancement import enhance_document
from processing.metrics import evaluate_sharpness

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
MAX_CONTENT_LENGTH = 12 * 1024 * 1024

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


def allowed_file(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    extension = "." + filename.rsplit(".", 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS


def decode_upload(file_storage) -> np.ndarray:
    raw = file_storage.read()
    if not raw:
        raise ValueError("Arquivo vazio.")

    try:
        pil_image = Image.open(io.BytesIO(raw))
        pil_image = pil_image.convert("RGB")
        rgb = np.array(pil_image)
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    except UnidentifiedImageError as exc:
        raise ValueError("Não foi possível ler a imagem enviada.") from exc


def encode_png_base64(image: np.ndarray) -> str:
    if image.ndim == 2:
        success, buffer = cv2.imencode(".png", image)
    else:
        success, buffer = cv2.imencode(".png", image)
    if not success:
        raise ValueError("Falha ao codificar a imagem de resposta.")
    return base64.b64encode(buffer.tobytes()).decode("ascii")


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/process")
def process_image():
    if "image" not in request.files:
        return jsonify({"error": "Envie o arquivo no campo 'image'."}), 400

    uploaded = request.files["image"]
    if not uploaded.filename:
        return jsonify({"error": "Nenhum arquivo selecionado."}), 400
    if not allowed_file(uploaded.filename):
        return jsonify(
            {
                "error": "Formato não suportado. Use PNG, JPG, JPEG, BMP, TIF ou WEBP.",
            }
        ), 400

    try:
        original = decode_upload(uploaded)
        enhanced = enhance_document(original)
        metrics = evaluate_sharpness(original, enhanced)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro interno ao processar a imagem."}), 500

    return jsonify(
        {
            "original_image": encode_png_base64(original),
            "enhanced_image": encode_png_base64(enhanced),
            "metrics": metrics,
            "filename": uploaded.filename,
        }
    )


@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": "Arquivo maior que 12 MB."}), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
