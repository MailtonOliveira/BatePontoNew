# BrasilAPI Feriados Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir `feriadosapi.com` por BrasilAPI (sem chave) com fallback local via algoritmo de Páscoa, adicionando feriados estaduais e municipais de capitais.

**Architecture:** Adicionar três dicts module-level (`FERIADOS_ESTADUAIS`, `IBGE_CAPITAIS`, `FERIADOS_MUNICIPAIS_CAPITAIS`) e duas funções puras (`_calcular_pascoa`, `_feriados_nacionais_fallback`) em `main.py`. Substituir `_carregar_feriados_do_ano` para usar BrasilAPI + dicts. Remover `_FERIADOS_API_KEY`.

**Tech Stack:** Python 3, requests, datetime, unittest.mock, pytest

---

## Mapa de arquivos

| Arquivo | Ação | Responsabilidade |
|---------|------|-----------------|
| `main.py` | Modificar | Adicionar dicts, funções puras, substituir `_carregar_feriados_do_ano`, remover `_FERIADOS_API_KEY` |
| `tests/test_main.py` | Modificar | Remover `test_feriados_api_key_constante_definida`, adicionar testes das novas funções |

---

## Task 1: `_calcular_pascoa` e `_feriados_nacionais_fallback`

**Files:**
- Modify: `tests/test_main.py`
- Modify: `main.py` (inserir antes da linha `# Cache de feriados`, ~linha 794)

- [ ] **Step 1: Adicionar testes em `tests/test_main.py`**

Adicionar após `test_smoke`:

```python
def test_calcular_pascoa_datas_conhecidas():
    """Algoritmo de Butcher deve bater com datas históricas conhecidas."""
    import datetime
    import main as m
    assert m._calcular_pascoa(2024) == datetime.date(2024, 3, 31)
    assert m._calcular_pascoa(2025) == datetime.date(2025, 4, 20)
    assert m._calcular_pascoa(2023) == datetime.date(2023, 4, 9)
    assert m._calcular_pascoa(2022) == datetime.date(2022, 4, 17)


def test_feriados_nacionais_fallback_contem_datas_fixas():
    """Fallback deve incluir todos os feriados nacionais fixos."""
    import main as m
    datas = m._feriados_nacionais_fallback(2025)
    assert "2025-01-01" in datas   # Confraternização
    assert "2025-04-21" in datas   # Tiradentes
    assert "2025-05-01" in datas   # Dia do Trabalho
    assert "2025-09-07" in datas   # Independência
    assert "2025-10-12" in datas   # Nossa Senhora Aparecida
    assert "2025-11-02" in datas   # Finados
    assert "2025-11-15" in datas   # Proclamação da República
    assert "2025-11-20" in datas   # Consciência Negra
    assert "2025-12-25" in datas   # Natal


def test_feriados_nacionais_fallback_contem_datas_variaveis():
    """Fallback deve incluir Carnaval e Corpus Christi derivados da Páscoa."""
    import datetime
    import main as m
    # Páscoa 2025 = 20/04; Carnaval seg = -48 = 03/03; ter = -47 = 04/03
    # Sexta Santa = -2 = 18/04; Corpus Christi = +60 = 19/06
    datas = m._feriados_nacionais_fallback(2025)
    assert "2025-03-03" in datas   # Carnaval segunda
    assert "2025-03-04" in datas   # Carnaval terça
    assert "2025-04-18" in datas   # Sexta-feira Santa
    assert "2025-06-19" in datas   # Corpus Christi
```

- [ ] **Step 2: Rodar testes — devem FALHAR**

```
python -m pytest tests/test_main.py::test_calcular_pascoa_datas_conhecidas tests/test_main.py::test_feriados_nacionais_fallback_contem_datas_fixas tests/test_main.py::test_feriados_nacionais_fallback_contem_datas_variaveis -v
```

Saída esperada: `FAILED` (funções não existem ainda)

- [ ] **Step 3: Implementar funções em `main.py`**

Inserir logo antes do comentário `# Cache de feriados` (~linha 794):

