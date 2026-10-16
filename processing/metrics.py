"""Métricas de nitidez para comparar o documento original com o realçado."""

from __future__ import annotations

import cv2
import numpy as np

IMPROVEMENT_THRESHOLD_PERCENT = 80.0


def _to_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def laplacian_variance(gray: np.ndarray) -> float:
    """Variância do Laplaciano: valores maiores indicam bordas mais nítidas."""
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def tenengrad(gray: np.ndarray) -> float:
    """Energia do gradiente de Sobel (Tenengrad)."""
    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    return float(np.mean(gx**2 + gy**2))


def rms_contrast(gray: np.ndarray) -> float:
    pixels = gray.astype(np.float64)
    return float(np.std(pixels))


def grayscale_histogram(gray: np.ndarray) -> list[int]:
    """Contagem de pixels por intensidade (0 a 255) em imagem em tons de cinza."""
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    return [int(value) for value in hist.flatten()]


def combined_sharpness(gray: np.ndarray) -> float:
    """
    Combina Laplaciano e Tenengrad.

    O texto nítido gera bordas fortes; as duas medidas capturam isso
    de formas complementares.
    """
    return 0.6 * laplacian_variance(gray) + 0.4 * tenengrad(gray)


def evaluate_sharpness(
    original_bgr: np.ndarray,
    enhanced: np.ndarray,
    threshold_percent: float = IMPROVEMENT_THRESHOLD_PERCENT,
) -> dict:
    original_gray = _to_gray(original_bgr)
    enhanced_gray = _to_gray(enhanced)

    original_score = combined_sharpness(original_gray)
    enhanced_score = combined_sharpness(enhanced_gray)

    if original_score <= 1e-9:
        improvement_percent = 100.0 if enhanced_score > 0 else 0.0
    else:
        improvement_percent = ((enhanced_score - original_score) / original_score) * 100.0

    meets_criterion = improvement_percent >= threshold_percent

    return {
        "original": {
            "laplacian": round(laplacian_variance(original_gray), 4),
            "tenengrad": round(tenengrad(original_gray), 4),
            "contraste_rms": round(rms_contrast(original_gray), 4),
            "nitidez": round(original_score, 4),
        },
        "enhanced": {
            "laplacian": round(laplacian_variance(enhanced_gray), 4),
            "tenengrad": round(tenengrad(enhanced_gray), 4),
            "contraste_rms": round(rms_contrast(enhanced_gray), 4),
            "nitidez": round(enhanced_score, 4),
        },
        "improvement_percent": round(improvement_percent, 2),
        "threshold_percent": threshold_percent,
        "meets_criterion": meets_criterion,
        "histograms": {
            "original": grayscale_histogram(original_gray),
            "enhanced": grayscale_histogram(enhanced_gray),
        },
        "verdict": (
            "O texto ficou pelo menos 80% mais nítido."
            if meets_criterion
            else "A nitidez melhorou, mas ainda não atingiu o critério de 80%."
            if improvement_percent > 0
            else "A imagem processada não ficou mais nítida que a original."
        ),
    }
