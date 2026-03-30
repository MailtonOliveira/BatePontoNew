import pystray
from PIL import Image, ImageDraw
import threading
import os
import sys
import time
import datetime
import tempfile
import re
import tkinter as tk
from tkinter import ttk, messagebox

from dotenv import load_dotenv, set_key
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pygetwindow as gw
import pyautogui

# ──────────────────────────────────────────────────────────────
# Carregar .env
# ──────────────────────────────────────────────────────────────

def get_env_path():
    """Retorna o caminho do .env, considerando exe (PyInstaller) ou script."""
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, '.env')

ENV_PATH = get_env_path()
load_dotenv(ENV_PATH)

senha = os.getenv("BATEPONTO_SENHA", "")
url = os.getenv("BATEPONTO_URL", "https://bateponto.pontotel.com.br/")
timeout_padrao = int(os.getenv("TIMEOUT_PADRAO", "15"))
intervalo_execucao = int(os.getenv("INTERVALO_EXECUCAO", "60"))

if not senha:
    pyautogui.alert(
        "BATEPONTO_SENHA não configurada!\nCrie um arquivo .env ao lado do executável.",
        title="Bate Ponto — Erro"
    )
    sys.exit(1)

# ──────────────────────────────────────────────────────────────
# Horários (thread-safe)
# ──────────────────────────────────────────────────────────────

_lock = threading.Lock()
_horarios = {}


def _carregar_horarios_do_env():
    """Carrega os 4 horários a partir das variáveis de ambiente."""
    return {
        os.getenv("HORARIO_ENTRADA", "08:00"): {
            'seletor': 'pontotel-botao-ponto[tipo="entrada"]',
            'nome': 'Entrada',
            'chave_env': 'HORARIO_ENTRADA'
        },
        os.getenv("HORARIO_PAUSA", "12:50"): {
            'seletor': 'pontotel-botao-ponto[tipo="pausa"]',
            'nome': 'Pausa',
            'chave_env': 'HORARIO_PAUSA'
        },
        os.getenv("HORARIO_RETORNO", "13:50"): {
            'seletor': 'pontotel-botao-ponto[tipo="retorno"]',
            'nome': 'Retorno',
            'chave_env': 'HORARIO_RETORNO'
        },
        os.getenv("HORARIO_SAIDA", "17:00"): {
            'seletor': 'pontotel-botao-ponto[tipo="saida"]',
            'nome': 'Saída',
            'chave_env': 'HORARIO_SAIDA'
        },
    }


def get_horarios():
    with _lock:
        return dict(_horarios)


def set_horarios(novos):
    with _lock:
        _horarios.clear()
        _horarios.update(novos)


# Carrega horários iniciais
set_horarios(_carregar_horarios_do_env())

# ──────────────────────────────────────────────────────────────
# Ícone do SysTray
# ──────────────────────────────────────────────────────────────

def create_image():
    image = Image.new('RGB', (64, 64), color=(76, 175, 80))
    draw = ImageDraw.Draw(image)
    draw.rectangle((16, 16, 48, 48), fill=(255, 255, 255))
    return image

# ──────────────────────────────────────────────────────────────
# Logs
# ──────────────────────────────────────────────────────────────

def get_logs_path():
    temp_dir = os.path.join(tempfile.gettempdir(), "BatePonto")
    os.makedirs(temp_dir, exist_ok=True)
    return os.path.join(temp_dir, "logs_bateponto.txt")

logs_path = get_logs_path()


