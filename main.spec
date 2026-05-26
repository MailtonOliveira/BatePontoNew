# -*- mode: python ; coding: utf-8 -*-
#
# Spec cross-platform para BatePonto.
# Compile no Windows  : py -m PyInstaller main.spec --clean
# Compile no Linux    : python -m PyInstaller main.spec --clean
#
import sys

_is_windows = sys.platform == "win32"

_hiddenimports_comum = [
    'dotenv',
    'pystray',
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'tkinter',
    'tkinter.ttk',
    'tkinter.messagebox',
    'selenium.webdriver.chrome.webdriver',
    'selenium.webdriver.chrome.options',
    'selenium.webdriver.chrome.service',
    'selenium.webdriver.common.by',
    'selenium.webdriver.support.ui',
    'selenium.webdriver.support.expected_conditions',
    'selenium.webdriver.support',
    'selenium.webdriver.remote.webdriver',
    'selenium.webdriver.remote.webelement',
    'selenium.webdriver.remote.command',
    'selenium.webdriver',
    'platform_utils',
]

# Dependências exclusivas do Windows
_hiddenimports_windows = [
    'pygetwindow',
    'pyautogui',
]

hiddenimports = _hiddenimports_comum + (_hiddenimports_windows if _is_windows else [])

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='BatePonto',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
