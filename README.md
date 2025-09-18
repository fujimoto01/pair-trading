# Análise de Liquidez para Pair Trading - Mercado Brasileiro

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Pandas](https://img.shields.io/badge/Pandas-2.0+-green.svg)
![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)

## 📊 Visão Geral

Sistema de análise de liquidez para identificação das ações mais líquidas da **B3 (Brasil, Bolsa, Balcão)** com foco em estratégias de **pair trading**. O projeto processa dados históricos do formato COTAHIST e gera rankings de liquidez baseados em múltiplas métricas quantitativas.

### 🏦 Contexto Institucional
- **Organização:** Itaú
- **Mercado:** Bolsa de Valores Brasileira (B3)
- **Domínio:** Análise Quantitativa e Trading Algorítmico
- **Objetivo:** Identificar pares de ações para estratégias de arbitragem

## 🎯 Funcionalidades Principais

### ✅ Análise de Liquidez Multifatorial
- **Volume médio diário** - Capacidade de absorção de grandes ordens
- **Frequência de negociação** - Consistência de presença no mercado
- **Número de negócios** - Atividade e interesse do mercado
- **Score de consistência** - Regularidade ao longo do período

### ✅ Filtros de Qualidade
- ✅ Apenas ações ordinárias e preferenciais (BDI 02)
- ✅ Mercado à vista (tipo 010)
- ✅ Exclusão de ETFs, Units e BDRs
- ✅ Validação de padrões de ticker brasileiros
- ✅ Filtros mínimos de volume e frequência

### ✅ Processamento de Dados Robusto
- ✅ Suporte a múltiplos anos de dados COTAHIST
- ✅ Parsing de formato fixed-width do B3
- ✅ Tratamento de erros e validação de dados
- ✅ Logs informativos de progresso

### ✅ Saídas Estruturadas
- ✅ **CSV completo** com todas as métricas calculadas
- ✅ **Lista de tickers** para integração com outros sistemas
- ✅ **Ranking Top 100** das ações mais líquidas
- ✅ Formato compatível com ferramentas de análise brasileiras

## 🏗️ Arquitetura

```
pair-trading/
├── .claude/                    # Contexto do projeto e memória de sessão
├── test.py                     # Script principal de análise
├── COTAHIST_A2014.TXT         # Dados B3 - ano 2014
├── COTAHIST_A2015.TXT         # Dados B3 - ano 2015
├── COTAHIST_A2016.TXT         # Dados B3 - ano 2016
└── README.md                  # Este arquivo
```

### 🔄 Fluxo de Dados
```
COTAHIST (Raw) → Parse & Filter → Liquidity Analysis → Ranking → CSV Output
```

## 🚀 Instalação e Uso

### Pré-requisitos
```bash
Python 3.8+
pandas
numpy
```

### Instalação
```bash
pip install pandas numpy
```

### Estrutura de Dados Esperada
Coloque os arquivos COTAHIST no mesmo diretório do script:
```
COTAHIST_A2014.TXT  # Dados históricos B3 - 2014
COTAHIST_A2015.TXT  # Dados históricos B3 - 2015
```

### Execução
```bash
python test.py
```

### Saídas Geradas
```
top_100_acoes_liquidas_2014_2015_completo.csv  # Dataset completo
top_100_acoes_liquidas_2014_2015_tickers.txt   # Lista de tickers
```

## 📈 Metodologia de Análise

### Score de Liquidez
O ranking é baseado em um **score composto** com os seguintes pesos:

| Métrica | Peso | Descrição |
|---------|------|-----------|
| **Volume Médio Diário** | 40% | Capacidade de absorção de ordens grandes |
| **Negócios Médios Diários** | 30% | Atividade e interesse do mercado |
| **Frequência de Negociação** | 20% | Consistência de presença |
| **Score de Consistência** | 10% | Regularidade ao longo do período |

### Filtros de Qualidade

#### Filtros de Validação de Ações
- **BDI 02:** Apenas ações ordinárias e preferenciais
- **Tipo de Mercado 010:** Mercado à vista (spot market)
- **Padrão de Ticker:** Regex `^[A-Z]{4}[34568]$|^[A-Z]{5}[34568]$`
- **Exclusões:** ETFs (terminam em 11), BDRs conhecidos

#### Filtros de Liquidez Mínima
- **Volume Médio:** R$ 500.000/dia mínimo
- **Frequência:** 80% dos dias úteis mínimo
- **Dias Negociados:** 100 dias mínimo no período

### Período de Análise
- **Anos:** 2014-2015 (período de formação)
- **Dias Úteis:** ~504 dias (252 por ano)
- **Dados:** Preços de fechamento, volumes, número de negócios

## 📊 Exemplo de Resultados

### Top 5 Ações Mais Líquidas (2014-2015)
| Ranking | Ticker | Nome | Volume Médio/Dia | Frequência |
|---------|--------|------|------------------|------------|
| 1 | PETR4 | PETROBRAS | R$ 651M | 98% |
| 2 | ITUB4 | ITAUUNIBANCO | R$ 446M | 98% |
| 3 | VALE5 | VALE | R$ 363M | 98% |
| 4 | BBDC4 | BRADESCO | R$ 283M | 98% |
| 5 | PETR3 | PETROBRAS | R$ 226M | 98% |

## 🔧 Configuração Avançada

### Customização de Períodos
Para analisar diferentes períodos, modifique a variável `file_paths` em `main()`:
```python
# Exemplo: Análise apenas 2015
file_paths = ['COTAHIST_A2015.TXT']
periodo_str = "2015"

# Exemplo: Análise 2014-2016
file_paths = ['COTAHIST_A2014.TXT', 'COTAHIST_A2015.TXT', 'COTAHIST_A2016.TXT']
periodo_str = "2014_2016"
```

### Ajuste de Filtros
Modifique os filtros mínimos na função `analyze_cotahist_liquidity()`:
```python
if (metrics['volume_medio_diario'] < 500000 or    # Volume mínimo
    metrics['frequencia_negociacao'] < 0.8 or     # Frequência mínima
    metrics['dias_negociados'] < 100):            # Dias mínimos
```

### Personalização de Pesos
Ajuste os pesos do score na função `calculate_liquidity_score()`:
```python
peso_volume = 0.4        # 40% - Volume
peso_negocios = 0.3      # 30% - Atividade
peso_frequencia = 0.2    # 20% - Frequência  
peso_consistencia = 0.1  # 10% - Consistência
```

## 📁 Formato dos Dados

### Arquivo COTAHIST (Input)
- **Formato:** Fixed-width text file
- **Encoding:** Latin-1 (ISO-8859-1)
- **Tamanho:** ~50MB por ano
- **Estrutura:** Baseada na especificação oficial B3

### CSV de Saída (Output)
- **Separador:** Ponto e vírgula (`;`)
- **Decimal:** Vírgula (`,`)
- **Encoding:** UTF-8 com BOM
- **Headers:** Em português para compatibilidade local

## ⚠️ Considerações Importantes

### Performance
- **Memória:** Arquivos COTAHIST são grandes (>50MB)
- **Processamento:** Pode levar alguns minutos dependendo do hardware
- **Logs:** Progresso exibido a cada 100.000 linhas processadas

### Qualidade dos Dados
- **Normalização:** Preços divididos por 100 conforme padrão B3
- **Validação:** Múltiplas camadas de filtros para garantir qualidade
- **Consistência:** Dados validados contra padrões conhecidos do mercado

### Limitações
- **Dados Históricos:** Análise baseada apenas em dados passados
- **Liquidez Intraday:** Não considera padrões intraday de liquidez
- **Custos de Transação:** Não inclui spreads ou custos operacionais
- **Eventos Corporativos:** Não ajusta para splits, bonificações, etc.

## 🛠️ Desenvolvimento

### Padrões de Código
- **Idioma:** Documentação em português (contexto brasileiro)
- **Estilo:** PEP 8 com adaptações para domínio financeiro
- **Funções:** Documentadas com docstrings detalhadas
- **Naming:** Snake_case descritivo

### Estrutura de Funções
```python
parse_cotahist_line()        # Parser de linha fixed-width
is_valid_stock()             # Validação de ações
calculate_liquidity_metrics() # Cálculo de métricas
calculate_liquidity_score()   # Score composto
analyze_cotahist_liquidity()  # Função principal
main()                       # Ponto de entrada
```

## 📞 Suporte e Contato

Para questões técnicas ou sugestões de melhoria:
- **Contexto:** Projeto interno Itaú
- **Domínio:** Análise quantitativa de mercado brasileiro
- **Stack:** Python/Pandas para processamento de dados financeiros

## 📜 Licença

Projeto proprietário - Itaú Unibanco

---

**Versão:** 1.0  
**Última Atualização:** Setembro 2025  
**Compatibilidade:** Python 3.8+, Pandas 2.0+