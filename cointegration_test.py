import pandas as pd
from itertools import combinations
from statsmodels.tsa.stattools import coint
import time
import os
def encontrar_pares_cointegrados(matriz_precos, p_valor_limite=0.05):
    """
    Encontra todos os pares de ativos cointegrados em uma matriz de preços.

    Args:
        matriz_precos (pd.DataFrame): DataFrame com datas no índice e tickers nas colunas.
        p_valor_limite (float): O limiar de significância para o teste de cointegração.

    Returns:
        pd.DataFrame: Um DataFrame com os pares cointegrados e seus respectivos p-valores.
    """
    n_ativos = matriz_precos.shape[1]
    total_combinacoes = n_ativos * (n_ativos - 1) // 2
    print(f"Iniciando busca por cointegração em {n_ativos} ativos ({total_combinacoes} combinações)...")

    # Lista para armazenar os resultados
    pares_encontrados = []
    
    # Obter a lista de tickers
    tickers = matriz_precos.columns

    # Iniciar contador para feedback
    contador = 0
    start_time = time.time()

    # Iterar sobre todas as combinações únicas de pares
    for par in combinations(tickers, 2):
        ticker1 = par[0]
        ticker2 = par[1]

        # Extrair as séries de preços para o par
        serie1 = matriz_precos[ticker1]
        serie2 = matriz_precos[ticker2]

        # Realizar o teste de cointegração de Engle-Granger
        score, p_valor, _ = coint(serie1, serie2)

        # Verificar se o p-valor está abaixo do nosso limiar
        if p_valor < p_valor_limite:
            pares_encontrados.append((ticker1, ticker2, p_valor))
            # print(f"  > Par encontrado: {ticker1}-{ticker2} | p-valor: {p_valor:.4f}")

        # Feedback de progresso
        contador += 1
        if contador % 500 == 0:
            tempo_passado = time.time() - start_time
            print(f"  Progresso: {contador}/{total_combinacoes} pares testados... ({tempo_passado:.2f}s)")

    print(f"\nBusca concluída em {time.time() - start_time:.2f} segundos.")
    print(f"Total de {len(pares_encontrados)} pares cointegrados encontrados (p < {p_valor_limite}).")

    # Criar um DataFrame com os resultados
    df_resultados = pd.DataFrame(pares_encontrados, columns=['Ativo_A', 'Ativo_B', 'p_valor_coint'])
    df_resultados.sort_values('p_valor_coint', ascending=True, inplace=True)

    return df_resultados

# --- Função de Execução ---
def main():
    arquivo_matriz_precos = 'matriz_precos_2014_2015.csv'
    arquivo_saida = 'pares_cointegrados_2014_2015.csv'

    # Verificar se o arquivo de entrada existe
    if not os.path.exists(arquivo_matriz_precos):
        print(f"Erro: Arquivo '{arquivo_matriz_precos}' não encontrado!")
        print("Execute o script de preparação de dados primeiro.")
        return

    # 1. Carregar a matriz de preços
    print(f"Carregando matriz de preços de '{arquivo_matriz_precos}'...")
    # index_col=0 para definir a primeira coluna (datas) como índice
    matriz_de_precos = pd.read_csv(arquivo_matriz_precos, sep=';', decimal=',', index_col=0, parse_dates=True)
    print("Matriz carregada com sucesso.")

    # 2. Encontrar os pares cointegrados
    df_pares = encontrar_pares_cointegrados(matriz_de_precos, p_valor_limite=0.05)

    # 3. Salvar o resultado
    if not df_pares.empty:
        try:
            df_pares.to_csv(arquivo_saida, index=False, sep=';', decimal=',')
            print(f"\nLista de pares cointegrados salva com sucesso em '{arquivo_saida}'")
            print("\nVisualização dos 10 pares com menor p-valor (mais fortemente cointegrados):")
            print(df_pares.head(10))
        except Exception as e:
            print(f"Ocorreu um erro ao salvar o arquivo: {e}")
    else:
        print("\nNenhum par cointegrado foi encontrado com os critérios definidos.")

if __name__ == "__main__":
    main()