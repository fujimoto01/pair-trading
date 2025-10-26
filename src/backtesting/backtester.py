import os
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
import numpy as np
import pandas as pd
import statsmodels.api as sm

from src.utils.config_manager import ConfigManager

@dataclass
class BacktestConfig:
    entry_threshold: float = 2.0
    exit_threshold: float = 0.0
    lookback_window: int = 252
    initial_capital: float = 100000.0
    max_position_size: float = 0.1
    transaction_cost: float = 0.001
    execution_delay: int = 1
    slippage: float = 0.0005
    in_sample_pct: float = 0.7
    # Novo: stop-loss por z-score
    stop_z: float | None = None

class PairBacktester:
    def __init__(self, config: ConfigManager | None = None, bt_params: BacktestConfig | None = None):
        self.config = config or ConfigManager()
        if bt_params is None:
            bt_params = BacktestConfig(
                entry_threshold=self.config.get('strategy.zscore.entry_threshold', 2.0),
                exit_threshold=self.config.get('strategy.zscore.exit_threshold', 0.0),
                lookback_window=self.config.get('strategy.zscore.lookback_window', 252),
                initial_capital=self.config.get('strategy.position.initial_capital', 100000.0),
                max_position_size=self.config.get('strategy.position.max_position_size', 0.1),
                transaction_cost=self.config.get('strategy.position.transaction_cost', 0.001),
                execution_delay=self.config.get('backtesting.execution.execution_delay', 1),
                slippage=self.config.get('backtesting.execution.slippage', 0.0005),
                in_sample_pct=self.config.get('backtesting.data_split.in_sample_pct', 0.7),
            )
        self.bt = bt_params

    def _compute_beta(self, a: pd.Series, b: pd.Series) -> float:
        try:
            X = sm.add_constant(b)
            model = sm.OLS(a, X, missing='drop').fit()
            # Try to get slope parameter robustly
            if hasattr(model, 'params'):
                params = model.params
                if 'const' in params.index:
                    slope_names = [nm for nm in params.index if nm != 'const']
                    if slope_names:
                        return float(params[slope_names[0]])
                # Fallback by position
                if len(params) >= 2:
                    return float(params.iloc[1])
        except Exception:
            pass
        # Ultimate fallback: covariance/variance
        a_vals = a.values
        b_vals = b.values
        var_b = np.var(b_vals)
        if var_b == 0:
            return 1.0
        cov_ab = np.cov(a_vals, b_vals)[0, 1]
        return float(cov_ab / var_b)

    def _zscore(self, x: pd.Series, window: int) -> pd.Series:
        mean = x.rolling(window=window, min_periods=window).mean()
        std = x.rolling(window=window, min_periods=window).std(ddof=0)
        return (x - mean) / std

    def _split_series(self, s: pd.Series, in_pct: float) -> Tuple[pd.Series, pd.Series]:
        n = len(s)
        cut = int(np.floor(n * in_pct))
        return s.iloc[:cut], s.iloc[cut:]

    def backtest_pair(self, prices: pd.DataFrame, ticker_a: str, ticker_b: str) -> Dict[str, Any]:
        a = prices[ticker_a].dropna()
        b = prices[ticker_b].dropna()
        idx = a.index.intersection(b.index)
        a = a.loc[idx]
        b = b.loc[idx]
        if len(idx) < self.bt.lookback_window + 10:
            return {
                'pair': f'{ticker_a}-{ticker_b}',
                'trades': 0,
                'win_rate': np.nan,
                'total_return': 0.0,
                'profit_factor': np.nan,
            }

        # Split in/out-of-sample
        a_in, a_out = self._split_series(a, self.bt.in_sample_pct)
        b_in, b_out = self._split_series(b, self.bt.in_sample_pct)

        # Hedge ratio on in-sample
        beta = self._compute_beta(a_in, b_in)
        # Compute spread on full series but act only on out-of-sample
        spread_full = a - beta * b
        z_full = self._zscore(spread_full, self.bt.lookback_window)

        entry = self.bt.entry_threshold
        exit_ = self.bt.exit_threshold
        stop_z = self.bt.stop_z

        capital = self.bt.initial_capital
        max_pos_value = capital * self.bt.max_position_size
        tc = self.bt.transaction_cost
        slip = self.bt.slippage
        delay = self.bt.execution_delay

        in_position = False
        position_side = 0  # +1 long spread, -1 short spread
        qty_a = 0.0
        qty_b = 0.0
        entry_price_a = entry_price_b = np.nan

        trade_returns: List[float] = []
        gross_profit = 0.0
        gross_loss = 0.0
        trade_log: List[Dict[str, Any]] = []

        dates_out = a_out.index
        for i in range(len(dates_out)):
            date = dates_out[i]
            z_i = z_full.loc[date] if date in z_full.index else np.nan

            # Execute with delay within out-of-sample
            exec_i = i + delay
            if exec_i >= len(dates_out):
                break
            date_exec = dates_out[exec_i]

            pa = a_out.iloc[exec_i]
            pb = b_out.iloc[exec_i]

            if not in_position:
                if z_i is not None and not np.isnan(z_i):
                    if z_i > entry:
                        # Short spread: short A, long B*beta
                        in_position = True
                        position_side = -1
                        qty_a = -(max_pos_value / pa)
                        qty_b = +(max_pos_value * beta / pb)
                        entry_price_a = pa * (1 + slip)
                        entry_price_b = pb * (1 - slip)
                    elif z_i < -entry:
                        # Long spread: long A, short B*beta
                        in_position = True
                        position_side = +1
                        qty_a = +(max_pos_value / pa)
                        qty_b = -(max_pos_value * beta / pb)
                        entry_price_a = pa * (1 + slip)
                        entry_price_b = pb * (1 + slip)
                continue

            # Manage exit
            if in_position:
                # Stop-loss por z-score extremo
                if stop_z is not None and z_i is not None and not np.isnan(z_i) and abs(z_i) >= stop_z:
                    exit_price_a = pa * (1 - slip)
                    exit_price_b = pb * (1 - slip)
                    if position_side == +1:
                        pnl_a = qty_a * (exit_price_a - entry_price_a)
                        pnl_b = qty_b * (entry_price_b - exit_price_b)
                    else:
                        pnl_a = (-qty_a) * (entry_price_a - exit_price_a)
                        pnl_b = (-qty_b) * (exit_price_b - entry_price_b)
                    pnl = pnl_a + pnl_b
                    costs = tc * (abs(qty_a) * entry_price_a + abs(qty_b) * entry_price_b)
                    costs += tc * (abs(qty_a) * exit_price_a + abs(qty_b) * exit_price_b)
                    net = pnl - costs
                    ret = net / capital
                    trade_returns.append(ret)
                    trade_log.append({'pair': f'{ticker_a}-{ticker_b}', 'date_exit': date_exec, 'ret': float(ret), 'net': float(net)})
                    if net >= 0:
                        gross_profit += net
                    else:
                        gross_loss += -net
                    in_position = False
                    position_side = 0
                    qty_a = qty_b = 0.0
                    entry_price_a = entry_price_b = np.nan
                    continue

                if z_i is not None and not np.isnan(z_i) and abs(z_i) <= exit_:
                    # Exit at next exec price
                    exit_price_a = pa * (1 - slip)
                    exit_price_b = pb * (1 - slip)

                    if position_side == +1:
                        pnl_a = qty_a * (exit_price_a - entry_price_a)
                        pnl_b = qty_b * (entry_price_b - exit_price_b)
                    else:
                        pnl_a = (-qty_a) * (entry_price_a - exit_price_a)
                        pnl_b = (-qty_b) * (exit_price_b - entry_price_b)
                    pnl = pnl_a + pnl_b

                    costs = tc * (abs(qty_a) * entry_price_a + abs(qty_b) * entry_price_b)
                    costs += tc * (abs(qty_a) * exit_price_a + abs(qty_b) * exit_price_b)

                    net = pnl - costs
                    ret = net / capital
                    trade_returns.append(ret)
                    trade_log.append({'pair': f'{ticker_a}-{ticker_b}', 'date_exit': date_exec, 'ret': float(ret), 'net': float(net)})
                    if net >= 0:
                        gross_profit += net
                    else:
                        gross_loss += -net

        trades = len(trade_returns)
        win_rate = float(np.mean(np.array(trade_returns) > 0)) if trades > 0 else np.nan
        total_return = float(np.sum(trade_returns)) if trades > 0 else 0.0
        profit_factor = (gross_profit / gross_loss) if (gross_loss > 0) else np.nan
        sharpe = np.nan
        if trades > 1:
            r = np.array(trade_returns)
            std = r.std(ddof=1)
            if std > 1e-12:
                sharpe = float(r.mean() / std * np.sqrt(trades))

        return {
            'pair': f'{ticker_a}-{ticker_b}',
            'beta': beta,
            'trades': trades,
            'win_rate': win_rate,
            'total_return': total_return,
            'profit_factor': profit_factor,
            'sharpe': sharpe,
            'trades_log': trade_log,
        }

    def run(self, n_pairs: int | None = None, criterio: str | None = None) -> pd.DataFrame:
        years = self.config.get('data.years', [])
        periodo_str = "_".join(map(str, years))
        sep = self.config.get('data.output.separator', ';')
        dec = self.config.get('data.output.decimal', ',')

        price_path = self.config.get_output_path(f'matriz_precos_{periodo_str}.csv', 'price_matrix')
        pairs_path = self.config.get_output_path(f'pares_finais_selecionados_{periodo_str}.csv', 'final_results')

        prices = pd.read_csv(price_path, sep=sep, decimal=dec, index_col=0, parse_dates=True)
        pairs = pd.read_csv(pairs_path, sep=sep, decimal=dec)

        if criterio and criterio in pairs.columns:
            ascending = (criterio == 'p_valor_coint')
            pairs = pairs.sort_values(by=criterio, ascending=ascending)
        elif 'mean_crossings' in pairs.columns:
            pairs = pairs.sort_values(by='mean_crossings', ascending=False)

        if n_pairs is not None:
            pairs = pairs.head(n_pairs)

        results: List[Dict[str, Any]] = []
        for _, row in pairs.iterrows():
            a = row['Ativo_A']
            b = row['Ativo_B']
            res = self.backtest_pair(prices, a, b)
            results.append(res)

        df_results = pd.DataFrame(results)
        # Save outputs
        out_dir = os.path.join('outputs', '07_backtesting')
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, f'backtest_results_{periodo_str}.csv')
        df_results.to_csv(out_file, index=False)
        return df_results