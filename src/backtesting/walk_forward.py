"""
Walk-forward backtest of the pair trading strategy.

This module replaces the first backtester, which had four known problems
(see README, "Backtest audit"):

1. Pairs were selected with statistics from the whole sample, including the
   period that was later traded. Here every trading window only uses pairs
   selected on the formation window that ends the day before it starts.
2. Trades of different pairs were compounded one after another. Here the
   whole portfolio is marked to market every day, and every pair gets a
   fixed slice of the same capital.
3. Annual return and Sharpe ratio treated each trade as one trading day.
   Here they come from the daily equity curve.
4. The profit of the second leg had its sign flipped. Here both legs are
   plain share positions (see `open_position`), covered by unit tests.

Selection criteria are the same as in the original pipeline (Engle-Granger,
Hurst exponent, mean crossings, tail dependence), computed on log prices.
"""

from __future__ import annotations

import io
import os
import re
import zipfile
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import coint

STOCK_RE = re.compile(r'^[A-Z]{4,5}[34568]$')
BENCHMARK = 'BOVA11'


@dataclass
class WalkForwardConfig:
    formation_days: int = 504        # 2 years used to select pairs
    trading_days: int = 126          # 6 months traded with those pairs
    top_n_stocks: int = 100
    min_presence: float = 0.95       # share of formation days with a trade
    significance: float = 0.05
    max_hurst: float = 0.5
    min_crossings: int = 24          # in the 2-year formation window
    u_low: float = 0.05
    u_high: float = 0.95
    min_lower_tail: float = 0.25
    min_upper_tail: float = 0.15
    n_pairs: int = 30
    entry_z: float = 2.5
    exit_z: float = 0.2
    lookback: int = 252
    stop_z: Optional[float] = None
    transaction_cost: float = 0.001
    slippage: float = 0.0005
    execution_delay: int = 1
    initial_capital: float = 100_000.0


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------

