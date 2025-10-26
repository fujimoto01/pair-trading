"""
Analisador de Tail Dependence

Este módulo calcula coeficientes empíricos de tail dependence (cauda inferior e superior)
entre retornos de dois ativos, conforme a definição baseada em quantis condicionais.

Referência conceitual:
- Daniel Bergmann; Mauri Aparecido de Oliveira.
  "Tail Dependence Accelerates Mean Reversion in Pairs Trading: Evidence from Brazil".

Implementação:
- Estimador empírico usando quantis u_low e u_high (padrão: 5% e 95%).
- Alinha os retornos diários dos dois ativos e computa probabilidades condicionais.
"""

from typing import Optional, Dict, Any
import pandas as pd
import numpy as np

from ..utils.config_manager import ConfigManager
from ..utils.progress_tracker import ProgressTracker, OperationContext
from ..utils.logger import get_logger


class TailDependenceAnalyzer:
    """
    Calcula tail dependence entre dois ativos e anota pares com métricas.
    """

    def __init__(self, config: Optional[ConfigManager] = None):
        self.config = config or ConfigManager()
        self.logger = get_logger(f"{__name__}.TailDependenceAnalyzer")
        self.tracker = ProgressTracker(show_progress=self.config.get('logging.show_progress', True))

    def _compute_returns(self, price_matrix: pd.DataFrame, ticker_a: str, ticker_b: str) -> pd.DataFrame:
        """Computa retornos diários alinhados (pct_change) para dois ativos."""
        a = price_matrix[ticker_a].dropna()
        b = price_matrix[ticker_b].dropna()
        idx = a.index.intersection(b.index)
        a = a.loc[idx]
        b = b.loc[idx]
        returns = pd.DataFrame({
            'ra': a.pct_change(),
            'rb': b.pct_change()
        }).dropna()
        return returns

    def empirical_tail_dependence(self, returns: pd.DataFrame, u_low: float = 0.05, u_high: float = 0.95) -> Dict[str, float]:
        """
        Estima tail dependence inferior e superior via quantis condicionais.

        lambda_L ≈ 0.5 * [ P(X ≤ qx_low | Y ≤ qy_low) + P(Y ≤ qy_low | X ≤ qx_low) ]
        lambda_U ≈ 0.5 * [ P(X ≥ qx_high | Y ≥ qy_high) + P(Y ≥ qy_high | X ≥ qx_high) ]
        """
        x = returns['ra'].values
        y = returns['rb'].values
        n = len(returns)
        if n < 50:
            return {'lambda_L': np.nan, 'lambda_U': np.nan}

        qx_low = np.quantile(x, u_low)
        qy_low = np.quantile(y, u_low)
        qx_high = np.quantile(x, u_high)
        qy_high = np.quantile(y, u_high)

        # Inferior (cauda esquerda)
        ix_x_low = x <= qx_low
        ix_y_low = y <= qy_low
        both_low = ix_x_low & ix_y_low
        p_x_le_given_y_le = both_low.sum() / max(ix_y_low.sum(), 1)
        p_y_le_given_x_le = both_low.sum() / max(ix_x_low.sum(), 1)
        lambda_L = 0.5 * (p_x_le_given_y_le + p_y_le_given_x_le)

        # Superior (cauda direita)
        ix_x_high = x >= qx_high
        ix_y_high = y >= qy_high
        both_high = ix_x_high & ix_y_high
        p_x_ge_given_y_ge = both_high.sum() / max(ix_y_high.sum(), 1)
        p_y_ge_given_x_ge = both_high.sum() / max(ix_x_high.sum(), 1)
        lambda_U = 0.5 * (p_x_ge_given_y_ge + p_y_ge_given_x_ge)

        return {'lambda_L': float(lambda_L), 'lambda_U': float(lambda_U)}

    def annotate_tail_dependence(self, pairs_df: pd.DataFrame, price_matrix: pd.DataFrame) -> pd.DataFrame:
        """
        Anota cada par com métricas de tail dependence, adicionando colunas
        'tail_dep_lower' e 'tail_dep_upper'.
        """
        if pairs_df.empty:
            return pairs_df.copy()

        u_low = self.config.get('analysis.tail_dependence.u_low', 0.05)
        u_high = self.config.get('analysis.tail_dependence.u_high', 0.95)

        annotated = []
        with OperationContext(self.tracker, "Calculando Tail Dependence", len(pairs_df)) as tracker:
            for _, row in pairs_df.iterrows():
                a = row['Ativo_A']
                b = row['Ativo_B']
                try:
                    rets = self._compute_returns(price_matrix, a, b)
                    vals = self.empirical_tail_dependence(rets, u_low=u_low, u_high=u_high)
                    data = row.to_dict()
                    data['tail_dep_lower'] = vals['lambda_L']
                    data['tail_dep_upper'] = vals['lambda_U']
                    annotated.append(data)
                    tracker.log_milestone(f"{a}-{b}: λL={vals['lambda_L']:.3f}, λU={vals['lambda_U']:.3f}")
                except Exception as e:
                    self.logger.debug(f"Erro em tail dependence {a}-{b}: {str(e)}")
                tracker.update(1)

        return pd.DataFrame(annotated) if annotated else pairs_df.copy()

    def filter_pairs_by_tail_dependence(self, pairs_df: pd.DataFrame) -> pd.DataFrame:
        """
        Filtra pares com base nos limiares de tail dependence configurados.
        
        Args:
            pairs_df: DataFrame com colunas 'tail_dep_lower' e 'tail_dep_upper'
            
        Returns:
            DataFrame filtrado com pares que atendem aos critérios de tail dependence
        """
        if pairs_df.empty:
            return pairs_df.copy()
            
        filter_enabled = self.config.get('analysis.tail_dependence.filter_enabled', False)
        if not filter_enabled:
            self.logger.info("Filtragem por tail dependence desabilitada")
            return pairs_df.copy()
            
        min_lower = self.config.get('analysis.tail_dependence.min_lower_tail', 0.0)
        min_upper = self.config.get('analysis.tail_dependence.min_upper_tail', 0.0)
        
        initial_count = len(pairs_df)
        
        # Filtra pares que não possuem valores válidos de tail dependence
        valid_pairs = pairs_df.dropna(subset=['tail_dep_lower', 'tail_dep_upper'])
        
        # Aplica filtros de limiar
        filtered_pairs = valid_pairs[
            (valid_pairs['tail_dep_lower'] >= min_lower) &
            (valid_pairs['tail_dep_upper'] >= min_upper)
        ].copy()
        
        final_count = len(filtered_pairs)
        filtered_count = initial_count - final_count
        
        self.logger.info(f"Filtragem por tail dependence:")
        self.logger.info(f"  - Pares iniciais: {initial_count}")
        self.logger.info(f"  - Limiar tail inferior: >= {min_lower}")
        self.logger.info(f"  - Limiar tail superior: >= {min_upper}")
        self.logger.info(f"  - Pares filtrados: {filtered_count}")
        self.logger.info(f"  - Pares finais: {final_count}")
        self.logger.info(f"  - Taxa de aprovação: {(final_count/initial_count)*100:.2f}%")
        
        return filtered_pairs