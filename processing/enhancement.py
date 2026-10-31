"""Pipelines de realce de texto em imagens de documentos."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

MAX_UPSCALE_SIDE = 2500
DEFAULT_FILTER_ID = "documento_impresso"


@dataclass(frozen=True)
class FilterProfile:
    id: str
    label: str
    description: str
    denoise: str
    nlmeans_h: float = 7.0
    nlmeans_template: int = 7
    nlmeans_search: int = 21
    bilateral_d: int = 5
    bilateral_sigma_color: float = 20.0
    bilateral_sigma_space: float = 20.0
    clahe_clip: float = 2.0
    clahe_tile: int = 8
    unsharp_amount: float = 0.8
    unsharp_sigma: float = 1.0
    binarize: bool = True
    block_size: int = 21
    c_constant: int = 10
    allow_upscale: bool = True


FILTERS: dict[str, FilterProfile] = {
    "documento_impresso": FilterProfile(
        id="documento_impresso",
        label="Documento impresso",
        description="Texto digitado, formulário ou comprovante. Saída em preto e branco.",
        denoise="nlmeans",
        nlmeans_h=7.0,
        clahe_clip=2.0,
        unsharp_amount=0.8,
        binarize=True,
        block_size=21,
        c_constant=10,
    ),
    "letra_cursiva": FilterProfile(
        id="letra_cursiva",
        label="Letra cursiva",
        description="Manuscrito, assinatura ou tinta irregular. Mantém tons de cinza para não romper o traço.",
        denoise="bilateral",
        bilateral_d=5,
        bilateral_sigma_color=20.0,
        bilateral_sigma_space=20.0,
        clahe_clip=1.5,
        unsharp_amount=0.35,
        unsharp_sigma=0.8,
        binarize=False,
        allow_upscale=False,
    ),
    "traco_fino": FilterProfile(
        id="traco_fino",
        label="Traço fino e letra miúda",
        description="Corpo pequeno e linhas finas impressas. Limiar mais conservador para não comer a tinta.",
        denoise="nlmeans",
        nlmeans_h=3.0,
        clahe_clip=1.8,
        unsharp_amount=0.5,
        unsharp_sigma=0.8,
        binarize=True,
        block_size=13,
        c_constant=5,
    ),
    "texto_grande": FilterProfile(
        id="texto_grande",
        label="Texto grande e traço grosso",
        description="Títulos e letra grande. Bloco maior no limiar para não preencher ocos.",
        denoise="nlmeans",
        nlmeans_h=10.0,
        clahe_clip=2.0,
        unsharp_amount=0.6,
        binarize=True,
        block_size=35,
        c_constant=15,
    ),
}


def list_filters() -> list[dict[str, str]]:
    return [
        {"id": profile.id, "label": profile.label, "description": profile.description}
        for profile in FILTERS.values()
    ]


def get_filter(filter_id: str | None) -> FilterProfile:
    chosen = (filter_id or DEFAULT_FILTER_ID).strip() or DEFAULT_FILTER_ID
    profile = FILTERS.get(chosen)
    if profile is None:
        known = ", ".join(FILTERS)
        raise ValueError(f"Filtro desconhecido: '{chosen}'. Use um de: {known}.")
    return profile


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
    if amount <= 0:
        return image
    blurred = cv2.GaussianBlur(image, (0, 0), sigma)
    sharpened = cv2.addWeighted(image, 1.0 + amount, blurred, -amount, 0)
    return np.clip(sharpened, 0, 255).astype(np.uint8)


def ensure_dark_text_on_white(image: np.ndarray) -> np.ndarray:
    """Garante fundo claro e texto escuro, padrão de documento impresso."""
    if np.mean(image) < 127:
        return cv2.bitwise_not(image)
    return image


def _denoise(gray: np.ndarray, profile: FilterProfile) -> np.ndarray:
    if profile.denoise == "bilateral":
        return cv2.bilateralFilter(
            gray,
            profile.bilateral_d,
            profile.bilateral_sigma_color,
            profile.bilateral_sigma_space,
        )
    if profile.denoise == "nlmeans":
        return cv2.fastNlMeansDenoising(
            gray,
            None,
            h=profile.nlmeans_h,
            templateWindowSize=profile.nlmeans_template,
            searchWindowSize=profile.nlmeans_search,
        )
    return gray


def enhance_document(
    image_bgr: np.ndarray,
    filter_id: str = DEFAULT_FILTER_ID,
) -> np.ndarray:
    """
    Realça o texto de um documento com o filtro escolhido pelo usuário.

    Etapas comuns: cinza, correção de inclinação, ruído, contraste e nitidez.
    A binarização e os parâmetros dependem do perfil.
    """
    profile = get_filter(filter_id)
    gray = _to_grayscale(image_bgr)
    aligned = deskew(gray)
    denoised = _denoise(aligned, profile)

    height, width = denoised.shape[:2]
    should_upscale = profile.allow_upscale and max(height, width) <= MAX_UPSCALE_SIDE
    working = (
        cv2.resize(denoised, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)
        if should_upscale
        else denoised
    )

    clahe = cv2.createCLAHE(
        clipLimit=profile.clahe_clip,
        tileGridSize=(profile.clahe_tile, profile.clahe_tile),
    )
    contrasted = clahe.apply(working)
    sharpened = unsharp_mask(
        contrasted,
        amount=profile.unsharp_amount,
        sigma=profile.unsharp_sigma,
    )

    if profile.binarize:
        result = cv2.adaptiveThreshold(
            sharpened,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            profile.block_size,
            profile.c_constant,
        )
        result = ensure_dark_text_on_white(result)
    else:
        result = ensure_dark_text_on_white(sharpened)

    if should_upscale:
        return cv2.resize(result, (width, height), interpolation=cv2.INTER_AREA)
    return result
