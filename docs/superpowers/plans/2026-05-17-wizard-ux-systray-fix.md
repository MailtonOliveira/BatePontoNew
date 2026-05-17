# Wizard UX, Systray Fix e Release — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corrigir três problemas pós-release: wizard bloqueando Chrome durante o passo 2, ícone da bandeja não percebido após o wizard, e asset da release com nome errado.

**Architecture:** Todas as mudanças são em `main.py` (arquivo único de produção). Fix 1 toca `_mostrar_passo2()` e `_on_pin_resultado()`. Fix 2 toca `_finalizar()` e o bloco de startup com `icon.run()`. Fix 3 é build + GitHub release via CLI.

**Tech Stack:** Python 3, tkinter, pystray, PyInstaller, GitHub CLI (`gh`)

---

## Mapa de arquivos

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `main.py` | Modificar | Fixes 1 e 2 — wizard UX e systray notification |
| `dist/BatePonto.exe` | Gerar | Build do PyInstaller para Fix 3 |

---

## Task 1: Wizard UX — remover topmost no passo 2 e trazer de volta ao detectar PIN

**Files:**
- Modify: `main.py` — função `_mostrar_passo2()` (~linha 723) e `_on_pin_resultado()` (~linha 874)

- [ ] **Step 1: Abrir `main.py` e localizar `_mostrar_passo2()`**

A função começa em torno da linha 723:
```python
def _mostrar_passo2():
    _limpar()
    ttk.Label(content, text="⏰ Bate Ponto", style='Header.TLabel').pack(pady=(0, 10))
```

- [ ] **Step 2: Adicionar `root.attributes('-topmost', False)` no início de `_mostrar_passo2()`**

Substituir:
```python
    def _mostrar_passo2():
        _limpar()
        ttk.Label(content, text="⏰ Bate Ponto", style='Header.TLabel').pack(pady=(0, 10))
        ttk.Label(content, text="Aguardando configuração...",
                  font=('Segoe UI', 11, 'bold'), background='#2b2b2b',
                  foreground='#ffffff').pack(pady=(0, 10))

        for txt in ["●  Faça login no site da Pontotel",
                    "●  Digite seu PIN quando pedido",
                    "●  Não feche o Chrome"]:
            tk.Label(content, text=txt, background='#2b2b2b', foreground='#aaaaaa',
                     font=('Segoe UI', 9)).pack(anchor='w', pady=1)

        spinner_var = tk.StringVar(value="◐  Detectando PIN...")
```

Por:
```python
    def _mostrar_passo2():
        root.attributes('-topmost', False)
        _limpar()
        ttk.Label(content, text="⏰ Bate Ponto", style='Header.TLabel').pack(pady=(0, 10))
        ttk.Label(content, text="Aguardando configuração...",
                  font=('Segoe UI', 11, 'bold'), background='#2b2b2b',
                  foreground='#ffffff').pack(pady=(0, 10))

        for txt in ["●  Faça login no site da Pontotel",
                    "●  Digite seu PIN quando pedido",
                    "●  Não feche o Chrome"]:
            tk.Label(content, text=txt, background='#2b2b2b', foreground='#aaaaaa',
                     font=('Segoe UI', 9)).pack(anchor='w', pady=1)

        banner = tk.Frame(content, bg='#3a3a2a', relief='flat', bd=0)
        banner.pack(fill='x', pady=(12, 0))
        tk.Label(banner,
                 text="💡  Minimize esta janela enquanto preenche o site",
                 background='#3a3a2a', foreground='#f0d060',
                 font=('Segoe UI', 9)).pack(pady=6, padx=10)

        spinner_var = tk.StringVar(value="◐  Detectando PIN...")
```

- [ ] **Step 3: Localizar `_on_pin_resultado()` (~linha 874)**

```python
    def _on_pin_resultado(pin):
        if pin:
            _salvar_pin(pin)
            _mostrar_conclusao()
        else:
            try:
                if driver:
                    driver.find_elements(By.CSS_SELECTOR, "body")
                _mostrar_fallback()
            except Exception:
                _mostrar_erro_chrome()
```

- [ ] **Step 4: Adicionar restauração do `topmost` antes de exibir conclusão ou fallback**

Substituir a função inteira por:
```python
    def _on_pin_resultado(pin):
        root.attributes('-topmost', True)
        root.lift()
        root.focus_force()
        if pin:
            _salvar_pin(pin)
            _mostrar_conclusao()
        else:
            try:
                if driver:
                    driver.find_elements(By.CSS_SELECTOR, "body")
                _mostrar_fallback()
            except Exception:
                _mostrar_erro_chrome()
```

- [ ] **Step 5: Verificar que os testes continuam passando**

```
pytest tests/ -v
```

Saída esperada: `14 passed`

- [ ] **Step 6: Commit**

```
git add main.py
git commit -m "fix: wizard passo2 sem topmost permanente e banner de dica; lift ao detectar PIN"
```

---

## Task 2: Systray — balloon de notificação após conclusão do wizard

**Files:**
- Modify: `main.py` — adicionar flag `_notificar_instalacao_ok` (~linha 665), atualizar `_finalizar()` (~linha 782), substituir `icon.run()` (~linha 1488)

- [ ] **Step 1: Localizar a linha logo antes de `def abrir_setup_wizard(` (~linha 668)**

Adicionar a flag de módulo ANTES da função. Localizar:
```python
def abrir_setup_wizard(pular_para_passo2=False):
```