```python
# ──────────────────────────────────────────────────────────────
# Cálculo local de feriados (fallback sem rede)
# ──────────────────────────────────────────────────────────────

def _calcular_pascoa(ano):
    a = ano % 19
    b, c = divmod(ano, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes, dia = divmod(114 + h + l - 7 * m, 31)
    return datetime.date(ano, mes, dia + 1)


def _feriados_nacionais_fallback(ano):
    pascoa = _calcular_pascoa(ano)
    datas = set()
    for mes, dia in [(1,1),(4,21),(5,1),(9,7),(10,12),(11,2),(11,15),(11,20),(12,25)]:
        datas.add(datetime.date(ano, mes, dia).strftime("%Y-%m-%d"))
    for delta in [-48, -47, -2, 60]:
        datas.add((pascoa + datetime.timedelta(days=delta)).strftime("%Y-%m-%d"))
    return datas

```

- [ ] **Step 4: Rodar testes — devem PASSAR**

```
python -m pytest tests/test_main.py::test_calcular_pascoa_datas_conhecidas tests/test_main.py::test_feriados_nacionais_fallback_contem_datas_fixas tests/test_main.py::test_feriados_nacionais_fallback_contem_datas_variaveis -v
```

Saída esperada: `3 passed`

- [ ] **Step 5: Commit**

```
git add main.py tests/test_main.py
git commit -m "feat: adicionar _calcular_pascoa e _feriados_nacionais_fallback"
```

---

## Task 2: Dicts de feriados estaduais e municipais das capitais

**Files:**
- Modify: `tests/test_main.py`
- Modify: `main.py` (inserir antes de `_calcular_pascoa`)

- [ ] **Step 1: Adicionar testes em `tests/test_main.py`**

Adicionar após os testes da Task 1:

```python
def test_feriados_estaduais_cobre_todas_ufs():
    """FERIADOS_ESTADUAIS deve ter entrada para todas as 27 UFs."""
    import main as m
    ufs_esperadas = {
        "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA",
        "MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN",
        "RO","RR","RS","SC","SE","SP","TO"
    }
    assert ufs_esperadas == set(m.FERIADOS_ESTADUAIS.keys())


def test_ibge_capitais_cobre_todas_ufs():
    """IBGE_CAPITAIS deve ter entrada para todas as 27 UFs."""
    import main as m
    ufs_esperadas = {
        "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA",
        "MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN",
        "RO","RR","RS","SC","SE","SP","TO"
    }
    assert ufs_esperadas == set(m.IBGE_CAPITAIS.keys())


def test_feriados_municipais_capitais_cobre_todas_ufs():
    """FERIADOS_MUNICIPAIS_CAPITAIS deve ter entrada para todas as 27 UFs."""
    import main as m
    ufs_esperadas = {
        "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA",
        "MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN",
        "RO","RR","RS","SC","SE","SP","TO"
    }
    assert ufs_esperadas == set(m.FERIADOS_MUNICIPAIS_CAPITAIS.keys())


def test_feriados_bh_inclui_padroeira():
    """BH deve ter Nossa Senhora da Boa Viagem (15/08) e aniversário (12/12)."""
    import main as m
    municipais_mg = m.FERIADOS_MUNICIPAIS_CAPITAIS["MG"]
    datas = [(mes, dia) for mes, dia, _ in municipais_mg]
    assert (8, 15) in datas, "Falta Nossa Senhora da Boa Viagem (15/08)"
    assert (12, 12) in datas, "Falta Aniversário de BH (12/12)"
```

- [ ] **Step 2: Rodar testes — devem FALHAR**

```
python -m pytest tests/test_main.py::test_feriados_estaduais_cobre_todas_ufs tests/test_main.py::test_ibge_capitais_cobre_todas_ufs tests/test_main.py::test_feriados_municipais_capitais_cobre_todas_ufs tests/test_main.py::test_feriados_bh_inclui_padroeira -v
```

Saída esperada: `FAILED` (dicts não existem ainda)

- [ ] **Step 3: Adicionar dicts em `main.py`**

Inserir logo antes de `_calcular_pascoa` (que foi inserida na Task 1):

