import pandas as pd
import numpy as np
from datetime import datetime
import re

def parse_cotahist_line(line):
    """
    Parse uma linha do arquivo COTAHIST formato fixo
    Retorna dicionário com os campos principais
    """
    if len(line) < 245:
        return None
    
    return {
        'tipo_registro': line[0:2],
        'data': line[2:10],
        'codigo_bdi': line[10:12],
        'codigo_negociacao': line[12:24].strip(),
        'tipo_mercado': line[24:27],
        'nome_resumido': line[27:39].strip(),
        'especificacao_papel': line[39:49].strip(),
        'prazo_dias': line[49:52],
        'moeda_referencia': line[52:56].strip(),
        'preco_abertura': int(line[56:69]) / 100.0,
        'preco_maximo': int(line[69:82]) / 100.0,
        'preco_minimo': int(line[82:95]) / 100.0,
        'preco_medio': int(line[95:108]) / 100.0,
        'preco_ultimo': int(line[108:121]) / 100.0,
        'preco_melhor_compra': int(line[121:134]) / 100.0,
        'preco_melhor_venda': int(line[134:147]) / 100.0,
        'numero_negocios': int(line[147:152]),
        'quantidade_titulos': int(line[152:170]),
        'volume_financeiro': int(line[170:188]) / 100.0
    }

def is_valid_stock(codigo_negociacao, codigo_bdi, especificacao_papel):
    """
    Verifica se é uma ação válida (não ETF, não units, não outros tipos)
    """
    codigo = codigo_negociacao.strip()
    
    # Deve ser BDI 02 (ações ordinárias e preferenciais)
    if codigo_bdi != '02':
        return False
    
    # Excluir ETFs (geralmente terminam com 11)
    if codigo.endswith('11'):
        return False
    
    # Excluir Units (geralmente terminam com 11, mas já coberto acima)
    # Excluir BDRs (geralmente começam com certas letras)
    if any(codigo.startswith(prefix) for prefix in ['AAPL', 'MSFT', 'GOOGL', 'AMZO']):
        return False
    
    # Excluir códigos muito curtos ou muito longos
    if len(codigo) < 4 or len(codigo) > 6:
        return False
    
    # Padrão típico de ações: 4 letras + 1 número ou 5 letras + 1 número
    if not re.match(r'^[A-Z]{4}[34568]$|^[A-Z]{5}[34568]$', codigo):
        return False
    
    return True

def calculate_liquidity_metrics(df_stock):
    """
    Calcula métricas de liquidez para uma ação específica
    """
    # Filtrar apenas dias com negociação
    df_traded = df_stock[df_stock['volume_financeiro'] > 0].copy()
    
    if len(df_traded) == 0:
        return None
    
    # Calcular métricas básicas
    volume_medio_diario = df_traded['volume_financeiro'].mean()
    negocios_medio_diario = df_traded['numero_negocios'].mean()
    
    # Frequência de negociação (assumindo ~504 dias úteis em 2 anos: 2014-2015)
    dias_uteis_periodo = 504  # Aproximação para 2 anos
    frequencia_negociacao = len(df_traded) / dias_uteis_periodo
    
    # Volume total no período
    volume_total_periodo = df_traded['volume_financeiro'].sum()
    
    # Quantidade média de títulos por negócio (indicador de tamanho médio das ordens)
    if df_traded['numero_negocios'].sum() > 0:
        titulos_por_negocio = df_traded['quantidade_titulos'].sum() / df_traded['numero_negocios'].sum()
    else:
        titulos_por_negocio = 0
    
    return {
        'volume_medio_diario': volume_medio_diario,
        'negocios_medio_diario': negocios_medio_diario,
        'frequencia_negociacao': frequencia_negociacao,
        'volume_total_periodo': volume_total_periodo,
        'dias_negociados': len(df_traded),
        'titulos_por_negocio': titulos_por_negocio
    }

def calculate_liquidity_score(metrics):
    """
    Calcula score de liquidez combinando múltiplas métricas
    """
    # Pesos para cada métrica (ajustáveis conforme necessidade)
    peso_volume = 0.4
    peso_negocios = 0.3
    peso_frequencia = 0.2
    peso_consistencia = 0.1
    
    # Normalização será feita depois no ranking
    volume_score = metrics['volume_medio_diario']
    negocios_score = metrics['negocios_medio_diario'] 
    frequencia_score = metrics['frequencia_negociacao']
    consistencia_score = min(metrics['dias_negociados'] / 504, 1.0)  # Máximo 1.0 (baseado em 2 anos ~504 dias úteis)
    
    # Score bruto (será normalizado depois)
    score = (peso_volume * volume_score + 
             peso_negocios * negocios_score + 
             peso_frequencia * frequencia_score * 1000000 +  # Ajuste de escala
             peso_consistencia * consistencia_score * 1000000)  # Ajuste de escala
    
    return score

