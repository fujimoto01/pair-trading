import pandas as pd
import os

def ranquear_pares_finais(arquivo_pares, arquivo_saida):
    """
    Carrega a lista final de pares e calcula um score combinado para ranqueá-los.

    Args:
        arquivo_pares (str): Caminho para o arquivo CSV com os pares selecionados.
        arquivo_saida (str): Caminho para salvar o arquivo CSV final e ranqueado.
    """
    # Verificar se o arquivo de entrada existe
    if not os.path.exists(arquivo_pares):
        print(f"Erro: Arquivo '{arquivo_pares}' não encontrado!")
        return

    print(f"Carregando a lista de pares de '{arquivo_pares}'...")
    df = pd.read_csv(arquivo_pares, sep=';', decimal=',')
    print(f"{len(df)} pares carregados.")

    print("Iniciando o processo de ranking...")

    # 1. Criar o Rank de Cointegração (quanto menor o p-valor, melhor)
    df['rank_p_valor'] = df['p_valor_coint'].rank(method='first', ascending=True)

    # 2. Criar o Rank de Hurst (quanto menor o expoente, melhor)
    df['rank_hurst'] = df['expoente_hurst'].rank(method='first', ascending=True)

    # 3. Criar o Rank de Frequência (quanto maior o número de cruzamentos, melhor)
    df['rank_cruzamentos'] = df['num_cruzamentos'].rank(method='first', ascending=False)

    # 4. Calcular o Score Final (soma dos ranks)
    df['Score_Final'] = df['rank_p_valor'] + df['rank_hurst'] + df['rank_cruzamentos']

    # Ordenar o DataFrame pelo Score Final (quanto menor o score, melhor o par)
    df_ranqueado = df.sort_values('Score_Final', ascending=True)

    print("Ranking concluído.")
    
    # Salvar o resultado
    try:
        df_ranqueado.to_csv(arquivo_saida, index=False, sep=';', decimal=',')
        print(f"\nLista final de pares ranqueados salva com sucesso em '{arquivo_saida}'")
        print("\n--- TOP 20 MELHORES PARES SEGUNDO O SCORE COMBINADO ---")
        
        # Selecionar colunas para uma visualização mais limpa
        colunas_display = [
            'Ativo_A', 'Ativo_B', 'Score_Final', 'p_valor_coint', 
            'expoente_hurst', 'num_cruzamentos'
        ]
        print(df_ranqueado[colunas_display].head(20).to_string(index=False))

    except Exception as e:
        print(f"Ocorreu um erro ao salvar o arquivo: {e}")

# --- Função de Execução ---
def main():
    arquivo_pares_selecionados = 'pares_finais_selecionados_2014_2015.csv'
    arquivo_ranqueado_saida = 'pares_ranqueados_final_2014_2015.csv'
    
    ranquear_pares_finais(arquivo_pares_selecionados, arquivo_ranqueado_saida)

if __name__ == "__main__":
    main()