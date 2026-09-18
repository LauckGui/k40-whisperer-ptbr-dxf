"""Selecao centralizada do backend USB usado pela controladora M2 Nano."""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path


def _application_roots():
    """Retorna locais confiaveis onde uma DLL empacotada pode estar."""
    roots = []
    if getattr(sys, "frozen", False):
        roots.append(Path(sys.executable).resolve().parent)
        bundle_root = getattr(sys, "_MEIPASS", None)
        if bundle_root:
            roots.append(Path(bundle_root).resolve())
    roots.append(Path(__file__).resolve().parents[1])
    return tuple(dict.fromkeys(roots))


def _bundled_libusb0_path():
    candidates = []
    for root in _application_roots():
        candidates.extend(
            (
                root / "libusb0.dll",
                root / "vendor" / "libusb0" / "win64" / "libusb0.dll",
            )
        )
    return next((path for path in candidates if path.is_file()), None)


@lru_cache(maxsize=1)
def get_usb_backend():
    """Prefere o backend legado da K40 e usa libusb 1 como alternativa."""
    import usb.backend.libusb0
    import usb.backend.libusb1

    bundled_libusb0 = _bundled_libusb0_path()
    if bundled_libusb0 is not None:
        backend = usb.backend.libusb0.get_backend(
            find_library=lambda _name: os.fspath(bundled_libusb0)
        )
        if backend is not None:
            return backend

    backend = usb.backend.libusb0.get_backend()
    if backend is not None:
        return backend

    try:
        import libusb_package

        backend = libusb_package.get_libusb1_backend()
        if backend is not None:
            return backend
    except (ImportError, OSError):
        pass

    return usb.backend.libusb1.get_backend()


def find_usb_device(**kwargs):
    """Executa ``usb.core.find`` sempre com um backend conhecido."""
    import usb.core

    backend = get_usb_backend()
    if backend is None:
        raise RuntimeError(
            "No USB backend available. The packaged libusb library could not be loaded."
        )
    return usb.core.find(backend=backend, **kwargs)