def load_cotahist(data_dir: str, years: List[int]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Reads B3's COTAHIST files (ZIP or TXT) and returns (close, volume)
    matrices indexed by date, one column per ticker. Keeps common and
    preferred shares on the spot market, plus the benchmark ETF."""
    rows: List[Tuple[str, str, float, float]] = []
    for year in years:
        zpath = os.path.join(data_dir, f'COTAHIST_A{year}.ZIP')
        tpath = os.path.join(data_dir, f'COTAHIST_A{year}.TXT')
        if os.path.exists(tpath):
            handle = open(tpath, 'r', encoding='latin-1')
        elif os.path.exists(zpath):
            zf = zipfile.ZipFile(zpath)
            handle = io.TextIOWrapper(zf.open(zf.namelist()[0]), encoding='latin-1')
        else:
            raise FileNotFoundError(f'COTAHIST file for {year} not found in {data_dir}')
        with handle:
            for line in handle:
                if line[0:2] != '01' or line[24:27] != '010':
                    continue
                ticker = line[12:24].strip()
                bdi = line[10:12]
                if not ((bdi == '02' and STOCK_RE.match(ticker)) or ticker == BENCHMARK):
                    continue
                close = int(line[108:121]) / 100.0
                volume = int(line[170:188]) / 100.0
                if close <= 0 or volume <= 0:
                    continue
                rows.append((line[2:10], ticker, close, volume))
    df = pd.DataFrame(rows, columns=['date', 'ticker', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
    close = df.pivot(index='date', columns='ticker', values='close').sort_index()
    volume = df.pivot(index='date', columns='ticker', values='volume').sort_index()
    return close, volume


def adjust_splits(close: pd.DataFrame, low: float = 0.6, high: float = 1.7) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """COTAHIST prices are not adjusted for corporate actions. A one-day
    price ratio below `low` or above `high` is treated as a split or reverse
    split, and earlier prices are rescaled so the series is continuous.
    Dividends and small bonus issues are not adjusted."""
    out = close.copy()
    events: List[Dict[str, Any]] = []
    for ticker in out.columns:
        s = out[ticker].dropna()
        if len(s) < 2:
            continue
        ratio = s / s.shift(1)
        jumps = ratio[(ratio < low) | (ratio > high)]
        if jumps.empty:
            continue
        factor = pd.Series(1.0, index=s.index)
        for date, r in jumps.items():
            factor.loc[factor.index < date] *= r
            events.append({'ticker': ticker, 'date': date.strftime('%Y-%m-%d'), 'ratio': round(float(r), 4)})
        out.loc[s.index, ticker] = s * factor
    return out, events


# --------------------------------------------------------------------------
# Pair selection (formation window only)
# --------------------------------------------------------------------------

def hurst_rs(spread: np.ndarray) -> float:
    """Simplified rescaled-range estimate, as in the original pipeline."""
    n = len(spread)
    if n < 50:
        return 0.5
    diffs = np.diff(spread)
    cumsum = np.cumsum(diffs - diffs.mean())
    s = diffs.std()
    if s == 0:
        return 0.5
    rs = (cumsum.max() - cumsum.min()) / s
    if rs <= 0:
        return 0.5
    return float(max(0.0, min(1.0, np.log(rs) / np.log(n))))


def mean_crossings(spread: np.ndarray) -> int:
    above = spread > spread.mean()
    return int(np.sum(above[1:] != above[:-1]))


def tail_dependence(ra: np.ndarray, rb: np.ndarray, u_low: float, u_high: float) -> Tuple[float, float]:
    xl, yl = ra <= np.quantile(ra, u_low), rb <= np.quantile(rb, u_low)
    xh, yh = ra >= np.quantile(ra, u_high), rb >= np.quantile(rb, u_high)
    both_l, both_h = (xl & yl).sum(), (xh & yh).sum()
    lam_l = 0.5 * (both_l / max(yl.sum(), 1) + both_l / max(xl.sum(), 1))
    lam_u = 0.5 * (both_h / max(yh.sum(), 1) + both_h / max(xh.sum(), 1))
    return float(lam_l), float(lam_u)


def _coint_chunk(args: Tuple[np.ndarray, List[Tuple[int, int]]]) -> List[Tuple[int, int, float]]:
    logp, pairs = args
    out = []
    for i, j in pairs:
        try:
            _, p, _ = coint(logp[:, i], logp[:, j])
        except Exception:
            p = 1.0
        out.append((i, j, float(p)))
    return out


def select_pairs(close_form: pd.DataFrame, volume_form: pd.DataFrame, cfg: WalkForwardConfig,
                 pool: Optional[ProcessPoolExecutor] = None) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Runs the whole selection funnel on one formation window."""
    n_days = len(close_form)
    presence = close_form.notna().sum() / n_days
    eligible = [t for t in close_form.columns
                if t != BENCHMARK and presence[t] >= cfg.min_presence and pd.notna(close_form[t].iloc[-1])]
    liquidity = volume_form[eligible].mean().sort_values(ascending=False)
    universe = list(liquidity.head(cfg.top_n_stocks).index)

    prices = close_form[universe].ffill().bfill()
    logp = np.log(prices.values)
    rets = np.diff(logp, axis=0)
    n = len(universe)
    all_pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]

    chunks = [(logp, all_pairs[k::16]) for k in range(16)]
    results: List[Tuple[int, int, float]] = []
    if pool is not None:
        for part in pool.map(_coint_chunk, chunks):
            results.extend(part)
    else:
        for c in chunks:
            results.extend(_coint_chunk(c))

    funnel = {'stocks': n, 'tested': len(all_pairs), 'cointegrated': 0, 'hurst': 0, 'crossings': 0, 'tail': 0}
    rows = []
    for i, j, p in results:
        if p >= cfg.significance:
            continue
        beta, alpha = np.polyfit(logp[:, j], logp[:, i], 1)
        if beta <= 0:
            continue
        funnel['cointegrated'] += 1
        spread = logp[:, i] - beta * logp[:, j] - alpha
        h = hurst_rs(spread)
        if h >= cfg.max_hurst:
            continue
        funnel['hurst'] += 1
        crossings = mean_crossings(spread)
        if crossings < cfg.min_crossings:
            continue
        funnel['crossings'] += 1
        lam_l, lam_u = tail_dependence(rets[:, i], rets[:, j], cfg.u_low, cfg.u_high)
        if lam_l < cfg.min_lower_tail or lam_u < cfg.min_upper_tail:
            continue
        funnel['tail'] += 1
        rows.append({'a': universe[i], 'b': universe[j], 'p_value': p, 'beta': float(beta), 'alpha': float(alpha),
                     'hurst': h, 'crossings': crossings, 'tail_lower': lam_l, 'tail_upper': lam_u})
    pairs = pd.DataFrame(rows)
    if not pairs.empty:
        pairs = pairs.sort_values(['crossings', 'p_value'], ascending=[False, True]).head(cfg.n_pairs).reset_index(drop=True)
    funnel['selected'] = len(pairs)
    return pairs, funnel


# --------------------------------------------------------------------------
# Trading
# --------------------------------------------------------------------------

def open_position(side: int, capital: float, beta: float, price_a: float, price_b: float) -> Tuple[float, float]:
    """Share quantities (signed) for one pair trade.

    side = +1 buys the spread (long A, short B); side = -1 sells it (short A,
    long B). `capital` is the gross amount committed to the pair, split
    between the legs in the proportion 1 : beta, which is the hedge ratio of
    the log-price regression."""
    notional_a = capital / (1.0 + beta)
    notional_b = capital * beta / (1.0 + beta)
    return side * notional_a / price_a, -side * notional_b / price_b


