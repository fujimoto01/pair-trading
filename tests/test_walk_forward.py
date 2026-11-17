"""Tests for the trade mechanics of the walk-forward backtester.

    python -m pytest tests
"""

import numpy as np
import pandas as pd
import pytest

from src.backtesting.walk_forward import (
    WalkForwardConfig, open_position, performance, position_pnl, trade_window,
)


def test_long_spread_is_long_a_short_b():
    sa, sb = open_position(+1, 1000.0, 1.0, 10.0, 20.0)
    assert sa > 0 and sb < 0
    assert sa * 10.0 == pytest.approx(500.0)
    assert -sb * 20.0 == pytest.approx(500.0)


def test_short_spread_is_short_a_long_b():
    sa, sb = open_position(-1, 1000.0, 1.0, 10.0, 20.0)
    assert sa < 0 and sb > 0


def test_long_spread_gains_when_a_rises_and_b_falls():
    sa, sb = open_position(+1, 1000.0, 1.0, 10.0, 20.0)
    assert position_pnl(sa, sb, +1.0, 0.0) == pytest.approx(50.0)
    assert position_pnl(sa, sb, 0.0, -2.0) == pytest.approx(50.0)
    assert position_pnl(sa, sb, -1.0, 0.0) == pytest.approx(-50.0)


def test_short_spread_gains_when_a_falls_and_b_rises():
    sa, sb = open_position(-1, 1000.0, 1.0, 10.0, 20.0)
    assert position_pnl(sa, sb, -1.0, 0.0) == pytest.approx(50.0)
    assert position_pnl(sa, sb, 0.0, +2.0) == pytest.approx(50.0)


@pytest.mark.parametrize('side', [+1, -1])
def test_position_is_neutral_to_a_common_move(side):
    # with beta = 1, both legs moving 10% together must cancel out
    sa, sb = open_position(side, 1000.0, 1.0, 10.0, 20.0)
    assert position_pnl(sa, sb, 1.0, 2.0) == pytest.approx(0.0)


def test_legs_follow_the_hedge_ratio():
    sa, sb = open_position(+1, 1500.0, 2.0, 10.0, 10.0)
    assert sa * 10.0 == pytest.approx(500.0)
    assert -sb * 10.0 == pytest.approx(1000.0)


def _toy_prices(n=400, seed=0):
    rng = np.random.default_rng(seed)
    b = 20.0 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    gap = np.zeros(n)
    for i in range(1, n):
        gap[i] = 0.9 * gap[i - 1] + rng.normal(0, 0.01)
    a = 10.0 * np.exp(np.log(b / 20.0) + gap)
    idx = pd.bdate_range('2020-01-01', periods=n)
    return pd.DataFrame({'AAAA3': a, 'BBBB3': b}, index=idx)


def test_trade_window_accounting_matches_trade_log():
    close = _toy_prices()
    cfg = WalkForwardConfig(lookback=60, entry_z=1.5, exit_z=0.2, n_pairs=1)
    pairs = pd.DataFrame([{'a': 'AAAA3', 'b': 'BBBB3', 'beta': 1.0}])
    pnl, gross, n_open, trades = trade_window(close, pairs, 200, 400, cfg, 100_000.0)
    assert len(trades) > 0
    # daily marking and the per-trade log must add up to the same profit
    assert pnl.sum() == pytest.approx(sum(t['pnl'] for t in trades))
    # nothing is left open after the window, and exposure never exceeds capital by much
    assert n_open.iloc[-1] == 0
    assert gross.max() < 1.2


def test_no_trade_uses_information_from_the_future():
    close = _toy_prices()
    cfg = WalkForwardConfig(lookback=60, entry_z=1.5, n_pairs=1)
    pairs = pd.DataFrame([{'a': 'AAAA3', 'b': 'BBBB3', 'beta': 1.0}])
    base = trade_window(close, pairs, 200, 300, cfg, 100_000.0)[0]
    changed = close.copy()
    changed.iloc[300:] *= 3.0          # rewrite everything after the window
    again = trade_window(changed, pairs, 200, 300, cfg, 100_000.0)[0]
    assert np.allclose(base.values, again.values)


def test_performance_on_a_known_curve():
    equity = pd.Series([101.0, 102.01], index=pd.bdate_range('2020-01-01', periods=2))
    m = performance(equity, 100.0)
    assert m['total_return'] == pytest.approx(0.0201)
    assert m['max_drawdown'] == pytest.approx(0.0)
