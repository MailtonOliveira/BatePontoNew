# tests/test_main.py
import sys
import os
import unittest.mock as mock

# Mocks para evitar que main.py abra Chrome, systray, etc. ao importar
sys.modules['pystray'] = mock.MagicMock()
sys.modules['PIL'] = mock.MagicMock()
sys.modules['PIL.Image'] = mock.MagicMock()
sys.modules['PIL.ImageDraw'] = mock.MagicMock()
sys.modules['pygetwindow'] = mock.MagicMock()
sys.modules['pyautogui'] = mock.MagicMock()

sys.modules['tkinter'] = mock.MagicMock()
sys.modules['tkinter.ttk'] = mock.MagicMock()
sys.modules['tkinter.messagebox'] = mock.MagicMock()


def test_smoke():
    """Garante que o módulo de testes carrega sem erros."""
    assert True
