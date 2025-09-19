"""
Módulo de Estratégias

Responsável pela geração de sinais de trading e definição de regras de entrada/saída.
"""

from .signal_generator import SignalGenerator
from .strategy_executor import StrategyExecutor

__all__ = ['SignalGenerator', 'StrategyExecutor']