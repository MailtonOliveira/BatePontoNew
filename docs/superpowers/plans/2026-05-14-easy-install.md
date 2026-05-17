# Easy Install — Zero-Config para Usuário Final

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transformar o BatePonto em um produto que o usuário instala e usa sem criar `.env`, obter chaves de API ou entender configurações técnicas.

**Architecture:** Embutir `FERIADOS_API_KEY` como constante no código; mover inicialização do Chrome para uma função `_init_driver()`; adicionar wizard tkinter de dois passos que captura o PIN via monitoramento Selenium; adicionar opção "Alterar PIN" no systray. Todo o código vive em `main.py`.

**Tech Stack:** Python 3, tkinter, Selenium 4, python-dotenv, pystray, pytest + unittest.mock (testes)

---

## Mapa de arquivos

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `main.py` | Modificar | Único arquivo de produção — todas as mudanças aqui |
| `requirements.txt` | Modificar | Adicionar pytest |
| `tests/test_main.py` | Criar | Testes unitários das funções puras/mockáveis |

---

## Task 1: Adicionar pytest ao projeto

**Files:**
- Modify: `requirements.txt`
- Create: `tests/__init__.py`
- Create: `tests/test_main.py`

- [ ] **Step 1: Adicionar pytest ao requirements.txt**

Abrir `requirements.txt` e adicionar ao final:
```
pytest==7.4.0
pytest-mock==3.11.1
```

- [ ] **Step 2: Criar pasta de testes**

```bash
mkdir tests
echo "" > tests/__init__.py
```

- [ ] **Step 3: Criar test_main.py com teste de smoke inicial**

Criar `tests/test_main.py`:
```python
# tests/test_main.py
import sys
import os

# Impede main.py de executar código de nível de módulo ao ser importado
# Fazemos isso mockando os módulos pesados antes do import
import unittest.mock as mock

# Mocks para evitar que main.py abra Chrome, systray, etc. ao importar
sys.modules['pystray'] = mock.MagicMock()
sys.modules['PIL'] = mock.MagicMock()
sys.modules['PIL.Image'] = mock.MagicMock()
sys.modules['PIL.ImageDraw'] = mock.MagicMock()
sys.modules['pygetwindow'] = mock.MagicMock()
sys.modules['pyautogui'] = mock.MagicMock()

# Precisamos de um .env temporário para o import não falhar
import tempfile, pathlib

def test_smoke():
    """Garante que o módulo de testes carrega sem erros."""
    assert True
```

- [ ] **Step 4: Instalar dependências e rodar teste**

```bash
pip install pytest==7.4.0 pytest-mock==3.11.1
pytest tests/test_main.py -v
```

Saída esperada:
```
PASSED tests/test_main.py::test_smoke
1 passed in 0.Xs
```

- [ ] **Step 5: Commit**

```bash
git add requirements.txt tests/
git commit -m "chore: adiciona pytest e estrutura de testes"
```

---

## Task 2: Embutir FERIADOS_API_KEY como constante

**Files:**
- Modify: `main.py` — adicionar constante após o bloco de imports, atualizar uso em `_carregar_feriados_do_ano()`

- [ ] **Step 1: Escrever teste para a constante**

Adicionar ao `tests/test_main.py` (antes do `def test_smoke`):
```python
def test_feriados_api_key_constante_definida():
    """_FERIADOS_API_KEY deve ser uma string não-vazia definida no módulo."""
    import importlib, types

    # Simula .env vazio para o import não falhar por falta de BATEPONTO_SENHA
    with mock.patch.dict(os.environ, {"BATEPONTO_SENHA": "1234"}):
        with mock.patch('selenium.webdriver.Chrome'):
            with mock.patch('pystray.Icon'):
                # Lê apenas a constante sem executar o módulo inteiro
                import ast, pathlib
                source = pathlib.Path('main.py').read_text(encoding='utf-8')
                tree = ast.parse(source)
                constantes = {
                    node.targets[0].id: node.value.s
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Assign)
                    and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id == '_FERIADOS_API_KEY'
                    and isinstance(node.value, ast.Constant)
                }
                assert '_FERIADOS_API_KEY' in constantes
                assert len(constantes['_FERIADOS_API_KEY']) > 0
```

