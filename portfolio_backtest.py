import argparse
import os

from src.utils.config_manager import ConfigManager
from src.backtesting.portfolio_backtester import PortfolioBacktester


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


def main():
    parser = argparse.ArgumentParser(description='Backtest de carteira com composição (equity curve).')
    parser.add_argument('--n-pares', type=int, default=50, help='Quantidade de pares na carteira')
    parser.add_argument('--criterio', type=str, default='mean_crossings', help='Coluna de ordenação dos pares')
    parser.add_argument('--anos', type=str, default=None, help='Período em anos. Ex.: 2014-2020 ou 2014,2015,2016')
    args = parser.parse_args()

    config = ConfigManager()

    if args.anos:
        years = parse_years_arg(args.anos)
        config.set('data.years', years)
        cotafiles = [f"data\\COTAHIST_A{y}.TXT" for y in years]
        config.set('data.cotahist_files', cotafiles)

    pbt = PortfolioBacktester(config)
    print('🚀 Executando backtest de carteira com composição...')
    res = pbt.run(n_pairs=args.n_pares, criterio=args.criterio)

    metrics = res['metrics']
    print('✅ Backtest de carteira concluído')
    print(f"Retorno total: {metrics.total_return:.2%}")
    print(f"Retorno anualizado (aprox.): {metrics.annualized_return:.2%}")
    print(f"Volatilidade (std dos trades): {metrics.volatility:.2%}")
    print(f"Sharpe (aprox.): {metrics.sharpe_ratio:.2f}")
    print(f"Max Drawdown: {metrics.max_drawdown:.2%}")
    print(f"Win Rate: {metrics.win_rate:.2%}")
    print(f"Profit Factor: {metrics.profit_factor:.2f}")
    print('📁 Resultados salvos em: outputs/07_backtesting_portfolio')


if __name__ == '__main__':
    main()