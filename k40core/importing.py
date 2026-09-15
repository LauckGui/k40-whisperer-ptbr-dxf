"""Contratos compartilhados por importadores executados em background."""

from dataclasses import dataclass
from typing import Callable, Optional


class ImportCancelled(Exception):
    """Cancelamento cooperativo solicitado pelo usuário."""


@dataclass(frozen=True)
class ImportProgress:
    phase: str
    completed: int = 0
    total: Optional[int] = None
    message: str = ""


ProgressCallback = Callable[[ImportProgress], None]
CancelCheck = Callable[[], bool]


def report_progress(callback, phase, completed=0, total=None, message=""):
    if callback is not None:
        callback(ImportProgress(phase, completed, total, message))


def check_cancelled(cancelled):
    if cancelled is not None and cancelled():
        raise ImportCancelled("Importação cancelada pelo usuário.")
