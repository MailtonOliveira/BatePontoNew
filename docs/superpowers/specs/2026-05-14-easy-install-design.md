# Design: BatePonto — Instalação Zero-Config para Usuário Final

**Data:** 2026-05-14  
**Status:** Aprovado

---

## Objetivo

Transformar o BatePonto em um produto que qualquer usuário consiga usar apenas baixando e executando o `.exe`, sem precisar criar arquivos `.env`, obter chaves de API ou configurar variáveis de ambiente.

---

## Problema atual

| Fricção | Impacto |
|---|---|
| `BATEPONTO_SENHA` ausente bloqueia o app com mensagem de erro técnica | Usuário não sabe o que é `.env` |
| `FERIADOS_API_KEY` exige cadastro em feriadosapi.com | Usuário precisaria se registrar em serviço externo |
| Sem orientação no primeiro uso | Chrome abre sem contexto; usuário não sabe o que fazer |

---

## Solução: Wizard de primeiro uso + chave embutida

### 1. Chave de feriados embutida

`FERIADOS_API_KEY` sai do `.env` e passa a ser uma constante hardcoded no código:

```python
_FERIADOS_API_KEY = "chave_do_desenvolvedor_aqui"
```

O `os.getenv('FERIADOS_API_KEY', '')` existente passa a usar essa constante como fallback:

```python
os.getenv('FERIADOS_API_KEY', _FERIADOS_API_KEY)
```

Mantém compatibilidade retroativa com quem ainda tiver a chave no `.env`.

### 2. Detecção de primeiro uso

Na inicialização, antes de qualquer outra coisa, o app verifica:

```
BATEPONTO_SENHA vazia ou ausente?
  └─ sim → abre SetupWizard (bloqueia até conclusão)
  └─ não → fluxo normal atual (sem mudança)
```

### 3. SetupWizard — dois passos

**Passo 1/2 — Boas-vindas** (Chrome ainda fechado):

- Explica o que o app faz
- Instrui o usuário a fazer login no site e digitar o PIN quando pedido
- Botão "Iniciar →" abre o Chrome e avança para o Passo 2

**Passo 2/2 — Aguardando PIN** (Chrome visível, wizard permanece em primeiro plano):

- Lista de instruções visíveis: fazer login, digitar PIN, não fechar o Chrome
- Spinner animado "Detectando PIN..."
- Thread em background monitora o Selenium:
  - Aguarda a página `pagina-sincronizacao-pin__input-pin` aparecer
  - Quando o usuário clica em confirmar (`pagina-sincronizacao-pin__botao-confirmar`), lê o valor do campo input via Shadow DOM antes do submit processar
  - Salva com `set_key(ENV_PATH, "BATEPONTO_SENHA", pin_capturado)`
  - Atualiza variável global `senha`
- Wizard transiciona para tela de conclusão (mesmo frame, sem nova janela)

**Conclusão** (inline no Passo 2):

- "✅ Configuração concluída!"
- Explica que o app roda em segundo plano no systray
- Botão "Fechar" — wizard fecha, Chrome se oculta, systray ativo

### 4. Opção "Alterar PIN" no systray

Novo item no menu do systray entre "Configurar Localização" e "Último Log":

```
⏰ Configurar Horários
📍 Configurar Localização
🔑 Alterar PIN          ← novo
Último Log
Sair
```

Abre janela simples (mesmo estilo visual das existentes) com:
- Campo de entrada para o novo PIN
- Botão "💾 Salvar" — salva com `set_key` e atualiza `senha` em memória
- Botão "Cancelar"

---

## Tratamento de erros

| Cenário | Comportamento |
|---|---|
| Usuário fecha o Chrome durante setup | Wizard detecta `WebDriverException`, exibe botão "Tentar novamente" que reabre o Chrome |
| Usuário clica "Cancelar" no Passo 2 | Wizard fecha, Chrome fecha, app encerra. Próxima execução reinicia o wizard |
| Detecção automática do PIN falha (timeout 5 min) | Wizard exibe campo manual: "Digite seu PIN aqui:" + botão Salvar |
| `.env` não existe no primeiro uso | `set_key()` cria o arquivo automaticamente (comportamento já existente) |

---

## O que NÃO muda

- Janela de configuração de horários (systray → "Configurar Horários")
- Janela de configuração de localização (systray → "Configurar Localização")
- Lógica de detecção de feriados, fuso horário, fins de semana
- Fluxo de automação Selenium para bater ponto
- Geração do `.exe` via PyInstaller

---

## Visual

Todas as novas janelas seguem o padrão existente:
- Fundo: `#2b2b2b`
- Texto principal: `#ffffff`
- Destaque/header: `#4CAF50`
- Fonte: Segoe UI
- Tema ttk: `clam`

---

## Arquivos afetados

- `main.py` — único arquivo a modificar:
  1. Adicionar constante `_FERIADOS_API_KEY`
  2. Atualizar fallback do `os.getenv('FERIADOS_API_KEY', ...)`
  3. Adicionar função `abrir_setup_wizard()`
  4. Adicionar função `abrir_janela_alterar_pin()`
  5. Adicionar item "Alterar PIN" no menu do systray
  6. Substituir o bloco de verificação `if not senha: sys.exit(1)` pelo dispatch para o wizard
