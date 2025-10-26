import argparse
from src.utils.config_manager import ConfigManager
from src.pipeline.pair_trading_pipeline import PairTradingPipeline


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
    parser = argparse.ArgumentParser(description='Executa a pipeline completa de Pair Trading para anos especificados.')
    parser.add_argument('--anos', type=str, required=True, help='Período em anos. Ex.: 2014-2020 ou 2014,2015,2016')
    args = parser.parse_args()

    config = ConfigManager()
    years = parse_years_arg(args.anos)
    config.set('data.years', years)
    cotafiles = [f"data\\COTAHIST_A{y}.TXT" for y in years]
    config.set('data.cotahist_files', cotafiles)

    print(f"🚀 Executando pipeline para anos: {years}")
    pipeline = PairTradingPipeline()
    # Aplicar overrides diretamente na configuração do pipeline
    pipeline.config.set('data.years', years)
    pipeline.config.set('data.cotahist_files', cotafiles)
    pipeline.clear_cache()
    results = pipeline.execute_full_pipeline()

    print('✅ Pipeline concluída')
    stats = pipeline.get_statistics()
    print('📊 Estatísticas:')
    for k, v in stats.items():
        print(f"  - {k}: {v}")


if __name__ == '__main__':
    main()