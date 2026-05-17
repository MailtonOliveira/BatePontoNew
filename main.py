# -*- coding: utf-8 -*-
import pystray
from PIL import Image, ImageDraw
import threading
import os
import sys
import time
import datetime
import tempfile
import re
import unicodedata
import shutil
import subprocess
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
import requests  # Adicionado para fazer requisições HTTP

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

print("[BatePonto] Inicializando...")

senha = os.getenv("BATEPONTO_SENHA", "")
url = os.getenv("BATEPONTO_URL", "https://bateponto.pontotel.com.br/")
timeout_padrao = int(os.getenv("TIMEOUT_PADRAO", "15"))

def _get_chrome_profile_dir():
    """Retorna %LOCALAPPDATA%\\BatePonto\\Chrome, migrando do local antigo se necessário."""
    local = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
    novo = os.path.join(local, 'BatePonto', 'Chrome')

    appdata = os.environ.get('APPDATA', '')
    antigo = os.path.join(appdata, 'BatePonto', 'Chrome')
    if os.path.exists(antigo) and not os.path.exists(novo):
        try:
            shutil.copytree(antigo, novo)
        except Exception:
            pass

    return novo


def _chrome_profile_exists():
    d = _get_chrome_profile_dir()
    return os.path.isdir(d) and bool(os.listdir(d))

_primeiro_uso = not senha or not _chrome_profile_exists()

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

def create_image(color=(76, 175, 80)):
    image = Image.new('RGB', (64, 64), color=color)
    draw = ImageDraw.Draw(image)
    draw.rectangle((16, 16, 48, 48), fill=(255, 255, 255))
    return image


def _atualizar_icone(estado: str = 'normal'):
    """normal=verde, descanso=amarelo, erro=vermelho."""
    cores = {
        'normal':   (76, 175, 80),
        'descanso': (255, 193, 7),
        'erro':     (220, 53, 69),
    }
    if systray_icon:
        systray_icon.icon = create_image(cores.get(estado, cores['normal']))


def _notificar_falha(nome_ponto: str):
    """Muda ícone para vermelho e exibe alerta persistente até o usuário fechar."""
    _atualizar_icone('erro')
    msg = (
        f"Falha ao registrar ponto: {nome_ponto}\n"
        "Verifique a conexão e o site do Pontotel.\n\n"
        "Clique em OK para fechar este aviso."
    )
    if systray_icon:
        systray_icon.notify(msg, "Erro — Ponto não registrado")
    threading.Thread(
        target=lambda: pyautogui.alert(msg, title="Erro — Ponto não registrado"),
        daemon=True
    ).start()

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
# Instalação e atalhos
# ──────────────────────────────────────────────────────────────

def get_install_dir():
    local = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
    return os.path.join(local, 'Programs', 'BatePonto')


def instalar_app():
    """Copia exe e .env para %LOCALAPPDATA%\\Programs\\BatePonto\\. Retorna caminho do exe instalado."""
    install_dir = get_install_dir()
    os.makedirs(install_dir, exist_ok=True)

    exe_destino = os.path.join(install_dir, 'BatePonto.exe')
    if getattr(sys, 'frozen', False):
        exe_atual = sys.executable
        if os.path.abspath(exe_atual) != os.path.abspath(exe_destino):
            shutil.copy2(exe_atual, exe_destino)

    env_destino = os.path.join(install_dir, '.env')
    if os.path.exists(ENV_PATH) and os.path.abspath(ENV_PATH) != os.path.abspath(env_destino):
        shutil.copy2(ENV_PATH, env_destino)

    registrar_log(f"App instalado em: {install_dir}")
    return exe_destino


def _criar_atalho(target, shortcut_path, descricao='Bate Ponto Automático'):
    script = (
        f"$ws = New-Object -ComObject WScript.Shell; "
        f"$s = $ws.CreateShortcut('{shortcut_path}'); "
        f"$s.TargetPath = '{target}'; "
        f"$s.Description = '{descricao}'; "
        f"$s.Save()"
    )
    subprocess.run(['powershell', '-Command', script], capture_output=True)


def criar_atalho_startup(exe_path):
    startup = os.path.join(
        os.environ['APPDATA'],
        'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup'
    )
    shortcut = os.path.join(startup, 'BatePonto.lnk')
    _criar_atalho(exe_path, shortcut)
    registrar_log(f"Atalho de inicialização criado: {shortcut}")


def criar_atalho_desktop(exe_path):
    result = subprocess.run(
        ['powershell', '-Command', "[System.Environment]::GetFolderPath('Desktop')"],
        capture_output=True, text=True
    )
    desktop = result.stdout.strip() or os.path.join(os.path.expanduser('~'), 'Desktop')
    shortcut = os.path.join(desktop, 'BatePonto.lnk')
    _criar_atalho(exe_path, shortcut)
    registrar_log(f"Atalho na área de trabalho criado: {shortcut}")


