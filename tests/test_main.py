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
    main_py_path = pathlib.Path(__file__).parent.parent / 'main.py'
    source = main_py_path.read_text(encoding='utf-8')
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


def test_init_driver_define_global_driver(tmp_path, monkeypatch):
    """_init_driver() deve atribuir um objeto Chrome à variável global driver."""
    import importlib
    import unittest.mock as mock

    mock_driver = mock.MagicMock()

    # Precisamos de um .env temporário para o import não falhar
    env_file = tmp_path / '.env'
    env_file.write_text('BATEPONTO_SENHA=1234\n', encoding='utf-8')

    with mock.patch('selenium.webdriver.Chrome', return_value=mock_driver):
        with mock.patch('os.makedirs'):
            with mock.patch('time.sleep'):
                # Import main como módulo (mas com driver=None já definido)
                import main as m
                original_driver = m.driver
                m.driver = None

                with mock.patch.object(m, 'gerenciar_janela'):
                    m._init_driver()

                assert m.driver is mock_driver
                m.driver = original_driver  # restaura


def test_smoke():
    """Garante que o módulo de testes carrega sem erros."""
    assert True
