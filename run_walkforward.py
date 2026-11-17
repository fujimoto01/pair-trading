"""
Runs the walk-forward backtest and writes the results used by the project page.

    python run_walkforward.py

Reads the COTAHIST files in data/ (ZIP or TXT), writes CSV outputs to
outputs/08_walk_forward/ and the page data to site/data.js.
"""

import argparse
import json
import os

import numpy as np
import pandas as pd

from src.backtesting.walk_forward import (
    BENCHMARK, WalkForwardConfig, adjust_splits, config_dict, load_cotahist,
    performance, rolling_zscore, run_walk_forward, select_pairs,
)

YEARS = list(range(2014, 2021))
OUT_DIR = os.path.join('outputs', '08_walk_forward')
EXAMPLE_PAIR = 'BRML3-MULT3'


def r(x, nd=4):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), nd)


def trades_frame(trades):
    df = pd.DataFrame(trades)
    if df.empty:
        return df
    df['entry'] = pd.to_datetime(df['entry'])
    df['exit'] = pd.to_datetime(df['exit'])
    return df.sort_values('entry').reset_index(drop=True)


def example_pair(close, result, cfg):
    """Exports prices, z-score and trades of one selected pair for the
    explanatory chart. EXAMPLE_PAIR (two shopping mall operators) is used when
    it was selected, because a pair from the same industry is easier to read;
    otherwise the pair with the most round trips in a single window."""
    tdf = trades_frame(result['trades'])
    tdf = tdf[tdf['reason'] == 'reversion']
    counts = tdf.groupby(['pair', 'window']).size().sort_values(ascending=False)
    preferred = [k for k in counts.index if k[0] == EXAMPLE_PAIR]
    pair, window = preferred[0] if preferred else counts.index[0]
    w = result['windows'][window]
    sel = result['selections']
    row = sel[(sel['window'] == window) & ((sel['a'] + '-' + sel['b']) == pair)].iloc[0]
    start = close.index.get_loc(pd.Timestamp(w['trade_start']))
    end = close.index.get_loc(pd.Timestamp(w['trade_end'])) + 1
    px = close.iloc[start - cfg.lookback - 5:end].ffill()
    spread = np.log(px[row['a']]) - row['beta'] * np.log(px[row['b']])
    z = rolling_zscore(spread, cfg.lookback).iloc[-(end - start):]
    a = px[row['a']].loc[z.index]
    b = px[row['b']].loc[z.index]
    all_trades = trades_frame(result['trades'])
    mine = all_trades[(all_trades['pair'] == pair) & (all_trades['window'] == window)]
    return {
        'a': row['a'], 'b': row['b'], 'beta': r(row['beta'], 3),
        'dates': [d.strftime('%Y-%m-%d') for d in z.index],
        'price_a': [r(v / a.iloc[0] * 100, 2) for v in a],
        'price_b': [r(v / b.iloc[0] * 100, 2) for v in b],
        'z': [r(v, 3) for v in z],
        'trades': [{'entry': t.entry.strftime('%Y-%m-%d'), 'exit': t.exit.strftime('%Y-%m-%d'),
                    'side': int(t.side), 'ret': r(t.ret), 'reason': t.reason} for t in mine.itertuples()],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', default='data')
    parser.add_argument('--workers', type=int, default=max(1, (os.cpu_count() or 2) - 1))
    args = parser.parse_args()

    cfg = WalkForwardConfig()
    print('Reading COTAHIST files...')
    raw_close, volume = load_cotahist(args.data_dir, YEARS)
    close, events = adjust_splits(raw_close)
    print(f'{close.shape[0]} trading days, {close.shape[1]} tickers, {len(events)} split adjustments')

    print('\nWalk-forward backtest (pairs selected on past data only)')
    wf = run_walk_forward(close, volume, cfg, workers=args.workers)

    print('\nComparison run: pairs selected once on the full sample (look-ahead)')
    biased_cfg = WalkForwardConfig()
    full_pairs, full_funnel = select_pairs(close, volume, biased_cfg, None) if args.workers <= 1 else _select_full(close, volume, biased_cfg, args.workers)
    biased = run_walk_forward(close, volume, cfg, fixed_pairs=full_pairs, log=lambda *_: None)

    metrics = performance(wf['equity'], cfg.initial_capital)
    biased_metrics = performance(biased['equity'], cfg.initial_capital)

    dates = wf['equity'].index
    bova = close[BENCHMARK].ffill().loc[dates]
    bova0 = close[BENCHMARK].ffill().iloc[cfg.formation_days - 1]
    bova_curve = bova / bova0 * cfg.initial_capital
    bova_metrics = performance(bova_curve, cfg.initial_capital)
    strat_ret = pd.concat([pd.Series([cfg.initial_capital]), wf['equity']]).pct_change().dropna()
    bova_ret = pd.concat([pd.Series([bova0]), bova]).pct_change().dropna()
    metrics['correlation_benchmark'] = float(np.corrcoef(strat_ret.values, bova_ret.values)[0, 1])
    metrics['beta_benchmark'] = float(np.cov(strat_ret.values, bova_ret.values)[0, 1] / bova_ret.values.var(ddof=1))

    tdf = trades_frame(wf['trades'])
    metrics.update({
        'trades': int(len(tdf)),
        'win_rate': float((tdf['ret'] > 0).mean()),
        'avg_trade_return': float(tdf['ret'].mean()),
        'median_days': float(tdf['days'].median()),
        'profit_factor': float(tdf.loc[tdf['pnl'] > 0, 'pnl'].sum() / -tdf.loc[tdf['pnl'] < 0, 'pnl'].sum()),
        'avg_gross_exposure': float(wf['gross'].mean()),
        'avg_open_pairs': float(wf['n_open'].mean()),
        'reversion_share': float((tdf['reason'] == 'reversion').mean()),
        'avg_reversion_return': float(tdf.loc[tdf['reason'] == 'reversion', 'ret'].mean()),
        'avg_window_end_return': float(tdf.loc[tdf['reason'] == 'window_end', 'ret'].mean()),
        'distinct_pairs': int(tdf['pair'].nunique()),
    })

    print('\n=== Walk-forward, out of sample ===')
    for k, v in metrics.items():
        print(f'{k:>24}: {v:.4f}')
    print('\n=== Same engine, pairs chosen with look-ahead ===')
    for k, v in biased_metrics.items():
        print(f'{k:>24}: {v:.4f}')
    print('\n=== BOVA11 ===')
    for k, v in bova_metrics.items():
        print(f'{k:>24}: {v:.4f}')

    os.makedirs(OUT_DIR, exist_ok=True)
    pd.DataFrame({'equity': wf['equity'], 'gross_exposure': wf['gross'], 'open_pairs': wf['n_open'],
                  'equity_lookahead': biased['equity'], 'bova11': bova_curve}).to_csv(os.path.join(OUT_DIR, 'equity_daily.csv'))
    tdf.drop(columns=['exit_cost']).to_csv(os.path.join(OUT_DIR, 'trades.csv'), index=False)
    wf['selections'].to_csv(os.path.join(OUT_DIR, 'selected_pairs.csv'), index=False)
    pd.DataFrame(events).to_csv(os.path.join(OUT_DIR, 'split_adjustments.csv'), index=False)

    # weekly points keep the page light; drawdown is computed on daily data
    peak = np.maximum.accumulate(np.concatenate([[cfg.initial_capital], wf['equity'].values]))[1:]
    dd = wf['equity'].values / peak - 1.0
    step = list(range(0, len(dates), 5))
    if step[-1] != len(dates) - 1:
        step.append(len(dates) - 1)
    yearly = []
    for year in sorted(set(dates.year)):
        m = dates.year == year
        e, bv = wf['equity'][m], bova_curve[m]
        e0 = wf['equity'][dates < e.index[0]].iloc[-1] if (dates < e.index[0]).any() else cfg.initial_capital
        b0 = bova_curve[dates < bv.index[0]].iloc[-1] if (dates < bv.index[0]).any() else cfg.initial_capital
        yearly.append({'year': int(year), 'strategy': r(e.iloc[-1] / e0 - 1), 'bova11': r(bv.iloc[-1] / b0 - 1)})

    by_pair = tdf.groupby('pair').agg(trades=('ret', 'size'), pnl=('pnl', 'sum'), win=('ret', lambda s: (s > 0).mean()),
                                      days=('days', 'mean')).sort_values('pnl', ascending=False)
    page = {
        'config': config_dict(cfg),
        'period': {'data_start': close.index[0].strftime('%Y-%m-%d'), 'trade_start': dates[0].strftime('%Y-%m-%d'),
                   'trade_end': dates[-1].strftime('%Y-%m-%d'), 'tickers': int(close.shape[1] - 1),
                   'split_adjustments': len(events)},
        'metrics': {k: r(v) for k, v in metrics.items()},
        'metrics_lookahead': {k: r(v) for k, v in biased_metrics.items()},
        'metrics_bova11': {k: r(v) for k, v in bova_metrics.items()},
        'lookahead_funnel': full_funnel,
        'curve': {
            'dates': [dates[i].strftime('%Y-%m-%d') for i in step],
            'strategy': [r(wf['equity'].iloc[i] / cfg.initial_capital * 100, 2) for i in step],
            'lookahead': [r(biased['equity'].iloc[i] / cfg.initial_capital * 100, 2) for i in step],
            'bova11': [r(bova_curve.iloc[i] / cfg.initial_capital * 100, 2) for i in step],
            'drawdown': [r(dd[max(0, i - 4):i + 1].min() * 100, 2) for i in step],
            'open_pairs': [int(wf['n_open'].iloc[max(0, i - 4):i + 1].max()) for i in step],
        },
        'yearly': yearly,
        'windows': wf['windows'],
        'trades': [{'pair': t.pair, 'entry': t.entry.strftime('%Y-%m-%d'), 'exit': t.exit.strftime('%Y-%m-%d'),
                    'side': int(t.side), 'ret': r(t.ret), 'days': int(t.days), 'reason': t.reason} for t in tdf.itertuples()],
        'pairs': [{'pair': p, 'trades': int(v.trades), 'pnl_pct': r(v.pnl / cfg.initial_capital * 100, 3),
                   'win': r(v.win, 3), 'days': r(v.days, 1)} for p, v in by_pair.iterrows()],
        'example': example_pair(close, wf, cfg),
    }
    os.makedirs('site', exist_ok=True)
    with open(os.path.join('site', 'data.js'), 'w', encoding='utf-8') as f:
        f.write('// Generated by run_walkforward.py. Do not edit by hand.\n')
        f.write('window.PT_DATA = ' + json.dumps(page, separators=(',', ':')) + ';\n')
    print(f"\nWrote {OUT_DIR} and site/data.js")


def _select_full(close, volume, cfg, workers):
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return select_pairs(close, volume, cfg, pool)


if __name__ == '__main__':
    main()