- [ ] **Step 2: Rodar teste — deve FALHAR**

```bash
pytest tests/test_main.py::test_feriados_api_key_constante_definida -v
```

Saída esperada: `FAILED` (constante ainda não existe)

- [ ] **Step 3: Adicionar a constante em main.py**

Em `main.py`, logo após o bloco de imports (depois da linha `import requests`), adicionar:

```python
# ──────────────────────────────────────────────────────────────
# Chave da API de feriados (embutida no build — não exposta ao usuário)
# ──────────────────────────────────────────────────────────────
_FERIADOS_API_KEY = "SUA_CHAVE_AQUI"  # substitua pela chave real antes de buildar
```

- [ ] **Step 4: Atualizar uso em `_carregar_feriados_do_ano()`**

Localizar a linha (dentro de `_carregar_feriados_do_ano`):
```python
headers = {"Authorization": f"Bearer {os.getenv('FERIADOS_API_KEY', '')}"}
```

Substituir por:
```python
headers = {"Authorization": f"Bearer {os.getenv('FERIADOS_API_KEY', _FERIADOS_API_KEY)}"}
```

- [ ] **Step 5: Rodar teste — deve PASSAR**

```bash
pytest tests/test_main.py::test_feriados_api_key_constante_definida -v
```

Saída esperada: `PASSED`

- [ ] **Step 6: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: embutir FERIADOS_API_KEY como constante no build"
```

---

## Task 3: Refatorar inicialização do Chrome em `_init_driver()`

Atualmente `driver = webdriver.Chrome(options=options)` roda no nível de módulo. O wizard precisa abrir o Chrome *depois* de mostrar a tela de boas-vindas. Esta task extrai essa lógica para uma função.

**Files:**
- Modify: `main.py` — criar `_init_driver()`, substituir bloco de inicialização do módulo

- [ ] **Step 1: Escrever teste para _init_driver()**

Adicionar ao `tests/test_main.py`:
```python
def test_init_driver_define_global_driver():
    """_init_driver() deve atribuir um objeto Chrome à variável global driver."""
    import main as m

    mock_driver = mock.MagicMock()
    with mock.patch('selenium.webdriver.Chrome', return_value=mock_driver) as mock_chrome:
        with mock.patch.object(m, 'driver', None):
            with mock.patch.object(m, 'gerenciar_janela'):
                m._init_driver()
                assert m.driver is mock_driver
```

> Nota: este teste só funciona após a Task 3 estar implementada. Escreva-o agora, ele vai falhar — isso é esperado.

- [ ] **Step 2: Rodar para confirmar falha**

```bash
pytest tests/test_main.py::test_init_driver_define_global_driver -v
```

Saída esperada: `FAILED` (função não existe ainda)

- [ ] **Step 3: Refatorar em main.py**

Localizar o bloco de inicialização do Chrome (linhas ~534–551):
```python
options = Options()
appdata_dir = os.environ.get('APPDATA')
user_data_dir = os.path.join(appdata_dir, "BatePonto", "Chrome")
os.makedirs(user_data_dir, exist_ok=True)
options.add_argument(f"--user-data-dir={user_data_dir}")
options.add_argument("--profile-directory=Default")
options.add_argument("--window-size=1280,720")
options.add_argument("--start-maximized")

print("[BatePonto] Abrindo Chrome...")
try:
    driver = webdriver.Chrome(options=options)
    print("[BatePonto] Chrome aberto com sucesso.")
except Exception as e:
    print(f"[BatePonto] ERRO ao abrir Chrome: {e}")
    print("[BatePonto] Verifique se o ChromeDriver está instalado e compatível com a versão do Chrome.")
    print("[BatePonto] Dica: execute 'pip install --upgrade selenium' ou instale o webdriver-manager.")
    sys.exit(1)
