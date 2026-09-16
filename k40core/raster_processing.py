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


def dither_image(image, method="Limiar"):
    """Convert a grayscale image to the same binary bitmap used for raster paths."""
    from PIL import Image
    import numpy as np

    source = np.asarray(image.convert("L"), dtype=np.float32).copy()
    name = (method or "Limiar").lower()
    if name == "limiar":
        return Image.fromarray(np.where(source < 128, 0, 255).astype("uint8"), "L")
    if name == "bayer 8×8":
        matrix = np.array([[0,48,12,60,3,51,15,63],[32,16,44,28,35,19,47,31],
                           [8,56,4,52,11,59,7,55],[40,24,36,20,43,27,39,23],
                           [2,50,14,62,1,49,13,61],[34,18,46,30,33,17,45,29],
                           [10,58,6,54,9,57,5,53],[42,26,38,22,41,25,37,21]], dtype=np.float32)
        threshold = (matrix + .5) * 255.0 / 64.0
        return Image.fromarray(np.where(source < np.tile(threshold, (source.shape[0]//8+1, source.shape[1]//8+1))[:source.shape[0], :source.shape[1]], 0, 255).astype("uint8"), "L")
    kernels = {
        "floyd–steinberg": ([(1,0,7),( -1,1,3),(0,1,5),(1,1,1)], 16),
        "atkinson": ([(1,0,1),(2,0,1),(-1,1,1),(0,1,1),(1,1,1),(0,2,1)], 8),
        "jarvis–judice–ninke": ([(1,0,7),(2,0,5),(-2,1,3),(-1,1,5),(0,1,7),(1,1,5),(2,1,3),(-2,2,1),(-1,2,3),(0,2,5),(1,2,3),(2,2,1)], 48),
    }
    kernel, divisor = kernels.get(name, kernels["floyd–steinberg"])
    height, width = source.shape
    for y in range(height):
        for x in range(width):
            old = source[y, x]; new = 0.0 if old < 128 else 255.0
            source[y, x] = new; error = (old-new)/divisor
            for dx, dy, weight in kernel:
                xx, yy = x+dx, y+dy
                if 0 <= xx < width and yy < height:
                    source[yy, xx] += error*weight
    return Image.fromarray(np.clip(source, 0, 255).astype("uint8"), "L")
