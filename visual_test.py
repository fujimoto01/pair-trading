import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
import os
import argparse
from src.utils.config_manager import ConfigManager


def plotar_teste_visual_completo(matriz_precos, df_pares, n_amostra=5, criterio='mean_crossings', incluir_piores=True, pasta_out='outputs/06_visual_tests'):
    """
    Gera gráficos de duas partes: preços normalizados e o spread com sua média.
    Permite escolher a quantidade de pares e o critério de seleção.
    """
    print("Iniciando a geração de gráficos de diagnóstico...")

    pasta_graficos = pasta_out
    if not os.path.exists(pasta_graficos):
        os.makedirs(pasta_graficos)
        print(f"Pasta '{pasta_graficos}' criada para salvar os gráficos.")

    # Ordenação dos pares pelo critério escolhido
    if criterio in df_pares.columns:
        sort_col = criterio
    else:
        sort_col = 'num_cruzamentos' if 'num_cruzamentos' in df_pares.columns else ('mean_crossings' if 'mean_crossings' in df_pares.columns else None)
    if sort_col is None:
        print("Nenhuma coluna de ordenação encontrada; mantendo a ordem original.")
        df_pares_sorted = df_pares
    else:
        # p-valor: menor é melhor (ascending=True). Para os demais, maior é melhor.
        ascending = (sort_col == 'p_valor_coint')
        df_pares_sorted = df_pares.sort_values(by=sort_col, ascending=ascending)

    # Amostra dos melhores e, opcionalmente, piores
    top_pares = df_pares_sorted.head(n_amostra)
    bottom_pares = df_pares_sorted.tail(n_amostra) if incluir_piores else pd.DataFrame(columns=df_pares_sorted.columns)
    amostra_total = pd.concat([top_pares, bottom_pares])

    for index, row in amostra_total.iterrows():
        ticker1 = row['Ativo_A']
        ticker2 = row['Ativo_B']
        p_valor = row['p_valor_coint']
        hurst = row.get('expoente_hurst', row.get('hurst_exponent', float('nan')))
        cruzamentos = row.get('num_cruzamentos', row.get('mean_crossings', None))

        print(f"  Plotando par: {ticker1}-{ticker2} ({cruzamentos} cruzamentos)...")

        # --- Cálculos ---
        # 1. Normalizar Preços
        serie1_norm = (matriz_precos[ticker1] / matriz_precos[ticker1].iloc[0]) * 100
        serie2_norm = (matriz_precos[ticker2] / matriz_precos[ticker2].iloc[0]) * 100
        
        # 2. Calcular o Spread
        serie1 = matriz_precos[ticker1]
        serie2 = matriz_precos[ticker2]
        serie2_com_constante = sm.add_constant(serie2)
        modelo = sm.OLS(serie1, serie2_com_constante).fit()
        spread = modelo.resid

        # --- Plotagem ---
        fig, axs = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
        fig.suptitle(f'Diagnóstico do Par: {ticker1} vs {ticker2}\np-valor: {p_valor:.3f} | Hurst: {hurst:.3f} | Cruzamentos da Média: {cruzamentos}', fontsize=16)

        # Gráfico Superior: Preços Normalizados
        axs[0].plot(serie1_norm, label=ticker1)
        axs[0].plot(serie2_norm, label=ticker2)
        axs[0].set_ylabel('Preço Normalizado (Base 100)')
        axs[0].legend()
        axs[0].grid(True)

        # Gráfico Inferior: Spread e Média
        axs[1].plot(spread, label='Spread do Par')
        axs[1].axhline(spread.mean(), color='red', linestyle='--', label='Média do Spread')
        axs[1].set_ylabel('Valor do Spread')
        axs[1].set_xlabel('Data')
        axs[1].legend()
        axs[1].grid(True)
        
        plt.tight_layout(rect=[0, 0.03, 1, 0.95]) # Ajusta para o supertítulo
        
        # Salvar o gráfico
        nome_arquivo = f'{pasta_graficos}/diagnostico_{ticker1}_{ticker2}.png'
        plt.savefig(nome_arquivo)
        plt.close()

    print(f"\nGráficos de diagnóstico salvos com sucesso na pasta '{pasta_graficos}'.")


# --- Função de Execução ---

def main():
    parser = argparse.ArgumentParser(description='Gerar gráficos de diagnóstico de pares.')
    parser.add_argument('--n-amostra', type=int, default=5, help='Quantidade de pares no topo/rodapé a serem plotados')
    parser.add_argument('--criterio', type=str, default='mean_crossings', help='Coluna para ordenar os pares (ex.: mean_crossings, p_valor_coint, hurst_exponent, score_coint)')
    parser.add_argument('--somente-top', action='store_true', help='Se definido, plota apenas os melhores, sem os piores')
    parser.add_argument('--pasta-out', type=str, default='outputs/06_visual_tests', help='Diretório de saída para salvar os gráficos')
    args = parser.parse_args()

    config = ConfigManager()
    years = config.get('data.years', [])
    periodo_str = "_".join(map(str, years))

    # Caminhos organizados conforme configuração
    arquivo_matriz_precos = config.get_output_path(f'matriz_precos_{periodo_str}.csv', 'price_matrix')
    arquivo_pares = config.get_output_path(f'pares_finais_selecionados_{periodo_str}.csv', 'final_results')

    print("Carregando arquivos de dados...")

    # Verificações de existência com mensagem amigável
    if not os.path.exists(arquivo_matriz_precos):
        print(f"Arquivo de matriz de preços não encontrado: {arquivo_matriz_precos}")
        print("Execute a pipeline (Fase 2) para gerar a matriz de preços.")
        return
    if not os.path.exists(arquivo_pares):
        print(f"Arquivo de pares finais não encontrado: {arquivo_pares}")
        print("Execute a pipeline (Fase 4) para gerar os pares finais.")
        return

    separator = config.get('data.output.separator', ';')
    decimal = config.get('data.output.decimal', ',')

    matriz_de_precos = pd.read_csv(arquivo_matriz_precos, sep=separator, decimal=decimal, index_col=0, parse_dates=True)
    df_pares_finais = pd.read_csv(arquivo_pares, sep=separator, decimal=decimal)
    print("Dados carregados.")

    plotar_teste_visual_completo(
        matriz_de_precos,
        df_pares_finais,
        n_amostra=args.n_amostra,
        criterio=args.criterio,
        incluir_piores=(not args.somente_top),
        pasta_out=args.pasta_out,
    )


if __name__ == "__main__":
    main()