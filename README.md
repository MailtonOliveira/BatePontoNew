# ⏰ BatePonto Automático

Automação em Python usando Selenium para bater o ponto automaticamente no sistema Pontotel, de forma discreta, configurável e segura.

## 🚀 Funcionalidades

- **Registro Automático:** Bate os 4 pontos (Entrada, Pausa, Retorno, Saída) nos horários configurados.
- **Configuração Segura (`.env`):** Senha PIN e horários configurados via variável de ambiente, garantindo que dados sensíveis não fiquem expostos no código.
- **Interface na Bandeja do Sistema (SysTray):** O script roda silenciosamente em segundo plano, acessível pelo ícone na área de notificação do Windows.
- **Edição em Tempo Real:** Permite configurar os horários de batida através de uma janela nativa (Tkinter), propagando as alterações instantaneamente sem necessidade de reiniciar.
- **Janela Discreta:** A janela do Chrome (necessária para login inicial) é posicionada fora da visão periférica (`position 10000,10000`) após o setup, operando de forma não-intrusiva.
- **Proteção contra Duplicidade:** O script verifica o "último ponto registrado" no HTML para garantir que o mesmo ponto não seja batido duas vezes no mesmo dia.

---

## 💻 Pré-requisitos

- **Sistema Operacional:** Windows (testado para rodar na SysTray)
- **Navegador:** Google Chrome instalado
- **Python:** 3.10+ (apenas se for rodar o código-fonte)

---

## ⚙️ Instalação e Uso

### Opção 1: Executável Pronto (Recomendado)

1. Baixe o executável `BatePonto.exe` gerado (se disponível na aba Releases).
2. Na mesma pasta do executável, crie um arquivo chamado `.env`
3. Copie o conteúdo do arquivo `.env.example` para o seu `.env` e preencha com a sua senha (PIN).
4. Execute o `BatePonto.exe`.

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
3. Copie o arquivo de exemplo do ambiente:
   ```bash
   cp .env.example .env
   ```
4. Edite o arquivo `.env` com seu **PIN** (senha).
5. Inicie a automação:
   ```bash
   python main.py
   ```

> ⚠️ **Atenção:** No primeiro login, o sistema Pontotel pode exigir um captcha ou login com sua conta do Google/e-mail corporativo. O próprio script identificará isso e moverá a janela do Chrome para o centro da sua tela. Após você finalizar esse login inicial, nos próximos dias (ou se fechar/abrir o script), o login usará o cache local e será automático.

---

## 🛠️ Como Configurar os Horários

Os horários podem ser configurados de duas formas:

1. **Pela Interface Gráfica:**
   - Clique com o botão direito no ícone verde do BatePonto perto do relógio do Windows.
   - Selecione **"⏰ Configurar Horários"**.
   - Digite os horários desejados no formato `HH:MM`.
   - Clique em **Salvar**. A alteração entra em vigor no mesmo segundo!
   
2. **Pelo arquivo `.env`:**
   - Abra o arquivo `.env` com o Bloco de Notas.
   - Edite as variáveis `HORARIO_ENTRADA`, `HORARIO_PAUSA`, etc.
   - Salve o arquivo e reinicie o BatePonto.

---

## 📦 Como Buildar o Executável (.exe)

Se você fez modificações no código e quer gerar o próprio executável:

1. Certifique-se de ter o PyInstaller instalado:
   ```bash
   pip install pyinstaller
   ```
2. Rode o comando de build usando o `.spec` otimizado:
   ```bash
   py -m PyInstaller main.spec --clean
   ```
3. O `BatePonto.exe` será criado dentro da pasta `dist/`.

> **Importante:** Sempre coloque o arquivo `.env` na mesma pasta onde colocar o seu novo `.exe`!

---

## 📝 Logs

O sistema cria logs de todas as verificações e eventos de batida de ponto para você ter certeza de que funcionou.

- Para visualizar rapidamente o resultado da última checagem: botão direito no ícone da bandeja -> **"Último Log"**.
- O arquivo completo fica salvo na pasta temporária do Windows (`%TEMP%\BatePonto\logs_bateponto.txt`).