def analyze_cotahist_liquidity(file_paths):
    """
    Função principal para analisar liquidez dos arquivos COTAHIST
    """
    print("Iniciando análise dos arquivos COTAHIST...")
    
    # Lista para armazenar dados
    data_list = []
    
    # Processar cada arquivo
    for file_path in file_paths:
        print(f"Processando arquivo: {file_path}...")
        
        # Ler arquivo linha por linha
        with open(file_path, 'r', encoding='latin-1') as file:
            for line_num, line in enumerate(file, 1):
                if line_num % 100000 == 0:
                    print(f"Processadas {line_num} linhas do arquivo {file_path}...")
            
                # Parse da linha
                parsed_data = parse_cotahist_line(line.strip())
                
                # Pular se não conseguiu fazer parse ou não é registro de cotação
                if not parsed_data or parsed_data['tipo_registro'] != '01':
                    continue
                
                # Filtrar apenas mercado à vista
                if parsed_data['tipo_mercado'] != '010':
                    continue
                
                # Verificar se é ação válida
                if not is_valid_stock(parsed_data['codigo_negociacao'], 
                                    parsed_data['codigo_bdi'],
                                    parsed_data['especificacao_papel']):
                    continue
                
                # Filtros de qualidade
                if (parsed_data['volume_financeiro'] <= 0 or 
                    parsed_data['preco_ultimo'] <= 0):
                    continue
                
                data_list.append(parsed_data)
    
    print(f"Total de registros válidos: {len(data_list)}")
    
    # Converter para DataFrame
    df = pd.DataFrame(data_list)
    
    # Agrupar por código de negociação e calcular métricas
    print("Calculando métricas de liquidez...")
    
    liquidity_results = []
    
    for codigo in df['codigo_negociacao'].unique():
        df_stock = df[df['codigo_negociacao'] == codigo]
        
        # Calcular métricas
        metrics = calculate_liquidity_metrics(df_stock)
        
        if metrics is None:
            continue
        
        # Filtros mínimos de liquidez (ajustados para período de 2 anos)
        if (metrics['volume_medio_diario'] < 500000 or  # R$ 500k/dia mínimo
            metrics['frequencia_negociacao'] < 0.8 or   # 80% dos dias mínimo
            metrics['dias_negociados'] < 100):          # 100 dias mínimo
            continue
        
        # Calcular score
        score = calculate_liquidity_score(metrics)
        
        # Informações adicionais da ação
        sample_row = df_stock.iloc[0]
        
        result = {
            'ticker': codigo,
            'nome_resumido': sample_row['nome_resumido'],
            'volume_medio_diario': metrics['volume_medio_diario'],
            'negocios_medio_diario': metrics['negocios_medio_diario'],
            'frequencia_negociacao': metrics['frequencia_negociacao'],
            'volume_total_periodo': metrics['volume_total_periodo'],
            'dias_negociados': metrics['dias_negociados'],
            'score_liquidez': score
        }
        
        liquidity_results.append(result)
    
    # Converter para DataFrame e ordenar por score
    df_liquidity = pd.DataFrame(liquidity_results)
    df_liquidity = df_liquidity.sort_values('score_liquidez', ascending=False).reset_index(drop=True)
    
    print(f"Total de ações analisadas: {len(df_liquidity)}")
    
    # Pegar top 100
    top_100 = df_liquidity.head(100).copy()
    top_100['ranking'] = range(1, len(top_100) + 1)
    
    return top_100

# Função para executar a análise
def main():
    # Lista de arquivos para análise (2014 e 2015)
    file_paths = ['COTAHIST_A2014.TXT', 'COTAHIST_A2015.TXT']
    periodo_str = "2014_2015"
    
    try:
        # Verificar se todos os arquivos existem
        import os
        for file_path in file_paths:
            if not os.path.exists(file_path):
                print(f"Erro: Arquivo '{file_path}' não encontrado.")
                print("Certifique-se de que todos os arquivos COTAHIST estão no mesmo diretório do script.")
                return
        
        # Executar análise
        result_df = analyze_cotahist_liquidity(file_paths)
        
        # Salvar resultado completo
        result_df.to_csv(f'top_100_acoes_liquidas_{periodo_str}_completo.csv', 
                        index=False, sep=';', decimal=',', encoding='utf-8-sig')
        
        # Salvar apenas lista de tickers
        tickers_only = result_df[['ranking', 'ticker']].copy()
        tickers_only.to_csv(f'top_100_acoes_liquidas_{periodo_str}_tickers.txt', 
                           index=False, header=['Ranking', 'Ticker'], sep='\t')
        
        # Exibir resultado
        print(f"\n=== TOP 20 AÇÕES MAIS LÍQUIDAS {periodo_str.replace('_', '-')} ===")
        print(result_df[['ranking', 'ticker', 'nome_resumido', 'volume_medio_diario', 
                        'frequencia_negociacao']].head(20).to_string(index=False))
        
        print(f"\nArquivos salvos:")
        print(f"- top_100_acoes_liquidas_{periodo_str}_completo.csv (dados completos)")
        print(f"- top_100_acoes_liquidas_{periodo_str}_tickers.txt (apenas tickers)")
        
    except FileNotFoundError as e:
        print(f"Erro: {str(e)}")
        print("Certifique-se de que todos os arquivos COTAHIST estão no mesmo diretório do script.")
    except Exception as e:
        print(f"Erro durante a execução: {str(e)}")

if __name__ == "__main__":
    main()