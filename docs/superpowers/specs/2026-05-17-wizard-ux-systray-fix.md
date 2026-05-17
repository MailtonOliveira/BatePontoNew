# Spec: Wizard UX, Systray Fix e Nome do Executável

**Data:** 2026-05-17  
**Escopo:** Três correções independentes em `main.py` + nova release do GitHub.

---

## Contexto

Problemas identificados após o merge da `feature/easy-install`:

1. O asset da Release no GitHub ainda está nomeado `BatePonto-1.0.exe` em vez de `BatePonto.exe`.
2. Após o wizard concluir (Chrome ocultado, wizard fechado), o ícone da bandeja não é percebido pelo usuário — provavelmente vai para o overflow da bandeja sem nenhum feedback visual.
3. O wizard mantém `-topmost: True` permanente, impedindo o usuário de clicar no Chrome durante o passo 2 (aguardando PIN).

---

## Fix 1 — Nome do executável na Release

### Problema
O `main.spec` produz `dist/BatePonto.exe`, mas o asset da release `v1.1.0` foi enviado como `BatePonto-1.0.exe`. Não há CI/CD.

### Solução
- Buildar com `pyinstaller main.spec` → `dist/BatePonto.exe`
- Criar nova release `v1.2.0` com o asset `BatePonto.exe`
- Atualizar a descrição da release (remover referência a `BatePonto-1.0.exe`)

---

## Fix 2 — Systray não percebida após wizard

### Problema
Após `root.destroy()` no `_finalizar()`, `icon.run()` é chamado corretamente — o ícone É registrado na bandeja. Porém, como o Chrome foi ocultado e a janela do wizard fechou, o usuário não percebe que o app ainda está rodando, e o ícone vai para a área de overflow (seta `^`) sem nenhuma notificação.

### Solução
Usar o parâmetro `setup=` do `icon.run()` para disparar um balloon de notificação **somente** quando o wizard concluiu (primeiro uso), via flag de módulo `_notificar_instalacao_ok`.

**Mudanças em `main.py`:**

```python
# flag de módulo (antes da função abrir_setup_wizard)
_notificar_instalacao_ok = False
```

Em `_finalizar()` (dentro do wizard), antes de `root.destroy()`:
```python
global _notificar_instalacao_ok
_notificar_instalacao_ok = True
```

Substituir `icon.run()` no bloco de startup por:
```python
def _on_systray_ready(icon):
    global _notificar_instalacao_ok
    icon.visible = True
    if _notificar_instalacao_ok:
        time.sleep(0.5)
        icon.notify("Rodando em segundo plano!", "Bate Ponto instalado ✅")
        _notificar_instalacao_ok = False

icon.run(setup=_on_systray_ready)
```

---

## Fix 3 — Wizard UX: acesso ao Chrome durante passo 2

### Problema
`root.attributes('-topmost', True)` é definido na criação do `root` e nunca removido, bloqueando qualquer clique no Chrome enquanto o wizard exibe o spinner.

### Solução

**A. Remover `-topmost` ao entrar no passo 2**

Em `_mostrar_passo2()`, adicionar:
```python
root.attributes('-topmost', False)
```

**B. Adicionar banner de dica**

Após a lista de instruções, antes do spinner:
```python
banner = tk.Frame(content, bg='#3a3a2a', relief='flat', bd=0)
banner.pack(fill='x', pady=(12, 0))
tk.Label(banner,
         text="💡  Minimize esta janela enquanto preenche o site",
         background='#3a3a2a', foreground='#f0d060',
         font=('Segoe UI', 9)).pack(pady=6, padx=10)
```

**C. Trazer wizard para frente quando PIN for detectado**

Em `_on_pin_resultado(pin)`, antes de chamar `_mostrar_conclusao()` ou `_mostrar_fallback()`:
```python
root.attributes('-topmost', True)
root.lift()
root.focus_force()
```

**D. Passo de conclusão retoma `-topmost`**

O `_mostrar_conclusao()` já terá `-topmost: True` restaurado pelo passo C.

---

## Não está no escopo

- Nenhuma mudança na lógica de captura de PIN
- Nenhuma mudança nos testes existentes (os três fixes são UI/startup, não funções puras)
- Não criar CI/CD agora

---

## Checklist de verificação manual

- [ ] `pyinstaller main.spec` gera `dist/BatePonto.exe` (sem versão no nome)
- [ ] Executar sem `.env` → wizard abre
- [ ] No passo 2: janela NÃO fica sempre na frente; clicar no Chrome funciona
- [ ] Banner amarelo "Minimize esta janela" aparece no passo 2
- [ ] Ao digitar PIN e submeter: wizard salta para frente automaticamente
- [ ] Clicar "Instalar e Fechar": wizard fecha, Chrome some, balloon aparece na bandeja
- [ ] Ícone da bandeja visível após balloon
