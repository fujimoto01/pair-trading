"""
Analisador de Expoente de Hurst

Este módulo contém a classe HurstAnalyzer responsável pelo cálculo
do expoente de Hurst para análise de reversão à média.
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List
from scipy import stats

from ..utils.config_manager import ConfigManager
from ..utils.progress_tracker import ProgressTracker, OperationContext
from ..utils.logger import get_logger


class HurstAnalyzer:
    """
    Analisador de expoente de Hurst para identificar séries com reversão à média.
    
    O expoente de Hurst indica se uma série temporal tem tendência de persistência
    (Hurst > 0.5) ou reversão à média (Hurst < 0.5).
    """
    
    def __init__(self, config: Optional[ConfigManager] = None):
        """
        Inicializa o analisador de Hurst.
        
        Args:
            config: Gerenciador de configurações. Se None, usa configuração padrão.
        """
        self.config = config or ConfigManager()
        self.logger = get_logger(f"{__name__}.HurstAnalyzer")
        self.tracker = ProgressTracker(show_progress=self.config.get('logging.show_progress', True))
        
    def calculate_hurst_exponent(self, series: pd.Series, method: str = "rs") -> float:
        """
        Calcula o expoente de Hurst para uma série temporal.
        
        Args:
            series: Série temporal para análise
            method: Método de cálculo ("rs" para Rescaled Range)
            
        Returns:
            Valor do expoente de Hurst
        """
        # Implementação básica do método R/S (Rescaled Range)
        series_clean = series.dropna()
        
        if len(series_clean) < 50:
            return 0.5  # Valor neutro para séries muito curtas
        
        # Converter para numpy array
        data = series_clean.values
        n = len(data)
        
        # Calcular diferenças
        diffs = np.diff(data)
        
        # Remover média
        mean_diff = np.mean(diffs)
        diffs_centered = diffs - mean_diff
        
        # Calcular soma cumulativa
        cumsum = np.cumsum(diffs_centered)
        
        # Calcular range
        R = np.max(cumsum) - np.min(cumsum)
        
        # Calcular desvio padrão
        S = np.std(diffs)
        
        if S == 0:
            return 0.5
        
        # Calcular R/S
        rs = R / S
        
        if rs <= 0:
            return 0.5
        
        # Estimar Hurst usando método simplificado
        # H ≈ log(R/S) / log(n)
        hurst = np.log(rs) / np.log(n)
        
        # Limitar entre 0 e 1
        return max(0, min(1, hurst))
    
    def filter_pairs_by_hurst(self, pairs_df: pd.DataFrame, 
                            price_matrix: pd.DataFrame) -> pd.DataFrame:
        """
        Filtra pares cointegrados pelo expoente de Hurst do spread.
        
        Args:
            pairs_df: DataFrame com pares cointegrados
            price_matrix: Matriz de preços para calcular spreads
            
        Returns:
            DataFrame com pares filtrados pelo critério de Hurst
        """
        if pairs_df.empty:
            return pairs_df.copy()
        
        max_hurst = self.config.get('analysis.hurst.max_hurst_exponent', 0.5)
        filtered_pairs = []
        
        with OperationContext(self.tracker, "Filtrando por Hurst", len(pairs_df)) as tracker:
            for _, row in pairs_df.iterrows():
                ticker1 = row['Ativo_A']
                ticker2 = row['Ativo_B']
                
                try:
                    # Calcular spread
                    spread = self._calculate_spread(price_matrix, ticker1, ticker2)
                    
                    # Calcular Hurst
                    hurst = self.calculate_hurst_exponent(spread)
                    
                    # Filtrar por critério
                    if hurst < max_hurst:
                        pair_data = row.to_dict()
                        pair_data['hurst_exponent'] = hurst
                        filtered_pairs.append(pair_data)
                        
                        tracker.log_milestone(f"Par aprovado: {ticker1}-{ticker2} (H={hurst:.3f})")
                
                except Exception as e:
                    self.logger.debug(f"Erro ao calcular Hurst para {ticker1}-{ticker2}: {str(e)}")
                
                tracker.update(1)
        
        result_df = pd.DataFrame(filtered_pairs) if filtered_pairs else pd.DataFrame()
        
        self.logger.info(f"Filtro de Hurst: {len(result_df)} pares de {len(pairs_df)} "
                        f"atenderam ao critério (H < {max_hurst})")
        
        return result_df
    
    def _calculate_spread(self, price_matrix: pd.DataFrame, ticker1: str, ticker2: str) -> pd.Series:
        """Calcula spread entre dois ativos."""
        log_prices1 = np.log(price_matrix[ticker1])
        log_prices2 = np.log(price_matrix[ticker2])
        return (log_prices1 - log_prices2).dropna()