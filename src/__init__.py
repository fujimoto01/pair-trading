"""
Pair Trading Analysis Package

Módulo completo para análise quantitativa de pair trading no mercado brasileiro (B3).
Inclui coleta de dados, análise de cointegração, estratégias e backtesting.
"""

__version__ = "1.2.0"
__author__ = "Itaú Unibanco"
__email__ = "quantitative-team@itau.com.br"

# Importações principais para facilitar o uso
from .pipeline.pair_trading_pipeline import PairTradingPipeline
from .utils.config_manager import ConfigManager

__all__ = [
    'PairTradingPipeline',
    'ConfigManager'
]