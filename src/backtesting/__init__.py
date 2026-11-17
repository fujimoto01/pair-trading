"""
Módulo de Backtesting

Responsável pela simulação de estratégias e avaliação de performance.
O backtest atual é o walk_forward; backtester e portfolio_backtester são a
primeira versão, mantida só para referência.
"""

from .backtester import PairBacktester
from .walk_forward import WalkForwardConfig, run_walk_forward

__all__ = ['PairBacktester', 'WalkForwardConfig', 'run_walk_forward']