```

Substituir por:

```python
driver = None  # inicializado por _init_driver()


def _init_driver():
    """Inicializa o Chrome e navega para a URL do BatePonto."""
    global driver
    options = Options()
    appdata_dir = os.environ.get('APPDATA')
    user_data_dir = os.path.join(appdata_dir, "BatePonto", "Chrome")
    os.makedirs(user_data_dir, exist_ok=True)
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--window-size=1280,720")
    options.add_argument("--start-maximized")

    print("[BatePonto] Abrindo Chrome...")
    try:
        driver = webdriver.Chrome(options=options)
        print("[BatePonto] Chrome aberto com sucesso.")
    except Exception as e:
        print(f"[BatePonto] ERRO ao abrir Chrome: {e}")
        sys.exit(1)

    driver.get(url)
    time.sleep(3)
    gerenciar_janela()
```

- [ ] **Step 4: Localizar o bloco de startup (após a definição de `main_loop`) e substituir**

Localizar (linhas ~676–678):
```python
driver.get(url)
time.sleep(3)
gerenciar_janela()
```

Substituir por:
```python
_init_driver()
```

- [ ] **Step 5: Rodar teste**

```bash
pytest tests/test_main.py::test_init_driver_define_global_driver -v
```

Saída esperada: `PASSED`

- [ ] **Step 6: Verificar que o app ainda funciona manualmente**

Executar `python main.py` — Chrome deve abrir normalmente. Encerrar com Ctrl+C.

- [ ] **Step 7: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "refactor: extrai inicialização do Chrome para _init_driver()"
```

---

## Task 4: Implementar `_monitorar_pin_setup()` — captura do PIN

Esta função roda em uma thread e monitora o campo de PIN no Shadow DOM. Quando o usuário submete o PIN e a página transiciona, retorna o valor capturado.

**Files:**
- Modify: `main.py` — adicionar `_monitorar_pin_setup()` após `_carregar_feriados_do_ano()`

- [ ] **Step 1: Escrever teste para _monitorar_pin_setup()**

Adicionar ao `tests/test_main.py`:
```python
def test_monitorar_pin_setup_retorna_pin_quando_pagina_muda():
    """Deve retornar o PIN capturado quando a página de configuração desaparece."""
    import main as m

    mock_driver = mock.MagicMock()
    # Simula: primeira chamada encontra o campo com PIN "1234",
    # segunda chamada não encontra mais o elemento (página mudou)
    mock_input = mock.MagicMock()
    mock_input.get_attribute.return_value = "1234"
    mock_driver.find_elements.side_effect = [
        [mock.MagicMock()],  # primeira poll: elemento presente
        [],                  # segunda poll: elemento sumiu (submit feito)
    ]
    mock_driver.execute_script.return_value = mock_input

    with mock.patch.object(m, 'driver', mock_driver):
        with mock.patch('time.sleep'):
            resultado = m._monitorar_pin_setup(timeout_segundos=10)

    assert resultado == "1234"


def test_monitorar_pin_setup_retorna_none_no_timeout():
    """Deve retornar None se o PIN não for capturado dentro do timeout."""
    import main as m

    mock_driver = mock.MagicMock()
    mock_driver.find_elements.return_value = []  # página nunca mostra o campo

    with mock.patch.object(m, 'driver', mock_driver):
        with mock.patch('time.sleep'):
            resultado = m._monitorar_pin_setup(timeout_segundos=1)

    assert resultado is None
```

- [ ] **Step 2: Rodar testes — devem FALHAR**

```bash
pytest tests/test_main.py::test_monitorar_pin_setup_retorna_pin_quando_pagina_muda tests/test_main.py::test_monitorar_pin_setup_retorna_none_no_timeout -v
```

Saída esperada: ambos `FAILED`

- [ ] **Step 3: Implementar `_monitorar_pin_setup()` em main.py**

Adicionar após a função `is_holiday()` (por volta da linha 528):

