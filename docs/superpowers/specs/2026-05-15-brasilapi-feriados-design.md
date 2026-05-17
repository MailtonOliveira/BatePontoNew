# Feriados via BrasilAPI — Nacionais + Estaduais + Municipais (Capitais)

**Data:** 2026-05-15
**Status:** Aprovado

## Contexto

O app usava `feriadosapi.com` com uma chave de API embutida no build. A chave foi removida do repositório por questões de segurança. O objetivo agora é substituir por uma solução sem chave que cubra feriados nacionais, estaduais e municipais das capitais — para workers em qualquer estado do Brasil.

## Escopo

- Substituir a chamada a `feriadosapi.com` por `brasilapi.com.br`
- Adicionar feriados estaduais fixos via dict hardcoded por UF (27 UFs + DF)
- Adicionar feriados municipais das capitais, aplicados apenas quando o IBGE detectado for o da capital
- Implementar fallback local (algoritmo de Páscoa) para quando BrasilAPI estiver indisponível
- Remover `_FERIADOS_API_KEY` e o header de autenticação

## Fora do escopo

- Feriados de municípios que não sejam capitais
- Pontos facultativos
- Alterações no wizard ou na detecção de localização (já funcionam)

---

## Arquitetura

### Fluxo de `_carregar_feriados_do_ano(ano)`

```
1. detectar_localizacao() → (uf, ibge)
2. GET brasilapi.com.br/api/feriados/v1/{ano}
     sucesso → set de datas nacionais
     falha   → _feriados_nacionais_fallback(ano)
3. FERIADOS_ESTADUAIS[uf] → adicionar fixos do estado
4. se ibge == IBGE_CAPITAIS[uf]:
       FERIADOS_MUNICIPAIS_CAPITAIS[uf] → adicionar municipais da capital
5. cache por ano → retornar set de strings "YYYY-MM-DD"
```

### Novas funções puras

**`_calcular_pascoa(ano) -> datetime.date`**
Algoritmo de Butcher (calendário gregoriano). Entrada: ano inteiro. Saída: data da Páscoa.

**`_feriados_nacionais_fallback(ano) -> set[str]`**
Calcula feriados nacionais sem rede. Datas fixas + variáveis derivadas da Páscoa.
Datas fixas: 01/01, 21/04, 01/05, 07/09, 12/10, 02/11, 15/11, 20/11, 25/12.
Variáveis (delta da Páscoa): −48 (Carnaval seg), −47 (Carnaval ter), −2 (Sexta Santa), +60 (Corpus Christi).

### Novos dicts module-level

**`FERIADOS_ESTADUAIS`** — `{UF: [(mes, dia, nome), ...]}`
Datas fixas por estado. Aplicadas a todos os usuários daquele estado.

**`IBGE_CAPITAIS`** — `{UF: ibge_str}`
Código IBGE de cada capital, para verificar se o usuário está na capital.

**`FERIADOS_MUNICIPAIS_CAPITAIS`** — `{UF: [(mes, dia, nome), ...]}`
Feriados municipais das capitais. Aplicados apenas quando `ibge == IBGE_CAPITAIS[uf]`.

---

## Dados

### FERIADOS_ESTADUAIS

| UF | Feriados |
|----|----------|
| AC | 15/06 Aniversário do Acre, 05/09 Dia do Acre |
| AL | 16/09 Emancipação Política de Alagoas |
| AM | 05/09 Elevação do Amazonas à categoria de Província |
| AP | 13/09 Criação do Território do Amapá |
| BA | 02/07 Independência da Bahia |
| CE | 25/03 Data Magna do Ceará |
| DF | 21/04 Fundação de Brasília |
| ES | 28/10 Dia do Servidor Público do ES |
| GO | 26/07 Fundação de Goiânia |
| MA | 28/07 Adesão do Maranhão à Independência |
| MG | 21/04 Tiradentes |
| MS | 11/10 Criação do Estado de MS |
| MT | 08/04 Criação da Capitania de MT |
| PA | 15/08 Adesão do Pará à Independência |
| PB | 05/08 Fundação do Estado da Paraíba |
| PE | 06/03 Revolução Pernambucana de 1817 |
| PI | 19/10 Dia do Piauí |
| PR | 19/12 Emancipação Política do Paraná |
| RJ | 23/04 Dia de São Jorge |
| RN | 03/10 Mártires de Cunhaú e Uruaçu |
| RO | 04/01 Criação do Estado de RO |
| RR | 05/10 Criação do Estado de RR |
| RS | 20/09 Revolução Farroupilha |
| SC | 11/08 Criação da Capitania de SC |
| SE | 08/07 Emancipação Política de Sergipe |
| SP | 09/07 Revolução Constitucionalista de 1932 |
| TO | 05/10 Criação do Estado do Tocantins |