```python
# ──────────────────────────────────────────────────────────────
# Feriados estaduais e municipais (hardcoded, sem API)
# ──────────────────────────────────────────────────────────────

FERIADOS_ESTADUAIS = {
    "AC": [(6,  15, "Aniversário do Acre"), (9, 5, "Dia do Acre")],
    "AL": [(9,  16, "Emancipação Política de Alagoas")],
    "AM": [(9,   5, "Elevação do Amazonas à categoria de Província")],
    "AP": [(9,  13, "Criação do Território do Amapá")],
    "BA": [(7,   2, "Independência da Bahia")],
    "CE": [(3,  25, "Data Magna do Ceará")],
    "DF": [(4,  21, "Fundação de Brasília")],
    "ES": [(10, 28, "Dia do Servidor Público do ES")],
    "GO": [(7,  26, "Fundação de Goiânia")],
    "MA": [(7,  28, "Adesão do Maranhão à Independência")],
    "MG": [(4,  21, "Tiradentes")],
    "MS": [(10, 11, "Criação do Estado de MS")],
    "MT": [(4,   8, "Criação da Capitania de MT")],
    "PA": [(8,  15, "Adesão do Pará à Independência")],
    "PB": [(8,   5, "Fundação do Estado da Paraíba")],
    "PE": [(3,   6, "Revolução Pernambucana de 1817")],
    "PI": [(10, 19, "Dia do Piauí")],
    "PR": [(12, 19, "Emancipação Política do Paraná")],
    "RJ": [(4,  23, "Dia de São Jorge")],
    "RN": [(10,  3, "Mártires de Cunhaú e Uruaçu")],
    "RO": [(1,   4, "Criação do Estado de RO")],
    "RR": [(10,  5, "Criação do Estado de RR")],
    "RS": [(9,  20, "Revolução Farroupilha")],
    "SC": [(8,  11, "Criação da Capitania de SC")],
    "SE": [(7,   8, "Emancipação Política de Sergipe")],
    "SP": [(7,   9, "Revolução Constitucionalista de 1932")],
    "TO": [(10,  5, "Criação do Estado do Tocantins")],
}

IBGE_CAPITAIS = {
    "AC": "1200401",
    "AL": "2704302",
    "AM": "1302603",
    "AP": "1600303",
    "BA": "2927408",
    "CE": "2304400",
    "DF": "5300108",
    "ES": "3205309",
    "GO": "5208707",
    "MA": "2111300",
    "MG": "3106200",
    "MS": "5002704",
    "MT": "5103403",
    "PA": "1501402",
    "PB": "2507507",
    "PE": "2611606",
    "PI": "2211001",
    "PR": "4106902",
    "RJ": "3304557",
    "RN": "2408102",
    "RO": "1100205",
    "RR": "1400100",
    "RS": "4314902",
    "SC": "4205407",
    "SE": "2800308",
    "SP": "3550308",
    "TO": "1721000",
}

FERIADOS_MUNICIPAIS_CAPITAIS = {
    "AC": [(6,   2, "Aniversário de Rio Branco")],
    "AL": [(12,  5, "Aniversário de Maceió")],
    "AM": [(10, 24, "Aniversário de Manaus")],
    "AP": [(2,   4, "Aniversário de Macapá")],
    "BA": [(3,  29, "Aniversário de Salvador")],
    "CE": [(4,  13, "Aniversário de Fortaleza")],
    "DF": [],
    "ES": [(9,   8, "Aniversário de Vitória")],
    "GO": [(10, 24, "Aniversário de Goiânia")],
    "MA": [(9,   8, "Aniversário de São Luís")],
    "MG": [(8,  15, "Nossa Senhora da Boa Viagem"), (12, 12, "Aniversário de BH")],
    "MS": [(8,  26, "Aniversário de Campo Grande")],
    "MT": [(4,   8, "Aniversário de Cuiabá")],
    "PA": [(1,  12, "Aniversário de Belém")],
    "PB": [(8,   5, "Aniversário de João Pessoa")],
    "PE": [(3,  12, "Aniversário de Recife")],
    "PI": [(8,  16, "Aniversário de Teresina")],
    "PR": [(3,  29, "Aniversário de Curitiba")],
    "RJ": [(1,  20, "Dia de São Sebastião"), (3, 1, "Aniversário do Rio de Janeiro")],
    "RN": [(12, 25, "Aniversário de Natal")],
    "RO": [(10,  2, "Aniversário de Porto Velho")],
    "RR": [(7,   9, "Aniversário de Boa Vista")],
    "RS": [(7,  26, "Aniversário de Porto Alegre")],
    "SC": [(3,  23, "Aniversário de Florianópolis")],
    "SE": [(3,  17, "Aniversário de Aracaju")],
    "SP": [(1,  25, "Aniversário de São Paulo")],
    "TO": [(5,  20, "Aniversário de Palmas")],
}

```

