# Deploy VPS (Oracle ARM64 Ubuntu 24.04)

Runbook testado em 30/09/2026 (instância `instance-20260930-0148`, IP interno Oracle, ARM64 aarch64, Snap Chromium).

## Provisionamento (ordem exata)

```bash
# 1. System deps + Python + Chromium (ARM64 usa snap)
sudo apt update && sudo apt install -y python3 python3-pip python3-venv git
sudo apt install -y chromium-browser  # snap

# 2. v4l2loopback OBRIGATÓRIO — sem /dev/video10 o Chrome headless falha com
#    "session not created" ao usar --use-fake-device-for-media-stream
sudo apt install -y linux-headers-$(uname -r) v4l2loopback-dkms
sudo modprobe v4l2loopback video_nr=10 card_label="VirtualCam" exclusive_caps=1
echo "v4l2loopback" | sudo tee /etc/modules-load.d/v4l2loopback.conf
echo 'options v4l2loopback video_nr=10 card_label="VirtualCam" exclusive_caps=1' | sudo tee /etc/modprobe.d/v4l2loopback.conf

# 3. Repo + venv
git clone https://github.com/MailtonOliveira/BatePontoNew.git ~/BatePonto
cd ~/BatePonto
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-server.txt

# 4. .env (ver .env.example)
cp .env.example .env && nano .env
```

## systemd unit (bateponto.service)

```ini
[Unit]
Description=BatePonto - Automacao Pontotel
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/BatePonto
Environment=CHROME_BIN=/snap/chromium/current/usr/lib/chromium-browser/chrome
Environment=BATEPONTO_HEADLESS=true
ExecStart=/home/ubuntu/BatePonto/.venv/bin/python3 /home/ubuntu/BatePonto/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now bateponto
```

## ⚠️ Pitfalls do unit (causaram crash loop real)

1. **`Environment=BATEPONTO_HEADLESS=true` é obrigatório no unit.**
   Sem ela, `HEADLESS_CHROME=False` → o código tenta abrir Chrome com GUI e
   wizard de setup → `ModuleNotFoundError: pystray` → crash loop.

2. **NÃO definir `Environment=DISPLAY=:0` (nem WAYLAND_DISPLAY) no unit.**
   O código deriva `_has_display` de `DISPLAY` e com display falso
   `SERVER_MODE` vira `False` → entra no fluxo de setup wizard (Tkinter/pystray)
   → crash. Em VPS headless o unit deve ter APENAS `CHROME_BIN` e
   `BATEPONTO_HEADLESS`.

3. **`v4l2loopback` antes do primeiro start** — o erro
   `session not created` no journalctl NÃO é do Selenium/driver, é a câmera
   fake sem device. Instalar headers + dkms + modprobe ANTES do `enable --now`.

## Verificação pós-deploy

```bash
systemctl is-active bateponto          # → active
ps aux | grep main.py | grep -v grep   # → exatamente 1 processo
tail -f /tmp/BatePonto/logs_bateponto.txt
# Esperado:
#   "Horários configurados: Entrada=08:00, Pausa=12:50, Retorno=13:50, Saída=17:00"
#   "Localização resolvida: <cidade>/<UF>"
#   "Script iniciado e monitorando horários..."
```

Sinais de erro conhecidos:
- `ERRO ao abrir Chrome: session not create...` → falta v4l2loopback (pitfall 3)
- `Aguardando configuração manual` em loop → unit com DISPLAY setado (pitfall 2)
- `ModuleNotFoundError: pystray` → falta BATEPONTO_HEADLESS (pitfall 1)

## Reinício após mudança de horário

```bash
sed -i 's/^HORARIO_SAIDA=.*/HORARIO_SAIDA=17:00/' ~/BatePonto/.env
sudo systemctl restart bateponto
```

Sempre `sudo systemctl restart bateponto` — nunca nohup manual junto do systemd
(profile Chrome duplicado → InvalidSessionIdException).