E adicionar acima:
```python
_notificar_instalacao_ok = False


```

O arquivo deve ficar assim nessa região:
```python
_notificar_instalacao_ok = False


def abrir_setup_wizard(pular_para_passo2=False):
```

- [ ] **Step 2: Localizar `_finalizar()` dentro do wizard (~linha 782)**

O início da função:
```python
        def _finalizar():
            try:
                exe_instalado = instalar_app()
```

O final da função:
```python
            try:
                if driver:
                    driver.set_window_position(10000, 10000)
            except Exception:
                pass
            root.destroy()
```

- [ ] **Step 3: Adicionar `_notificar_instalacao_ok = True` antes de `root.destroy()`**

Substituir o final de `_finalizar()`:
```python
            try:
                if driver:
                    driver.set_window_position(10000, 10000)
            except Exception:
                pass
            root.destroy()
```

Por:
```python
            try:
                if driver:
                    driver.set_window_position(10000, 10000)
            except Exception:
                pass
            global _notificar_instalacao_ok
            _notificar_instalacao_ok = True
            root.destroy()
```

- [ ] **Step 4: Localizar `icon.run()` no final do arquivo (~linha 1488)**

O bloco atual:
```python
systray_icon = icon
icon.run()
```

- [ ] **Step 5: Substituir `icon.run()` por `icon.run(setup=_on_systray_ready)` com a função setup**

Substituir:
```python
systray_icon = icon
icon.run()
```

Por:
```python
systray_icon = icon


def _on_systray_ready(icon):
    global _notificar_instalacao_ok
    icon.visible = True
    if _notificar_instalacao_ok:
        time.sleep(0.5)
        icon.notify("Rodando em segundo plano!", "Bate Ponto instalado ✅")
        _notificar_instalacao_ok = False


icon.run(setup=_on_systray_ready)
```

- [ ] **Step 6: Verificar que os testes continuam passando**

```
pytest tests/ -v
```

Saída esperada: `14 passed`

- [ ] **Step 7: Commit**

```
git add main.py
git commit -m "feat: balloon de notificação na bandeja ao concluir wizard de primeiro uso"
```

---

## Task 3: Build e publicação da release v1.2.0 com nome correto

**Files:**
- Gerar: `dist/BatePonto.exe` via PyInstaller

- [ ] **Step 1: Garantir que estamos na branch `main` com o código atualizado**

```
git checkout main
git merge feature/easy-install
```

> Se preferir criar PR antes de fazer merge, pule este step e volte após o PR ser aprovado.

- [ ] **Step 2: Buildar o executável**

```
pyinstaller main.spec
```

Saída esperada: `dist/BatePonto.exe` criado sem erros de WARNING crítico. O arquivo deve ter em torno de 30–50 MB.

Verificar:
```
ls dist/
```

Deve existir `BatePonto.exe` (e não `BatePonto-1.0.exe`).

- [ ] **Step 3: Testar o executável manualmente (smoke test)**

1. Copiar `dist/BatePonto.exe` para uma pasta limpa (sem `.env`)
2. Executar o `.exe`
3. Wizard de boas-vindas deve abrir
4. Clicar "Cancelar" — app fecha

- [ ] **Step 4: Criar tag v1.2.0**

```
git tag v1.2.0
git push origin v1.2.0
```

- [ ] **Step 5: Publicar release no GitHub com o asset correto**

```
gh release create v1.2.0 dist/BatePonto.exe \
  --title "BatePonto v1.2.0" \
  --notes "## O que há de novo

### Melhorias no wizard de instalação
- **Passo 2 não bloqueia mais o Chrome:** a janela do wizard agora pode ser minimizada enquanto o usuário preenche login e PIN no site. Quando o PIN é detectado, o wizard salta automaticamente para frente.
- **Banner de dica:** faixa amarela no passo 2 orienta o usuário a minimizar a janela.
- **Notificação na bandeja:** ao concluir a instalação, um balloon aparece na bandeja do sistema confirmando que o app está rodando em segundo plano.
- **Nome do executável corrigido:** o arquivo agora se chama \`BatePonto.exe\` (sem versão no nome do arquivo).

### Como usar
1. Baixe o \`BatePonto.exe\`
2. Execute — o wizard abrirá automaticamente
3. Faça login no Pontotel; minimize o wizard enquanto preenche o site
4. O wizard volta à frente quando detectar o PIN
5. Escolha atalhos e clique em **Instalar e Fechar**
6. Um balloon confirmará que o app está na bandeja do sistema

### Requisitos
- Windows 10 ou superior
- Google Chrome instalado"
```

- [ ] **Step 6: Confirmar a release no GitHub**

```
gh release view v1.2.0
```

Verificar que o asset listado é `BatePonto.exe` e não `BatePonto-1.0.exe`.

---

## Checklist de cobertura da spec

| Requisito | Task |
|---|---|
| Remover `-topmost` permanente no passo 2 | Task 1 Step 2 |
| Banner "Minimize esta janela" no passo 2 | Task 1 Step 2 |
| Wizard volta para frente quando PIN detectado | Task 1 Step 4 |
| Balloon de notificação após wizard concluir | Task 2 Steps 3–5 |
| Asset da release nomeado `BatePonto.exe` | Task 3 |
| Release notes sem referência a `BatePonto-1.0.exe` | Task 3 Step 5 |
