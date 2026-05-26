# -*- coding: utf-8 -*-
"""
platform_utils.py — Abstração de plataforma para o BatePonto.

Encapsula toda lógica dependente de OS (Windows / Linux) de forma que
main.py não precise de nenhum `if sys.platform` direto.
"""

import os
import sys
import subprocess
import threading
import tempfile

IS_WINDOWS = sys.platform == "win32"
IS_LINUX   = sys.platform.startswith("linux")

# ──────────────────────────────────────────────────────────────
# Diretórios base
# ──────────────────────────────────────────────────────────────

def get_chrome_profile_dir() -> str:
    """Retorna o diretório do perfil Chrome do BatePonto.

    Windows : %LOCALAPPDATA%\\BatePonto\\Chrome
    Linux   : ~/.local/share/BatePonto/Chrome
    """
    if IS_WINDOWS:
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    else:
        base = os.path.join(
            os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
        )
    return os.path.join(base, "BatePonto", "Chrome")


def get_install_dir() -> str:
    """Retorna o diretório de instalação do executável.

    Windows : %LOCALAPPDATA%\\Programs\\BatePonto
    Linux   : ~/.local/share/BatePonto
    """
    if IS_WINDOWS:
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        return os.path.join(base, "Programs", "BatePonto")
    else:
        base = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
        return os.path.join(base, "BatePonto")


def get_config_dir() -> str:
    """Retorna o diretório de configuração (.env).

    Windows : mesmo diretório do executável (comportamento atual)
    Linux   : ~/.config/BatePonto
    """
    if IS_WINDOWS:
        # Mantém comportamento atual — .env fica junto ao exe
        if getattr(sys, "frozen", False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))
    else:
        base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        config_dir = os.path.join(base, "BatePonto")
        os.makedirs(config_dir, exist_ok=True)
        return config_dir


def get_logs_dir() -> str:
    """Retorna o diretório de logs. Usa tempfile em ambas as plataformas."""
    return os.path.join(tempfile.gettempdir(), "BatePonto")


# ──────────────────────────────────────────────────────────────
# Migração de perfil Chrome (Windows-only)
# ──────────────────────────────────────────────────────────────

def migrar_perfil_chrome_legado():
    """
    Migra perfil de %APPDATA%\\BatePonto\\Chrome para %LOCALAPPDATA%\\BatePonto\\Chrome.
    Não-op no Linux.
    """
    if not IS_WINDOWS:
        return
    import shutil
    novo = get_chrome_profile_dir()
    appdata = os.environ.get("APPDATA", "")
    antigo = os.path.join(appdata, "BatePonto", "Chrome")
    if os.path.exists(antigo) and not os.path.exists(novo):
        try:
            shutil.copytree(antigo, novo)
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────
# Criação de atalhos
# ──────────────────────────────────────────────────────────────

def _criar_atalho_windows(target: str, shortcut_path: str, descricao: str = "Bate Ponto Automático"):
    """Cria atalho .lnk via PowerShell/WScript.Shell."""
    script = (
        f"$ws = New-Object -ComObject WScript.Shell; "
        f"$s = $ws.CreateShortcut('{shortcut_path}'); "
        f"$s.TargetPath = '{target}'; "
        f"$s.Description = '{descricao}'; "
        f"$s.Save()"
    )
    subprocess.run(["powershell", "-Command", script], capture_output=True)


def _criar_desktop_entry_linux(exe_path: str, destino: str):
    """Cria arquivo .desktop no caminho especificado."""
    conteudo = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=BatePonto\n"
        "Comment=Automação de ponto no Pontotel\n"
        f"Exec={exe_path}\n"
        "Icon=appointment\n"
        "Terminal=false\n"
        "Categories=Utility;\n"
        "StartupNotify=false\n"
    )
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, "w", encoding="utf-8") as f:
        f.write(conteudo)
    # Torna o .desktop executável (obrigatório em algumas DEs)
    try:
        os.chmod(destino, 0o755)
    except Exception:
        pass


def criar_atalho_startup(exe_path: str):
    """Configura o app para iniciar com o sistema."""
    if IS_WINDOWS:
        startup = os.path.join(
            os.environ.get("APPDATA", ""),
            "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
        )
        shortcut = os.path.join(startup, "BatePonto.lnk")
        _criar_atalho_windows(exe_path, shortcut)
    else:
        autostart = os.path.join(
            os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
            "autostart"
        )
        destino = os.path.join(autostart, "bateponto.desktop")
        _criar_desktop_entry_linux(exe_path, destino)


def criar_atalho_desktop(exe_path: str):
    """Cria atalho na área de trabalho."""
    if IS_WINDOWS:
        result = subprocess.run(
            ["powershell", "-Command", "[System.Environment]::GetFolderPath('Desktop')"],
            capture_output=True, text=True
        )
        desktop = result.stdout.strip() or os.path.join(os.path.expanduser("~"), "Desktop")
        shortcut = os.path.join(desktop, "BatePonto.lnk")
        _criar_atalho_windows(exe_path, shortcut)
    else:
        # Tenta XDG_DESKTOP_DIR; fallback para ~/Desktop e ~/Área de Trabalho
        xdg_dirs = _get_xdg_user_dir("DESKTOP")
        desktop = xdg_dirs or os.path.join(os.path.expanduser("~"), "Desktop")
        destino = os.path.join(desktop, "bateponto.desktop")
        _criar_desktop_entry_linux(exe_path, destino)