### FERIADOS_MUNICIPAIS_CAPITAIS

| UF | Capital | Feriados |
|----|---------|----------|
| AC | Rio Branco | 02/06 Aniversário de Rio Branco |
| AL | Maceió | 05/12 Aniversário de Maceió |
| AM | Manaus | 24/10 Aniversário de Manaus |
| AP | Macapá | 04/02 Aniversário de Macapá |
| BA | Salvador | 29/03 Aniversário de Salvador |
| CE | Fortaleza | 13/04 Aniversário de Fortaleza |
| DF | Brasília | — (21/04 já no estadual) |
| ES | Vitória | 08/09 Aniversário de Vitória |
| GO | Goiânia | 24/10 Aniversário de Goiânia |
| MA | São Luís | 08/09 Aniversário de São Luís |
| MG | Belo Horizonte | 15/08 Nossa Senhora da Boa Viagem, 12/12 Aniversário de BH |
| MS | Campo Grande | 26/08 Aniversário de Campo Grande |
| MT | Cuiabá | 08/04 Aniversário de Cuiabá |
| PA | Belém | 12/01 Aniversário de Belém |
| PB | João Pessoa | 05/08 Aniversário de João Pessoa |
| PE | Recife | 12/03 Aniversário de Recife |
| PI | Teresina | 16/08 Aniversário de Teresina |
| PR | Curitiba | 29/03 Aniversário de Curitiba |
| RJ | Rio de Janeiro | 20/01 Dia de São Sebastião, 01/03 Aniversário do Rio |
| RN | Natal | 25/12 Aniversário de Natal (coincide com Natal/Xmas) |
| RO | Porto Velho | 02/10 Aniversário de Porto Velho |
| RR | Boa Vista | 09/07 Aniversário de Boa Vista |
| RS | Porto Alegre | 26/07 Aniversário de Porto Alegre |
| SC | Florianópolis | 23/03 Aniversário de Florianópolis |
| SE | Aracaju | 17/03 Aniversário de Aracaju |
| SP | São Paulo | 25/01 Aniversário de São Paulo |
| TO | Palmas | 20/05 Aniversário de Palmas |

---

## Tratamento de erros

| Situação | Comportamento |
|----------|---------------|
| BrasilAPI indisponível | Usa `_feriados_nacionais_fallback(ano)` — calcula localmente |
| UF não encontrada nos dicts | Aplica só nacionais |
| IBGE não é de capital | Aplica só nacionais + estaduais |
| Qualquer exceção em `_carregar_feriados_do_ano` | Log + retorna `None`; `is_holiday()` assume dia útil |

---

## Arquivos modificados

| Arquivo | Mudança |
|---------|---------|
| `main.py` | Substituir `_carregar_feriados_do_ano`, adicionar `_calcular_pascoa`, `_feriados_nacionais_fallback`, `FERIADOS_ESTADUAIS`, `IBGE_CAPITAIS`, `FERIADOS_MUNICIPAIS_CAPITAIS`; remover `_FERIADOS_API_KEY` |
| `tests/test_main.py` | Adicionar testes para `_calcular_pascoa` e `_carregar_feriados_do_ano` |

---

## Testes

- `test_calcular_pascoa` — valida datas conhecidas (ex: 2024=31/03, 2025=20/04)
- `test_feriados_nacionais_fallback` — verifica que 01/01, Carnaval, Páscoa, etc. estão no set
- `test_carregar_feriados_brasilapi_sucesso` — mock da BrasilAPI retorna lista; verifica que nacionais + estaduais SP são incluídos
- `test_carregar_feriados_brasilapi_falha` — mock da BrasilAPI lança exceção; verifica fallback local
- `test_carregar_feriados_capital` — mock com IBGE de SP capital; verifica que 25/01 está incluído
- `test_carregar_feriados_interior` — mock com IBGE de Campinas; verifica que 25/01 não está incluído