```python
def _monitorar_pin_setup(timeout_segundos=300):
    """
    Monitora o campo de PIN no Shadow DOM durante o setup inicial.
    Retorna o PIN capturado quando a página de configuração desaparece,
    ou None se expirar o timeout.
    """
    seletor_pin = ".pagina-sincronizacao-pin__input-pin"
    pin_capturado = None
    inicio = time.time()

    while time.time() - inicio < timeout_segundos:
        try:
            hosts = driver.find_elements(By.CSS_SELECTOR, seletor_pin)
            if hosts:
                campo = driver.execute_script(
                    "return arguments[0].shadowRoot"
                    " ? arguments[0].shadowRoot.querySelector('input')"
                    " : arguments[0]",
                    hosts[0]
                )
                if campo:
                    val = campo.get_attribute("value") or ""
                    if val:
                        pin_capturado = val
            else:
                # Página de PIN sumiu — usuário submeteu ou navegou
                if pin_capturado:
                    return pin_capturado
        except Exception:
            if pin_capturado:
                return pin_capturado

        time.sleep(0.5)

    return None
```

- [ ] **Step 4: Rodar testes — devem PASSAR**

```bash
pytest tests/test_main.py::test_monitorar_pin_setup_retorna_pin_quando_pagina_muda tests/test_main.py::test_monitorar_pin_setup_retorna_none_no_timeout -v
```

Saída esperada: ambos `PASSED`

