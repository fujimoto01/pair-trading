import pandas as pd
import numpy as np
import statsmodels.api as sm
import time

def contar_cruzamentos_media(series):
    """
    Conta quantas vezes uma série temporal cruza sua própria média.

    Args:
        series (pd.Series): A série temporal do spread.

    Returns:
        int: O número de vezes que a série cruzou sua média.
    """
    # Calcula a média da série
    media = series.mean()
    
    # Cria uma série booleana: True se o valor está acima da média, False caso contrário
    acima_da_media = series > media
    
    # Compara a série booleana com sua versão defasada em 1 período.
    # Um cruzamento ocorre onde o valor de hoje é diferente do de ontem.
    cruzamentos = (acima_da_media != acima_da_media.shift(1)).sum()
    
    return cruzamentos

def aplicar_filtro_frequencia(matriz_precos, df_pares_filtrados, min_cruzamentos=24):
    """
    Aplica o filtro de frequência de cruzamento da média aos pares.
    """
    print(f"Iniciando Filtro de Frequência para {len(df_pares_filtrados)} pares...")
    
    resultados_finais = []
    start_time = time.time()
    
    for index, row in df_pares_filtrados.iterrows():
        ticker1 = row['Ativo_A']
        ticker2 = row['Ativo_B']
        p_valor_coint = row['p_valor_coint']
        hurst = row['expoente_hurst']
        
        # 1. Calcular o Spread
        serie1 = matriz_precos[ticker1]
        serie2 = matriz_precos[ticker2]
        serie2_com_constante = sm.add_constant(serie2)
        modelo = sm.OLS(serie1, serie2_com_constante).fit()
        spread = modelo.resid
        
        # 2. Contar os cruzamentos da média
        num_cruzamentos = contar_cruzamentos_media(spread)
        
        # 3. Aplicar o filtro
        if num_cruzamentos >= min_cruzamentos:
            resultados_finais.append((ticker1, ticker2, p_valor_coint, hurst, num_cruzamentos))

    print(f"\nFiltro de Frequência concluído em {time.time() - start_time:.2f} segundos.")
    
    df_resultados = pd.DataFrame(resultados_finais, columns=['Ativo_A', 'Ativo_B', 'p_valor_coint', 'expoente_hurst', 'num_cruzamentos'])
    # Ordenar pelo número de cruzamentos, do maior para o menor
    df_resultados.sort_values('num_cruzamentos', ascending=False, inplace=True)
    
    print(f"Resultado: {len(df_resultados)} de {len(df_pares_filtrados)} pares passaram no filtro (>= {min_cruzamentos} cruzamentos).")
    
    return df_resultados

# --- Função de Execução ---
def main():
    arquivo_matriz_precos = 'matriz_precos_2014_2015.csv'
    arquivo_pares_hurst = 'pares_filtrados_hurst_2014_2015.csv'
    arquivo_saida = 'pares_finais_selecionados_2014_2015.csv'

    print("Carregando arquivos de dados...")
    matriz_de_precos = pd.read_csv(arquivo_matriz_precos, sep=';', decimal=',', index_col=0, parse_dates=True)
    df_pares_filtrados = pd.read_csv(arquivo_pares_hurst, sep=';', decimal=',')
    print("Dados carregados.")

    df_final = aplicar_filtro_frequencia(matriz_de_precos, df_pares_filtrados)

    df_final.to_csv(arquivo_saida, index=False, sep=';', decimal=',')
    print(f"\nLista final de pares selecionados salva com sucesso em '{arquivo_saida}'")
    print("\nVisualização dos 15 pares com maior frequência de cruzamento:")
    print(df_final.head(15))


if __name__ == "__main__":
    main()