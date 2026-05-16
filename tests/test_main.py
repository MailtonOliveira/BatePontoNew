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

sys.modules['selenium'] = mock.MagicMock()
sys.modules['selenium.webdriver'] = mock.MagicMock()
sys.modules['selenium.webdriver.chrome'] = mock.MagicMock()
sys.modules['selenium.webdriver.chrome.options'] = mock.MagicMock()
sys.modules['selenium.webdriver.common'] = mock.MagicMock()
sys.modules['selenium.webdriver.common.by'] = mock.MagicMock()
sys.modules['selenium.webdriver.support'] = mock.MagicMock()
sys.modules['selenium.webdriver.support.ui'] = mock.MagicMock()
sys.modules['selenium.webdriver.support.expected_conditions'] = mock.MagicMock()


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


def test_calcular_pascoa_datas_conhecidas():
    """Algoritmo de Butcher deve bater com datas históricas conhecidas."""
    import datetime
    import main as m
    assert m._calcular_pascoa(2024) == datetime.date(2024, 3, 31)
    assert m._calcular_pascoa(2025) == datetime.date(2025, 4, 20)
    assert m._calcular_pascoa(2023) == datetime.date(2023, 4, 9)
    assert m._calcular_pascoa(2022) == datetime.date(2022, 4, 17)


def test_feriados_nacionais_fallback_contem_datas_fixas():
    """Fallback deve incluir todos os feriados nacionais fixos."""
    import main as m
    datas = m._feriados_nacionais_fallback(2025)
    assert "2025-01-01" in datas   # Confraternização
    assert "2025-04-21" in datas   # Tiradentes
    assert "2025-05-01" in datas   # Dia do Trabalho
    assert "2025-09-07" in datas   # Independência
    assert "2025-10-12" in datas   # Nossa Senhora Aparecida
    assert "2025-11-02" in datas   # Finados
    assert "2025-11-15" in datas   # Proclamação da República
    assert "2025-11-20" in datas   # Consciência Negra
    assert "2025-12-25" in datas   # Natal


def test_feriados_estaduais_cobre_todas_ufs():
    """FERIADOS_ESTADUAIS deve ter entrada para todas as 27 UFs."""
    import main as m
    ufs_esperadas = {
        "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA",
        "MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN",
        "RO","RR","RS","SC","SE","SP","TO"
    }
    assert ufs_esperadas == set(m.FERIADOS_ESTADUAIS.keys())


def test_ibge_capitais_cobre_todas_ufs():
    """IBGE_CAPITAIS deve ter entrada para todas as 27 UFs."""
    import main as m
    ufs_esperadas = {
        "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA",
        "MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN",
        "RO","RR","RS","SC","SE","SP","TO"
    }
    assert ufs_esperadas == set(m.IBGE_CAPITAIS.keys())


def test_feriados_municipais_capitais_cobre_todas_ufs():
    """FERIADOS_MUNICIPAIS_CAPITAIS deve ter entrada para todas as 27 UFs."""
    import main as m
    ufs_esperadas = {
        "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA",
        "MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN",
        "RO","RR","RS","SC","SE","SP","TO"
    }
    assert ufs_esperadas == set(m.FERIADOS_MUNICIPAIS_CAPITAIS.keys())


def test_feriados_bh_inclui_padroeira():
    """BH deve ter Nossa Senhora da Boa Viagem (15/08) e aniversário (12/12)."""
    import main as m
    municipais_mg = m.FERIADOS_MUNICIPAIS_CAPITAIS["MG"]
    datas = [(mes, dia) for mes, dia, _ in municipais_mg]
    assert (8, 15) in datas, "Falta Nossa Senhora da Boa Viagem (15/08)"
    assert (12, 12) in datas, "Falta Aniversário de BH (12/12)"


def test_feriados_nacionais_fallback_contem_datas_variaveis():
    """Fallback deve incluir Carnaval e Corpus Christi derivados da Páscoa."""
    import main as m
    # Páscoa 2025 = 20/04; Carnaval seg = -48 = 03/03; ter = -47 = 04/03
    # Sexta Santa = -2 = 18/04; Corpus Christi = +60 = 19/06
    datas = m._feriados_nacionais_fallback(2025)
    assert "2025-03-03" in datas   # Carnaval segunda
    assert "2025-03-04" in datas   # Carnaval terça
    assert "2025-04-18" in datas   # Sexta-feira Santa
    assert "2025-06-19" in datas   # Corpus Christi
