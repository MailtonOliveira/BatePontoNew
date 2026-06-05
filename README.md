# ⏰ BatePonto Automático

Automação em Python usando Selenium para bater o ponto automaticamente no sistema Pontotel, de forma discreta, configurável e segura.

> **Compatível com Windows e Linux** 🐧

## 🚀 Funcionalidades

- **Registro Automático:** Bate os 4 pontos (Entrada, Pausa, Retorno, Saída) nos horários configurados.
- **Configuração Segura (`.env`):** PIN e horários configurados via variável de ambiente, garantindo que dados sensíveis não fiquem expostos no código.
- **Interface na Bandeja do Sistema (SysTray):** O script roda silenciosamente em segundo plano, acessível pelo ícone na área de notificação (Windows e Linux).
- **Edição em Tempo Real:** Permite configurar os horários de batida através de uma janela nativa (Tkinter), propagando as alterações instantaneamente sem reiniciar.
- **Janela Discreta:** A janela do Chrome é posicionada fora da visão após o setup (`position 10000,10000`), operando de forma não-intrusiva.
- **Proteção contra Duplicidade:** Verifica o "último ponto registrado" no HTML para garantir que o mesmo ponto não seja batido duas vezes no mesmo dia.
- **Feriados e Fins de Semana:** Detecta automaticamente feriados nacionais, estaduais e municipais (via BrasilAPI + fallback local) e fins de semana, pulando a batida nesses dias.
- **Localização Automática:** Detecta sua cidade e UF via IP para aplicar os feriados corretos. Pode ser configurado manualmente pelo menu.

### 🎨 Indicação visual por cor do ícone

| Cor | Significado |
|-----|-------------|
| 🟢 Verde | Funcionando normalmente |
| 🟡 Amarelo | Feriado ou fim de semana — ponto suspenso |
| 🔴 Vermelho | Falha ao registrar o ponto — ação necessária |

### 🔔 Notificações

- **Ponto registrado com sucesso:** notificação balloon no systray com o nome do ponto e horário.
- **Falha ao registrar:** ícone muda para vermelho + balloon + alerta persistente na tela que fica visível até o usuário fechar.

---

## 💻 Pré-requisitos

### Windows
- **Navegador:** Google Chrome instalado
- **Python:** 3.10+ (apenas se for rodar o código-fonte)

### Linux 🐧
- **Navegador:** Google Chrome ou Chromium instalado
- **Python:** 3.10+
- **Tkinter:** `sudo apt install python3-tk` (Ubuntu/Debian)
- **Suporte ao SysTray:** `sudo apt install gir1.2-appindicator3-0.1` (GNOME) ou equivalente
- **Foco automático de janela** *(opcional)*: `sudo apt install xdotool`

