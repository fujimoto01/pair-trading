import pandas as pd
import os

def criar_matriz_de_precos(lista_tickers, caminhos_cotahist):
    """
    Cria uma matriz de preços de fechamento a partir dos arquivos COTAHIST
    para uma lista específica de tickers.
    """
    colunas = [
        ('TIPO_REGISTRO', 1, 2), ('DATA_PREGAO', 3, 10), ('COD_BDI', 11, 12),
        ('CODIGO_NEGOCIACAO', 13, 24), ('TIPO_MERCADO', 25, 27),
        ('PRECO_FECHAMENTO', 109, 121)
    ]
    col_names = [c[0] for c in colunas]
    col_specs = [(c[1]-1, c[2]) for c in colunas]

    dfs_anuais = []

    print("Iniciando processamento dos arquivos COTAHIST...")
    for caminho in caminhos_cotahist:
        print(f"Lendo o arquivo: {os.path.basename(caminho)}...")
        df_ano = pd.read_fwf(
            caminho, colspecs=col_specs, names=col_names,
            header=None, skiprows=1, skipfooter=1, encoding='latin-1'
        )
        dfs_anuais.append(df_ano)

    df_total = pd.concat(dfs_anuais, ignore_index=True)
    print("Arquivos concatenados.")

    print("Iniciando filtragem e limpeza dos dados...")
    df_total = df_total[df_total['TIPO_REGISTRO'] == 1].copy()
    df_total['COD_BDI'] = df_total['COD_BDI'].astype(str).str.zfill(2)
    df_total = df_total[df_total['COD_BDI'] == '02']
    df_total = df_total[df_total['TIPO_MERCADO'] == 10]
    df_total['CODIGO_NEGOCIACAO'] = df_total['CODIGO_NEGOCIACAO'].str.strip()
    df_total['DATA_PREGAO'] = pd.to_datetime(df_total['DATA_PREGAO'], format='%Y%m%d')
    df_total['PRECO_FECHAMENTO'] = pd.to_numeric(df_total['PRECO_FECHAMENTO'], errors='coerce') / 100
    df_total.dropna(subset=['PRECO_FECHAMENTO'], inplace=True)
    df_filtrado = df_total[df_total['CODIGO_NEGOCIACAO'].isin(lista_tickers)].copy()
    print(f"Dados filtrados. Restaram {len(df_filtrado)} registros.")
    
    print("Criando a matriz de preços...")
    matriz_precos = df_filtrado.pivot_table(
        index='DATA_PREGAO',
        columns='CODIGO_NEGOCIACAO',
        values='PRECO_FECHAMENTO'
    )
    print("Matriz de preços criada com sucesso.")
    
    # --- CORREÇÃO APLICADA AQUI ---
    # Usamos ffill() (forward fill) para preencher com o último preço válido.
    matriz_precos.ffill(inplace=True)
    # E bfill() (backward fill) para preencher os NaNs que possam ter sobrado no início.
    matriz_precos.bfill(inplace=True)
    # -----------------------------

    return matriz_precos

# --- A função main() permanece a mesma ---
def main():
    arquivo_tickers = 'top_100_acoes_liquidas_2014_2015_completo.csv'
    arquivos_cotahist = ['COTAHIST_A2014.TXT', 'COTAHIST_A2015.TXT']
    arquivo_saida = 'matriz_precos_2014_2015.csv'

    if not os.path.exists(arquivo_tickers):
        print(f"Erro: Arquivo de tickers '{arquivo_tickers}' não encontrado!")
        return
    for f in arquivos_cotahist:
        if not os.path.exists(f):
            print(f"Erro: Arquivo COTAHIST '{f}' não encontrado!")
            return

    df_top100 = pd.read_csv(arquivo_tickers, sep=';')
    lista_de_tickers = df_top100['ticker'].tolist()
    print(f"{len(lista_de_tickers)} tickers carregados com sucesso.")

    matriz_de_precos = criar_matriz_de_precos(lista_de_tickers, arquivos_cotahist)

    try:
        matriz_de_precos.to_csv(arquivo_saida, sep=';', decimal=',')
        print(f"\nMatriz de preços salva com sucesso em '{arquivo_saida}'")
        print(f"Dimensões da matriz: {matriz_de_precos.shape[0]} dias x {matriz_de_precos.shape[1]} ativos.")
        print("\nVisualização das 5 primeiras linhas da matriz:")
        print(matriz_de_precos.head())
    except Exception as e:
        print(f"Ocorreu um erro ao salvar a matriz de preços: {e}")


if __name__ == "__main__":
    main()