def criar_atalho_menu_iniciar(exe_path):
    programs = os.path.join(
        os.environ['APPDATA'],
        'Microsoft', 'Windows', 'Start Menu', 'Programs'
    )
    shortcut = os.path.join(programs, 'BatePonto.lnk')
    _criar_atalho(exe_path, shortcut)
    registrar_log(f"Atalho no Menu Iniciar criado: {shortcut}")



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

def is_weekend():
    hoje = datetime.datetime.now().weekday()
    return hoje >= 5  # 5 é sábado, 6 é domingo

# ──────────────────────────────────────────────────────────────
# Detecção automática de localização
# ──────────────────────────────────────────────────────────────

_localizacao_cache = None       # (uf, ibge) — localização ativa
_localizacao_auto_info = None   # {'uf', 'ibge', 'cidade'} — detectada via IP
_localizacao_lock = threading.Lock()


def _normalizar_nome(nome):
    nfkd = unicodedata.normalize('NFKD', nome)
    return ''.join(c for c in nfkd if not unicodedata.combining(c)).lower()


def _resolver_ibge_por_cidade(uf, cidade):
    """Resolve código IBGE e nome oficial para uma cidade/UF. Retorna (ibge_code, nome) ou (None, None)."""
    resp = requests.get(
        f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios",
        timeout=10
    )
    resp.raise_for_status()
    municipios = resp.json()
    cidade_norm = _normalizar_nome(cidade)

    for m in municipios:
        if _normalizar_nome(m["nome"]) == cidade_norm:
            return str(m["id"]), m["nome"]

    for m in municipios:
        nome_norm = _normalizar_nome(m["nome"])
        if cidade_norm in nome_norm or nome_norm in cidade_norm:
            registrar_log(f"Município aproximado: {m['nome']} ({m['id']})")
            return str(m["id"]), m["nome"]

    return None, None


def detectar_localizacao():
    """
    Detecta UF e IBGE via IP (sempre primeiro).
    Fallback: valores do .env ou padrão SP/3550308.
    """
    global _localizacao_cache, _localizacao_auto_info
    with _localizacao_lock:
        if _localizacao_cache:
            return _localizacao_cache

        # 1. Detecção via IP (sempre primeiro)
        try:
            geo_resp = requests.get(
                "http://ip-api.com/json/?lang=pt-BR&fields=status,city,region",
                timeout=5
            )
            geo_resp.raise_for_status()
            geo = geo_resp.json()

            if geo.get("status") != "success":
                raise ValueError(f"ip-api retornou status inesperado: {geo.get('status')}")

            uf = geo.get("region", "").strip()
            cidade = geo.get("city", "").strip()

            if not uf or not cidade:
                raise ValueError(f"ip-api não retornou region/city: {geo}")
            registrar_log(f"Localização detectada via IP: {cidade}/{uf}")

            ibge_code, nome_oficial = _resolver_ibge_por_cidade(uf, cidade)
            if not ibge_code:
                raise ValueError(f"Município '{cidade}' não encontrado na UF {uf}")

            _localizacao_auto_info = {'uf': uf, 'ibge': ibge_code, 'cidade': nome_oficial or cidade}
            _localizacao_cache = (uf, ibge_code)
            registrar_log(f"Localização resolvida: {cidade}/{uf} (IBGE {ibge_code})")
            return _localizacao_cache

        except Exception as e:
            registrar_log(f"Erro ao detectar localização automaticamente: {e}")

        # 2. Fallback para valores do .env ou padrão
        uf_fallback = os.getenv("REGIAO_UF", "SP")
        ibge_fallback = os.getenv("REGIAO_IBGE", "3550308")
        _localizacao_cache = (uf_fallback, ibge_fallback)
        registrar_log(f"Usando localização de fallback: UF={uf_fallback}, IBGE={ibge_fallback}")
        return _localizacao_cache


