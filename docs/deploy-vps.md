# Deploy VPS (Oracle ARM64 Ubuntu 24.04)

Runbook testado em 30/09/2026 (instância Oracle ARM64 aarch64, Snap Chromium).

## ⚠️ Autenticação no Pontotel — LEIA ANTES DE SUBIR

O **PIN do `.env` NÃO faz login no portal**. O Chrome precisa de uma sessão
autenticada no `bateponto.pontotel.com.br` ANTES do primeiro start do serviço
— sem ela o script fica preso para sempre em
`Aguardando configuração manual (Login ou Setup)` (o wizard é Tkinter e não
existe em VPS headless) e **nenhum ponto é batido**.

Duas formas de autenticar:

### Opção A — Subir o perfil Chrome já logado (do seu PC)

1. Rode o BatePonto uma vez no PC (Windows), faça o login no portal quando
   pedir. O perfil fica em `%LOCALAPPDATA%\BatePonto\Chrome`.
2. Empacote SEM os caches e suba:

```bash
cd /c/Users/<user>/AppData/Local/BatePonto
tar --exclude='Chrome/Default/Cache' --exclude='Chrome/Default/Code Cache' \
    --exclude='Chrome/Default/GPUCache' --exclude='Chrome/Default/DawnGraphiteCache' \
    --exclude='Chrome/Default/DawnWebGPUCache' --exclude='Chrome/GrShaderCache' \
    --exclude='Chrome/ShaderCache' -czf bp_profile.tar.gz Chrome
scp -i ~/.ssh/<key> bp_profile.tar.gz ubuntu@<IP>:/tmp/
```

3. Na VPS (serviço parado):

```bash
sudo systemctl stop bateponto
rm -rf ~/BatePonto/chrome_profile
tar -xzf /tmp/bp_profile.tar.gz -C ~/BatePonto/
mv ~/BatePonto/Chrome ~/BatePonto/chrome_profile
sudo systemctl start bateponto
```

⚠️ Sessões expiram — se o perfil subir velho, o site volta pra
`#/autenticacao` e a Opção B é necessária.

### Opção B — Login via DevTools no Chrome headless da VPS

O serviço roda com `--remote-debugging-port=9222`, então dá pra logar sem GUI:

```bash
# ver a página atual
curl -s http://127.0.0.1:9222/json | python3 -c "import json,sys; [print(p['url']) for p in json.load(sys.stdin) if p.get('type')=='page']"

# preencher email/senha e submeter via WebSocket (websocket-client, suppress_origin=True
# — o DevTools recusa conexão com header Origin)
pip install websocket-client  # dentro do .venv
python3 << 'EOF'
import json, subprocess, websocket, time
pages = json.loads(subprocess.check_output(['curl','-s','http://127.0.0.1:9222/json']).decode())
page = [p for p in pages if p.get('type')=='page'][0]
ws = websocket.create_connection(page['webSocketDebuggerUrl'], timeout=15, suppress_origin=True)
def ev(expr):
    ws.send(json.dumps({'id':1,'method':'Runtime.evaluate','params':{'expression':expr,'returnByValue':True}}))
    return json.loads(ws.recv())['result']['result']['value']
ev("var e=document.querySelector('#email'); e.focus(); e.value='SEU_EMAIL'; e.dispatchEvent(new Event('input',{bubbles:true})); 'ok'")
ev("var s=document.querySelector('#senha'); s.focus(); s.value='SUA_SENHA'; s.dispatchEvent(new Event('input',{bubbles:true})); 'ok'")
ev("var b=Array.from(document.querySelectorAll('button')).filter(function(x){return x.innerText.trim()==='Entrar'}); b[0].click(); 'ok'")
time.sleep(10)
print(ev('location.href'), ev("document.body.innerText.substring(0,200)"))
EOF
```

Após o login o site pede um nome de coletor (`#nome-coletor`) → preencher e
clicar "Salvar". A sessão fica gravada no perfil — login é só uma vez.

### Confirmar que funcionou

```bash
tail -f /tmp/BatePonto/logs_bateponto.txt
# ✅ "Configuração concluída. Janela oculta." + "Próximo ponto às HH:MM. Aguardando..."
# ❌ "Aguardando configuração manual (Login ou Setup)" = sem sessão / login falhou
```

## Provisionamento (ordem exata)

```bash
# 0. Timezone OBRIGATÓRIO — America/Sao_Paulo. O código usa datetime.now()
#    sem timezone; servidor em UTC = todos os pontos 3h adiantados.
sudo timedatectl set-timezone America/Sao_Paulo

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
- `Aguardando configuração manual` em loop → sem login no Pontotel (ver seção Autenticação) ou unit com DISPLAY setado (pitfall 2)
- `ModuleNotFoundError: pystray` → falta BATEPONTO_HEADLESS (pitfall 1)
- "Email ou senha inválidos" na tela `#/autenticacao` → conferir credenciais do portal (não são o PIN do `.env`)

## Reinício após mudança de horário

```bash
sed -i 's/^HORARIO_SAIDA=.*/HORARIO_SAIDA=17:00/' ~/BatePonto/.env
sudo systemctl restart bateponto
```

Sempre `sudo systemctl restart bateponto` — nunca nohup manual junto do systemd
(profile Chrome duplicado → InvalidSessionIdException).