def registrar_log(msg):
    timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    with open(logs_path, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(msg)

# ──────────────────────────────────────────────────────────────
# Janela tkinter — Configurar Horários
# ──────────────────────────────────────────────────────────────

def _extrair_horarios_por_nome():
    """Retorna dict {nome: horario} a partir dos horários atuais."""
    horarios = get_horarios()
    resultado = {}
    for horario, info in horarios.items():
        resultado[info['nome']] = horario
    return resultado


def _validar_horario(valor):
    """Retorna True se valor está no formato HH:MM válido."""
    if not re.match(r'^\d{2}:\d{2}$', valor):
        return False
    h, m = valor.split(':')
    return 0 <= int(h) <= 23 and 0 <= int(m) <= 59


NOMES_PONTOS = [
    ('Entrada', 'HORARIO_ENTRADA', 'pontotel-botao-ponto[tipo="entrada"]'),
    ('Pausa',   'HORARIO_PAUSA',   'pontotel-botao-ponto[tipo="pausa"]'),
    ('Retorno', 'HORARIO_RETORNO', 'pontotel-botao-ponto[tipo="retorno"]'),
    ('Saída',   'HORARIO_SAIDA',   'pontotel-botao-ponto[tipo="saida"]'),
]


def abrir_janela_configuracao():
    """Abre janela tkinter para configurar os 4 horários."""

    def _criar_janela():
        atuais = _extrair_horarios_por_nome()

        root = tk.Tk()
        root.title("Configurar Horários")
        root.resizable(False, False)
        root.attributes('-topmost', True)

        # Centralizar janela
        largura, altura = 340, 280
        x = (root.winfo_screenwidth() // 2) - (largura // 2)
        y = (root.winfo_screenheight() // 2) - (altura // 2)
        root.geometry(f"{largura}x{altura}+{x}+{y}")

        # Estilo
        root.configure(bg='#2b2b2b')
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TLabel', background='#2b2b2b', foreground='#ffffff', font=('Segoe UI', 11))
        style.configure('TEntry', font=('Segoe UI', 11))
        style.configure('TButton', font=('Segoe UI', 10, 'bold'), padding=6)
        style.configure('Header.TLabel', background='#2b2b2b', foreground='#4CAF50',
                        font=('Segoe UI', 13, 'bold'))

        # Header
        header = ttk.Label(root, text="⏰ Horários dos Pontos", style='Header.TLabel')
        header.pack(pady=(15, 10))

        frame = ttk.Frame(root, style='TLabel')
        frame.pack(padx=20, fill='x')

        entradas = {}
        for i, (nome, chave_env, seletor) in enumerate(NOMES_PONTOS):
            lbl = ttk.Label(frame, text=f"{nome}:")
            lbl.grid(row=i, column=0, sticky='w', pady=5, padx=(0, 10))

            var = tk.StringVar(value=atuais.get(nome, '00:00'))
            entry = ttk.Entry(frame, textvariable=var, width=8, justify='center',
                              font=('Segoe UI', 12))
            entry.grid(row=i, column=1, pady=5)
            entradas[nome] = (var, chave_env, seletor)

        def salvar():
            novos_horarios = {}
            for nome, (var, chave_env, seletor) in entradas.items():
                valor = var.get().strip()
                if not _validar_horario(valor):
                    messagebox.showerror(
                        "Formato inválido",
                        f"O horário de '{nome}' deve estar no formato HH:MM.\nValor informado: {valor}",
                        parent=root
                    )
                    return

                novos_horarios[valor] = {
                    'seletor': seletor,
                    'nome': nome,
                    'chave_env': chave_env
                }

                # Atualiza .env em disco
                set_key(ENV_PATH, chave_env, valor)

            # Propaga em tempo real na memória
            set_horarios(novos_horarios)

            resumo = ', '.join(f"{info['nome']}={h}" for h, info in novos_horarios.items() if 'nome' in info)
            registrar_log(f"Horários atualizados via UI: {resumo}")

            messagebox.showinfo(
                "Salvo ✅",
                "Horários atualizados com sucesso!\nAs alterações já estão ativas.",
                parent=root
            )
            root.destroy()

        btn_frame = ttk.Frame(root, style='TLabel')
        btn_frame.pack(pady=15)

        btn_salvar = ttk.Button(btn_frame, text="💾 Salvar", command=salvar)
        btn_salvar.pack(side='left', padx=5)

        btn_cancelar = ttk.Button(btn_frame, text="Cancelar", command=root.destroy)
        btn_cancelar.pack(side='left', padx=5)

        root.mainloop()

    threading.Thread(target=_criar_janela, daemon=True).start()

# ──────────────────────────────────────────────────────────────
# Funções de horário
# ──────────────────────────────────────────────────────────────

def horario_valido():
    agora = datetime.datetime.now().strftime("%H:%M")
    horarios = get_horarios()
    return agora if agora in horarios else None

# ──────────────────────────────────────────────────────────────
# Selenium setup
# ──────────────────────────────────────────────────────────────

options = Options()
appdata_dir = os.environ.get('APPDATA')
user_data_dir = os.path.join(appdata_dir, "BatePonto", "Chrome")
os.makedirs(user_data_dir, exist_ok=True)
options.add_argument(f"--user-data-dir={user_data_dir}")
options.add_argument("--profile-directory=Default")
options.add_argument("--window-size=1280,720")
options.add_argument("--start-maximized")
driver = webdriver.Chrome(options=options)

# ──────────────────────────────────────────────────────────────
# Fluxo principal (inalterado na lógica)
# ──────────────────────────────────────────────────────────────

def preencher_senha():
    try:
        wait = WebDriverWait(driver, 10)
        host = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, ".pagina-sincronizacao-pin__input-pin")))
        campo = driver.execute_script(
            "return arguments[0].shadowRoot ? arguments[0].shadowRoot.querySelector('input') : arguments[0]",
            host)
        if campo:
            campo.clear()
            for digito in senha:
                campo.send_keys(digito)
                time.sleep(0.1)
            registrar_log("Senha preenchida.")
            return True
        else:
            registrar_log("Elemento input interno não encontrado no Shadow DOM.")
            return False
    except Exception as e:
        registrar_log(f"Campo de senha não encontrado. Erro: {type(e).__name__}")
        return False