def abrir_janela_localizacao():
    """Abre janela para configurar localização manualmente, com resolução de conflito se diferir do IP."""

    def _criar_janela():
        global _localizacao_cache, _feriados_cache

        with _localizacao_lock:
            auto = _localizacao_auto_info

        root = tk.Tk()
        root.title("Configurar Localização")
        root.resizable(False, False)
        root.attributes('-topmost', True)

        largura, altura = 400, 310
        x = (root.winfo_screenwidth() // 2) - (largura // 2)
        y = (root.winfo_screenheight() // 2) - (altura // 2)
        root.geometry(f"{largura}x{altura}+{x}+{y}")

        root.configure(bg='#2b2b2b')
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TLabel', background='#2b2b2b', foreground='#ffffff', font=('Segoe UI', 11))
        style.configure('TEntry', font=('Segoe UI', 11))
        style.configure('TButton', font=('Segoe UI', 10, 'bold'), padding=6)
        style.configure('Header.TLabel', background='#2b2b2b', foreground='#4CAF50',
                        font=('Segoe UI', 13, 'bold'))
        style.configure('Info.TLabel', background='#2b2b2b', foreground='#aaaaaa',
                        font=('Segoe UI', 9))

        ttk.Label(root, text="📍 Localização", style='Header.TLabel').pack(pady=(15, 4))

        if auto:
            info_txt = f"Detectado via IP: {auto['cidade']}/{auto['uf']} (IBGE: {auto['ibge']})"
        else:
            info_txt = "Detecção via IP: não disponível"
        ttk.Label(root, text=info_txt, style='Info.TLabel').pack(pady=(0, 12))

        frame = ttk.Frame(root, style='TLabel')
        frame.pack(padx=20, fill='x')

        ttk.Label(frame, text="UF:").grid(row=0, column=0, sticky='w', pady=6, padx=(0, 10))
        var_uf = tk.StringVar(value=os.getenv("REGIAO_UF", ""))
        ttk.Entry(frame, textvariable=var_uf, width=6, justify='center',
                  font=('Segoe UI', 12)).grid(row=0, column=1, pady=6, sticky='w')

        ttk.Label(frame, text="Cidade:").grid(row=1, column=0, sticky='w', pady=6, padx=(0, 10))
        var_cidade = tk.StringVar(value=os.getenv("REGIAO_CIDADE", ""))
        ttk.Entry(frame, textvariable=var_cidade, width=28, justify='left',
                  font=('Segoe UI', 12)).grid(row=1, column=1, pady=6, sticky='w')

        status_var = tk.StringVar()
        ttk.Label(root, textvariable=status_var, style='Info.TLabel').pack(pady=(6, 0))

        def salvar():
            global _localizacao_cache, _feriados_cache

            uf = var_uf.get().strip().upper()
            cidade = var_cidade.get().strip()

            if len(uf) != 2 or not uf.isalpha():
                messagebox.showerror("UF inválida", "Informe uma UF válida com 2 letras (ex: MG, SP).", parent=root)
                return
            if not cidade:
                messagebox.showerror("Cidade inválida", "Informe o nome da cidade.", parent=root)
                return

            status_var.set("Buscando código IBGE...")
            root.update()

            try:
                ibge_code, nome_oficial = _resolver_ibge_por_cidade(uf, cidade)
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao consultar API do IBGE:\n{e}", parent=root)
                status_var.set("")
                return

            if not ibge_code:
                messagebox.showerror(
                    "Não encontrado",
                    f"Cidade '{cidade}' não encontrada na UF {uf}.\nVerifique o nome e tente novamente.",
                    parent=root
                )
                status_var.set("")
                return

            uf_final, ibge_final, cidade_final = uf, ibge_code, nome_oficial

            # Conflito com localização automática?
            if auto and (ibge_code != auto['ibge'] or uf != auto['uf']):
                escolha = messagebox.askquestion(
                    "Localização diferente da detectada",
                    f"A localização manual difere da detectada via IP.\n\n"
                    f"  Automático:  {auto['cidade']}/{auto['uf']}  (IBGE {auto['ibge']})\n"
                    f"  Manual:      {nome_oficial}/{uf}  (IBGE {ibge_code})\n\n"
                    f"Deseja usar a localização manual?\n"
                    f"(Clique 'Não' para manter a automática)",
                    icon='question',
                    parent=root
                )
                if escolha == 'no':
                    uf_final = auto['uf']
                    ibge_final = auto['ibge']
                    cidade_final = auto['cidade']

            with _localizacao_lock:
                _localizacao_cache = (uf_final, ibge_final)

            set_key(ENV_PATH, "REGIAO_UF", uf_final)
            set_key(ENV_PATH, "REGIAO_IBGE", ibge_final)
            set_key(ENV_PATH, "REGIAO_CIDADE", cidade_final)

            with _feriados_cache_lock:
                _feriados_cache.clear()

            registrar_log(f"Localização definida: {cidade_final}/{uf_final} (IBGE {ibge_final})")
            messagebox.showinfo("Salvo ✅", f"Localização ativa: {cidade_final}/{uf_final}", parent=root)
            root.destroy()

        btn_frame = ttk.Frame(root, style='TLabel')
        btn_frame.pack(pady=14)
        ttk.Button(btn_frame, text="💾 Salvar", command=salvar).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=root.destroy).pack(side='left', padx=5)

        root.mainloop()

    threading.Thread(target=_criar_janela, daemon=True).start()


# ──────────────────────────────────────────────────────────────
# Wizard de primeiro uso
# ──────────────────────────────────────────────────────────────

def abrir_input_pin_simples():
    """
    Pede o PIN via input simples quando o perfil Chrome já tem o Pontotel configurado.
    Roda na thread principal (bloqueia até concluir).
    """
    global senha

    root = tk.Tk()
    root.title("Bate Ponto — PIN")
    root.resizable(False, False)
    root.attributes('-topmost', True)

    largura, altura = 360, 240
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

    ttk.Label(root, text="⏰ Bate Ponto", style='Header.TLabel').pack(pady=(18, 8))
    ttk.Label(root,
              text="Perfil já configurado.\nDigite seu PIN para continuar:",
              wraplength=300, justify='center').pack(pady=(0, 12))

    var_pin = tk.StringVar()
    entry = ttk.Entry(root, textvariable=var_pin, width=14, justify='center',
                      font=('Segoe UI', 14), show='*')
    entry.pack(pady=(0, 8))
    ttk.Label(root,
              text="💡 Dica: no primeiro cadastro na plataforma, o PIN geralmente é o seu CPF.",
              wraplength=300, justify='center',
              font=('Segoe UI', 8)).pack(pady=(0, 12))
    entry.focus()

    def salvar():
        global senha
        pin = var_pin.get().strip()
        if not pin:
            messagebox.showerror("PIN inválido", "O PIN não pode ser vazio.", parent=root)
            return
        set_key(ENV_PATH, "BATEPONTO_SENHA", pin)
        senha = pin
        registrar_log("PIN salvo via input simples (perfil já configurado).")
        root.destroy()

    def cancelar():
        try:
            if driver:
                driver.quit()
        except Exception:
            pass
        root.destroy()
        os._exit(0)

    root.bind('<Return>', lambda e: salvar())

    btn_frame = ttk.Frame(root, style='TLabel')
    btn_frame.pack()
    ttk.Button(btn_frame, text="💾 Salvar", command=salvar).pack(side='left', padx=5)
    ttk.Button(btn_frame, text="Cancelar", command=cancelar).pack(side='left', padx=5)

    root.mainloop()


_notificar_instalacao_ok = False


def abrir_setup_wizard(pular_para_passo2=False):
    """
    Wizard de primeiro uso. Roda na thread principal (bloqueia até concluir).
    Se pular_para_passo2=True, o Chrome já está aberto — vai direto para o passo 2.
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

    content = tk.Frame(root, bg='#2b2b2b')
    content.pack(fill='both', expand=True, padx=30, pady=20)

    def _limpar():
        for w in content.winfo_children():
            w.destroy()

    _spinner_chars = ['◐', '◓', '◑', '◒']
    _spinner_idx = [0]
    _spinner_job = [None]

    def _mostrar_passo1():
        _limpar()
        ttk.Label(content, text="⏰ Bate Ponto", style='Header.TLabel').pack(pady=(0, 10))
        ttk.Label(content, text="Bem-vindo! Vou te guiar pela configuração inicial.",
                  wraplength=360, background='#2b2b2b', foreground='#ffffff',
                  font=('Segoe UI', 11)).pack(pady=(0, 6))
        ttk.Label(content,
                  text="Na próxima etapa o Chrome vai abrir o site da Pontotel.\n"
                       "Faça login com seu e-mail e senha.\n"
                       "Quando o site pedir seu PIN, digite normalmente —\n"
                       "o app vai capturá-lo sozinho.",
                  wraplength=360, justify='left',
                  background='#2b2b2b', foreground='#ffffff',
                  font=('Segoe UI', 11)).pack(pady=(0, 20))
        ttk.Button(content, text="Iniciar →", command=_iniciar).pack()

    def _mostrar_passo2():
        root.attributes('-topmost', False)
        _limpar()
        ttk.Label(content, text="⏰ Bate Ponto", style='Header.TLabel').pack(pady=(0, 10))
        ttk.Label(content, text="Aguardando configuração...",
                  font=('Segoe UI', 11, 'bold'), background='#2b2b2b',
                  foreground='#ffffff').pack(pady=(0, 10))

        for txt in ["●  Faça login no site da Pontotel",
                    "●  Digite seu PIN quando pedido",
                    "●  Não feche o Chrome"]:
            tk.Label(content, text=txt, background='#2b2b2b', foreground='#aaaaaa',
                     font=('Segoe UI', 9)).pack(anchor='w', pady=1)

        banner = tk.Frame(content, bg='#3a3a2a', relief='flat', bd=0)
        banner.pack(fill='x', pady=(12, 0))
        tk.Label(banner,
                 text="💡  Minimize esta janela enquanto preenche o site",
                 background='#3a3a2a', foreground='#f0d060',
                 font=('Segoe UI', 9)).pack(pady=6, padx=10)

        spinner_var = tk.StringVar(value="◐  Detectando PIN...")
        tk.Label(content, textvariable=spinner_var, background='#2b2b2b',
                 foreground='#aaaaaa', font=('Segoe UI', 9)).pack(pady=(16, 0))

        def _tick_spinner():
            _spinner_idx[0] = (_spinner_idx[0] + 1) % len(_spinner_chars)
            spinner_var.set(f"{_spinner_chars[_spinner_idx[0]]}  Detectando PIN...")
            _spinner_job[0] = root.after(300, _tick_spinner)

        _tick_spinner()
        ttk.Button(content, text="Cancelar", command=_cancelar).pack(pady=(20, 0))

        def _thread_monitoramento():
            pin = _monitorar_pin_setup(timeout_segundos=300)
            root.after(0, lambda: _on_pin_resultado(pin))

        threading.Thread(target=_thread_monitoramento, daemon=True).start()

    def _mostrar_conclusao():
        if _spinner_job[0]:
            root.after_cancel(_spinner_job[0])
        _limpar()
        ttk.Label(content, text="⏰ Bate Ponto", style='Header.TLabel').pack(pady=(0, 6))
        tk.Label(content, text="✅ Configuração concluída!",
                 font=('Segoe UI', 13, 'bold'), background='#2b2b2b',
                 foreground='#4CAF50').pack(pady=(0, 6))
        tk.Label(content,
                 text="PIN salvo. Escolha como deseja instalar o app:",
                 wraplength=360, justify='center',
                 background='#2b2b2b', foreground='#ffffff',
                 font=('Segoe UI', 10)).pack(pady=(0, 10))

        var_startup = tk.BooleanVar(value=True)
        var_menu = tk.BooleanVar(value=True)
        var_desktop = tk.BooleanVar(value=True)

        chk_kw = dict(background='#2b2b2b', foreground='#ffffff',
                      selectcolor='#444444', activebackground='#2b2b2b',
                      activeforeground='#ffffff', font=('Segoe UI', 10))
        tk.Checkbutton(content, text="Iniciar com o Windows",
                       variable=var_startup, **chk_kw).pack(anchor='w', padx=50)
        tk.Checkbutton(content, text="Salvar no Menu Iniciar",
                       variable=var_menu, **chk_kw).pack(anchor='w', padx=50, pady=(4, 0))
        tk.Checkbutton(content, text="Atalho na Área de Trabalho",
                       variable=var_desktop, **chk_kw).pack(anchor='w', padx=50, pady=(4, 14))

        def _finalizar():
            try:
                exe_instalado = instalar_app()
                if var_startup.get():
                    criar_atalho_startup(exe_instalado)
                if var_menu.get():
                    criar_atalho_menu_iniciar(exe_instalado)
                if var_desktop.get():
                    criar_atalho_desktop(exe_instalado)
            except Exception as e:
                registrar_log(f"Erro durante instalação: {e}")
            try:
                if driver:
                    driver.set_window_position(10000, 10000)
            except Exception:
                pass
            global _notificar_instalacao_ok
            _notificar_instalacao_ok = True
            root.destroy()

        ttk.Button(content, text="Instalar e Fechar", command=_finalizar).pack()

    def _mostrar_fallback():
        if _spinner_job[0]:
            root.after_cancel(_spinner_job[0])
        _limpar()
        ttk.Label(content, text="⏰ Bate Ponto", style='Header.TLabel').pack(pady=(0, 10))
        tk.Label(content,
                 text="Não consegui capturar o PIN automaticamente.\n"
                      "Digite-o manualmente:",
                 wraplength=360, justify='center',
                 background='#2b2b2b', foreground='#ffffff',
                 font=('Segoe UI', 11)).pack(pady=(0, 10))
        var_pin = tk.StringVar()
        entry = ttk.Entry(content, textvariable=var_pin, width=12, justify='center',
                          font=('Segoe UI', 14), show='*')
        entry.pack(pady=(0, 6))
        tk.Label(content,
                 text="💡 Dica: no primeiro cadastro na plataforma, o PIN geralmente é o seu CPF.",
                 wraplength=340, justify='center',
                 background='#2b2b2b', foreground='#aaaaaa',
                 font=('Segoe UI', 8)).pack(pady=(0, 14))
        entry.focus()

        def _salvar_manual():
            pin = var_pin.get().strip()
            if not pin:
                messagebox.showerror("PIN inválido", "O PIN não pode ser vazio.", parent=root)
                return
            _salvar_pin(pin)
            _mostrar_conclusao()

        ttk.Button(content, text="💾 Salvar", command=_salvar_manual).pack()

    def _mostrar_erro_chrome():
        if _spinner_job[0]:
            root.after_cancel(_spinner_job[0])
        _limpar()
        ttk.Label(content, text="⏰ Bate Ponto", style='Header.TLabel').pack(pady=(0, 10))
        tk.Label(content, text="O Chrome foi fechado antes de concluir.",
                 wraplength=360, justify='center',
                 background='#2b2b2b', foreground='#ffffff',
                 font=('Segoe UI', 11)).pack(pady=(0, 10))
        ttk.Button(content, text="Tentar novamente", command=_reiniciar).pack(pady=(0, 6))
        ttk.Button(content, text="Cancelar", command=_cancelar).pack()

    def _salvar_pin(pin):
        global senha
        set_key(ENV_PATH, "BATEPONTO_SENHA", pin)
        senha = pin
        registrar_log("PIN capturado e salvo durante setup inicial.")

    def _iniciar():
        if not pular_para_passo2:
            _init_driver()
        _mostrar_passo2()

    def _reiniciar():
        global driver
        driver = None  # força reinicialização
        _init_driver()
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
        root.deiconify()
        root.attributes('-topmost', True)
        root.lift()
        root.focus_force()
        if pin:
            _salvar_pin(pin)
            _mostrar_conclusao()
        else:
            try:
                if driver:
                    driver.find_elements(By.CSS_SELECTOR, "body")
                _mostrar_fallback()
            except Exception:
                _mostrar_erro_chrome()

    if pular_para_passo2:
        _mostrar_passo2()
    else:
        _mostrar_passo1()
    root.mainloop()


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


# ──────────────────────────────────────────────────────────────
# Feriados estaduais e municipais das capitais (hardcoded, sem API)
# ──────────────────────────────────────────────────────────────

FERIADOS_ESTADUAIS = {
    "AC": [(6,  15, "Aniversário do Acre"), (9, 5, "Dia do Acre")],
    "AL": [(9,  16, "Emancipação Política de Alagoas")],
    "AM": [(9,   5, "Elevação do Amazonas à categoria de Província")],
    "AP": [(9,  13, "Criação do Território do Amapá")],
    "BA": [(7,   2, "Independência da Bahia")],
    "CE": [(3,  25, "Data Magna do Ceará")],
    "DF": [(4,  21, "Fundação de Brasília")],
    "ES": [(10, 28, "Dia do Servidor Público do ES")],
    "GO": [(7,  26, "Fundação de Goiânia")],
    "MA": [(7,  28, "Adesão do Maranhão à Independência")],
    "MG": [(4,  21, "Tiradentes")],
    "MS": [(10, 11, "Criação do Estado de MS")],
    "MT": [(4,   8, "Criação da Capitania de MT")],
    "PA": [(8,  15, "Adesão do Pará à Independência")],
    "PB": [(8,   5, "Fundação do Estado da Paraíba")],
    "PE": [(3,   6, "Revolução Pernambucana de 1817")],
    "PI": [(10, 19, "Dia do Piauí")],
    "PR": [(12, 19, "Emancipação Política do Paraná")],
    "RJ": [(4,  23, "Dia de São Jorge")],
    "RN": [(10,  3, "Mártires de Cunhaú e Uruaçu")],
    "RO": [(1,   4, "Criação do Estado de RO")],
    "RR": [(10,  5, "Criação do Estado de RR")],
    "RS": [(9,  20, "Revolução Farroupilha")],
    "SC": [(8,  11, "Criação da Capitania de SC")],
    "SE": [(7,   8, "Emancipação Política de Sergipe")],
    "SP": [(7,   9, "Revolução Constitucionalista de 1932")],
    "TO": [(10,  5, "Criação do Estado do Tocantins")],
}

IBGE_CAPITAIS = {
    "AC": "1200401",
    "AL": "2704302",
    "AM": "1302603",
    "AP": "1600303",
    "BA": "2927408",
    "CE": "2304400",
    "DF": "5300108",
    "ES": "3205309",
    "GO": "5208707",
    "MA": "2111300",
    "MG": "3106200",
    "MS": "5002704",
    "MT": "5103403",
    "PA": "1501402",
    "PB": "2507507",
    "PE": "2611606",
    "PI": "2211001",
    "PR": "4106902",
    "RJ": "3304557",
    "RN": "2408102",
    "RO": "1100205",
    "RR": "1400100",
    "RS": "4314902",
    "SC": "4205407",
    "SE": "2800308",
    "SP": "3550308",
    "TO": "1721000",
}

FERIADOS_MUNICIPAIS_CAPITAIS = {
    "AC": [(6,   2, "Aniversário de Rio Branco")],
    "AL": [(12,  5, "Aniversário de Maceió")],
    "AM": [(10, 24, "Aniversário de Manaus")],
    "AP": [(2,   4, "Aniversário de Macapá")],
    "BA": [(3,  29, "Aniversário de Salvador")],
    "CE": [(4,  13, "Aniversário de Fortaleza")],
    "DF": [],
    "ES": [(9,   8, "Aniversário de Vitória")],
    "GO": [(10, 24, "Aniversário de Goiânia")],
    "MA": [(9,   8, "Aniversário de São Luís")],
    "MG": [(8,  15, "Nossa Senhora da Boa Viagem"), (12, 12, "Aniversário de BH")],
    "MS": [(8,  26, "Aniversário de Campo Grande")],
    "MT": [(4,   8, "Aniversário de Cuiabá")],
    "PA": [(1,  12, "Aniversário de Belém")],
    "PB": [(8,   5, "Aniversário de João Pessoa")],
    "PE": [(3,  12, "Aniversário de Recife")],
    "PI": [(8,  16, "Aniversário de Teresina")],
    "PR": [(3,  29, "Aniversário de Curitiba")],
    "RJ": [(1,  20, "Dia de São Sebastião"), (3, 1, "Aniversário do Rio de Janeiro")],
    "RN": [(12, 25, "Aniversário de Natal")],
    "RO": [(10,  2, "Aniversário de Porto Velho")],
    "RR": [(7,   9, "Aniversário de Boa Vista")],
    "RS": [(7,  26, "Aniversário de Porto Alegre")],
    "SC": [(3,  23, "Aniversário de Florianópolis")],
    "SE": [(3,  17, "Aniversário de Aracaju")],
    "SP": [(1,  25, "Aniversário de São Paulo")],
    "TO": [(5,  20, "Aniversário de Palmas")],
}


# ──────────────────────────────────────────────────────────────
# Cálculo local de feriados (fallback sem rede)
# ──────────────────────────────────────────────────────────────

def _calcular_pascoa(ano):
    a = ano % 19
    b, c = divmod(ano, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes, dia = divmod(114 + h + l - 7 * m, 31)
    return datetime.date(ano, mes, dia + 1)


def _feriados_nacionais_fallback(ano):
    pascoa = _calcular_pascoa(ano)
    datas = set()
    for mes, dia in [(1,1),(4,21),(5,1),(9,7),(10,12),(11,2),(11,15),(11,20),(12,25)]:
        datas.add(datetime.date(ano, mes, dia).strftime("%Y-%m-%d"))
    for delta in [-48, -47, -2, 60]:
        datas.add((pascoa + datetime.timedelta(days=delta)).strftime("%Y-%m-%d"))
    return datas


# ──────────────────────────────────────────────────────────────
# Cache de feriados (por ano, para evitar chamadas repetidas)
# ──────────────────────────────────────────────────────────────

_feriados_cache = {}
_feriados_cache_lock = threading.Lock()


def _carregar_feriados_do_ano(ano):
    """Carrega e cacheia feriados: nacionais (BrasilAPI) + estaduais + municipais da capital."""
    with _feriados_cache_lock:
        if ano in _feriados_cache:
            return _feriados_cache[ano]

        uf, ibge = detectar_localizacao()
        datas = set()

        try:
            r = requests.get(
                f"https://brasilapi.com.br/api/feriados/v1/{ano}",
                timeout=10
            )
            r.raise_for_status()
            for f in r.json():
                data = f.get("date", "")
                if data:
                    datas.add(data)
        except Exception as e:
            registrar_log(f"BrasilAPI indisponível ({e}). Usando fallback local.")
            datas |= _feriados_nacionais_fallback(ano)

        for mes, dia, _ in FERIADOS_ESTADUAIS.get(uf, []):
            datas.add(f"{ano}-{mes:02d}-{dia:02d}")

        if ibge == IBGE_CAPITAIS.get(uf):
            for mes, dia, _ in FERIADOS_MUNICIPAIS_CAPITAIS.get(uf, []):
                datas.add(f"{ano}-{mes:02d}-{dia:02d}")

        _feriados_cache[ano] = datas
        registrar_log(f"Feriados {ano} carregados: {len(datas)} datas (UF={uf}, IBGE={ibge})")
        return datas


def is_holiday():
    hoje = datetime.datetime.now()
    try:
        feriados = _carregar_feriados_do_ano(hoje.year)
        return hoje.strftime("%Y-%m-%d") in feriados
    except Exception as e:
        registrar_log(f"Erro ao verificar feriado: {e}. Assumindo dia útil.")
        return False


def _monitorar_pin_setup(timeout_segundos=300):
    """
    Monitora o campo de PIN no Shadow DOM durante o setup inicial.
    Retorna o PIN capturado quando a página desaparece, ou None no timeout.
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
                if pin_capturado:
                    return pin_capturado
        except Exception:
            if pin_capturado:
                return pin_capturado

        time.sleep(0.5)

    return None

# ──────────────────────────────────────────────────────────────
# Selenium setup
# ──────────────────────────────────────────────────────────────

driver = None  # inicializado por _init_driver()


def _init_driver():
    """Inicializa o Chrome e navega para a URL do BatePonto."""
    global driver
    if driver is not None:
        return
    options = Options()
    user_data_dir = _get_chrome_profile_dir()
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

        registrar_log(f"Timeout ({timeout_padrao}s): botão '{nome}' não encontrado.")
        return False
    except Exception as e:
        registrar_log(f"Erro ao tentar clicar na opção '{nome}': {str(e)}.")
        return False

# ──────────────────────────────────────────────────────────────
# Gerenciamento de janela
# ──────────────────────────────────────────────────────────────

janela_visivel = None
systray_icon = None


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


# ──────────────────────────────────────────────────────────────
# Startup
# ──────────────────────────────────────────────────────────────

if _primeiro_uso:
    _init_driver()  # abre Chrome para detectar estado do perfil
    if janela_visivel:  # Chrome visível = precisa de login = wizard completo
        abrir_setup_wizard(pular_para_passo2=True)
    else:  # Chrome oculto = perfil já configurado = só precisa do PIN
        abrir_input_pin_simples()
else:
    _init_driver()


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


def segundos_ate_proximo_ponto():
    """Retorna quantos segundos faltam para o próximo horário de ponto configurado."""
    agora = datetime.datetime.now()
    horarios = get_horarios()
    proximos = []
    for horario_str in horarios:
        h, m = map(int, horario_str.split(':'))
        candidato = agora.replace(hour=h, minute=m, second=0, microsecond=0)
        if candidato <= agora:
            candidato += datetime.timedelta(days=1)
        proximos.append(candidato)
    if not proximos:
        return 60
    return max(1, (min(proximos) - agora).total_seconds())


def main_loop():
    registrar_log("Script iniciado e monitorando horários...")
    horarios = get_horarios()
    resumo = ', '.join(f"{info['nome']}={h}" for h, info in horarios.items())
    registrar_log(f"Horários configurados: {resumo}")
    detectar_localizacao()
    focar_janela_do_chrome()

    _ANTECEDENCIA = 10  # segundos antes do ponto para iniciar polling fino

    try:
        while True:
            # Aguarda login/setup manual se necessário
            if gerenciar_janela():
                time.sleep(5)
                continue

            # Pula fins de semana e feriados (dorme até o dia seguinte)
            if is_weekend() or is_holiday():
                registrar_log("Hoje é final de semana ou feriado. Ponto não será batido.")
                _atualizar_icone('descanso')
                agora = datetime.datetime.now()
                amanha = (agora + datetime.timedelta(days=1)).replace(
                    hour=0, minute=5, second=0, microsecond=0)
                time.sleep((amanha - agora).total_seconds())
                _atualizar_icone('normal')
                continue

            # Smart sleep: dorme até _ANTECEDENCIA segundos antes do próximo ponto
            faltam = segundos_ate_proximo_ponto()
            if faltam > _ANTECEDENCIA:
                proximo_str = (
                    datetime.datetime.now() + datetime.timedelta(seconds=faltam)
                ).strftime("%H:%M")
                registrar_log(f"Próximo ponto às {proximo_str}. Aguardando...")
                time.sleep(faltam - _ANTECEDENCIA)

            # Polling fino: espera o segundo exato (janela de até 20s)
            horario_atual = None
            for _ in range(20):
                horario_atual = horario_valido()
                if horario_atual:
                    break
                time.sleep(1)

            if not horario_atual:
                continue

            # Executa o ponto
            registrar_log(f"Horário válido detectado: {horario_atual}")
            horarios = get_horarios()
            nome_ponto = horarios.get(horario_atual, {}).get('nome', horario_atual)
            try:
                if preencher_senha():
                    time.sleep(1)
                    if clicar_confirmar_pin():
                        time.sleep(2)
                        if clicar_opcao(horario_atual):
                            agora_str = datetime.datetime.now().strftime("%H:%M")
                            msg_ok = f"{nome_ponto} registrado às {agora_str}"
                            registrar_log(f"Ponto batido: {msg_ok}")
                            _atualizar_icone('normal')
                            if systray_icon:
                                systray_icon.notify(msg_ok, "Ponto Batido!")
                            time.sleep(5)
                            driver.refresh()
                        else:
                            registrar_log(f"Falha ao clicar no botão do ponto '{nome_ponto}'.")
                            _notificar_falha(nome_ponto)
                    else:
                        registrar_log(f"Falha ao confirmar PIN para o ponto '{nome_ponto}'.")
                        _notificar_falha(nome_ponto)
                else:
                    registrar_log(f"Falha ao preencher senha para o ponto '{nome_ponto}'.")
                    _notificar_falha(nome_ponto)
            except Exception as e:
                registrar_log(f"Erro inesperado: {str(e)}")
                _notificar_falha(nome_ponto)

            # Sai da janela do minuto atual antes de recalcular o próximo
            time.sleep(65)

    except KeyboardInterrupt:
        registrar_log("Execução interrompida pelo usuário.")
        driver.quit()

# ──────────────────────────────────────────────────────────────
# SysTray
# ──────────────────────────────────────────────────────────────

def on_systray_exit(icon, item):
    registrar_log("Encerrando pelo systray.")
    icon.stop()
    if driver is not None:
        driver.quit()
    os._exit(0)


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


def configurar_localizacao_systray(icon, item):
    abrir_janela_localizacao()


def alterar_pin_systray(icon, item):
    abrir_janela_alterar_pin()


threading.Thread(target=main_loop, daemon=True).start()

icon = pystray.Icon("bateponto", create_image(), "Bate Ponto", menu=pystray.Menu(
    pystray.MenuItem("⏰ Configurar Horários", configurar_horarios_systray),
    pystray.MenuItem("📍 Configurar Localização", configurar_localizacao_systray),
    pystray.MenuItem("🔑 Alterar PIN", alterar_pin_systray),
    pystray.MenuItem("Último Log", mostrar_ultimo_log),
    pystray.MenuItem("Sair", on_systray_exit)
))

systray_icon = icon

icon.run()