> 💡 **Nota sobre SysTray no Linux:** Em desktops GNOME puro é necessário a extensão [AppIndicator](https://extensions.gnome.org/extension/615/appindicator-support/). No KDE, XFCE, MATE e outros funciona nativamente.

---

## ⚙️ Instalação e Uso

### Opção 1: Executável Pronto (Recomendado)

| Plataforma | Arquivo |
|---|---|
| Windows | `BatePonto.exe` |
| Linux | `BatePonto` (binário ELF) |

1. Baixe o executável correspondente à sua plataforma na aba **Releases**.
2. **Linux:** torne o binário executável antes de rodar:
   ```bash
   chmod +x BatePonto
   ./BatePonto
   ```
3. Na primeira execução um wizard vai guiar a configuração.

### Opção 2: Rodar do Código-Fonte

1. Clone o repositório:
   ```bash
   git clone https://github.com/MailtonOliveira/BatePontoNew.git
   cd BatePontoNew
   ```
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Inicie a automação:
   ```bash
   python main.py
   ```

> ⚠️ **Primeiro uso:** Na primeira execução o app abre o Chrome e exibe um wizard. Faça login no Pontotel com seu e-mail/senha corporativo e aguarde — o PIN será capturado automaticamente e o arquivo `.env` será criado. Nos usos seguintes o login é silencioso.

---

## 🛠️ Como Configurar os Horários

1. **Pela Interface Gráfica (recomendado):**
   - Clique com o botão direito no ícone do BatePonto na bandeja.
   - Selecione **"⏰ Configurar Horários"**.
   - Digite os horários no formato `HH:MM` e clique em **Salvar**. A alteração entra em vigor imediatamente.

2. **Pelo arquivo `.env`:**
   - Edite as variáveis `HORARIO_ENTRADA`, `HORARIO_PAUSA`, `HORARIO_RETORNO` e `HORARIO_SAIDA`.
   - Salve e reinicie o BatePonto.

---

## 📍 Como Configurar a Localização

A localização é detectada automaticamente via IP. Para sobrescrever manualmente:

- Clique com o botão direito no ícone → **"📍 Configurar Localização"**.
- Informe a UF (ex: `MG`) e o nome da cidade.
- O app consulta a API do IBGE para validar e salva no `.env`.

A localização correta garante que feriados estaduais e municipais sejam respeitados.

---

## 🔑 Como Alterar o PIN

- Clique com o botão direito no ícone → **"🔑 Alterar PIN"**.
- Digite o novo PIN e clique em **Salvar**.

---

## ☁️ Modo Servidor (Ubuntu headless)

Para rodar em um servidor Ubuntu sem interface gráfica (ex: Oracle Cloud, VPS), o BatePonto suporta um modo headless que dispensa pystray, Tkinter e display virtual. O Chrome roda em background com `--headless=new`.

### Pré-requisitos no servidor

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv python3-tk wget gnupg2

# Google Chrome
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | \
    sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update && sudo apt install -y google-chrome-stable

# Timezone correto (Brasil)
sudo timedatectl set-timezone America/Sao_Paulo
```

### Instalação

```bash
git clone https://github.com/MailtonOliveira/BatePontoNew.git ~/BatePonto
cd ~/BatePonto
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-server.txt
```

### Configuração do `.env`

Crie o arquivo `.env` na pasta do projeto (`~/BatePonto/.env`) com `BATEPONTO_SERVER=true` e a localização manual (necessária pois o IP do servidor pode estar em outro estado):

```env
BATEPONTO_SENHA=seu_pin_aqui
BATEPONTO_URL=https://bateponto.pontotel.com.br/
BATEPONTO_SERVER=true
CHROME_BIN=/opt/google/chrome/google-chrome
HORARIO_ENTRADA=08:00
HORARIO_PAUSA=12:50
HORARIO_RETORNO=13:50
HORARIO_SAIDA=17:00
TIMEOUT_PADRAO=15
REGIAO_UF=MG
REGIAO_IBGE=3106200
```

> ⚠️ Com `REGIAO_UF` e `REGIAO_IBGE` definidos, a detecção automática por IP é ignorada — necessário para servidores em datacenter.

### Transferir perfil Chrome (sessão de login)

O app precisa do perfil Chrome do Windows (onde você já fez login no Pontotel). No Windows, compacte e envie via SSH:

```bash
# No bash do Windows (Git Bash / WSL):
tar -czf /tmp/chrome_profile.tar.gz -C "$LOCALAPPDATA/BatePonto" Chrome
scp -i ~/.ssh/sua_chave /tmp/chrome_profile.tar.gz usuario@ip-servidor:~/
```

```bash
# No servidor:
mkdir -p ~/.local/share/BatePonto
tar -xzf ~/chrome_profile.tar.gz -C ~/.local/share/BatePonto/
```

### Rodar como serviço systemd

```bash
sudo tee /etc/systemd/system/bateponto.service > /dev/null << 'EOF'
[Unit]
Description=BatePonto Automatico
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/BatePonto
ExecStart=/home/ubuntu/BatePonto/.venv/bin/python3 -u -W ignore::FutureWarning -W ignore::DeprecationWarning /home/ubuntu/BatePonto/main.py
Restart=on-failure
RestartSec=60
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now bateponto
```

### Monitorar logs

```bash
# Logs do systemd (tempo real)
sudo journalctl -u bateponto -f

# Arquivo de log do app
tail -f /tmp/BatePonto/logs_bateponto.txt
```

---

## 📦 Como Buildar o Executável

1. Instale o PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Gere o executável:

   **Windows:**
   ```bash
   py -m PyInstaller main.spec --clean
   ```
   O arquivo `dist\BatePonto.exe` será criado.

   **Linux:**
   ```bash
   python -m PyInstaller main.spec --clean
   ```
   O binário `dist/BatePonto` será criado. Torne-o executável:
   ```bash
   chmod +x dist/BatePonto
   ```

> 💡 O `main.spec` detecta automaticamente a plataforma e inclui apenas as dependências necessárias.

---

## 📝 Logs

| Plataforma | Caminho do log |
|---|---|
| Windows | `%TEMP%\BatePonto\logs_bateponto.txt` |
| Linux | `/tmp/BatePonto/logs_bateponto.txt` |

- Para ver o último evento rapidamente: botão direito no ícone → **"Último Log"**.

---

## 📂 Diretórios usados pelo app

| Finalidade | Windows | Linux |
|---|---|---|
| Perfil Chrome | `%LOCALAPPDATA%\BatePonto\Chrome` | `~/.local/share/BatePonto/Chrome` |
| Instalação | `%LOCALAPPDATA%\Programs\BatePonto` | `~/.local/share/BatePonto` |
| Config (`.env`) | Junto ao executável | `~/.config/BatePonto/` |
| Logs | `%TEMP%\BatePonto\` | `/tmp/BatePonto/` |
| Autostart | `%APPDATA%\...\Startup\BatePonto.lnk` | `~/.config/autostart/bateponto.desktop` |
| Menu de apps | `%APPDATA%\...\Programs\BatePonto.lnk` | `~/.local/share/applications/bateponto.desktop` |
