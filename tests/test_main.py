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


def test_feriados_api_key_constante_definida():
    """_FERIADOS_API_KEY deve ser uma string não-vazia definida no módulo."""
    import ast
    import pathlib
    source = pathlib.Path('main.py').read_text(encoding='utf-8')
    tree = ast.parse(source)
    constantes = {}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign)
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == '_FERIADOS_API_KEY'
                and isinstance(node.value, ast.Constant)):
            constantes[node.targets[0].id] = node.value.value
    assert '_FERIADOS_API_KEY' in constantes
    assert len(constantes['_FERIADOS_API_KEY']) > 0


def test_smoke():
    """Garante que o módulo de testes carrega sem erros."""
    assert True
