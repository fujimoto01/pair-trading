import pandas as pd
import numpy as np
import statsmodels.api as sm
import time
from hurst import compute_Hc 

def aplicar_filtro_hurst_com_biblioteca(matriz_precos, df_pares_cointegrados, hurst_limite=0.5):
    """
    Usa a biblioteca 'hurst' para calcular o expoente e filtrar os pares.
    """
    print(f"Iniciando Filtro de Hurst (com biblioteca) em {len(df_pares_cointegrados)} pares...")
    
    pares_filtrados = []
    start_time = time.time()
    
    for index, row in df_pares_cointegrados.iterrows():
        ticker1 = row['Ativo_A']
        ticker2 = row['Ativo_B']
        p_valor_coint = row['p_valor_coint']
        
        # 1. Calcular o Spread (mesma lógica de antes)
        serie1 = matriz_precos[ticker1]
        serie2 = matriz_precos[ticker2]
        
        serie2_com_constante = sm.add_constant(serie2)
        modelo = sm.OLS(serie1, serie2_com_constante).fit()
        spread = modelo.resid
        
        # Se o spread tiver variância zero, pule o par
        if np.std(spread) == 0:
            continue
            
        # 2. Calcular o Expoente de Hurst usando a biblioteca
        # A função compute_Hc retorna H, c, e os dados da regressão. Só precisamos de H.
        H, _, _ = compute_Hc(spread, kind='random_walk', simplified=True)
        
        # 3. Aplicar o filtro
        if H < hurst_limite:
            pares_filtrados.append((ticker1, ticker2, p_valor_coint, H))

    print(f"\nFiltro de Hurst concluído em {time.time() - start_time:.2f} segundos.")
    
    df_resultados = pd.DataFrame(pares_filtrados, columns=['Ativo_A', 'Ativo_B', 'p_valor_coint', 'expoente_hurst'])
    df_resultados.sort_values('expoente_hurst', ascending=True, inplace=True)
    
    print(f"Resultado: {len(df_resultados)} de {len(df_pares_cointegrados)} pares passaram no filtro (H < {hurst_limite}).")
    
    return df_resultados

# --- Função de Execução (main) ---
def main():
    arquivo_matriz_precos = 'matriz_precos_2014_2015.csv'
    arquivo_pares_coint = 'pares_cointegrados_2014_2015.csv'
    arquivo_saida = 'pares_filtrados_hurst_2014_2015.csv'

    print("Carregando arquivos de dados...")
    matriz_de_precos = pd.read_csv(arquivo_matriz_precos, sep=';', decimal=',', index_col=0, parse_dates=True)
    df_pares_cointegrados = pd.read_csv(arquivo_pares_coint, sep=';', decimal=',')
    print("Dados carregados.")

    df_pares_filtrados = aplicar_filtro_hurst_com_biblioteca(matriz_de_precos, df_pares_cointegrados)

    if not df_pares_filtrados.empty:
        df_pares_filtrados.to_csv(arquivo_saida, index=False, sep=';', decimal=',')
        print(f"\nLista de pares filtrados por Hurst salva com sucesso em '{arquivo_saida}'")
        print("\nVisualização dos 10 pares com maior reversão à média (menor Hurst):")
        print(df_pares_filtrados.head(10))
    else:
        print("\nNenhum par sobreviveu ao filtro de Hurst com os critérios definidos.")

if __name__ == "__main__":
    main()