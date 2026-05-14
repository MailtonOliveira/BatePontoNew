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
    assert constantes['_FERIADOS_API_KEY'] != "SUA_CHAVE_AQUI", (
        "Substitua _FERIADOS_API_KEY pela chave real antes de buildar!"
    )


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


def test_monitorar_pin_setup_retorna_pin_quando_pagina_muda():
    """Deve retornar o PIN capturado quando a página de configuração desaparece."""
    import main as m
    import unittest.mock as mock

    mock_driver = mock.MagicMock()
    mock_input = mock.MagicMock()
    mock_input.get_attribute.return_value = "1234"

    # Primeira poll: elemento presente com PIN; segunda: elemento sumiu
    mock_driver.find_elements.side_effect = [
        [mock.MagicMock()],  # página de PIN presente
        [],                  # página sumiu (usuário submeteu)
    ]
    mock_driver.execute_script.return_value = mock_input

    with mock.patch.object(m, 'driver', mock_driver):
        with mock.patch('time.sleep'):
            resultado = m._monitorar_pin_setup(timeout_segundos=10)

    assert resultado == "1234"


def test_monitorar_pin_setup_retorna_none_no_timeout():
    """Deve retornar None se o PIN não for capturado dentro do timeout."""
    import main as m
    import unittest.mock as mock

    mock_driver = mock.MagicMock()
    mock_driver.find_elements.return_value = []  # campo nunca aparece

    with mock.patch.object(m, 'driver', mock_driver):
        with mock.patch('time.sleep'):
            with mock.patch('time.time', side_effect=[0, 0, 2]):  # simula timeout imediato
                resultado = m._monitorar_pin_setup(timeout_segundos=1)

    assert resultado is None


def test_smoke():
    """Garante que o módulo de testes carrega sem erros."""
    assert True
