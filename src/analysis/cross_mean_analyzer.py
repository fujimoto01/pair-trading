"""
Analisador de Cruzamento da Média

Este módulo contém a classe CrossMeanAnalyzer responsável pela análise
de frequência de cruzamento da média do spread.
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any

from ..utils.config_manager import ConfigManager
from ..utils.progress_tracker import ProgressTracker, OperationContext
from ..utils.logger import get_logger


class CrossMeanAnalyzer:
    """
    Analisador de cruzamento da média para pares de trading.
    
    Conta quantas vezes o spread cruza sua média histórica, indicando
    oportunidades de reversão à média.
    """
    
    def __init__(self, config: Optional[ConfigManager] = None):
        """
        Inicializa o analisador de cruzamento da média.
        
        Args:
            config: Gerenciador de configurações. Se None, usa configuração padrão.
        """
        self.config = config or ConfigManager()
        self.logger = get_logger(f"{__name__}.CrossMeanAnalyzer")
        self.tracker = ProgressTracker(show_progress=self.config.get('logging.show_progress', True))
    
    def count_mean_crossings(self, spread: pd.Series) -> int:
        """
        Conta o número de cruzamentos da média em uma série.
        
        Args:
            spread: Série temporal do spread
            
        Returns:
            Número de cruzamentos da média
        """
        if len(spread) < 10:
            return 0
        
        # Calcular média móvel
        mean_spread = spread.mean()
        
        # Identificar quando está acima ou abaixo da média
        above_mean = spread > mean_spread
        
        # Contar mudanças de sinal (cruzamentos)
        crossings = np.sum(above_mean.diff().fillna(False) != 0)
        
        return int(crossings)
    
    def filter_pairs_by_crossings(self, pairs_df: pd.DataFrame, 
                                price_matrix: pd.DataFrame) -> pd.DataFrame:
        """
        Filtra pares pela frequência de cruzamento da média.
        
        Args:
            pairs_df: DataFrame com pares para filtrar
            price_matrix: Matriz de preços para calcular spreads
            
        Returns:
            DataFrame com pares filtrados
        """
        if pairs_df.empty:
            return pairs_df.copy()
        
        min_crossings = self.config.get('analysis.cross_mean.min_crossings_2y', 24)
        filtered_pairs = []
        
        with OperationContext(self.tracker, "Filtrando por cruzamentos", len(pairs_df)) as tracker:
            for _, row in pairs_df.iterrows():
                ticker1 = row['Ativo_A']
                ticker2 = row['Ativo_B']
                
                try:
                    # Calcular spread
                    spread = self._calculate_spread(price_matrix, ticker1, ticker2)
                    
                    # Contar cruzamentos
                    crossings = self.count_mean_crossings(spread)
                    
                    # Filtrar por critério
                    if crossings >= min_crossings:
                        pair_data = row.to_dict()
                        pair_data['mean_crossings'] = crossings
                        filtered_pairs.append(pair_data)
                        
                        tracker.log_milestone(f"Par aprovado: {ticker1}-{ticker2} ({crossings} cruzamentos)")
                
                except Exception as e:
                    self.logger.debug(f"Erro ao calcular cruzamentos para {ticker1}-{ticker2}: {str(e)}")
                
                tracker.update(1)
        
        result_df = pd.DataFrame(filtered_pairs) if filtered_pairs else pd.DataFrame()
        
        self.logger.info(f"Filtro de cruzamentos: {len(result_df)} pares de {len(pairs_df)} "
                        f"atenderam ao critério (>= {min_crossings} cruzamentos)")
        
        return result_df
    
    def _calculate_spread(self, price_matrix: pd.DataFrame, ticker1: str, ticker2: str) -> pd.Series:
        """Calcula spread entre dois ativos."""
        log_prices1 = np.log(price_matrix[ticker1])
        log_prices2 = np.log(price_matrix[ticker2])
        return (log_prices1 - log_prices2).dropna()