def criar_atalho_menu_iniciar(exe_path: str):
    """Cria atalho no menu de aplicativos."""
    if IS_WINDOWS:
        programs = os.path.join(
            os.environ.get("APPDATA", ""),
            "Microsoft", "Windows", "Start Menu", "Programs"
        )
        shortcut = os.path.join(programs, "BatePonto.lnk")
        _criar_atalho_windows(exe_path, shortcut)
    else:
        applications = os.path.join(
            os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
            "applications"
        )
        destino = os.path.join(applications, "bateponto.desktop")
        _criar_desktop_entry_linux(exe_path, destino)


def _get_xdg_user_dir(key: str) -> str | None:
    """Consulta xdg-user-dir para obter diretório XDG (ex: DESKTOP)."""
    try:
        result = subprocess.run(
            ["xdg-user-dir", key],
            capture_output=True, text=True, timeout=3
        )
        path = result.stdout.strip()
        return path if path and os.path.isdir(path) else None
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────
# Instalação do app
# ──────────────────────────────────────────────────────────────

def instalar_app(env_path: str, registrar_log_fn) -> str | None:
    """
    Copia o executável e o .env para o diretório de instalação.
    Retorna o caminho do executável instalado, ou None se não estiver rodando como exe.
    """
    import shutil

    if not getattr(sys, "frozen", False):
        registrar_log_fn("Modo script: instalação ignorada.")
        return None

    install_dir = get_install_dir()
    os.makedirs(install_dir, exist_ok=True)

    exe_nome = "BatePonto.exe" if IS_WINDOWS else "BatePonto"
    exe_destino = os.path.join(install_dir, exe_nome)
    exe_atual = sys.executable

    if os.path.abspath(exe_atual) != os.path.abspath(exe_destino):
        shutil.copy2(exe_atual, exe_destino)
        if IS_LINUX:
            os.chmod(exe_destino, 0o755)

    env_destino = os.path.join(install_dir, ".env")
    if os.path.exists(env_path) and os.path.abspath(env_path) != os.path.abspath(env_destino):
        shutil.copy2(env_path, env_destino)

    registrar_log_fn(f"App instalado em: {install_dir}")
    return exe_destino


# ──────────────────────────────────────────────────────────────
# Foco de janela do Chrome
# ──────────────────────────────────────────────────────────────

def focar_janela_chrome(registrar_log_fn=None):
    """
    Tenta trazer a janela do Chrome / Pontotel para o primeiro plano.

    Windows : usa pygetwindow
    Linux   : usa xdotool (opcional — se não instalado, apenas loga e ignora)
    """
    if IS_WINDOWS:
        try:
            import pygetwindow as gw
            import time
            time.sleep(3)
            janelas = gw.getWindowsWithTitle("Chrome")
            for janela in janelas:
                if "Pontotel" in janela.title or "Chrome" in janela.title:
                    janela.activate()
                    break
        except Exception as e:
            if registrar_log_fn:
                registrar_log_fn(f"Erro ao focar janela (Windows): {e}")
    else:
        _focar_janela_chrome_linux(registrar_log_fn)


def _focar_janela_chrome_linux(registrar_log_fn=None):
    """Foca a janela do Chrome no Linux usando xdotool (opcional)."""
    try:
        # Verifica se xdotool está disponível
        check = subprocess.run(
            ["which", "xdotool"], capture_output=True, timeout=2
        )
        if check.returncode != 0:
            if registrar_log_fn:
                registrar_log_fn(
                    "xdotool não instalado — foco automático de janela desativado. "
                    "Instale com: sudo apt install xdotool"
                )
            return

        import time
        time.sleep(3)

        result = subprocess.run(
            ["xdotool", "search", "--name", "Pontotel"],
            capture_output=True, text=True, timeout=5
        )
        ids = result.stdout.strip().split()
        if not ids:
            result = subprocess.run(
                ["xdotool", "search", "--name", "Chrome"],
                capture_output=True, text=True, timeout=5
            )
            ids = result.stdout.strip().split()

        if ids:
            subprocess.run(
                ["xdotool", "windowactivate", "--sync", ids[0]],
                capture_output=True, timeout=5
            )
    except Exception as e:
        if registrar_log_fn:
            registrar_log_fn(f"Erro ao focar janela (Linux/xdotool): {e}")


# ──────────────────────────────────────────────────────────────
# Alertas modais (substitui pyautogui.alert)
# ──────────────────────────────────────────────────────────────

def mostrar_alerta(msg: str, titulo: str = "BatePonto"):
    """
    Exibe um alerta modal bloqueante usando Tkinter puro.
    Funciona em Windows e Linux. Roda em thread separada para não bloquear o systray.
    """
    def _exibir():
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            messagebox.showwarning(titulo, msg, parent=root)
            root.destroy()
        except Exception:
            # Fallback mínimo: imprime no terminal
            print(f"[ALERTA] {titulo}: {msg}")

    threading.Thread(target=_exibir, daemon=True).start()


# ──────────────────────────────────────────────────────────────
# Rótulos de UI adaptados por plataforma
# ──────────────────────────────────────────────────────────────

def label_startup() -> str:
    """Texto do checkbox de startup no wizard de instalação."""
    return "Iniciar com o Windows" if IS_WINDOWS else "Iniciar com o sistema (autostart)"


def label_menu() -> str:
    """Texto do checkbox de menu de aplicativos."""
    return "Salvar no Menu Iniciar" if IS_WINDOWS else "Adicionar ao menu de aplicativos"


def label_desktop() -> str:
    """Texto do checkbox de atalho na área de trabalho."""
    return "Atalho na Área de Trabalho" if IS_WINDOWS else "Atalho na Área de Trabalho"
