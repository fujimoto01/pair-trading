# Pair Trading Brasil - Pipeline Quantitativo Completo

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Pandas](https://img.shields.io/badge/Pandas-2.0+-green.svg)
![Status](https://img.shields.io/badge/Status-Produção-green.svg)

## 📊 Visão Geral

Pipeline quantitativo profissional para seleção, análise e simulação de estratégias de **pair trading** no mercado brasileiro (B3), utilizando dados históricos COTAHIST e múltiplos filtros estatísticos. 

### 🆕 Nova Arquitetura Profissional (v2.0)

- **🏗️ Arquitetura Modular:** Código organizado em classes e módulos profissionais
- **⚙️ Configuração Centralizada:** Parâmetros ajustáveis via YAML com validação
- **📱 Interface Interativa:** Jupyter notebook com widgets para controle user-friendly
- **📊 Progress Tracking:** Indicadores de progresso em tempo real
- **💾 Cache Inteligente:** Sistema de cache para otimizar re-execuções
- **🔒 Error Handling:** Tratamento robusto de erros com mensagens user-friendly

---

## 🚀 Início Rápido

### 1. Instalação de Dependências

```bash
pip install -r requirements.txt
```

### 2. Interface Jupyter (Recomendado)

```bash
jupyter notebook pair_trading_analysis.ipynb
```

**✨ A interface Jupyter oferece:**
- Controles interativos para ajuste de parâmetros
- Execução passo-a-passo com feedback visual
- Widgets para configuração sem editar código
- Progress bars em tempo real
- Visualização automática de resultados

### 3. Uso Programático

```python
from src.pipeline.pair_trading_pipeline import PairTradingPipeline

# Inicializar pipeline
pipeline = PairTradingPipeline()

# Executar análise completa
results = pipeline.execute_full_pipeline()

# Obter pares finais
final_pairs = results['final_pairs']
```

---

## 🗂️ Estrutura do Projeto

### **Arquitetura Modular Profissional**

```
pair-trading/
├── 📁 src/                          # Código fonte principal
│   ├── 📁 collection/               # Fase 1: Coleta e análise de liquidez
│   │   └── data_collector.py        # Classe DataCollector
│   ├── 📁 preparation/              # Fase 2: Preparação de dados
│   │   └── data_preparator.py       # Classe DataPreparator
│   ├── 📁 analysis/                 # Fase 3: Análise estatística
│   │   ├── cointegration_analyzer.py # Classe CointegrationAnalyzer
│   │   ├── hurst_analyzer.py        # Classe HurstAnalyzer
│   │   └── cross_mean_analyzer.py   # Classe CrossMeanAnalyzer
│   ├── 📁 strategy/                 # Fase 4: Estratégias (futuro)
│   ├── 📁 backtesting/              # Fase 5: Backtesting (futuro)
│   ├── 📁 utils/                    # Utilitários
│   │   ├── config_manager.py        # Gerenciador de configurações
│   │   ├── progress_tracker.py      # Sistema de progresso
│   │   └── logger.py                # Sistema de logging
│   └── 📁 pipeline/                 # Orquestrador principal
│       └── pair_trading_pipeline.py # Classe PairTradingPipeline
├── 📁 config/                       # Configurações
│   └── config.yaml                  # Parâmetros configuráveis
├── 📁 .claude/                      # Contexto do projeto
│   ├── project-context.json         # Contexto técnico
│   └── session-memory.json         # Memória de decisões
├── 📊 pair_trading_analysis.ipynb   # Interface Jupyter interativa
├── 📋 requirements.txt              # Dependências
├── 🗃️ COTAHIST_A2014.TXT           # Dados históricos B3
├── 🗃️ COTAHIST_A2015.TXT           # Dados históricos B3
└── 📖 README.md                     # Esta documentação
```

### **Componentes Principais**

#### 🏗️ Pipeline Principal (`PairTradingPipeline`)
- Orquestrador que coordena todas as fases
- Sistema de cache inteligente
- Progress tracking automático
- Error handling robusto

#### ⚙️ Configuração (`ConfigManager`)
- Parâmetros centralizados em YAML
- Validação automática de configurações
- Interface para ajuste via notebook

#### 📊 Análise Modular
- **DataCollector:** Análise de liquidez do mercado
- **DataPreparator:** Criação de matrizes de preços
- **CointegrationAnalyzer:** Testes estatísticos de cointegração
- **HurstAnalyzer:** Análise de reversão à média
- **CrossMeanAnalyzer:** Análise de frequência de sinais

---

## 🚀 Como Usar

### **Opção 1: Interface Jupyter (Recomendado)**

1. **Abrir o notebook:**
   ```bash
   jupyter notebook pair_trading_analysis.ipynb
   ```

2. **Seguir o workflow interativo:**
   - ⚙️ Configurar parâmetros com widgets
   - ▶️ Executar fases individualmente ou completa
   - 📊 Visualizar resultados em tempo real
   - 🎯 Ajustar configurações e re-executar

### **Opção 2: Uso Programático**

```python
from src.pipeline.pair_trading_pipeline import PairTradingPipeline

# Inicializar pipeline
pipeline = PairTradingPipeline()

# Executar fases individuais
liquidity_results = pipeline.execute_phase_1_liquidity()
price_matrix = pipeline.execute_phase_2_preparation()
cointegrated_pairs = pipeline.execute_phase_3_cointegration()
final_pairs = pipeline.execute_phase_4_statistical_filters()

# OU executar pipeline completo
all_results = pipeline.execute_full_pipeline()
```

### **Opção 3: Scripts Legados (Compatibilidade)**

```bash
# Ainda funcionam para compatibilidade
python data_collection.py
python data_preparing.py
python cointegration_test.py
```

---

## ⚙️ Configuração de Parâmetros

### **Via Interface Jupyter**
- Widgets interativos para ajuste em tempo real
- Validação automática de parâmetros
- Preview de configurações antes da execução

### **Via Arquivo YAML**
```yaml
# config/config.yaml
liquidity:
  selection:
    top_n_stocks: 100              # Número de ações mais líquidas
    min_daily_volume: 500000       # Volume mínimo diário (R$)
    min_trading_frequency: 0.8     # Frequência mínima (80%)

analysis:
  cointegration:
    significance_level: 0.05       # P-valor máximo
  hurst:
    max_hurst_exponent: 0.5        # Hurst máximo para reversão
  cross_mean:
    min_crossings_2y: 24           # Cruzamentos mínimos em 2 anos
```

### **Via Código**
```python
from src.utils.config_manager import ConfigManager

config = ConfigManager()
config.set('liquidity.selection.top_n_stocks', 150)
config.set('analysis.cointegration.significance_level', 0.01)
config.save()  # Salvar alterações
```

---

## 📈 Metodologia

### **Pipeline de 4 Fases**

#### **📊 Fase 1: Análise de Liquidez**
- **Objetivo:** Selecionar as N ações mais líquidas do mercado
- **Metodologia:** Score multifatorial baseado em:
  - Volume médio diário
  - Número de negócios
  - Frequência de negociação
  - Consistência temporal
- **Filtros:** Volume > R$ 500k/dia, Frequência > 80%
- **Saída:** Top 100 ações mais líquidas

#### **🔧 Fase 2: Preparação de Dados**
- **Objetivo:** Criar matriz estruturada de preços
- **Metodologia:** 
  - Parsing otimizado de arquivos COTAHIST
  - Filtros de qualidade e consistência
  - Tratamento de valores ausentes
- **Saída:** Matriz de preços (datas x tickers)

#### **🔬 Fase 3: Análise de Cointegração**
- **Objetivo:** Identificar pares estatisticamente relacionados
- **Metodologia:** Teste de Engle-Granger para todas as combinações
- **Critério:** P-valor < 0.05 (configurável)
- **Saída:** Pares cointegrados ordenados por significância

#### **🎯 Fase 4: Filtros Estatísticos**
- **Objetivo:** Selecionar pares com características de reversão
- **Filtro 1 - Hurst:** Expoente < 0.5 (reversão à média)
- **Filtro 2 - Frequência:** Mínimo 24 cruzamentos da média em 2 anos
- **Saída:** Pares finais prontos para estratégia

### **Critérios de Qualidade**

- **Mercado:** Apenas ações ordinárias/preferenciais (BDI 02)
- **Tipo:** Mercado à vista (tipo 10)
- **Exclusões:** ETFs, BDRs, Units, FIIs
- **Validação:** Preços positivos, volumes consistentes

---

## 🔍 Resultados Esperados

### **Estatísticas Típicas**
- **Ações analisadas:** ~2.000-3.000 por ano
- **Top 100 líquidas:** Filtradas por volume e frequência
- **Combinações testadas:** ~4.950 pares (100 escolhe 2)
- **Pares cointegrados:** 50-200 (dependendo do p-valor)
- **Pares finais:** 5-50 (após filtros estatísticos)

### **Taxa de Conversão**
- **Típica:** 0.1% - 1.0% dos pares testados
- **Meta:** Encontrar 10-20 pares robustos para estratégia

### **Arquivos Gerados**
```
📁 Resultados/
├── top_100_acoes_liquidas_2014_2015_completo.csv
├── top_100_acoes_liquidas_2014_2015_tickers.txt
├── matriz_precos_2014_2015.csv
├── pares_cointegrados_2014_2015.csv
├── pares_filtrados_hurst_2014_2015.csv
└── pares_finais_selecionados_2014_2015.csv
```

---

## �️ Desenvolvimento e Extensão

### **Próximas Fases (Roadmap)**

#### **Fase 5: Estratégias de Trading**
```python
# Implementação planejada
from src.strategy import SignalGenerator, StrategyExecutor

signal_gen = SignalGenerator()
signals = signal_gen.generate_zscore_signals(best_pair, threshold=2.0)
```

#### **Fase 6: Backtesting Engine**
```python
# Implementação planejada
from src.backtesting import BacktestEngine

engine = BacktestEngine()
results = engine.run_backtest(signals, initial_capital=100000)
```

#### **Fase 7: Performance Analytics**
```python
# Implementação planejada
from src.backtesting import PerformanceAnalyzer

analyzer = PerformanceAnalyzer()
metrics = analyzer.calculate_metrics(results)
```

### **Extensibilidade**

#### **Novos Filtros**
```python
# Exemplo: adicionar novo filtro
class VolatilityAnalyzer:
    def filter_pairs_by_volatility(self, pairs_df, price_matrix):
        # Implementar lógica de filtro
        pass
```

#### **Novas Estratégias**
```python
# Exemplo: estratégia alternativa
class MachineLearningStrategy:
    def generate_ml_signals(self, features, model):
        # Implementar ML para sinais
        pass
```

### **Testes e Validação**
```bash
# Testes unitários (futuro)
pytest tests/

# Validação de dados
python -m src.utils.data_validator
```

---

## 📊 Monitoramento e Performance

### **Progress Tracking**
- Barras de progresso em tempo real
- Estimativas de tempo restante
- Logs detalhados de cada etapa
- Milestone tracking automático

### **Sistema de Cache**
- Cache inteligente de resultados intermediários
- Invalidação automática quando parâmetros mudam
- Otimização para re-execuções

### **Error Handling**
- Mensagens de erro user-friendly
- Validação proativa de dados
- Recovery automático quando possível
- Logging detalhado para debugging

---

## 🔧 Troubleshooting

### **Problemas Comuns**

#### **Arquivos COTAHIST não encontrados**
```
❌ Erro: Arquivo 'COTAHIST_A2014.TXT' não encontrado!
✅ Solução: Baixar arquivos da B3 e colocar no diretório raiz
```

#### **Memória insuficiente**
```
❌ Erro: MemoryError durante processamento
✅ Solução: Ajustar chunk_size no config.yaml
```

#### **Nenhum par encontrado**
```
❌ Nenhum par passou pelos filtros
✅ Solução: Relaxar parâmetros (aumentar p-valor, Hurst, etc.)
```

### **Configurações de Debug**
```yaml
# config.yaml
logging:
  level: "DEBUG"
  show_progress: true
  file: "debug.log"
```

---

## 📜 Licença e Informações

**Projeto:** Pair Trading Brasil - Pipeline Quantitativo  
**Proprietário:** Itaú Unibanco  
**Versão:** 2.0 (Arquitetura Profissional)  
**Última Atualização:** Setembro 2025  
**Compatibilidade:** Python 3.8+, Pandas 2.0+, Jupyter

### **Créditos**
- **Desenvolvimento:** Equipe Quantitativa Itaú Unibanco
- **Dados:** B3 - Bolsa de Valores Brasileira (COTAHIST)
- **Metodologia:** Baseada em literatura acadêmica de pair trading

### **Changelog v2.0**
- ✅ Migração para arquitetura orientada a objetos
- ✅ Sistema de configuração YAML centralizado
- ✅ Interface Jupyter interativa com widgets
- ✅ Progress tracking e error handling robusto
- ✅ Sistema de cache inteligente
- ✅ Documentação profissional completa
- ✅ Estrutura modular extensível

### **Próximas Versões**
- 🔄 v2.1: Implementação de estratégias de sinais
- 🔄 v2.2: Engine de backtesting completo
- 🔄 v2.3: Dashboards de visualização
- 🔄 v3.0: Machine Learning e otimização de portfólio

---

**💡 Dica:** Use a interface Jupyter para a melhor experiência de usuário!