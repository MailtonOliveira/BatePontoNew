#!/usr/bin/env bash
# BatePonto — instalador para Ubuntu/Debian
# Uso: bash install.sh
#      curl -fsSL https://raw.githubusercontent.com/MailtonOliveira/BatePontoNew/main/install.sh | bash

set -e

REPO="MailtonOliveira/BatePontoNew"
APP_NAME="BatePonto"
INSTALL_DIR="$HOME/.local/share/BatePonto"
BIN_PATH="$INSTALL_DIR/$APP_NAME"
DESKTOP_DIR="$HOME/.local/share/applications"
AUTOSTART_DIR="$HOME/.config/autostart"

# ── Cores ──────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[BatePonto]${NC} $*"; }
warn()    { echo -e "${YELLOW}[aviso]${NC} $*"; }
erro()    { echo -e "${RED}[erro]${NC} $*"; exit 1; }

# ── Verifica distro ────────────────────────────────────────────
if ! command -v apt-get &>/dev/null; then
    erro "Este instalador requer Ubuntu/Debian (apt). Para outras distros, baixe o binário manualmente."
fi

echo ""
echo "  ⏰  BatePonto — Instalador"
echo "  ─────────────────────────"
echo ""

# ── Dependências do sistema ────────────────────────────────────
info "Instalando dependências do sistema..."
sudo apt-get update -q
sudo apt-get install -y python3-tk gir1.2-appindicator3-0.1 wget curl libglib2.0-0 \
    libgtk-3-0 libappindicator3-1 2>/dev/null || true

# ── Google Chrome ──────────────────────────────────────────────
if ! command -v google-chrome &>/dev/null && ! command -v google-chrome-stable &>/dev/null; then
    info "Google Chrome não encontrado. Instalando..."
    wget -q -O /tmp/google-chrome.gpg https://dl.google.com/linux/linux_signing_key.pub
    sudo apt-key add /tmp/google-chrome.gpg 2>/dev/null
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" \
        | sudo tee /etc/apt/sources.list.d/google-chrome.list > /dev/null
    sudo apt-get update -q
    sudo apt-get install -y google-chrome-stable
    info "Chrome instalado com sucesso."
else
    info "Google Chrome já está instalado."
fi

# ── Baixar binário ─────────────────────────────────────────────
info "Buscando última versão no GitHub..."
LATEST=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
    | grep '"tag_name"' | head -1 | cut -d'"' -f4)

if [ -z "$LATEST" ]; then
    erro "Não foi possível obter a versão mais recente. Verifique sua conexão."
fi

info "Versão encontrada: $LATEST"

DOWNLOAD_URL="https://github.com/$REPO/releases/download/$LATEST/$APP_NAME"

info "Baixando $APP_NAME..."
mkdir -p "$INSTALL_DIR"
curl -fsSL "$DOWNLOAD_URL" -o "$BIN_PATH" || erro "Falha ao baixar o binário. Verifique se o release '$LATEST' contém o arquivo '$APP_NAME'."
chmod +x "$BIN_PATH"
info "Binário instalado em: $BIN_PATH"

# ── Atalho no menu de aplicativos ─────────────────────────────
mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_DIR/bateponto.desktop" << EOF
[Desktop Entry]
Type=Application
Name=BatePonto
Comment=Automação de ponto no Pontotel
Exec=$BIN_PATH
Icon=appointment
Terminal=false
Categories=Utility;
StartupNotify=false
EOF
chmod +x "$DESKTOP_DIR/bateponto.desktop"
info "Atalho criado no menu de aplicativos."

# ── Autostart ─────────────────────────────────────────────────
echo ""
read -rp "  Iniciar BatePonto automaticamente com o sistema? [s/N] " resp
if [[ "$resp" =~ ^[Ss]$ ]]; then
    mkdir -p "$AUTOSTART_DIR"
    cp "$DESKTOP_DIR/bateponto.desktop" "$AUTOSTART_DIR/bateponto.desktop"
    info "Autostart configurado."
fi

# ── Concluído ──────────────────────────────────────────────────
echo ""
echo -e "  ${GREEN}✅ Instalação concluída!${NC}"
echo ""
echo "  Para iniciar:  $BIN_PATH"
echo "  Ou pelo menu de aplicativos: BatePonto"
echo ""

read -rp "  Iniciar o BatePonto agora? [S/n] " resp
if [[ ! "$resp" =~ ^[Nn]$ ]]; then
    info "Iniciando BatePonto..."
    nohup "$BIN_PATH" &>/dev/null &
fi
