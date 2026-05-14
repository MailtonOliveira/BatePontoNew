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
# Chave da API de feriados (embutida no build — não exposta ao usuário)
# ──────────────────────────────────────────────────────────────
_FERIADOS_API_KEY = "SUA_CHAVE_AQUI"  # substitua pela chave real antes de buildar

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
        ttk.Label(content, text="⏰ Bate Ponto", style='Header.TLabel').pack(pady=(0, 10))
        tk.Label(content, text="✅ Configuração concluída!",
                 font=('Segoe UI', 13, 'bold'), background='#2b2b2b',
                 foreground='#4CAF50').pack(pady=(0, 10))
        tk.Label(content,
                 text="Seu PIN foi salvo com sucesso.\n"
                      "O app está rodando em segundo plano —\n"
                      "veja o ícone na bandeja do sistema.",
                 wraplength=360, justify='center',
                 background='#2b2b2b', foreground='#ffffff',
                 font=('Segoe UI', 11)).pack(pady=(0, 20))
        ttk.Button(content, text="Fechar", command=root.destroy).pack()

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
# Cache de feriados (por ano, para evitar chamadas repetidas)
# ──────────────────────────────────────────────────────────────

_feriados_cache = {}
_feriados_cache_lock = threading.Lock()


def _carregar_feriados_do_ano(ano):
    """Carrega e cacheia feriados nacionais + municipais do ano via feriadosapi.com."""
    with _feriados_cache_lock:
        if ano in _feriados_cache:
            return _feriados_cache[ano]

        uf, ibge = detectar_localizacao()
        headers = {"Authorization": f"Bearer {os.getenv('FERIADOS_API_KEY', _FERIADOS_API_KEY)}"}
        datas = set()

        def _extrair_data(item):
            if isinstance(item, str):
                return item
            if isinstance(item, dict):
                return item.get("data") or item.get("date") or item.get("Data")
            return None

        try:
            r = requests.get(
                f"https://feriadosapi.com/api/v1/feriados/cidade/{ibge}?ano={ano}",
                headers=headers, timeout=10
            )
            r.raise_for_status()
            for f in r.json():
                data = _extrair_data(f)
                if data:
                    datas.add(data)
        except Exception as e:
            registrar_log(f"Erro ao carregar feriados {ano} (IBGE {ibge}): {e}")

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


# ──────────────────────────────────────────────────────────────
# Startup
# ──────────────────────────────────────────────────────────────

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
                agora = datetime.datetime.now()
                amanha = (agora + datetime.timedelta(days=1)).replace(
                    hour=0, minute=5, second=0, microsecond=0)
                time.sleep((amanha - agora).total_seconds())
                continue

            # Smart sleep: dorme até _ANTECEDENCIA segundos antes do próximo ponto
            faltam = segundos_ate_proximo_ponto()
            if faltam > _ANTECEDENCIA:
                proximo_str = (
                    datetime.datetime.now() + datetime.timedelta(seconds=faltam)
                ).strftime("%H:%M")
                registrar_log(f"Próximo ponto às {proximo_str} (em {int(faltam)}s). Aguardando...")
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

icon.run()