- [ ] **Step 4: Rodar testes — devem PASSAR**

```
python -m pytest tests/test_main.py::test_feriados_estaduais_cobre_todas_ufs tests/test_main.py::test_ibge_capitais_cobre_todas_ufs tests/test_main.py::test_feriados_municipais_capitais_cobre_todas_ufs tests/test_main.py::test_feriados_bh_inclui_padroeira -v
```

Saída esperada: `4 passed`

- [ ] **Step 5: Commit**

```
git add main.py tests/test_main.py
git commit -m "feat: adicionar dicts FERIADOS_ESTADUAIS, IBGE_CAPITAIS e FERIADOS_MUNICIPAIS_CAPITAIS"
```

---

## Task 3: Substituir `_carregar_feriados_do_ano`

**Files:**
- Modify: `tests/test_main.py`
- Modify: `main.py` (~linha 802, função `_carregar_feriados_do_ano`)

- [ ] **Step 1: Adicionar testes em `tests/test_main.py`**

Adicionar após os testes da Task 2:

```python
def test_carregar_feriados_brasilapi_sucesso():
    """Com BrasilAPI disponível, deve incluir nacionais + estaduais de SP."""
    import main as m

    resposta_api = [
        {"date": "2025-01-01", "name": "Confraternização Universal", "type": "national"},
        {"date": "2025-04-18", "name": "Sexta-feira Santa", "type": "national"},
    ]
    mock_resp = mock.MagicMock()
    mock_resp.json.return_value = resposta_api
    mock_resp.raise_for_status.return_value = None

    with mock.patch('main.requests.get', return_value=mock_resp):
        with mock.patch('main.detectar_localizacao', return_value=("SP", "3550308")):
            with mock.patch.object(m, '_feriados_cache', {}):
                datas = m._carregar_feriados_do_ano(2025)

    assert "2025-01-01" in datas          # nacional via API
    assert "2025-04-18" in datas          # nacional via API
    assert "2025-07-09" in datas          # estadual SP (Revolução Constitucionalista)
    assert "2025-01-25" in datas          # municipal SP capital (Aniversário de SP)


def test_carregar_feriados_brasilapi_falha_usa_fallback():
    """Com BrasilAPI indisponível, deve usar fallback local com feriados nacionais."""
    import main as m

    with mock.patch('main.requests.get', side_effect=Exception("timeout")):
        with mock.patch('main.detectar_localizacao', return_value=("SP", "3550308")):
            with mock.patch.object(m, '_feriados_cache', {}):
                datas = m._carregar_feriados_do_ano(2025)

    assert "2025-01-01" in datas          # fallback: Confraternização
    assert "2025-12-25" in datas          # fallback: Natal
    assert "2025-07-09" in datas          # estadual SP (mesmo sem API)


def test_carregar_feriados_interior_nao_recebe_municipais_capital():
    """Usuário fora da capital não deve receber feriados municipais da capital."""
    import main as m

    mock_resp = mock.MagicMock()
    mock_resp.json.return_value = []
    mock_resp.raise_for_status.return_value = None

    # IBGE de Campinas (não é SP capital)
    with mock.patch('main.requests.get', return_value=mock_resp):
        with mock.patch('main.detectar_localizacao', return_value=("SP", "3509502")):
            with mock.patch.object(m, '_feriados_cache', {}):
                datas = m._carregar_feriados_do_ano(2025)

    assert "2025-01-25" not in datas      # aniversário de SP não se aplica
    assert "2025-07-09" in datas          # estadual SP continua valendo
```

