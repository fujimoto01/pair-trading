# Pair Trading Brasil - Pipeline Quantitativo Completo

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Pandas](https://img.shields.io/badge/Pandas-2.0+-green.svg)
![Status](https://img.shields.io/badge/Status-Em_Desenvolvimento-yellow.svg)

## 📊 Visão Geral

Pipeline quantitativo para seleção, análise e simulação de estratégias de **pair trading** no mercado brasileiro (B3), utilizando dados históricos COTAHIST e múltiplos filtros estatísticos. O projeto é modular, com cada fase documentada e scripts separados para facilitar manutenção e evolução.

---

## 🗂️ Fases do Projeto

### **Fase 1: Universo de Ativos e Coleta de Dados**
- **Objetivo:** Definir o universo de ações negociadas e selecionar as 100 mais líquidas dos 2 anos anteriores.
- **Scripts:** `data_collection.py`, `test.py`
- **Principais etapas:**
  1. Coleta de todos os ativos do B3 via arquivos COTAHIST.
  2. Filtro para manter apenas ações (exclui ETFs, BDRs, units, etc).
  3. Seleção de ações negociadas em pelo menos 98% dos dias úteis (~504 dias).
  4. Cálculo de métricas de liquidez:
     - Volume médio diário
     - Número médio de negócios por dia
     - Frequência de negociação
     - Consistência (dias negociados/504)
  5. Filtros mínimos:
     - Volume > R$ 500k/dia
     - Frequência > 80%
     - Mínimo 100 dias negociados
  6. Score composto: `Score = 0.4*Volume + 0.3*Negócios + 0.2*Frequência + 0.1*Consistência`
  7. Seleção das 100 ações mais líquidas.
- **Saídas:**
  - `top_100_acoes_liquidas_2014_2015_completo.csv`
  - `top_100_acoes_liquidas_2014_2015_tickers.txt`

---

### **Fase 2: Análise Estatística e Seleção de Pares**
- **Objetivo:** Encontrar pares de ações cointegrados e com características favoráveis para reversão à média.
- **Scripts:** `cointegration_test.py`, `hurst_filter.py`, `cross_mean.py`
- **Principais etapas:**
  1. **Busca por Cointegração:**
     - Testa todas as combinações de pares possíveis entre as 100 ações.
     - Aplica o teste de cointegração de Engle-Granger.
     - Seleciona pares com p-valor < 0.05.
  2. **Filtro de Reversão à Média:**
     - Calcula o expoente de Hurst do spread de cada par cointegrado.
     - Mantém apenas pares com Hurst < 0.5 (característica de reversão).
  3. **Filtro de Frequência de Cruzamento da Média:**
     - Conta quantas vezes o spread cruzou sua própria média histórica.
     - Mantém apenas pares com pelo menos 24 cruzamentos em 2 anos (12/ano).
- **Saídas:**
  - `pares_filtrados_hurst_2014_2015.csv` (após filtro de Hurst)
  - `pares_finais_selecionados_2014_2015.csv` (após todos os filtros)

---

### **Fase 3: Modelagem da Estratégia e Geração de Sinais**
- **Objetivo:** Definir regras de entrada/saída e gerar sinais de trading para o melhor par selecionado.
- **Principais etapas:**
  1. Selecionar o par com menor p-valor de cointegração.
  2. Calcular e normalizar o spread (Z-Score).
  3. Definir sinais de entrada (Z > +2 ou Z < -2) e saída (Z cruza 0).
- **Status:** _A implementar_

---

### **Fase 4: Backtesting da Estratégia**
- **Objetivo:** Simular operações no período fora da amostra e calcular retornos.
- **Principais etapas:**
  1. Dividir dados em in-sample/out-of-sample.
  2. Simular operações com base nos sinais.
  3. Calcular retorno diário e curva de capital.
- **Status:** _A implementar_

---

### **Fase 5: Avaliação de Performance e Visualização**
- **Objetivo:** Avaliar risco/retorno e visualizar resultados.
- **Principais etapas:**
  1. Calcular métricas: Retorno total, anualizado, volatilidade, Sharpe, drawdown.
  2. Gerar gráficos do spread, sinais e curva de capital.
  3. Analisar resultados e discutir próximos passos (ex: múltiplos pares, machine learning).
- **Status:** _A implementar_

---

## 🧩 Scripts e Funções Principais

### `data_collection.py` / `test.py`
- `parse_cotahist_line()` — Parser linha a linha do COTAHIST
- `is_valid_stock()` — Filtro de ações válidas
- `calculate_liquidity_metrics()` — Métricas de liquidez
- `calculate_liquidity_score()` — Score composto
- `analyze_cotahist_liquidity()` — Função principal de análise

### `cointegration_test.py`
- `testar_cointegracao()` — Testa Engle-Granger para todos os pares
- `salvar_pares_cointegrados()` — Salva pares cointegrados

### `hurst_filter.py`
- `calcular_hurst()` — Calcula expoente de Hurst do spread
- `filtrar_pares_hurst()` — Filtra pares com Hurst < 0.5

### `cross_mean.py`
- `contar_cruzamentos_media()` — Conta cruzamentos do spread com a média
- `aplicar_filtro_frequencia()` — Filtra pares com cruzamentos suficientes

---

## 📁 Estrutura de Diretórios

```
pair-trading/
├── data_collection.py
├── test.py
├── cointegration_test.py
├── hurst_filter.py
├── cross_mean.py
├── COTAHIST_A2014.TXT
├── COTAHIST_A2015.TXT
├── ...
```

---

## 🚀 Como Usar

1. **Coleta e filtro de liquidez:**
   ```bash
   python data_collection.py
   # ou
   python test.py
   ```
2. **Teste de cointegração:**
   ```bash
   python cointegration_test.py
   ```
3. **Filtro de Hurst:**
   ```bash
   python hurst_filter.py
   ```
4. **Filtro de cruzamento de média:**
   ```bash
   python cross_mean.py
   ```

---

## 📈 Metodologia Resumida

- **Liquidez:** Score multifatorial, top 100 ações negociadas em 98% dos dias.
- **Cointegração:** Engle-Granger, p < 0.05.
- **Reversão:** Hurst < 0.5.
- **Frequência:** Mínimo 24 cruzamentos do spread com a média em 2 anos.
- **Sinais:** Z-Score do spread, thresholds ±2 para entrada, 0 para saída.

---

## 📜 Licença
Projeto proprietário - Itaú Unibanco

---
**Versão:** 1.1  
**Última Atualização:** Setembro 2025  
**Compatibilidade:** Python 3.8+, Pandas 2.0+