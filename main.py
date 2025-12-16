import pystray
from PIL import Image, ImageDraw
import threading
import os
import sys
import time
import datetime
import tempfile

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import pygetwindow as gw
import pyautogui

senha = "01630290670"
url = "https://bateponto.pontotel.com.br/"
timeout_padrao = 15
intervalo_execucao = 60

def create_image():
    image = Image.new('RGB', (64, 64), color=(76, 175, 80))
    draw = ImageDraw.Draw(image)
    draw.rectangle((16, 16, 48, 48), fill=(255, 255, 255))
    return image

def get_logs_path():
    temp_dir = os.path.join(tempfile.gettempdir(), "BatePonto")
    os.makedirs(temp_dir, exist_ok=True)
    return os.path.join(temp_dir, "logs_bateponto.txt")

logs_path = get_logs_path()

horarios_permitidos = {
    "08:00": {'seletor': 'button.btn-success .kind-number', 'nome': 'Entrada'},
    "12:50": {'seletor': 'button.btn-info .kind-number', 'nome': 'Pausa'},
    "13:50": {'seletor': 'button.btn-warning .kind-number', 'nome': 'Retorno'},
    "17:00": {'seletor': 'button.btn-danger .kind-number', 'nome': 'Saída'}
}

def registrar_log(msg):
    timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    with open(logs_path, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(msg)

def horario_valido():
    agora = datetime.datetime.now().strftime("%H:%M")
    return agora if agora in horarios_permitidos else None

options = Options()
user_data_dir = r"C:\BateBonto\AppData\Local\Google\Chrome\User Data"
options.add_argument(f"--user-data-dir={user_data_dir}")
options.add_argument("--profile-directory=Defaut")
options.add_argument("--window-size=1280,720")
# options.add_argument("--window-position=10000,10000")

options.add_argument("--start-maximized")
driver = webdriver.Chrome(options=options)

def preencher_senha():
    try:
        campo = driver.find_element(By.ID, "senhanumerica")
        campo.clear()
        for digito in senha:
            campo.send_keys(digito)
            time.sleep(0.1)
        registrar_log("Senha preenchida.")
        return True
    except:
        registrar_log("Campo de senha não encontrado.")
        return False

def clicar_confirmar_pin():
    try:
        botao = driver.find_element(By.ID, "confirmasenhanumerica")
        botao.click()
        registrar_log("Botão confirmar PIN clicado.")
        return True
    except:
        registrar_log("Botão confirmar PIN não encontrado.")
        return False

def clicar_confirmar_janela():
    try:
        botao = driver.find_element(By.CSS_SELECTOR, ".btn-success.block")
        botao.click()
        registrar_log("Botão confirmar janela clicado.")
        return True
    except:
        registrar_log("Botão confirmar janela não encontrado.")
        return False

def clicar_opcao(horario_atual):
    seletor = horarios_permitidos[horario_atual]["seletor"]
    nome = horarios_permitidos[horario_atual]["nome"]
    try:
        for _ in range(timeout_padrao):
            botoes = driver.find_elements(By.CSS_SELECTOR, seletor)
            if botoes:
                botoes[0].find_element(By.XPATH, "./ancestor::button").click()
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

def executar_fluxo():
    horario_atual = horario_valido()
    if not horario_atual:
        return

    registrar_log(f"Horário válido detectado: {horario_atual}")
    try:
        if preencher_senha():
            time.sleep(1)
            if clicar_confirmar_pin():
                time.sleep(2)
                if clicar_confirmar_janela():
                    time.sleep(2)
                    if clicar_opcao(horario_atual):
                        time.sleep(5)
                        driver.refresh()
    except Exception as e:
        registrar_log(f"Erro inesperado: {str(e)}")

driver.get(url)

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
    focar_janela_do_chrome()
    try:
        while True:
            executar_fluxo()
            time.sleep(intervalo_execucao)
    except KeyboardInterrupt:
        registrar_log("Execução interrompida pelo usuário.")
        driver.quit()

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

threading.Thread(target=main_loop, daemon=True).start()

icon = pystray.Icon("bateponto", create_image(), "Bate Ponto", menu=pystray.Menu(
    pystray.MenuItem("Último Log", mostrar_ultimo_log),
    pystray.MenuItem("Sair", on_systray_exit)
))

icon.run()
