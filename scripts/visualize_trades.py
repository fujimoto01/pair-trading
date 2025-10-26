import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime


def parse_years_arg(anos_str: str):
    anos = []
    if '-' in anos_str:
        ini, fim = anos_str.split('-', 1)
        ini = int(ini.strip())
        fim = int(fim.strip())
        anos = list(range(ini, fim + 1))
    else:
        anos = [int(x.strip()) for x in anos_str.split(',') if x.strip()]
    return anos


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def load_outputs(periodo_str: str):
    out_dir = os.path.join('outputs', '07_backtesting_portfolio')
    eq_path = os.path.join(out_dir, f'equity_curve_{periodo_str}.csv')
    tr_path = os.path.join(out_dir, f'portfolio_trades_{periodo_str}.csv')
    if not os.path.exists(eq_path):
        raise FileNotFoundError(f"Equity curve não encontrado: {eq_path}")
    if not os.path.exists(tr_path):
        raise FileNotFoundError(f"Trades da carteira não encontrado: {tr_path}")
    equity = pd.read_csv(eq_path, index_col=0, parse_dates=True)
    # equity pode vir sem nome de coluna
    if equity.columns.empty:
        equity.columns = ['equity']
    trades = pd.read_csv(tr_path)
    trades['date_exit'] = pd.to_datetime(trades['date_exit'])
    return equity['equity'], trades


def plot_equity_and_trades(equity: pd.Series, trades: pd.DataFrame, periodo_str: str, out_dir: str):
    ensure_dir(out_dir)

    # Figura com 2 subplots: equity e retornos por trade
    fig, axs = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    fig.suptitle(f'Simulação da Carteira ({periodo_str}) — Equity e Trades', fontsize=16)

    # Subplot 1: Equity curve com drawdown
    axs[0].plot(equity.index, equity.values, color='navy', label='Equity')
    roll_max = equity.cummax()
    drawdown = (equity / roll_max - 1.0)
    axs[0].fill_between(equity.index, equity.values, roll_max.values, color='red', alpha=0.15, label='Drawdown')
    axs[0].set_ylabel('Equity (R$)')
    axs[0].grid(True, alpha=0.3)
    axs[0].legend(loc='upper left')

    # Subplot 2: Retornos por trade (barras) com cores por sinal
    trades_sorted = trades.sort_values('date_exit')
    colors = ['#2ca02c' if r > 0 else '#d62728' for r in trades_sorted['ret']]
    axs[1].bar(trades_sorted['date_exit'], trades_sorted['ret'] * 100.0, color=colors, width=3)
    axs[1].axhline(0, color='black', linewidth=0.8)
    axs[1].set_ylabel('Retorno por Trade (%)')
    axs[1].set_xlabel('Data de Saída do Trade')
    axs[1].grid(True, alpha=0.3)

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    png_path = os.path.join(out_dir, f'portfolio_equity_and_trades_{periodo_str}.png')
    plt.savefig(png_path, dpi=120)
    plt.close(fig)

    # Figura adicional: linha do equity com marcações de trades (win/loss)
    fig2, ax2 = plt.subplots(figsize=(14, 4))
    ax2.plot(equity.index, equity.values, color='navy', label='Equity')
    wins = trades_sorted[trades_sorted['ret'] > 0]
    losses = trades_sorted[trades_sorted['ret'] <= 0]
    # Deduplicar índice da equity para permitir reindex sem erro
    equity_dedup = equity.groupby(equity.index).last()
    ax2.scatter(wins['date_exit'], equity_dedup.reindex(wins['date_exit'], method='nearest'), marker='^', color='#2ca02c', label='Win', s=40, alpha=0.8)
    ax2.scatter(losses['date_exit'], equity_dedup.reindex(losses['date_exit'], method='nearest'), marker='v', color='#d62728', label='Loss', s=40, alpha=0.8)
    ax2.set_title(f'Equity com marcações de Trades ({periodo_str})')
    ax2.set_ylabel('Equity (R$)')
    ax2.set_xlabel('Data')
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper left')
    png2_path = os.path.join(out_dir, f'portfolio_equity_marks_{periodo_str}.png')
    plt.savefig(png2_path, dpi=120)
    plt.close(fig2)

    return [png_path, png2_path]


def main():
    parser = argparse.ArgumentParser(description='Visualização gráfica do robô realizando os trades (equity + trades).')
    parser.add_argument('--anos', type=str, required=True, help='Período em anos. Ex.: 2014-2020 ou 2014,2015,2016')
    parser.add_argument('--out-dir', type=str, default=os.path.join('outputs', '08_visualization'), help='Pasta de saída para os gráficos')
    args = parser.parse_args()

    years = parse_years_arg(args.anos)
    periodo_str = "_".join(map(str, years))

    equity, trades = load_outputs(periodo_str)
    paths = plot_equity_and_trades(equity, trades, periodo_str, args.out_dir)

    print('✅ Gráficos gerados:')
    for p in paths:
        print(' -', p)


if __name__ == '__main__':
    main()