def clicar_confirmar_pin():
    try:
        wait = WebDriverWait(driver, 10)
        host = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, ".pagina-sincronizacao-pin__botao-confirmar")))
        botao = driver.execute_script(
            "return arguments[0].shadowRoot ? arguments[0].shadowRoot.querySelector('button') : arguments[0]",
            host)
        if botao:
            driver.execute_script("arguments[0].click();", botao)
            registrar_log("Botão confirmar PIN clicado (via JS).")
            return True
        else:
            registrar_log("Elemento button interno não encontrado no Shadow DOM.")
            return False
    except Exception as e:
        registrar_log(f"Botão confirmar PIN não encontrado. Erro: {type(e).__name__}")
        return False


def clicar_opcao(horario_atual):
    horarios = get_horarios()
    seletor = horarios[horario_atual]["seletor"]
    nome = horarios[horario_atual]["nome"]
    hoje_str = datetime.datetime.now().strftime("%d.%m.%y")

    try:
        for _ in range(timeout_padrao):
            botoes = driver.find_elements(By.CSS_SELECTOR, seletor)
            if botoes:
                host = botoes[0]

                # Verificação de ponto duplicado
                ultimo_ponto = host.get_attribute("ultimo-ponto")
                if ultimo_ponto and ultimo_ponto.startswith(hoje_str):
                    msg = f"Aviso: Ponto '{nome}' já foi registrado hoje ({ultimo_ponto}). Ignorando novo clique."
                    registrar_log(msg)
                    return True

                botao_interno = driver.execute_script(
                    "return arguments[0].shadowRoot ? arguments[0].shadowRoot.querySelector('button') : arguments[0]",
                    host)
                if botao_interno:
                    driver.execute_script("arguments[0].click();", botao_interno)
                else:
                    driver.execute_script("arguments[0].click();", host)

                msg = f"Opção '{nome}' selecionada. Página será reiniciada."
                registrar_log(msg)
                return True
            time.sleep(1)

        msg = f"Timeout ({timeout_padrao}s): botão '{nome}' não encontrado. Página será reiniciada."
        registrar_log(msg)
        pyautogui.alert(msg, title="Bate Ponto")
        return False
    except Exception as e:
        msg = f"Erro ao tentar clicar na opção '{nome}': {str(e)}. Página será reiniciada."
        registrar_log(msg)
        pyautogui.alert(msg, title="Bate Ponto")
        return False

