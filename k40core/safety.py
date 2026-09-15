"""Validações puras executadas antes de gerar ou enviar um trabalho."""

from dataclasses import dataclass

from .model import Bounds


class WorkAreaError(ValueError):
    pass


def placed_job_bounds(
    width_mm: float,
    height_mm: float,
    anchor_x_mm: float,
    anchor_y_mm: float,
    home_on_right: bool = False,
) -> Bounds:
    if width_mm < 0 or height_mm < 0:
        raise ValueError("Dimensões do trabalho não podem ser negativas.")
    if home_on_right:
        min_x, max_x = anchor_x_mm - width_mm, anchor_x_mm
    else:
        min_x, max_x = anchor_x_mm, anchor_x_mm + width_mm
    return Bounds(min_x, anchor_y_mm - height_mm, max_x, anchor_y_mm)


def validate_work_area(job: Bounds, machine: Bounds, tolerance_mm: float = 0.025) -> None:
    if job.width > machine.width + tolerance_mm or job.height > machine.height + tolerance_mm:
        raise WorkAreaError(
            "O trabalho mede %.2f × %.2f mm e excede a área útil de %.2f × %.2f mm."
            % (job.width, job.height, machine.width, machine.height)
        )
    if (
        job.min_x < machine.min_x - tolerance_mm
        or job.max_x > machine.max_x + tolerance_mm
        or job.min_y < machine.min_y - tolerance_mm
        or job.max_y > machine.max_y + tolerance_mm
    ):
        raise WorkAreaError(
            "O trabalho está fora da área útil: X %.2f…%.2f mm, Y %.2f…%.2f mm."
            % (job.min_x, job.max_x, job.min_y, job.max_y)
        )
