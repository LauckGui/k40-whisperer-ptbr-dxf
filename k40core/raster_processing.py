"""Preparação tonal de imagens antes da geração de trajetórias raster."""

from __future__ import annotations

import math


def prepare_grayscale(image, brightness=0.0, contrast=1.0, gamma=1.0,
                      invert=False):
    """Return an opaque 8-bit grayscale image prepared for dithering.

    Transparency is composited over white, matching the laser convention in
    which white pixels do not fire the laser. Brightness is a signed percentage
    (-100 through 100); contrast and gamma must be positive multipliers.
    """
    from PIL import Image, ImageEnhance, ImageOps

    brightness = float(brightness)
    contrast = float(contrast)
    gamma = float(gamma)
    if not -100.0 <= brightness <= 100.0:
        raise ValueError("O brilho deve estar entre -100 e 100.")
    if not math.isfinite(contrast) or contrast <= 0.0:
        raise ValueError("O contraste deve ser maior que zero.")
    if not math.isfinite(gamma) or gamma <= 0.0:
        raise ValueError("O gamma deve ser maior que zero.")

    # Convert palette/CMYK/RGBA inputs predictably and preserve transparency as
    # laser-off white rather than an opaque black region.
    rgba = image.convert("RGBA")
    background = Image.new("RGBA", rgba.size, "white")
    grayscale = Image.alpha_composite(background, rgba).convert("L")
    if brightness:
        grayscale = ImageEnhance.Brightness(grayscale).enhance((100.0 + brightness)/100.0)
    if contrast != 1.0:
        grayscale = ImageEnhance.Contrast(grayscale).enhance(contrast)
    if gamma != 1.0:
        inverse_gamma = 1.0/gamma
        grayscale = grayscale.point(
            [int(round(255.0*((value/255.0) ** inverse_gamma))) for value in range(256)]
        )
    return ImageOps.invert(grayscale) if invert else grayscale


def color_intensities_from_document(document):
    """Map DXF fill colors to laser intensity by perceived luminance.

    Black maps to 1.0 (full raster density), white to 0.0, and colored fills
    receive an intermediate density. This keeps color-coded fills useful on a
    binary laser without assuming arbitrary named-color presets.
    """
    result = {}
    for fill in document.fills:
        if fill.color is None:
            continue
        color = fill.color
        luminance = (0.299*color.red + 0.587*color.green + 0.114*color.blue)/255.0
        result[color.hex_rgb.lower()] = max(0.0, min(1.0, 1.0-luminance))
    return result
