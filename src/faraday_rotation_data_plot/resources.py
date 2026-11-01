from __future__ import annotations

import os
from ctypes import windll
from pathlib import Path

from matplotlib import font_manager

PROJECT_ROOT = Path(__file__).resolve().parents[2]
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