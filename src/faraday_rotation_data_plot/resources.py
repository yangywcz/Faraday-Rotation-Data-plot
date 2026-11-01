from __future__ import annotations

import os
import sys
from ctypes import windll
from pathlib import Path

from matplotlib import font_manager

PACKAGE_ROOT = Path(__file__).resolve().parent


def _resource_root() -> Path:
    candidates = [
        PACKAGE_ROOT.parent.parent,
        PACKAGE_ROOT.parent,
        Path(sys.executable).resolve().parent,
        Path.cwd(),
    ]
    if hasattr(sys, "_MEIPASS"):
        candidates.insert(0, Path(sys._MEIPASS))
    for candidate in candidates:
        if (candidate / "logo.ico").exists() and (candidate / "SplashScreen.png").exists():
            return candidate
    return candidates[0]


PROJECT_ROOT = _resource_root()
ASSETS_DIR = PROJECT_ROOT / "assets"
FONT_DIR = ASSETS_DIR / "fonts"
ICON_PATH = PROJECT_ROOT / "logo.ico"
SPLASH_PATH = PROJECT_ROOT / "SplashScreen.png"
HONOR_SANS_CN = "HONOR Sans CN"


def load_fonts() -> str:
    """Load the bundled font and return its family name."""
    font_paths = (
        FONT_DIR / "HONORSansCN-Regular.ttf",
        FONT_DIR / "HONORSansCN-Bold.ttf",
    )
    for font_path in font_paths:
        if not font_path.exists():
            continue
        font_manager.fontManager.addfont(str(font_path))
        if os.name == "nt":
            windll.gdi32.AddFontResourceExW(str(font_path), 0x10, 0)
    return HONOR_SANS_CN