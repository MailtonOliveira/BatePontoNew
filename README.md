# ⏰ BatePonto Automático

Automação em Python usando Selenium para bater o ponto automaticamente no sistema Pontotel, de forma discreta, configurável e segura.

## 🚀 Funcionalidades

- **Registro Automático:** Bate os 4 pontos (Entrada, Pausa, Retorno, Saída) nos horários configurados.
- **Configuração Segura (`.env`):** PIN e horários configurados via variável de ambiente, garantindo que dados sensíveis não fiquem expostos no código.
- **Interface na Bandeja do Sistema (SysTray):** O script roda silenciosamente em segundo plano, acessível pelo ícone na área de notificação do Windows.
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

- **Sistema Operacional:** Windows (testado para rodar na SysTray)
- **Navegador:** Google Chrome instalado
- **Python:** 3.10+ (apenas se for rodar o código-fonte)

---

## ⚙️ Instalação e Uso

### Opção 1: Executável Pronto (Recomendado)

1. Baixe o executável `BatePonto.exe` disponível na aba Releases.
2. Execute o `BatePonto.exe` — na primeira execução um wizard vai guiar a configuração.

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

## 📦 Como Buildar o Executável (.exe)

1. Instale o PyInstaller:
   ```bash
   pip install pyinstaller
   ```
2. Gere o executável:
   ```bash
   py -m PyInstaller main.spec --clean
   ```
3. O `BatePonto.exe` será criado em `dist/`.

---

## 📝 Logs

Todos os eventos são registrados em `%TEMP%\BatePonto\logs_bateponto.txt`.

- Para ver o último evento rapidamente: botão direito no ícone → **"Último Log"**.
