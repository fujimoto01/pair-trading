import argparse
import os
import pandas as pd

from src.utils.config_manager import ConfigManager
from src.backtesting.backtester import PairBacktester


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
    parser = argparse.ArgumentParser(description='Backtest de pares por z-score (mean reversion).')
    parser.add_argument('--n-pares', type=int, default=20, help='Quantidade de pares para backtest (top N)')
    parser.add_argument('--criterio', type=str, default='mean_crossings', help='Coluna de ordenação dos pares')
    parser.add_argument('--z-entry', type=float, default=None, help='Limite de entrada do z-score')
    parser.add_argument('--z-exit', type=float, default=None, help='Limite de saída do z-score')
    parser.add_argument('--lookback', type=int, default=None, help='Janela de cálculo do z-score')
    parser.add_argument('--stop-z', type=float, default=None, help='Stop-loss quando |z| >= stop_z')
    parser.add_argument('--anos', type=str, default=None, help='Período em anos. Ex.: 2014-2020 ou 2014,2015,2016')
    args = parser.parse_args()

    config = ConfigManager()

    # Override de anos e arquivos COTAHIST (se fornecido)
    if args.anos:
        years = parse_years_arg(args.anos)
        config.set('data.years', years)
        cotafiles = [f"data\\COTAHIST_A{y}.TXT" for y in years]
        config.set('data.cotahist_files', cotafiles)

    bt = PairBacktester(config)

    # Override params if provided
    if args.z_entry is not None:
        bt.bt.entry_threshold = args.z_entry
    if args.z_exit is not None:
        bt.bt.exit_threshold = args.z_exit
    if args.lookback is not None:
        bt.bt.lookback_window = args.lookback
    if args.stop_z is not None:
        bt.bt.stop_z = args.stop_z

    print('🚀 Executando backtest...')
    df = bt.run(n_pairs=args.n_pares, criterio=args.criterio)

    # Métricas gerais
    trades = int(df['trades'].sum())
    win_rate = float((df['win_rate'] * df['trades']).sum() / trades) if trades > 0 else float('nan')
    total_return = float(df['total_return'].sum())

    print('✅ Backtest concluído')
    print(f'Trades totais: {trades}')
    print(f'Acurácia (win rate global): {win_rate:.2%}' if trades > 0 else 'Acurácia indisponível')
    print(f'Retorno total agregado (sobre capital inicial por trade): {total_return:.2%}')

    # Salvar resumo
    years = config.get('data.years', [])
    periodo_str = "_".join(map(str, years))
    out_dir = os.path.join('outputs', '07_backtesting')
    os.makedirs(out_dir, exist_ok=True)
    resumo_path = os.path.join(out_dir, f'resumo_{periodo_str}.txt')
    with open(resumo_path, 'w', encoding='utf-8') as f:
        f.write('Resumo do Backtest\n')
        f.write(f'Trades totais: {trades}\n')
        if trades > 0:
            f.write(f'Acurácia (win rate global): {win_rate:.2%}\n')
        f.write(f'Retorno total agregado: {total_return:.2%}\n')
        f.write('\nTop 10 pares por win rate:\n')
        top10 = df.sort_values(by=['win_rate','trades'], ascending=[False, False]).head(10)
        for _, r in top10.iterrows():
            f.write(f"{r['pair']}: trades={int(r['trades'])}, win_rate={r['win_rate']:.2%}, total_return={r['total_return']:.2%}\n")

    print(f'📁 Resultados salvos em: outputs/07_backtesting')


if __name__ == '__main__':
    main()