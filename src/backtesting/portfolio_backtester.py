import os
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd

from src.utils.config_manager import ConfigManager
from .backtester import PairBacktester, BacktestConfig

@dataclass
class PortfolioMetrics:
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float

class PortfolioBacktester:
    def __init__(self, config: Optional[ConfigManager] = None, bt_params: Optional[BacktestConfig] = None):
        self.config = config or ConfigManager()
        self.pair_bt = PairBacktester(self.config, bt_params)
        self.rfr = float(self.config.get('performance.risk_free_rate', 0.0))

    def _calc_metrics(self, equity: pd.Series, trade_df: pd.DataFrame) -> PortfolioMetrics:
        # Total return
        total_ret = float(equity.iloc[-1] / equity.iloc[0] - 1.0) if len(equity) > 1 else 0.0
        # Annualized return
        days = (equity.index[-1] - equity.index[0]).days if len(equity) > 1 else 0
        ann = float((1 + total_ret) ** (252 / max(1, len(equity))) - 1) if len(equity) > 1 else 0.0
        # Volatility (std of trade returns)
        vol = float(np.std(trade_df['ret'], ddof=1)) if len(trade_df) > 1 else 0.0
        # Sharpe (using trade frequency as periods; approximate)
        sharpe = float((np.mean(trade_df['ret']) - self.rfr / 252) / vol * np.sqrt(252)) if vol > 1e-12 and len(trade_df) > 1 else 0.0
        # Max drawdown
        roll_max = equity.cummax()
        dd = (equity / roll_max - 1.0)
        mdd = float(dd.min()) if len(dd) > 0 else 0.0
        # Win rate and profit factor (aggregate from trades)
        win_rate = float(np.mean(trade_df['ret'] > 0)) if len(trade_df) > 0 else 0.0
        gross_profit = float(trade_df.loc[trade_df['net'] > 0, 'net'].sum())
        gross_loss = float(-trade_df.loc[trade_df['net'] < 0, 'net'].sum())
        profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else 0.0
        return PortfolioMetrics(total_ret, ann, vol, sharpe, mdd, win_rate, profit_factor)

    def run(self, n_pairs: Optional[int] = None, criterio: Optional[str] = None) -> Dict[str, Any]:
        years = self.config.get('data.years', [])
        periodo_str = "_".join(map(str, years))
        sep = self.config.get('data.output.separator', ';')
        dec = self.config.get('data.output.decimal', ',')

        # Load prices and pairs
        price_path = self.config.get_output_path(f'matriz_precos_{periodo_str}.csv', 'price_matrix')
        pairs_path = self.config.get_output_path(f'pares_finais_selecionados_{periodo_str}.csv', 'final_results')
        prices = pd.read_csv(price_path, sep=sep, decimal=dec, index_col=0, parse_dates=True)
        pairs = pd.read_csv(pairs_path, sep=sep, decimal=dec)

        # Sort and select top N
        if criterio and criterio in pairs.columns:
            ascending = (criterio == 'p_valor_coint')
            pairs = pairs.sort_values(by=criterio, ascending=ascending)
        elif 'mean_crossings' in pairs.columns:
            pairs = pairs.sort_values(by='mean_crossings', ascending=False)
        if n_pairs is not None:
            pairs = pairs.head(n_pairs)

        # Collect trades across pairs
        trades: List[Dict[str, Any]] = []
        for _, row in pairs.iterrows():
            a = row['Ativo_A']
            b = row['Ativo_B']
            res = self.pair_bt.backtest_pair(prices, a, b)
            tlog = res.get('trades_log', [])
            for t in tlog:
                trades.append(t)

        if not trades:
            return {
                'equity_curve': pd.Series(dtype=float),
                'trades': pd.DataFrame(columns=['date_exit','pair','ret','net']),
                'metrics': PortfolioMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
            }

        trade_df = pd.DataFrame(trades)
        trade_df['date_exit'] = pd.to_datetime(trade_df['date_exit'])
        trade_df = trade_df.sort_values(by='date_exit')

        # Simulate compounding sequentially by trade exit date
        initial_capital = float(self.config.get('strategy.position.initial_capital', 100000.0))
        equity = []
        cap = initial_capital
        last_date = trade_df['date_exit'].iloc[0]
        equity_dates = []
        equity.append(cap)
        equity_dates.append(last_date)
        for _, tr in trade_df.iterrows():
            cap = cap * (1.0 + float(tr['ret']))
            equity.append(cap)
            equity_dates.append(tr['date_exit'])
        equity_series = pd.Series(equity, index=pd.to_datetime(equity_dates))

        metrics = self._calc_metrics(equity_series, trade_df)

        # Save outputs
        out_dir = os.path.join('outputs', '07_backtesting_portfolio')
        os.makedirs(out_dir, exist_ok=True)
        eq_path = os.path.join(out_dir, f'equity_curve_{periodo_str}.csv')
        trade_path = os.path.join(out_dir, f'portfolio_trades_{periodo_str}.csv')
        resumo_path = os.path.join(out_dir, f'portfolio_resumo_{periodo_str}.txt')
        equity_series.to_csv(eq_path, header=['equity'])
        trade_df.to_csv(trade_path, index=False)
        with open(resumo_path, 'w', encoding='utf-8') as f:
            f.write('Resumo do Backtest de Carteira (com composição)\n')
            f.write(f'Pares: {len(pairs)}\n')
            f.write(f'Trades: {len(trade_df)}\n')
            f.write(f'Retorno total: {metrics.total_return:.2%}\n')
            f.write(f'Retorno anualizado (aprox.): {metrics.annualized_return:.2%}\n')
            f.write(f'Volatilidade (std dos trades): {metrics.volatility:.2%}\n')
            f.write(f'Sharpe (aprox.): {metrics.sharpe_ratio:.2f}\n')
            f.write(f'Max Drawdown: {metrics.max_drawdown:.2%}\n')
            f.write(f'Win Rate: {metrics.win_rate:.2%}\n')
            f.write(f'Profit Factor: {metrics.profit_factor:.2f}\n')
            
        return {
            'equity_curve': equity_series,
            'trades': trade_df,
            'metrics': metrics,
            'outputs_dir': out_dir,
        }