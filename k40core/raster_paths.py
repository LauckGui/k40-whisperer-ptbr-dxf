"""Fast scanline extraction from prepared monochrome raster images."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class RasterScanlines:
    ecoords: list[list[float]]
    length_inches: float
    scanline_count: int
    hull_points: list[list[float]]


def extract_scanlines(image, dpi: float, raster_step_mils: int, cutoff: int = 128,
                      cancelled: Callable[[], bool] | None = None,
                      progress: Callable[[float], None] | None = None,
                      collect_coords: bool = True,
                      collect_hull: bool = True) -> RasterScanlines:
    """Extract dark pixel runs using vectorized per-row transition detection."""
    import numpy as np

    if dpi <= 0.0 or raster_step_mils <= 0:
        raise ValueError("DPI e passo do raster precisam ser positivos.")
    pixels = np.asarray(image.convert("L"))
    height, width = pixels.shape
    height_mils = int(height/dpi*1000.0)
    ecoords = []
    hull_points = []
    length = 0.0
    scanlines = 0
    loop = 1
    steps = range(0, height_mils, raster_step_mils)

    for step_index, y_mils in enumerate(steps):
        if cancelled is not None and cancelled():
            raise RuntimeError("Cálculo do raster cancelado.")
        row_index = min(height-1, int(y_mils*dpi/1000.0))
        dark = pixels[row_index] <= cutoff
        if dark.any():
            padded = np.empty(width+2, dtype=np.bool_)
            padded[0] = False
            padded[-1] = False
            padded[1:-1] = dark
            runs = np.flatnonzero(padded[1:] != padded[:-1]).reshape((-1, 2))
            left = int(runs[0, 0])
            right = int(runs[-1, 1])
            y = (height_mils-y_mils)/1000.0
            length += (right-left)/dpi
            scanlines += 1
            if collect_hull:
                hull_points.extend(([left/dpi, y], [right/dpi, y]))
            for start, end in runs:
                loop += 1
                if collect_coords:
                    ecoords.extend((
                        [float(start)/dpi, y, loop],
                        [float(end)/dpi, y, loop],
                    ))
        if progress is not None and step_index % 100 == 0:
            progress(100.0*row_index/max(1, height))

    return RasterScanlines(ecoords, length, scanlines, hull_points)
