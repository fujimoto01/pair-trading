import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
import os

def plotar_teste_visual_completo(matriz_precos, df_pares, n_amostra=5):
    """
    Gera gráficos de duas partes: preços normalizados e o spread com sua média.
    Plota os N melhores (mais cruzamentos) e os N piores (menos cruzamentos).
    """
    print("Iniciando a geração de gráficos de diagnóstico...")

    pasta_graficos = 'testes_visuais_frequencia'
    if not os.path.exists(pasta_graficos):
        os.makedirs(pasta_graficos)
        print(f"Pasta '{pasta_graficos}' criada para salvar os gráficos.")

    # Amostra dos melhores e piores
    top_pares = df_pares.head(n_amostra)
    bottom_pares = df_pares.tail(n_amostra)
    amostra_total = pd.concat([top_pares, bottom_pares])

    for index, row in amostra_total.iterrows():
        ticker1 = row['Ativo_A']
        ticker2 = row['Ativo_B']
        p_valor = row['p_valor_coint']
        hurst = row['expoente_hurst']
        cruzamentos = row['num_cruzamentos']

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
    arquivo_matriz_precos = 'matriz_precos_2014_2015.csv'
    # Usamos o arquivo final, que contém a contagem de cruzamentos
    arquivo_pares = 'pares_finais_selecionados_2014_2015.csv'

    print("Carregando arquivos de dados...")
    matriz_de_precos = pd.read_csv(arquivo_matriz_precos, sep=';', decimal=',', index_col=0, parse_dates=True)
    df_pares_finais = pd.read_csv(arquivo_pares, sep=';', decimal=',')
    print("Dados carregados.")

    plotar_teste_visual_completo(matriz_de_precos, df_pares_finais, n_amostra=5)

if __name__ == "__main__":
    main()