# ──────────────────────────────────────────────────────────────
# Gerenciamento de janela
# ──────────────────────────────────────────────────────────────

janela_visivel = None


def gerenciar_janela():
    global janela_visivel
    try:
        elementos_prontos = driver.find_elements(
            By.CSS_SELECTOR, ".pagina-sincronizacao-pin__input-pin, pontotel-botao-ponto")

        if elementos_prontos:
            if janela_visivel is not False:
                driver.set_window_position(10000, 10000)
                registrar_log("Configuração concluída. Janela oculta.")
                janela_visivel = False
            return False
        else:
            if janela_visivel is not True:
                driver.set_window_position(50, 50)
                registrar_log("Aguardando configuração manual (Login ou Setup). Janela exibida.")
                janela_visivel = True
            return True
    except Exception as e:
        registrar_log(f"Erro ao gerenciar janela: {e}")
        return False


def executar_fluxo():
    esperando_setup = gerenciar_janela()
    if esperando_setup:
        return True

    horario_atual = horario_valido()
    if not horario_atual:
        return False

    registrar_log(f"Horário válido detectado: {horario_atual}")
    try:
        if preencher_senha():
            time.sleep(1)
            if clicar_confirmar_pin():
                time.sleep(2)
                if clicar_opcao(horario_atual):
                    time.sleep(5)
                    driver.refresh()
    except Exception as e:
        registrar_log(f"Erro inesperado: {str(e)}")

    return False

# ──────────────────────────────────────────────────────────────
# Startup
# ──────────────────────────────────────────────────────────────

driver.get(url)
time.sleep(3)
gerenciar_janela()


def focar_janela_do_chrome():
    try:
        time.sleep(3)
        janelas = gw.getWindowsWithTitle('Chrome')
        for janela in janelas:
            if 'Pontotel' in janela.title or 'Chrome' in janela.title:
                janela.activate()
                break
    except Exception as e:
        registrar_log(f"Erro ao focar janela: {e}")


def main_loop():
    registrar_log("Script iniciado e monitorando horários...")
    horarios = get_horarios()
    resumo = ', '.join(f"{info['nome']}={h}" for h, info in horarios.items())
    registrar_log(f"Horários configurados: {resumo}")
    focar_janela_do_chrome()
    try:
        while True:
            esperando_setup = executar_fluxo()
            if esperando_setup:
                time.sleep(5)
            else:
                time.sleep(intervalo_execucao)
    except KeyboardInterrupt:
        registrar_log("Execução interrompida pelo usuário.")
        driver.quit()

# ──────────────────────────────────────────────────────────────
# SysTray
# ──────────────────────────────────────────────────────────────

def on_systray_exit(icon, item):
    registrar_log("Encerrando pelo systray.")
    icon.stop()
    driver.quit()
    sys.exit()


def mostrar_ultimo_log(icon, item):
    def exibir_alerta():
        try:
            if os.path.exists(logs_path):
                with open(logs_path, "r", encoding="utf-8") as f:
                    linhas = f.readlines()
                    if linhas:
                        ultimo_log = linhas[-1].strip()
                    else:
                        ultimo_log = "Log vazio."
            else:
                ultimo_log = "Arquivo de log não encontrado."
        except Exception as e:
            ultimo_log = f"Erro ao ler o log: {str(e)}"
        pyautogui.alert(ultimo_log, title="Último Log")
    threading.Thread(target=exibir_alerta).start()


def configurar_horarios_systray(icon, item):
    abrir_janela_configuracao()


threading.Thread(target=main_loop, daemon=True).start()

icon = pystray.Icon("bateponto", create_image(), "Bate Ponto", menu=pystray.Menu(
    pystray.MenuItem("⏰ Configurar Horários", configurar_horarios_systray),
    pystray.MenuItem("Último Log", mostrar_ultimo_log),
    pystray.MenuItem("Sair", on_systray_exit)
))

icon.run()