- [ ] **Step 5: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: adiciona _monitorar_pin_setup() para captura automática do PIN"
```

---

## Task 5: Implementar `abrir_setup_wizard()`

Janela tkinter de dois passos que guia o usuário no primeiro uso.

**Files:**
- Modify: `main.py` — adicionar `abrir_setup_wizard()` após `abrir_janela_localizacao()`

- [ ] **Step 1: Implementar `abrir_setup_wizard()` em main.py**

Adicionar a função após `abrir_janela_localizacao()` (por volta da linha 475):

```python
def abrir_setup_wizard():
    """
    Wizard de primeiro uso. Roda na thread principal (bloqueia até concluir).
    Abre o Chrome após o usuário clicar em 'Iniciar', monitora o PIN e salva.
    """
    global senha

    root = tk.Tk()
    root.title("Bate Ponto — Configuração Inicial")
    root.resizable(False, False)
    root.attributes('-topmost', True)

    largura, altura = 420, 320
    x = (root.winfo_screenwidth() // 2) - (largura // 2)
    y = (root.winfo_screenheight() // 2) - (altura // 2)
    root.geometry(f"{largura}x{altura}+{x}+{y}")

    root.configure(bg='#2b2b2b')
    style = ttk.Style()
    style.theme_use('clam')
    style.configure('TLabel', background='#2b2b2b', foreground='#ffffff',
                    font=('Segoe UI', 11))
    style.configure('TButton', font=('Segoe UI', 10, 'bold'), padding=8)
    style.configure('Header.TLabel', background='#2b2b2b', foreground='#4CAF50',
                    font=('Segoe UI', 14, 'bold'))
    style.configure('Sub.TLabel', background='#2b2b2b', foreground='#aaaaaa',
                    font=('Segoe UI', 9))

    # ── frame de conteúdo (trocamos o conteúdo sem recriar a janela) ──
    content = tk.Frame(root, bg='#2b2b2b')
    content.pack(fill='both', expand=True, padx=30, pady=20)

    def _limpar():
        for w in content.winfo_children():
            w.destroy()

    # ── Passo 1: Boas-vindas ──────────────────────────────────────────
    def _mostrar_passo1():
        _limpar()
        ttk.Label(content, text="⏰ Bate Ponto", style='Header.TLabel').pack(pady=(0, 10))
        ttk.Label(content, text="Bem-vindo! Vou te guiar pela configuração inicial.",
                  wraplength=360).pack(pady=(0, 6))
        ttk.Label(content,
                  text="Na próxima etapa o Chrome vai abrir o site da Pontotel.\n"
                       "Faça login com seu e-mail e senha.\n"
                       "Quando o site pedir seu PIN, digite normalmente —\n"
                       "o app vai capturá-lo sozinho.",
                  wraplength=360, justify='left').pack(pady=(0, 20))
        ttk.Button(content, text="Iniciar →", command=_iniciar).pack()

    # ── Passo 2: Aguardando PIN ───────────────────────────────────────
    _spinner_chars = ['◐', '◓', '◑', '◒']
    _spinner_idx = [0]
    _spinner_job = [None]
    _monitor_thread = [None]

    def _mostrar_passo2():
        _limpar()
        ttk.Label(content, text="⏰ Bate Ponto", style='Header.TLabel').pack(pady=(0, 10))
        ttk.Label(content, text="Aguardando configuração...",
                  font=('Segoe UI', 11, 'bold'), background='#2b2b2b',
                  foreground='#ffffff').pack(pady=(0, 10))

        instrucoes = [
            "●  Faça login no site da Pontotel",
            "●  Digite seu PIN quando pedido",
            "●  Não feche o Chrome",
        ]
        for txt in instrucoes:
            ttk.Label(content, text=txt, style='Sub.TLabel').pack(anchor='w', pady=1)

        spinner_var = tk.StringVar(value="◐  Detectando PIN...")
        ttk.Label(content, textvariable=spinner_var, style='Sub.TLabel').pack(pady=(16, 0))

        def _tick_spinner():
            _spinner_idx[0] = (_spinner_idx[0] + 1) % len(_spinner_chars)
            spinner_var.set(f"{_spinner_chars[_spinner_idx[0]]}  Detectando PIN...")
            _spinner_job[0] = root.after(300, _tick_spinner)

        _tick_spinner()

        ttk.Button(content, text="Cancelar", command=_cancelar).pack(pady=(20, 0))

        # Thread de monitoramento
        def _thread_monitoramento():
            pin = _monitorar_pin_setup(timeout_segundos=300)
            root.after(0, lambda: _on_pin_resultado(pin))

        _monitor_thread[0] = threading.Thread(target=_thread_monitoramento, daemon=True)
        _monitor_thread[0].start()

    # ── Conclusão ─────────────────────────────────────────────────────
    def _mostrar_conclusao():
        if _spinner_job[0]:
            root.after_cancel(_spinner_job[0])
        _limpar()
        ttk.Label(content, text="⏰ Bate Ponto", style='Header.TLabel').pack(pady=(0, 10))
        ttk.Label(content, text="✅ Configuração concluída!",
                  font=('Segoe UI', 13, 'bold'), background='#2b2b2b',
                  foreground='#4CAF50').pack(pady=(0, 10))
        ttk.Label(content,
                  text="Seu PIN foi salvo com sucesso.\n"
                       "O app está rodando em segundo plano —\n"
                       "veja o ícone na bandeja do sistema.",
                  wraplength=360, justify='center').pack(pady=(0, 20))
        ttk.Button(content, text="Fechar", command=root.destroy).pack()

    # ── Fallback: PIN não capturado ───────────────────────────────────
    def _mostrar_fallback():
        if _spinner_job[0]:
            root.after_cancel(_spinner_job[0])
        _limpar()
        ttk.Label(content, text="⏰ Bate Ponto", style='Header.TLabel').pack(pady=(0, 10))
        ttk.Label(content,
                  text="Não consegui capturar o PIN automaticamente.\n"
                       "Digite-o manualmente:",
                  wraplength=360, justify='center').pack(pady=(0, 10))
        var_pin = tk.StringVar()
        entry = ttk.Entry(content, textvariable=var_pin, width=12, justify='center',
                          font=('Segoe UI', 14), show='*')
        entry.pack(pady=(0, 16))
        entry.focus()

        def _salvar_manual():
            pin = var_pin.get().strip()
            if not pin:
                messagebox.showerror("PIN inválido", "O PIN não pode ser vazio.", parent=root)
                return
            _salvar_pin(pin)
            _mostrar_conclusao()

        ttk.Button(content, text="💾 Salvar", command=_salvar_manual).pack()

    # ── Erro: Chrome fechado ──────────────────────────────────────────
    def _mostrar_erro_chrome():
        if _spinner_job[0]:
            root.after_cancel(_spinner_job[0])
        _limpar()
        ttk.Label(content, text="⏰ Bate Ponto", style='Header.TLabel').pack(pady=(0, 10))
        ttk.Label(content, text="O Chrome foi fechado antes de concluir.",
                  wraplength=360, justify='center').pack(pady=(0, 10))
        ttk.Button(content, text="Tentar novamente", command=_reiniciar).pack(pady=(0, 6))
        ttk.Button(content, text="Cancelar", command=_cancelar).pack()

    # ── Callbacks ─────────────────────────────────────────────────────
    def _salvar_pin(pin):
        global senha
        set_key(ENV_PATH, "BATEPONTO_SENHA", pin)
        senha = pin
        registrar_log("PIN capturado e salvo durante setup inicial.")

    def _iniciar():
        try:
            _init_driver()
        except SystemExit:
            _mostrar_erro_chrome()
            return
        _mostrar_passo2()

    def _reiniciar():
        try:
            _init_driver()
        except SystemExit:
            _mostrar_erro_chrome()
            return
        _mostrar_passo2()

    def _cancelar():
        if _spinner_job[0]:
            root.after_cancel(_spinner_job[0])
        try:
            if driver:
                driver.quit()
        except Exception:
            pass
        root.destroy()
        os._exit(0)

    def _on_pin_resultado(pin):
        if pin:
            _salvar_pin(pin)
            _mostrar_conclusao()
        else:
            try:
                driver.find_elements(By.CSS_SELECTOR, "body")
                _mostrar_fallback()
            except Exception:
                _mostrar_erro_chrome()

    # ── Inicia no Passo 1 ─────────────────────────────────────────────
    _mostrar_passo1()
    root.mainloop()
```

- [ ] **Step 2: Verificação manual — Passo 1**

Temporariamente, em `main.py`, antes da linha `_init_driver()` no bloco de startup, adicionar:
```python
abrir_setup_wizard()
```
Executar `python main.py`. A janela de boas-vindas deve aparecer. Fechar sem clicar em nada. O app deve encerrar.

Remover a linha temporária após a verificação.

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: adiciona wizard de configuração inicial (abrir_setup_wizard)"
```

---

## Task 6: Implementar `abrir_janela_alterar_pin()`

Janela simples para troca de PIN via systray após o setup inicial.

**Files:**
- Modify: `main.py` — adicionar função após `abrir_setup_wizard()`, adicionar item no menu systray

- [ ] **Step 1: Implementar `abrir_janela_alterar_pin()` em main.py**

Adicionar após `abrir_setup_wizard()`:

```python
def abrir_janela_alterar_pin():
    """Abre janela para alterar o PIN armazenado no .env."""

    def _criar_janela():
        global senha

        root = tk.Tk()
        root.title("Alterar PIN")
        root.resizable(False, False)
        root.attributes('-topmost', True)

        largura, altura = 320, 220
        x = (root.winfo_screenwidth() // 2) - (largura // 2)
        y = (root.winfo_screenheight() // 2) - (altura // 2)
        root.geometry(f"{largura}x{altura}+{x}+{y}")

        root.configure(bg='#2b2b2b')
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TLabel', background='#2b2b2b', foreground='#ffffff',
                        font=('Segoe UI', 11))
        style.configure('TButton', font=('Segoe UI', 10, 'bold'), padding=6)
        style.configure('Header.TLabel', background='#2b2b2b', foreground='#4CAF50',
                        font=('Segoe UI', 13, 'bold'))

        ttk.Label(root, text="🔑 Alterar PIN", style='Header.TLabel').pack(pady=(18, 12))
        ttk.Label(root, text="Novo PIN:").pack()

        var_pin = tk.StringVar()
        entry = ttk.Entry(root, textvariable=var_pin, width=14, justify='center',
                          font=('Segoe UI', 13), show='*')
        entry.pack(pady=(4, 16))
        entry.focus()

        def salvar():
            global senha
            pin = var_pin.get().strip()
            if not pin:
                messagebox.showerror("PIN inválido", "O PIN não pode ser vazio.", parent=root)
                return
            set_key(ENV_PATH, "BATEPONTO_SENHA", pin)
            senha = pin
            registrar_log("PIN alterado via systray.")
            messagebox.showinfo("Salvo ✅", "PIN atualizado com sucesso!", parent=root)
            root.destroy()

        btn_frame = ttk.Frame(root, style='TLabel')
        btn_frame.pack()
        ttk.Button(btn_frame, text="💾 Salvar", command=salvar).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=root.destroy).pack(side='left', padx=5)

        root.mainloop()

    threading.Thread(target=_criar_janela, daemon=True).start()
```

- [ ] **Step 2: Adicionar callback e item no menu do systray**

Localizar a função `configurar_localizacao_systray`:
```python
def configurar_localizacao_systray(icon, item):
    abrir_janela_localizacao()
```

Logo após ela, adicionar:
```python
def alterar_pin_systray(icon, item):
    abrir_janela_alterar_pin()
```

- [ ] **Step 3: Atualizar o menu do systray**

Localizar:
```python
icon = pystray.Icon("bateponto", create_image(), "Bate Ponto", menu=pystray.Menu(
    pystray.MenuItem("⏰ Configurar Horários", configurar_horarios_systray),
    pystray.MenuItem("📍 Configurar Localização", configurar_localizacao_systray),
    pystray.MenuItem("Último Log", mostrar_ultimo_log),
    pystray.MenuItem("Sair", on_systray_exit)
))
```

Substituir por:
```python
icon = pystray.Icon("bateponto", create_image(), "Bate Ponto", menu=pystray.Menu(
    pystray.MenuItem("⏰ Configurar Horários", configurar_horarios_systray),
    pystray.MenuItem("📍 Configurar Localização", configurar_localizacao_systray),
    pystray.MenuItem("🔑 Alterar PIN", alterar_pin_systray),
    pystray.MenuItem("Último Log", mostrar_ultimo_log),
    pystray.MenuItem("Sair", on_systray_exit)
))
```

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: adiciona opção 'Alterar PIN' no menu do systray"
```

---

## Task 7: Atualizar sequência de startup — gate de primeiro uso

Substitui o bloco `if not senha: sys.exit(1)` pelo dispatch para o wizard.

**Files:**
- Modify: `main.py` — bloco de verificação de senha (~linha 46) e bloco de startup (~linha 676)

- [ ] **Step 1: Localizar e substituir o bloco de erro de senha**

Localizar (linhas ~46–51):
```python
if not senha:
    pyautogui.alert(
        "BATEPONTO_SENHA não configurada!\nCrie um arquivo .env ao lado do executável.",
        title="Bate Ponto — Erro"
    )
    sys.exit(1)
```

Substituir por:
```python
_primeiro_uso = not senha
```

- [ ] **Step 2: Atualizar o bloco de startup**

Localizar o bloco de startup (logo antes de `threading.Thread(target=main_loop...)`):
```python
_init_driver()
```

Substituir por:
```python
if _primeiro_uso:
    abrir_setup_wizard()

_init_driver() if not _primeiro_uso else None
```

> **Atenção:** quando `_primeiro_uso` é True, `abrir_setup_wizard()` já chama `_init_driver()` internamente (ao clicar em "Iniciar"). Por isso o `_init_driver()` abaixo só deve rodar se NÃO for primeiro uso. O bloco acima garante isso.

O bloco final de startup deve ficar assim:
```python
if _primeiro_uso:
    abrir_setup_wizard()
else:
    _init_driver()

threading.Thread(target=main_loop, daemon=True).start()

icon = pystray.Icon(...)
icon.run()
```

- [ ] **Step 3: Verificação manual — fluxo de primeiro uso**

1. Renomear temporariamente o `.env` para `.env.bak` (se existir)
2. Executar `python main.py`
3. **Esperado:** Wizard de boas-vindas abre
4. Clicar "Iniciar →" — Chrome deve abrir com o site da Pontotel
5. **Esperado:** Passo 2 aparece com spinner
6. Fazer login no site e digitar o PIN
7. **Esperado:** Wizard fecha mostrando "✅ Configuração concluída!"
8. Verificar que `.env` foi criado com `BATEPONTO_SENHA=<seu_pin>`
9. Restaurar `.env.bak` se necessário

- [ ] **Step 4: Verificação manual — fluxo normal (já configurado)**

1. Com `.env` contendo `BATEPONTO_SENHA`, executar `python main.py`
2. **Esperado:** Chrome abre diretamente, sem wizard
3. Ícone aparece no systray
4. Menu systray → "🔑 Alterar PIN" — janela deve abrir

- [ ] **Step 5: Rodar todos os testes**

```bash
pytest tests/ -v
```

Saída esperada: todos `PASSED`

- [ ] **Step 6: Commit final**

```bash
git add main.py
git commit -m "feat: wizard de primeiro uso substitui erro de startup sem .env"
```

---

## Task 8: Build e verificação do executável

**Files:**
- Modify: `main.spec` — garantir que não inclui `.env` no bundle (correto já hoje)

- [ ] **Step 1: Substituir a chave placeholder pela chave real**

Em `main.py`, linha com `_FERIADOS_API_KEY`:
```python
_FERIADOS_API_KEY = "SUA_CHAVE_AQUI"
```
Substituir `"SUA_CHAVE_AQUI"` pela chave real da feriadosapi.com.

- [ ] **Step 2: Gerar o executável**

```bash
pyinstaller main.spec
```

Saída esperada: `dist/BatePonto-1.0.exe` gerado sem erros.

- [ ] **Step 3: Verificar que o .exe não contém o .env**

O `main.spec` atual não inclui `datas=[]` com `.env` — correto. Confirmar que o `.env` não está dentro do `dist/`.

```bash
ls dist/
```

Deve conter apenas `BatePonto-1.0.exe` (sem `.env`).

- [ ] **Step 4: Teste de smoke do executável**

1. Copiar `dist/BatePonto-1.0.exe` para uma pasta limpa (sem `.env`)
2. Executar o `.exe`
3. **Esperado:** Wizard de boas-vindas abre
4. Encerrar o wizard (Cancelar) — app fecha
5. Executar novamente com `.env` contendo `BATEPONTO_SENHA`
6. **Esperado:** Chrome abre diretamente, sem wizard

- [ ] **Step 5: Commit de release**

```bash
git add main.py
git commit -m "build: chave de feriados embutida, pronto para distribuição"
```

---

## Checklist de cobertura da spec

| Requisito da spec | Task que cobre |
|---|---|
| `_FERIADOS_API_KEY` embutida como constante | Task 2 |
| Fallback `os.getenv(..., _FERIADOS_API_KEY)` | Task 2 |
| Detecção de primeiro uso (`_primeiro_uso`) | Task 7 |
| Wizard Passo 1 — boas-vindas | Task 5 |
| Wizard Passo 2 — spinner + instruções | Task 5 |
| Chrome abre ao clicar "Iniciar" | Task 5 + Task 3 |
| Captura PIN via Shadow DOM | Task 4 |
| Salva PIN no `.env` e variável global | Task 5 |
| Tela de conclusão inline | Task 5 |
| Fallback manual se PIN não capturado | Task 5 |
| Erro se Chrome for fechado | Task 5 |
| Cancelar encerra o app | Task 5 |
| Opção "Alterar PIN" no systray | Task 6 |
| Visual consistente (#2b2b2b, #4CAF50) | Tasks 5, 6 |
| Fluxo normal inalterado quando senha existe | Task 7 |
