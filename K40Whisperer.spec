# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules


project_dir = Path(SPEC).resolve().parent
hidden_imports = (
    collect_submodules("ezdxf")
    + collect_submodules("cairosvg")
    + collect_submodules("cairocffi")
    + collect_submodules("libusb_package")
)
cairo_datas = collect_data_files("cairosvg") + collect_data_files("cairocffi")
cairo_binaries = collect_dynamic_libs("cairocffi")
usb_binaries = collect_dynamic_libs("libusb_package")
legacy_usb_dll = project_dir / "vendor" / "libusb0" / "win64" / "libusb0.dll"
if legacy_usb_dll.is_file():
    usb_binaries.append((str(legacy_usb_dll), "."))

a = Analysis(
    [str(project_dir / "k40_whisperer.py")],
    pathex=[str(project_dir)],
    binaries=cairo_binaries + usb_binaries,
    datas=[
        (str(project_dir / "emblem"), "."),
        (str(project_dir / "gpl-3.0.txt"), "."),
    ] + cairo_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "PyQt5", "PyQt6", "PySide2", "PySide6"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="K40 Whisperer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_dir / "scorchworks.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="K40 Whisperer",
)
