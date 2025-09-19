"""
Analisador de Cointegração

Este módulo contém a classe CointegrationAnalyzer responsável pelos
testes de cointegração entre pares de ações.
"""

import pandas as pd
import numpy as np
from itertools import combinations
from statsmodels.tsa.stattools import coint
import time
import os
from typing import List, Tuple, Optional, Dict, Any

from ..utils.config_manager import ConfigManager
from ..utils.progress_tracker import ProgressTracker, OperationContext
from ..utils.logger import get_logger


class CointegrationAnalyzer:
    """
    Analisador de cointegração para pares de ações.
    
    Esta classe implementa testes de cointegração de Engle-Granger para
    identificar pares de ações que se movem juntas no longo prazo.
    """
    
    def __init__(self, config: Optional[ConfigManager] = None):
        """
        Inicializa o analisador de cointegração.
        
        Args:
            config: Gerenciador de configurações. Se None, usa configuração padrão.
        """
        self.config = config or ConfigManager()
        self.logger = get_logger(f"{__name__}.CointegrationAnalyzer")
        self.tracker = ProgressTracker(show_progress=self.config.get('logging.show_progress', True))
        
        # Cache para resultados
        self._cointegrated_pairs: Optional[pd.DataFrame] = None
        
    def test_pair_cointegration(self, series1: pd.Series, series2: pd.Series) -> Tuple[float, float, float]:
        """
        Testa cointegração entre duas séries temporais.
        
        Args:
            series1: Primeira série de preços
            series2: Segunda série de preços
            
        Returns:
            Tuple com (score, p_valor, valor_critico)
            
        Raises:
            ValueError: Se séries são inválidas
        """
        # Validar séries
        if len(series1) != len(series2):
            raise ValueError("Séries devem ter o mesmo comprimento")
        
        if len(series1) < 30:
            raise ValueError("Séries muito curtas para teste de cointegração")
        
        # Remover NaNs alinhados
        valid_data = pd.DataFrame({'s1': series1, 's2': series2}).dropna()
        
        if len(valid_data) < 30:
            raise ValueError("Dados insuficientes após remoção de NaNs")
        
        try:
            # Teste de cointegração de Engle-Granger
            score, p_valor, valores_criticos = coint(valid_data['s1'], valid_data['s2'])
            
            # Valor crítico para 5% (índice 1)
            valor_critico = valores_criticos[1] if len(valores_criticos) > 1 else valores_criticos[0]
            
            return score, p_valor, valor_critico
            
        except Exception as e:
            self.logger.debug(f"Erro no teste de cointegração: {str(e)}")
            # Retornar valores indicando não cointegração
            return 0.0, 1.0, 0.0
    
    def find_cointegrated_pairs(self, price_matrix: pd.DataFrame, 
                              p_value_threshold: Optional[float] = None) -> pd.DataFrame:
        """
        Encontra todos os pares cointegrados em uma matriz de preços.
        
        Args:
            price_matrix: DataFrame com preços (datas x tickers)
            p_value_threshold: Limiar de p-valor. Se None, usa configuração.
            
        Returns:
            DataFrame com pares cointegrados e seus p-valores
            
        Raises:
            ValueError: Se matriz é inválida
        """
        if price_matrix.empty:
            raise ValueError("Matriz de preços está vazia")
        
        if price_matrix.shape[1] < 2:
            raise ValueError("Matriz deve ter pelo menos 2 ativos para análise de pares")
        
        # Buscar configurações
        if p_value_threshold is None:
            p_value_threshold = self.config.get('analysis.cointegration.significance_level', 0.05)
        
        n_ativos = price_matrix.shape[1]
        total_combinacoes = n_ativos * (n_ativos - 1) // 2
        
        self.logger.info(f"Iniciando busca por cointegração em {n_ativos} ativos "
                        f"({total_combinacoes} combinações)")
        
        pares_encontrados = []
        tickers = price_matrix.columns.tolist()
        
        with OperationContext(self.tracker, "Testando cointegração", total_combinacoes) as tracker:
            contador = 0
            
            for par in combinations(tickers, 2):
                ticker1, ticker2 = par
                
                try:
                    # Extrair séries de preços
                    serie1 = price_matrix[ticker1]
                    serie2 = price_matrix[ticker2]
                    
                    # Realizar teste de cointegração
                    score, p_valor, valor_critico = self.test_pair_cointegration(serie1, serie2)
                    
                    # Verificar se é significativo
                    if p_valor < p_value_threshold:
                        pares_encontrados.append({
                            'Ativo_A': ticker1,
                            'Ativo_B': ticker2,
                            'p_valor_coint': p_valor,
                            'score_coint': score,
                            'valor_critico': valor_critico
                        })
                        
                        tracker.log_milestone(f"Par cointegrado: {ticker1}-{ticker2} (p={p_valor:.4f})")
                    
                except Exception as e:
                    self.logger.debug(f"Erro ao testar par {ticker1}-{ticker2}: {str(e)}")
                
                contador += 1
                tracker.update(1)
                
                # Feedback periódico
                if contador % 500 == 0:
                    tracker.log_milestone(f"Progresso: {contador}/{total_combinacoes} pares testados")
        
        self.logger.info(f"Busca concluída. {len(pares_encontrados)} pares cointegrados encontrados "
                        f"(p < {p_value_threshold})")
        
        # Criar DataFrame com resultados
        if pares_encontrados:
            df_resultados = pd.DataFrame(pares_encontrados)
            # Ordenar por p-valor (mais significativos primeiro)
            df_resultados = df_resultados.sort_values('p_valor_coint', ascending=True).reset_index(drop=True)
        else:
            # DataFrame vazio com colunas corretas
            df_resultados = pd.DataFrame(columns=['Ativo_A', 'Ativo_B', 'p_valor_coint', 
                                                'score_coint', 'valor_critico'])
        
        # Cache resultado
        self._cointegrated_pairs = df_resultados
        
        return df_resultados
    
    def load_price_matrix(self, file_path: str) -> pd.DataFrame:
        """
        Carrega matriz de preços de arquivo CSV.
        
        Args:
            file_path: Caminho para arquivo com matriz de preços
            
        Returns:
            DataFrame com matriz de preços
            
        Raises:
            FileNotFoundError: Se arquivo não existe
            ValueError: Se arquivo é inválido
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        
        try:
            # Configurações de entrada
            separator = self.config.get('data.output.separator', ';')
            decimal = self.config.get('data.output.decimal', ',')
            
            # Carregar com primeira coluna como índice (datas)
            price_matrix = pd.read_csv(
                file_path, sep=separator, decimal=decimal, 
                index_col=0, parse_dates=True
            )
            
            self.logger.info(f"Matriz de preços carregada: {price_matrix.shape[0]} dias x "
                           f"{price_matrix.shape[1]} ativos")
            
            return price_matrix
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar matriz de preços: {str(e)}")
            raise ValueError(f"Arquivo inválido: {str(e)}")
    
    def save_cointegrated_pairs(self, pairs_df: pd.DataFrame, output_file: str) -> str:
        """
        Salva lista de pares cointegrados em arquivo.
        
        Args:
            pairs_df: DataFrame com pares cointegrados
            output_file: Nome do arquivo de saída
            
        Returns:
            Caminho completo do arquivo salvo
        """
        if pairs_df.empty:
            self.logger.warning("Nenhum par cointegrado para salvar")
            return ""
        
        # Configurações de saída
        separator = self.config.get('data.output.separator', ';')
        decimal = self.config.get('data.output.decimal', ',')
        encoding = self.config.get('data.output.encoding_out', 'utf-8-sig')
        
        output_path = self.config.get_output_path(output_file, 'cointegration')
        
        try:
            pairs_df.to_csv(output_path, index=False, sep=separator, 
                          decimal=decimal, encoding=encoding)
            
            self.logger.info(f"Pares cointegrados salvos em: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar pares cointegrados: {str(e)}")
            raise
    
    def analyze_cointegration_results(self, pairs_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analisa resultados de cointegração e gera estatísticas.
        
        Args:
            pairs_df: DataFrame com pares cointegrados
            
        Returns:
            Dicionário com estatísticas dos resultados
        """
        if pairs_df.empty:
            return {
                'total_pairs': 0,
                'mean_p_value': None,
                'median_p_value': None,
                'min_p_value': None,
                'max_p_value': None,
                'most_frequent_stocks': {},
                'strongest_pairs': []
            }
        
        # Estatísticas básicas
        stats = {
            'total_pairs': len(pairs_df),
            'mean_p_value': pairs_df['p_valor_coint'].mean(),
            'median_p_value': pairs_df['p_valor_coint'].median(),
            'min_p_value': pairs_df['p_valor_coint'].min(),
            'max_p_value': pairs_df['p_valor_coint'].max()
        }
        
        # Ações mais frequentes
        all_stocks = list(pairs_df['Ativo_A']) + list(pairs_df['Ativo_B'])
        stock_counts = pd.Series(all_stocks).value_counts()
        stats['most_frequent_stocks'] = stock_counts.head(10).to_dict()
        
        # Pares mais fortes (menor p-valor)
        strongest = pairs_df.head(10)[['Ativo_A', 'Ativo_B', 'p_valor_coint']].to_dict('records')
        stats['strongest_pairs'] = strongest
        
        # Log das estatísticas
        self.logger.info("Análise dos resultados de cointegração:")
        self.logger.info(f"  - Total de pares: {stats['total_pairs']}")
        self.logger.info(f"  - P-valor médio: {stats['mean_p_value']:.4f}")
        self.logger.info(f"  - P-valor mínimo: {stats['min_p_value']:.6f}")
        
        self.logger.info("Top 5 ações mais frequentes:")
        for stock, count in list(stats['most_frequent_stocks'].items())[:5]:
            self.logger.info(f"  - {stock}: {count} pares")
        
        self.logger.info("Top 5 pares mais fortes:")
        for i, pair in enumerate(stats['strongest_pairs'][:5], 1):
            self.logger.info(f"  {i}. {pair['Ativo_A']}-{pair['Ativo_B']}: p={pair['p_valor_coint']:.6f}")
        
        return stats
    
    def execute_full_analysis(self, price_matrix_file: Optional[str] = None) -> pd.DataFrame:
        """
        Executa análise completa de cointegração.
        
        Args:
            price_matrix_file: Arquivo com matriz de preços. Se None, usa padrão.
            
        Returns:
            DataFrame com pares cointegrados
        """
        # Definir arquivo padrão se necessário
        if price_matrix_file is None:
            years = self.config.get('data.years', [])
            periodo_str = "_".join(map(str, years))
            price_matrix_file = f'matriz_precos_{periodo_str}.csv'
        
        # Carregar matriz de preços
        price_matrix = self.load_price_matrix(price_matrix_file)
        
        # Encontrar pares cointegrados
        pairs_df = self.find_cointegrated_pairs(price_matrix)
        
        # Analisar resultados
        self.analyze_cointegration_results(pairs_df)
        
        # Salvar resultados
        if not pairs_df.empty:
            years = self.config.get('data.years', [])
            periodo_str = "_".join(map(str, years))
            output_file = f'pares_cointegrados_{periodo_str}.csv'
            self.save_cointegrated_pairs(pairs_df, output_file)
            
            # Mostrar preview dos resultados
            self.logger.info("\nPreview dos 10 pares com menor p-valor:")
            preview = pairs_df.head(10)[['Ativo_A', 'Ativo_B', 'p_valor_coint']]
            for _, row in preview.iterrows():
                self.logger.info(f"  {row['Ativo_A']}-{row['Ativo_B']}: p={row['p_valor_coint']:.6f}")
        
        else:
            self.logger.warning("Nenhum par cointegrado encontrado com os critérios atuais")
        
        return pairs_df
    
    def get_spread(self, price_matrix: pd.DataFrame, ticker1: str, ticker2: str) -> pd.Series:
        """
        Calcula o spread entre dois ativos.
        
        Args:
            price_matrix: DataFrame com preços
            ticker1: Primeiro ativo
            ticker2: Segundo ativo
            
        Returns:
            Série temporal com o spread
            
        Raises:
            ValueError: Se tickers não existem na matriz
        """
        if ticker1 not in price_matrix.columns:
            raise ValueError(f"Ticker {ticker1} não encontrado na matriz")
        
        if ticker2 not in price_matrix.columns:
            raise ValueError(f"Ticker {ticker2} não encontrado na matriz")
        
        # Calcular spread simples (log dos preços)
        log_prices1 = np.log(price_matrix[ticker1])
        log_prices2 = np.log(price_matrix[ticker2])
        
        spread = log_prices1 - log_prices2
        
        return spread.dropna()
    
    def get_cached_pairs(self) -> Optional[pd.DataFrame]:
        """
        Retorna pares cointegrados em cache.
        
        Returns:
            DataFrame com pares ou None se não há cache
        """
        return self._cointegrated_pairs
    
    def clear_cache(self) -> None:
        """Limpa cache de pares cointegrados."""
        self._cointegrated_pairs = None
        self.logger.debug("Cache de pares cointegrados limpo")