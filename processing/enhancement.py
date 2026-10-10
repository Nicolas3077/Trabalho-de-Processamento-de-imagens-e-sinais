"""Pipeline de realce de texto em imagens de documentos."""

from __future__ import annotations

import cv2
import numpy as np

MAX_UPSCALE_SIDE = 2500


def _to_grayscale(image_bgr: np.ndarray) -> np.ndarray:
    if image_bgr.ndim == 2:
        return image_bgr
    if image_bgr.shape[2] == 4:
        return cv2.cvtColor(image_bgr, cv2.COLOR_BGRA2GRAY)
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)


def deskew(gray: np.ndarray) -> np.ndarray:
    """Corrige pequena inclinação do documento usando o retângulo mínimo dos pixels de texto."""
    inverted = cv2.bitwise_not(gray)
    thresh = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    coords = cv2.findNonZero(thresh)
    if coords is None or len(coords) < 50:
        return gray

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    elif angle > 45:
        angle = angle - 90

    if abs(angle) < 0.4:
        return gray

    height, width = gray.shape[:2]
    center = (width // 2, height // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        gray,
        matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def unsharp_mask(image: np.ndarray, amount: float = 0.8, sigma: float = 1.0) -> np.ndarray:
    blurred = cv2.GaussianBlur(image, (0, 0), sigma)
    sharpened = cv2.addWeighted(image, 1.0 + amount, blurred, -amount, 0)
    return np.clip(sharpened, 0, 255).astype(np.uint8)


def ensure_dark_text_on_white(binary: np.ndarray) -> np.ndarray:
    """Garante fundo claro e texto escuro, padrão de documento impresso."""
    if np.mean(binary) < 127:
        return cv2.bitwise_not(binary)
    return binary


def enhance_document(image_bgr: np.ndarray) -> np.ndarray:
    """
    Realça o texto de um documento com traço mais fino e bordas suaves.

    Etapas:
    1. Conversão para tons de cinza
    2. Correção de inclinação
    3. Redução de ruído (mais branda, para não borrar letra pequena)
    4. Ampliação 2x (exceto imagens já grandes)
    5. Equalização local de contraste (CLAHE)
    6. Nitidez leve (unsharp mask)
    7. Binarização adaptativa
    8. Redução à resolução original com INTER_AREA (antialias nas bordas)
    """
    gray = _to_grayscale(image_bgr)
    aligned = deskew(gray)

    denoised = cv2.fastNlMeansDenoising(
        aligned,
        None,
        h=7,
        templateWindowSize=7,
        searchWindowSize=21,
    )

    height, width = denoised.shape[:2]
    should_upscale = max(height, width) <= MAX_UPSCALE_SIDE
    working = (
        cv2.resize(denoised, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)
        if should_upscale
        else denoised
    )

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrasted = clahe.apply(working)
    sharpened = unsharp_mask(contrasted, amount=0.8, sigma=1.0)

    binary = cv2.adaptiveThreshold(
        sharpened,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        21,
        10,
    )
    binary = ensure_dark_text_on_white(binary)

    if should_upscale:
        return cv2.resize(binary, (width, height), interpolation=cv2.INTER_AREA)
    return binary