def position_pnl(shares_a: float, shares_b: float, da: float, db: float) -> float:
    """Profit of a pair position for price changes da and db."""
    return shares_a * da + shares_b * db


def rolling_zscore(spread: pd.Series, window: int) -> pd.Series:
    mean = spread.rolling(window, min_periods=window).mean()
    std = spread.rolling(window, min_periods=window).std(ddof=0)
    return (spread - mean) / std


def trade_window(close: pd.DataFrame, pairs: pd.DataFrame, start: int, end: int, cfg: WalkForwardConfig,
                 equity0: float) -> Tuple[pd.Series, pd.Series, pd.Series, List[Dict[str, Any]]]:
    """Trades `pairs` on rows [start, end) of `close`, marking the portfolio
    to market every day. Returns daily profit, gross exposure, number of open
    pairs and the trade log. All positions are closed on the last day."""
    dates = close.index[start:end]
    pnl = pd.Series(0.0, index=dates)
    gross = pd.Series(0.0, index=dates)
    n_open = pd.Series(0, index=dates)
    trades: List[Dict[str, Any]] = []
    if pairs.empty:
        return pnl, gross, n_open, trades

    cost_rate = cfg.transaction_cost + cfg.slippage
    lo = max(0, start - cfg.lookback - 5)
    px = close.iloc[lo:end].ffill()
    offset = start - lo
    slot = 1.0 / cfg.n_pairs
    equity = equity0
    last = len(dates) - 1

    state = []
    for _, row in pairs.iterrows():
        a, b = px[row['a']], px[row['b']]
        spread = np.log(a) - row['beta'] * np.log(b)
        z = rolling_zscore(spread, cfg.lookback).values[offset:]
        state.append({'a': a.values[offset:], 'b': b.values[offset:], 'z': z, 'row': row,
                      'side': 0, 'sa': 0.0, 'sb': 0.0, 'pending': None, 'trade': None})

    for d in range(len(dates)):
        day_pnl = 0.0
        day_gross = 0.0
        opened = 0
        for st in state:
            pa, pb = st['a'][d], st['b'][d]
            if np.isnan(pa) or np.isnan(pb):
                continue
            # 1) mark the open position to market
            if st['side'] != 0 and d > 0:
                gain = position_pnl(st['sa'], st['sb'], pa - st['a'][d - 1], pb - st['b'][d - 1])
                day_pnl += gain
                st['trade']['pnl'] += gain

            # 2) execute the order decided `execution_delay` days ago
            order = st['pending']
            if order is not None and order[0] == d:
                st['pending'] = None
                if order[1] == 'open' and st['side'] == 0 and d < last:
                    side = order[2]
                    capital = equity * slot
                    st['sa'], st['sb'] = open_position(side, capital, st['row']['beta'], pa, pb)
                    cost = cost_rate * (abs(st['sa']) * pa + abs(st['sb']) * pb)
                    day_pnl -= cost
                    st['side'] = side
                    st['trade'] = {'pair': f"{st['row']['a']}-{st['row']['b']}", 'side': side,
                                   'entry': dates[d], 'entry_z': float(order[3]), 'capital': capital, 'pnl': -cost}
                elif order[1] == 'close' and st['side'] != 0:
                    _close(st, pa, pb, cost_rate, dates[d], order[2], trades)
                    day_pnl -= trades[-1]['exit_cost']
            # 3) forced exit on the last day of the window
            if d == last and st['side'] != 0:
                _close(st, pa, pb, cost_rate, dates[d], 'window_end', trades)
                day_pnl -= trades[-1]['exit_cost']

            # 4) today's signal, executed later
            zt = st['z'][d]
            exec_day = d + cfg.execution_delay
            if st['pending'] is None and not np.isnan(zt) and exec_day <= last:
                if st['side'] == 0:
                    if zt > cfg.entry_z:
                        st['pending'] = (exec_day, 'open', -1, zt)
                    elif zt < -cfg.entry_z:
                        st['pending'] = (exec_day, 'open', +1, zt)
                else:
                    if cfg.stop_z is not None and abs(zt) >= cfg.stop_z:
                        st['pending'] = (exec_day, 'close', 'stop')
                    elif (st['side'] == +1 and zt >= -cfg.exit_z) or (st['side'] == -1 and zt <= cfg.exit_z):
                        st['pending'] = (exec_day, 'close', 'reversion')

            if st['side'] != 0:
                day_gross += abs(st['sa']) * pa + abs(st['sb']) * pb
                opened += 1
        pnl.iloc[d] = day_pnl
        equity += day_pnl
        gross.iloc[d] = day_gross / equity if equity > 0 else 0.0
        n_open.iloc[d] = opened
    return pnl, gross, n_open, trades


