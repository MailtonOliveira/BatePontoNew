# ⏰ BatePonto Automático

Automação em Python usando Selenium para bater o ponto automaticamente no sistema Pontotel, de forma discreta, configurável e segura.

> **Compatível com Windows e Linux** 🐧

## 🚀 Funcionalidades

- **Registro Automático:** Bate os 4 pontos (Entrada, Pausa, Retorno, Saída) nos horários configurados.
- **Configuração Segura (`.env`):** PIN e horários configurados via variável de ambiente, garantindo que dados sensíveis não fiquem expostos no código.
- **Interface na Bandeja do Sistema (SysTray):** O script roda silenciosamente em segundo plano, acessível pelo ícone na área de notificação (Windows e Linux desktop).
- **Modo Headless:** Chrome roda invisível em background com `BATEPONTO_HEADLESS=true` — sem janela visível, com systray ativo no Windows e Linux desktop.
- **Modo Servidor:** Suporte a servidores Linux sem display (ex: Oracle Cloud, VPS) — sem systray, sem Tkinter, Chrome headless puro.
- **Instalação Automática do Chrome:** Se o Chrome não estiver instalado, o app detecta e oferece instalar automaticamente (Windows: installer oficial; Linux: apt).
- **Edição em Tempo Real:** Permite configurar os horários de batida através de uma janela nativa (Tkinter), propagando as alterações instantaneamente sem reiniciar.
- **Janela Discreta:** A janela do Chrome é posicionada fora da visão após o setup, operando de forma não-intrusiva.
- **Proteção contra Duplicidade:** Verifica o "último ponto registrado" no HTML para garantir que o mesmo ponto não seja batido duas vezes no mesmo dia.
- **Feriados e Fins de Semana:** Detecta automaticamente feriados nacionais, estaduais e municipais (via BrasilAPI + fallback local) e fins de semana, pulando a batida nesses dias.
- **Localização Automática:** Detecta sua cidade e UF via IP para aplicar os feriados corretos. Configuração manual tem prioridade sobre detecção por IP.

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
- **Navegador:** Google Chrome — se não estiver instalado, o app oferece instalar automaticamente
- **Python:** 3.10+ (apenas se for rodar o código-fonte; o executável já inclui Python)

### Linux desktop 🐧
- **Navegador:** Google Chrome ou Chromium — se não encontrado, o app oferece instalar via apt
- **Python:** 3.10+
- **Tkinter:** `sudo apt install python3-tk`
- **Suporte ao SysTray:** `sudo apt install gir1.2-appindicator3-0.1` (GNOME) ou equivalente
- **Foco automático de janela** *(opcional)*: `sudo apt install xdotool`

> 💡 **Nota sobre SysTray no Linux:** Em desktops GNOME puro é necessário a extensão [AppIndicator](https://extensions.gnome.org/extension/615/appindicator-support/). No KDE, XFCE, MATE e outros funciona nativamente.

### Linux servidor (sem display)
Consulte a seção [Modo Servidor](#️-modo-servidor-ubuntu-headless) abaixo.

---

## ⚙️ Instalação e Uso

### Windows

**Opção A — Executável (recomendado)**

1. Baixe o `BatePonto.exe` na aba **Releases**.
2. Execute o arquivo — se o Chrome não estiver instalado, o app oferece instalar.
3. Na primeira execução um wizard abre o Chrome para você fazer login no Pontotel. O PIN é capturado automaticamente.

**Opção B — Código-fonte**

```bash
git clone https://github.com/MailtonOliveira/BatePontoNew.git
cd BatePontoNew
pip install -r requirements.txt
python main.py
```

---

### Ubuntu / Linux desktop

**Opção A — Instalador automático (recomendado)**

Cole no terminal e siga as instruções:

```bash
curl -fsSL https://raw.githubusercontent.com/MailtonOliveira/BatePontoNew/main/install.sh -o /tmp/install.sh && bash /tmp/install.sh
```

O script instala as dependências, baixa o binário mais recente, cria o atalho no menu de aplicativos e pergunta se deseja configurar o autostart.

**Opção B — Executável manual**

1. Baixe o binário `BatePonto` (sem extensão) na aba **Releases**.
2. Instale as dependências:
   ```bash
   sudo apt install -y python3-tk gir1.2-appindicator3-0.1
   ```
3. Torne executável e rode:
   ```bash
   chmod +x BatePonto
   ./BatePonto
   ```

**Opção C — Código-fonte**

```bash
sudo apt install -y python3-venv python3-tk gir1.2-appindicator3-0.1
git clone https://github.com/MailtonOliveira/BatePontoNew.git
cd BatePontoNew
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

> ⚠️ **Primeiro uso (Windows e Linux):** O app abre o Chrome e exibe um wizard. Faça login no Pontotel com seu e-mail/senha corporativo e aguarde — o PIN é capturado automaticamente e o `.env` é criado. Nas execuções seguintes o login é silencioso.

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

## 🔇 Modo Headless (Chrome invisível)

Ative com `BATEPONTO_HEADLESS=true` no `.env` para rodar o Chrome sem nenhuma janela visível. O systray continua ativo — você ainda acessa configurações pelo ícone na bandeja.

| Plataforma | Chrome | Systray |
|---|---|---|
| Windows | Invisível | ✅ ativo |
| Linux desktop (com display) | Invisível | ✅ ativo |
| Linux servidor (sem display) | Invisível | ❌ não aplicável |

```env
BATEPONTO_HEADLESS=true
```

> Para servidores Linux sem display, veja a seção abaixo — o comportamento é detectado automaticamente pela ausência de `$DISPLAY`.

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

Crie o arquivo `.env` na pasta do projeto (`~/BatePonto/.env`) com `BATEPONTO_HEADLESS=true` (ou o alias `BATEPONTO_SERVER=true`) e a localização manual (necessária pois o IP do servidor pode estar em outro estado):

```env
BATEPONTO_SENHA=seu_pin_aqui
BATEPONTO_URL=https://bateponto.pontotel.com.br/
BATEPONTO_HEADLESS=true
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