- [ ] **Step 2: Rodar testes — devem FALHAR**

```
python -m pytest tests/test_main.py::test_carregar_feriados_brasilapi_sucesso tests/test_main.py::test_carregar_feriados_brasilapi_falha_usa_fallback tests/test_main.py::test_carregar_feriados_interior_nao_recebe_municipais_capital -v
```

Saída esperada: `FAILED` (função ainda usa feriadosapi.com)

- [ ] **Step 3: Substituir `_carregar_feriados_do_ano` em `main.py`**

Localizar e substituir a função completa (~linha 802):

```python
def _carregar_feriados_do_ano(ano):
    """Carrega e cacheia feriados: nacionais (BrasilAPI) + estaduais + municipais da capital."""
    with _feriados_cache_lock:
        if ano in _feriados_cache:
            return _feriados_cache[ano]

        uf, ibge = detectar_localizacao()
        datas = set()

        try:
            r = requests.get(
                f"https://brasilapi.com.br/api/feriados/v1/{ano}",
                timeout=10
            )
            r.raise_for_status()
            for f in r.json():
                data = f.get("date", "")
                if data:
                    datas.add(data)
        except Exception as e:
            registrar_log(f"BrasilAPI indisponível ({e}). Usando fallback local.")
            datas |= _feriados_nacionais_fallback(ano)

        for mes, dia, _ in FERIADOS_ESTADUAIS.get(uf, []):
            datas.add(f"{ano}-{mes:02d}-{dia:02d}")

        if ibge == IBGE_CAPITAIS.get(uf):
            for mes, dia, _ in FERIADOS_MUNICIPAIS_CAPITAIS.get(uf, []):
                datas.add(f"{ano}-{mes:02d}-{dia:02d}")

        _feriados_cache[ano] = datas
        registrar_log(f"Feriados {ano} carregados: {len(datas)} datas (UF={uf}, IBGE={ibge})")
        return datas
```

- [ ] **Step 4: Rodar testes — devem PASSAR**

```
python -m pytest tests/test_main.py::test_carregar_feriados_brasilapi_sucesso tests/test_main.py::test_carregar_feriados_brasilapi_falha_usa_fallback tests/test_main.py::test_carregar_feriados_interior_nao_recebe_municipais_capital -v
```

Saída esperada: `3 passed`

- [ ] **Step 5: Commit**

```
git add main.py tests/test_main.py
git commit -m "feat: substituir feriadosapi.com por BrasilAPI com fallback local e feriados estaduais/municipais"
```

---

## Task 4: Cleanup — remover `_FERIADOS_API_KEY`

**Files:**
- Modify: `main.py` (remover linha 28)
- Modify: `tests/test_main.py` (remover `test_feriados_api_key_constante_definida`)

- [ ] **Step 1: Remover `_FERIADOS_API_KEY` de `main.py`**

Localizar e remover o bloco (linhas 25–28):

```python
# ──────────────────────────────────────────────────────────────
# Chave da API de feriados (embutida no build — não exposta ao usuário)
# ──────────────────────────────────────────────────────────────
_FERIADOS_API_KEY = ""
```

- [ ] **Step 2: Remover `test_feriados_api_key_constante_definida` de `tests/test_main.py`**

Localizar e remover a função completa (linhas 19–37):

```python
def test_feriados_api_key_constante_definida():
    ...
```

- [ ] **Step 3: Rodar todos os testes**

```
python -m pytest tests/ -v
```

Saída esperada: todos `PASSED` (o teste removido não aparece mais; os demais continuam verdes)

- [ ] **Step 4: Commit final**

```
git add main.py tests/test_main.py
git commit -m "chore: remover _FERIADOS_API_KEY — substituída por BrasilAPI sem autenticação"
```
