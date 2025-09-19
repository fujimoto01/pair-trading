"""
Módulo de Backtesting

Responsável pela simulação de estratégias e avaliação de performance.
"""

from .backtest_engine import BacktestEngine
from .performance_analyzer import PerformanceAnalyzer

__all__ = ['BacktestEngine', 'PerformanceAnalyzer']