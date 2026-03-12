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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
    "08:00": {'seletor': 'pontotel-botao-ponto[tipo="entrada"]', 'nome': 'Entrada'},
    "12:50": {'seletor': 'pontotel-botao-ponto[tipo="pausa"]', 'nome': 'Pausa'},
    "13:50": {'seletor': 'pontotel-botao-ponto[tipo="retorno"]', 'nome': 'Retorno'},
    "18:00": {'seletor': 'pontotel-botao-ponto[tipo="saida"]', 'nome': 'Saída'}
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
appdata_dir = os.environ.get('APPDATA')
user_data_dir = os.path.join(appdata_dir, "BatePonto", "Chrome")
os.makedirs(user_data_dir, exist_ok=True)
options.add_argument(f"--user-data-dir={user_data_dir}")
options.add_argument("--profile-directory=Default")
options.add_argument("--window-size=1280,720")
# options.add_argument("--window-position=10000,10000") # Removido para controle dinâmico

options.add_argument("--start-maximized")
driver = webdriver.Chrome(options=options)

def preencher_senha():
    try:
        wait = WebDriverWait(driver, 10)
        host = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".pagina-sincronizacao-pin__input-pin")))
        
        # Tenta acessar o Shadow DOM usando JS para máxima compatibilidade
        campo = driver.execute_script("return arguments[0].shadowRoot ? arguments[0].shadowRoot.querySelector('input') : arguments[0]", host)
        
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
        host = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".pagina-sincronizacao-pin__botao-confirmar")))
        
        # O botão interno de `<pontotel-botao>`
        botao = driver.execute_script("return arguments[0].shadowRoot ? arguments[0].shadowRoot.querySelector('button') : arguments[0]", host)
        
        if botao:
            # Substituído `botao.click()` por execução via JS
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
    seletor = horarios_permitidos[horario_atual]["seletor"]
    nome = horarios_permitidos[horario_atual]["nome"]
    hoje_str = datetime.datetime.now().strftime("%d.%m.%y")
    
    try:
        for _ in range(timeout_padrao):
            botoes = driver.find_elements(By.CSS_SELECTOR, seletor)
            if botoes:
                host = botoes[0]
                
                # VERIFICAÇÃO DE PONTO DUPLICADO
                ultimo_ponto = host.get_attribute("ultimo-ponto")
                if ultimo_ponto and ultimo_ponto.startswith(hoje_str):
                    msg = f"Aviso: Ponto '{nome}' já foi registrado hoje ({ultimo_ponto}). Ignorando novo clique."
                    registrar_log(msg)
                    return True
                
                botao_interno = driver.execute_script("return arguments[0].shadowRoot ? arguments[0].shadowRoot.querySelector('button') : arguments[0]", host)
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

janela_visivel = None

def gerenciar_janela():
    global janela_visivel
    try:
        # A página está pronta se tivermos o campo de PIN ou os botões de ponto
        elementos_prontos = driver.find_elements(By.CSS_SELECTOR, ".pagina-sincronizacao-pin__input-pin, pontotel-botao-ponto")
        
        if elementos_prontos:
            if janela_visivel is not False:
                # Tudo configurado (página de bater ponto normal), esconde a janela lá longe
                driver.set_window_position(10000, 10000)
                registrar_log("Configuração concluída. Janela oculta.")
                janela_visivel = False
            return False
        else:
            if janela_visivel is not True:
                # A página precisa de login ou está carregando. Traz para a tela principal!
                driver.set_window_position(50, 50)
                registrar_log("Aguardando configuração manual (Login ou Setup). Janela exibida.")
                janela_visivel = True
            return True
    except Exception as e:
        registrar_log(f"Erro ao gerenciar janela: {e}")
        return False

def executar_fluxo():
    # Gerencia a janela antes de tentar qualquer fluxo.
    # Se ainda estiver na página de login, mantemos a janela visível
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

driver.get(url)
time.sleep(3) # Aguarda carregar para avaliar URL
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
    focar_janela_do_chrome()
    try:
        while True:
            esperando_setup = executar_fluxo()
            if esperando_setup:
                time.sleep(5)  # Checa rápido enquanto está configurando
            else:
                time.sleep(intervalo_execucao)  # Checa no intervalo normal de 60s
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
