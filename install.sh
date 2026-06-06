#!/usr/bin/env bash
# BatePonto — instalador para Ubuntu/Debian
# Uso: curl -fsSL https://raw.githubusercontent.com/MailtonOliveira/BatePontoNew/main/install.sh -o /tmp/install.sh && bash /tmp/install.sh

REPO="MailtonOliveira/BatePontoNew"
APP_NAME="BatePonto"
INSTALL_DIR="$HOME/.local/share/BatePonto"
BIN_PATH="$INSTALL_DIR/$APP_NAME"
SRC_DIR="$HOME/.local/share/BatePonto-src"
DESKTOP_DIR="$HOME/.local/share/applications"
AUTOSTART_DIR="$HOME/.config/autostart"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info() { echo -e "${GREEN}[BatePonto]${NC} $*"; }
warn() { echo -e "${YELLOW}[aviso]${NC} $*"; }
erro() { echo -e "${RED}[erro]${NC} $*"; exit 1; }

if ! command -v apt-get &>/dev/null; then
    erro "Este instalador requer Ubuntu/Debian (apt)."
fi

echo ""
echo "  ⏰  BatePonto — Instalador"
echo "  ─────────────────────────"
echo ""

info "Instalando dependências do sistema..."
sudo apt-get update -q
sudo apt-get install -y python3-tk python3-venv gir1.2-appindicator3-0.1 wget curl git \
    libglib2.0-0t64 libgtk-3-0t64 libappindicator3-1 2>/dev/null || \
sudo apt-get install -y python3-tk python3-venv gir1.2-appindicator3-0.1 wget curl git \
    libglib2.0-0 libgtk-3-0 libappindicator3-1 2>/dev/null || true

if ! command -v google-chrome &>/dev/null && ! command -v google-chrome-stable &>/dev/null; then
    info "Google Chrome não encontrado. Instalando..."
    wget -q --show-progress -O /tmp/google-chrome.deb \
        https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    sudo apt-get install -y /tmp/google-chrome.deb
    rm -f /tmp/google-chrome.deb
    info "Chrome instalado com sucesso."
else
    info "Google Chrome já está instalado."
fi

mkdir -p "$INSTALL_DIR"
USE_SOURCE=false

info "Buscando última versão no GitHub..."
LATEST=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
    | grep '"tag_name"' | head -1 | cut -d'"' -f4)

if [ -z "$LATEST" ]; then
    warn "Não foi possível consultar releases. Usando código-fonte."
    USE_SOURCE=true
else
    info "Versão encontrada: $LATEST"
    DOWNLOAD_URL="https://github.com/$REPO/releases/download/$LATEST/$APP_NAME"
    info "Baixando binário $APP_NAME..."
    if curl -fsSL "$DOWNLOAD_URL" -o "$BIN_PATH" 2>/dev/null; then
        chmod +x "$BIN_PATH"
        info "Binário instalado em: $BIN_PATH"
    else
        warn "Binário Linux não disponível neste release. Instalando do código-fonte..."
        USE_SOURCE=true
    fi
fi

if [ "$USE_SOURCE" = true ]; then
    info "Clonando repositório..."
    rm -rf "$SRC_DIR"
    git clone --depth=1 "https://github.com/$REPO.git" "$SRC_DIR"

    info "Criando ambiente virtual Python..."
    python3 -m venv "$SRC_DIR/.venv"
    "$SRC_DIR/.venv/bin/pip" install -q --upgrade pip
    "$SRC_DIR/.venv/bin/pip" install -q -r "$SRC_DIR/requirements-server.txt"
    "$SRC_DIR/.venv/bin/pip" install -q "pystray>=0.19" 2>/dev/null || true

    printf '#!/usr/bin/env bash\nexec "%s/.venv/bin/python3" "%s/main.py" "$@"\n' \
        "$SRC_DIR" "$SRC_DIR" > "$BIN_PATH"
    chmod +x "$BIN_PATH"
    info "Instalado do código-fonte em: $SRC_DIR"
fi

mkdir -p "$DESKTOP_DIR"
printf '[Desktop Entry]\nType=Application\nName=BatePonto\nComment=Automação de ponto no Pontotel\nExec=%s\nIcon=appointment\nTerminal=false\nCategories=Utility;\nStartupNotify=false\n' \
    "$BIN_PATH" > "$DESKTOP_DIR/bateponto.desktop"
chmod +x "$DESKTOP_DIR/bateponto.desktop"
info "Atalho criado no menu de aplicativos."

echo ""
read -rp "  Iniciar BatePonto automaticamente com o sistema? [s/N] " resp </dev/tty
if [[ "$resp" =~ ^[Ss]$ ]]; then
    mkdir -p "$AUTOSTART_DIR"
    cp "$DESKTOP_DIR/bateponto.desktop" "$AUTOSTART_DIR/bateponto.desktop"
    info "Autostart configurado."
fi

echo ""
echo -e "  ${GREEN}✅ Instalação concluída!${NC}"
echo ""
echo "  Para iniciar:  $BIN_PATH"
echo "  Ou pelo menu de aplicativos: BatePonto"
echo ""

read -rp "  Iniciar o BatePonto agora? [S/n] " resp </dev/tty
if [[ ! "$resp" =~ ^[Nn]$ ]]; then
    info "Iniciando BatePonto..."
    export DISPLAY="${DISPLAY:-:0}"
    export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-autolaunch:}"
    exec "$BIN_PATH"
fi