def _close(st: Dict[str, Any], pa: float, pb: float, cost_rate: float, date, reason: str,
           trades: List[Dict[str, Any]]) -> None:
    cost = cost_rate * (abs(st['sa']) * pa + abs(st['sb']) * pb)
    t = st['trade']
    t['pnl'] -= cost
    t['exit'] = date
    t['reason'] = reason
    t['exit_cost'] = cost
    t['ret'] = t['pnl'] / t['capital']
    t['days'] = int((date - t['entry']).days)
    trades.append(t)
    st['side'], st['sa'], st['sb'], st['trade'] = 0, 0.0, 0.0, None


# --------------------------------------------------------------------------
# Walk-forward loop and metrics
# --------------------------------------------------------------------------

def run_walk_forward(close: pd.DataFrame, volume: pd.DataFrame, cfg: WalkForwardConfig,
                     fixed_pairs: Optional[pd.DataFrame] = None, workers: int = 0,
                     log=print) -> Dict[str, Any]:
    """Rolls formation and trading windows over the sample.

    `fixed_pairs` reproduces the look-ahead bias of the first backtest: the
    same pairs, selected elsewhere, are traded in every window. It exists
    only to measure how much that bias inflates the result."""
    n = len(close)
    pool = ProcessPoolExecutor(max_workers=workers) if workers > 1 else None
    equity = cfg.initial_capital
    pnl_parts, gross_parts, open_parts = [], [], []
    trades: List[Dict[str, Any]] = []
    windows: List[Dict[str, Any]] = []
    selections: List[pd.DataFrame] = []
    try:
        start = cfg.formation_days
        while start < n - 1:
            end = min(start + cfg.trading_days, n)
            form = slice(start - cfg.formation_days, start)
            if fixed_pairs is None:
                pairs, funnel = select_pairs(close.iloc[form], volume.iloc[form], cfg, pool)
            else:
                pairs, funnel = fixed_pairs, {}
            pnl, gross, n_open, tlog = trade_window(close, pairs, start, end, cfg, equity)
            w_ret = pnl.sum() / equity
            equity += pnl.sum()
            windows.append({
                'formation_start': close.index[form.start].strftime('%Y-%m-%d'),
                'formation_end': close.index[start - 1].strftime('%Y-%m-%d'),
                'trade_start': close.index[start].strftime('%Y-%m-%d'),
                'trade_end': close.index[end - 1].strftime('%Y-%m-%d'),
                'funnel': funnel, 'trades': len(tlog), 'ret': float(w_ret),
            })
            sel = pairs.copy()
            sel['window'] = len(windows) - 1
            selections.append(sel)
            for t in tlog:
                t['window'] = len(windows) - 1
            trades.extend(tlog)
            pnl_parts.append(pnl); gross_parts.append(gross); open_parts.append(n_open)
            log(f"window {len(windows):2d} {windows[-1]['trade_start']} to {windows[-1]['trade_end']}: "
                f"{funnel} trades={len(tlog)} ret={w_ret:+.2%}")
            start = end
    finally:
        if pool is not None:
            pool.shutdown()
    pnl = pd.concat(pnl_parts)
    equity_curve = cfg.initial_capital + pnl.cumsum()
    return {'equity': equity_curve, 'pnl': pnl, 'gross': pd.concat(gross_parts), 'n_open': pd.concat(open_parts),
            'trades': trades, 'windows': windows, 'selections': pd.concat(selections, ignore_index=True)}


def performance(equity: pd.Series, initial: float) -> Dict[str, float]:
    """Metrics computed on the daily equity curve."""
    full = pd.concat([pd.Series([initial]), equity.reset_index(drop=True)])
    rets = full.pct_change().dropna().values
    years = len(rets) / 252.0
    total = float(equity.iloc[-1] / initial - 1.0)
    vol = float(rets.std(ddof=1) * np.sqrt(252))
    peak = np.maximum.accumulate(full.values)
    return {
        'total_return': total,
        'annual_return': float((1.0 + total) ** (1.0 / years) - 1.0),
        'annual_volatility': vol,
        'sharpe': float(rets.mean() / rets.std(ddof=1) * np.sqrt(252)) if rets.std(ddof=1) > 0 else 0.0,
        'max_drawdown': float((full.values / peak - 1.0).min()),
        'years': float(years),
    }


def config_dict(cfg: WalkForwardConfig) -> Dict[str, Any]:
    return asdict(cfg)
