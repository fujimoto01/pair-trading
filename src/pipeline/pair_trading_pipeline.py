"""
Pipeline Principal de Pair Trading

Este módulo contém a classe PairTradingPipeline que orquestra todas as fases
do processo de análise de pair trading.
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List
from pathlib import Path
import os

from ..collection.data_collector import DataCollector
from ..preparation.data_preparator import DataPreparator
from ..analysis.cointegration_analyzer import CointegrationAnalyzer
from ..analysis.hurst_analyzer import HurstAnalyzer
from ..analysis.cross_mean_analyzer import CrossMeanAnalyzer
from ..analysis.tail_dependence_analyzer import TailDependenceAnalyzer
from ..utils.config_manager import ConfigManager
from ..utils.progress_tracker import ProgressTracker, OperationContext
from ..utils.logger import get_logger


class PairTradingPipeline:
    """
    Pipeline completo para análise de pair trading.
    
    Esta classe orquestra todas as fases do processo:
    1. Coleta e análise de liquidez
    2. Preparação de dados (matriz de preços)
    3. Análise de cointegração
    4. Filtros estatísticos (Hurst, cruzamento da média)
    5. Seleção final de pares
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa o pipeline.
        
        Args:
            config_path: Caminho para arquivo de configuração personalizado
        """
        self.config = ConfigManager(config_path) if config_path else ConfigManager()
        self.logger = get_logger(f"{__name__}.PairTradingPipeline")
        self.tracker = ProgressTracker(show_progress=self.config.get('logging.show_progress', True))
        
        # Inicializar componentes
        self.data_collector = DataCollector(self.config)
        self.data_preparator = DataPreparator(self.config)
        self.cointegration_analyzer = CointegrationAnalyzer(self.config)
        self.hurst_analyzer = HurstAnalyzer(self.config)
        self.cross_mean_analyzer = CrossMeanAnalyzer(self.config)
        self.tail_dependence_analyzer = TailDependenceAnalyzer(self.config)
        
        # Cache de resultados
        self.results = {
            'liquidity_analysis': None,
            'price_matrix': None,
            'cointegrated_pairs': None,
            'hurst_filtered_pairs': None,
            'final_pairs': None
        }
        
        # Estatísticas do pipeline
        self.stats = {
            'total_stocks_analyzed': 0,
            'top_liquid_stocks': 0,
            'total_pair_combinations': 0,
            'cointegrated_pairs': 0,
            'hurst_filtered_pairs': 0,
            'final_selected_pairs': 0,
            'execution_time': {}
        }
    
    def execute_phase_1_liquidity(self, force_reload: bool = False) -> pd.DataFrame:
        """
        Executa Fase 1: Análise de liquidez e seleção das ações mais líquidas.
        
        Args:
            force_reload: Se True, recarrega dados mesmo se há cache
            
        Returns:
            DataFrame com top N ações mais líquidas
        """
        self.logger.info("=== FASE 1: ANÁLISE DE LIQUIDEZ ===")
        
        # Verificar cache
        if not force_reload and self.results['liquidity_analysis'] is not None:
            self.logger.info("Usando resultados em cache da análise de liquidez")
            return self.results['liquidity_analysis']
        
        # Executar análise
        with OperationContext(self.tracker, "Fase 1 - Análise de Liquidez") as tracker:
            try:
                df_liquidity = self.data_collector.execute_full_analysis()
                
                # Armazenar resultado e estatísticas
                self.results['liquidity_analysis'] = df_liquidity
                self.stats['top_liquid_stocks'] = len(df_liquidity)
                
                tracker.log_milestone(f"Fase 1 concluída: {len(df_liquidity)} ações selecionadas")
                return df_liquidity
                
            except Exception as e:
                self.logger.error(f"Erro na Fase 1: {str(e)}")
                raise
    
    def execute_phase_2_preparation(self, force_reload: bool = False) -> pd.DataFrame:
        """
        Executa Fase 2: Preparação da matriz de preços.
        
        Args:
            force_reload: Se True, recria matriz mesmo se há cache
            
        Returns:
            DataFrame com matriz de preços
        """
        self.logger.info("=== FASE 2: PREPARAÇÃO DE DADOS ===")
        
        # Verificar cache
        if not force_reload and self.results['price_matrix'] is not None:
            self.logger.info("Usando matriz de preços em cache")
            return self.results['price_matrix']
        
        # Executar preparação
        with OperationContext(self.tracker, "Fase 2 - Preparação de Dados") as tracker:
            try:
                price_matrix = self.data_preparator.execute_full_preparation()
                
                # Armazenar resultado e estatísticas
                self.results['price_matrix'] = price_matrix
                self.stats['total_stocks_analyzed'] = price_matrix.shape[1]
                self.stats['total_pair_combinations'] = (price_matrix.shape[1] * (price_matrix.shape[1] - 1)) // 2
                
                tracker.log_milestone(f"Fase 2 concluída: matriz {price_matrix.shape[0]}x{price_matrix.shape[1]}")
                return price_matrix
                
            except Exception as e:
                self.logger.error(f"Erro na Fase 2: {str(e)}")
                raise
    
    def execute_phase_3_cointegration(self, force_reload: bool = False) -> pd.DataFrame:
        """
        Executa Fase 3: Análise de cointegração.
        
        Args:
            force_reload: Se True, recalcula mesmo se há cache
            
        Returns:
            DataFrame com pares cointegrados
        """
        self.logger.info("=== FASE 3: ANÁLISE DE COINTEGRAÇÃO ===")
        
        # Verificar cache
        if not force_reload and self.results['cointegrated_pairs'] is not None:
            self.logger.info("Usando pares cointegrados em cache")
            return self.results['cointegrated_pairs']
        
        # Garantir que temos matriz de preços
        if self.results['price_matrix'] is None:
            self.logger.info("Matriz de preços não disponível, executando Fase 2 primeiro")
            self.execute_phase_2_preparation()
        
        # Executar análise
        with OperationContext(self.tracker, "Fase 3 - Análise de Cointegração") as tracker:
            try:
                cointegrated_pairs = self.cointegration_analyzer.find_cointegrated_pairs(
                    self.results['price_matrix']
                )
                
                # Salvar resultados
                if not cointegrated_pairs.empty:
                    years = self.config.get('data.years', [])
                    periodo_str = "_".join(map(str, years))
                    output_file = f'pares_cointegrados_{periodo_str}.csv'
                    self.cointegration_analyzer.save_cointegrated_pairs(cointegrated_pairs, output_file)
                
                # Armazenar resultado e estatísticas
                self.results['cointegrated_pairs'] = cointegrated_pairs
                self.stats['cointegrated_pairs'] = len(cointegrated_pairs)
                
                tracker.log_milestone(f"Fase 3 concluída: {len(cointegrated_pairs)} pares cointegrados")
                return cointegrated_pairs
                
            except Exception as e:
                self.logger.error(f"Erro na Fase 3: {str(e)}")
                raise
    
    def execute_phase_4_statistical_filters(self, force_reload: bool = False) -> pd.DataFrame:
        """
        Executa Fase 4: Filtros estatísticos (Hurst + Cruzamento da média).
        
        Args:
            force_reload: Se True, recalcula mesmo se há cache
            
        Returns:
            DataFrame com pares finais selecionados
        """
        self.logger.info("=== FASE 4: FILTROS ESTATÍSTICOS ===")
        
        # Verificar cache
        if not force_reload and self.results['final_pairs'] is not None:
            self.logger.info("Usando pares filtrados em cache")
            return self.results['final_pairs']
        
        # Garantir que temos pares cointegrados
        if self.results['cointegrated_pairs'] is None:
            self.logger.info("Pares cointegrados não disponíveis, executando Fase 3 primeiro")
            self.execute_phase_3_cointegration()
        
        if self.results['cointegrated_pairs'].empty:
            self.logger.warning("Nenhum par cointegrado disponível para filtrar")
            empty_df = pd.DataFrame()
            self.results['final_pairs'] = empty_df
            return empty_df
        
        # Executar filtros
        with OperationContext(self.tracker, "Fase 4 - Filtros Estatísticos") as tracker:
            try:
                # Filtro 1: Expoente de Hurst
                tracker.log_milestone("Aplicando filtro de Hurst...")
                hurst_filtered = self.hurst_analyzer.filter_pairs_by_hurst(
                    self.results['cointegrated_pairs'],
                    self.results['price_matrix']
                )
                
                self.results['hurst_filtered_pairs'] = hurst_filtered
                self.stats['hurst_filtered_pairs'] = len(hurst_filtered)
                
                if hurst_filtered.empty:
                    self.logger.warning("Nenhum par passou no filtro de Hurst")
                    self.results['final_pairs'] = hurst_filtered
                    return hurst_filtered
                
                # Filtro 2: Cruzamento da média
                tracker.log_milestone("Aplicando filtro de cruzamento da média...")
                final_pairs = self.cross_mean_analyzer.filter_pairs_by_crossings(
                    hurst_filtered,
                    self.results['price_matrix']
                )
                
                # Anotar métricas de tail dependence nos pares finais
                final_pairs = self.tail_dependence_analyzer.annotate_tail_dependence(
                    final_pairs,
                    self.results['price_matrix']
                )
                
                # Filtro 3: Tail Dependence (opcional)
                tracker.log_milestone("Aplicando filtro de tail dependence...")
                final_pairs = self.tail_dependence_analyzer.filter_pairs_by_tail_dependence(
                    final_pairs
                )
                
                # Salvar resultados finais
                if not final_pairs.empty:
                    years = self.config.get('data.years', [])
                    periodo_str = "_".join(map(str, years))
                    
                    # Salvar pares após filtro de Hurst
                    hurst_file = f'pares_filtrados_hurst_{periodo_str}.csv'
                    self._save_dataframe(hurst_filtered, hurst_file, 'filtered_pairs')
                    
                    # Salvar pares finais
                    final_file = f'pares_finais_selecionados_{periodo_str}.csv'
                    self._save_dataframe(final_pairs, final_file, 'final_results')
                
                # Armazenar resultado e estatísticas
                self.results['final_pairs'] = final_pairs
                self.stats['final_selected_pairs'] = len(final_pairs)
                
                tracker.log_milestone(f"Fase 4 concluída: {len(final_pairs)} pares finais selecionados")
                return final_pairs
                
            except Exception as e:
                self.logger.error(f"Erro na Fase 4: {str(e)}")
                raise
    
    def execute_full_pipeline(self, force_reload: bool = False) -> Dict[str, pd.DataFrame]:
        """
        Executa pipeline completo de análise.
        
        Args:
            force_reload: Se True, recalcula tudo do zero
            
        Returns:
            Dicionário com todos os resultados
        """
        self.logger.info("=== INICIANDO PIPELINE COMPLETO DE PAIR TRADING ===")
        
        pipeline_start = pd.Timestamp.now()
        
        try:
            # Fase 1: Liquidez
            self.execute_phase_1_liquidity(force_reload)
            
            # Fase 2: Preparação
            self.execute_phase_2_preparation(force_reload)
            
            # Fase 3: Cointegração
            self.execute_phase_3_cointegration(force_reload)
            
            # Fase 4: Filtros
            self.execute_phase_4_statistical_filters(force_reload)
            
            # Calcular tempo total
            pipeline_end = pd.Timestamp.now()
            total_time = (pipeline_end - pipeline_start).total_seconds()
            
            # Gerar relatório final
            self._generate_final_report(total_time)
            
            return self.results.copy()
            
        except Exception as e:
            self.logger.error(f"Erro no pipeline: {str(e)}")
            raise
    
    def _save_dataframe(self, df: pd.DataFrame, filename: str, category: str = 'final_results') -> None:
        """Salva DataFrame usando configurações padrão em diretório organizado."""
        separator = self.config.get('data.output.separator', ';')
        decimal = self.config.get('data.output.decimal', ',')
        encoding = self.config.get('data.output.encoding_out', 'utf-8-sig')
        
        output_path = self.config.get_output_path(filename, category)
        df.to_csv(output_path, index=False, sep=separator, decimal=decimal, encoding=encoding)
        
        self.logger.info(f"Arquivo salvo: {output_path}")
    
    def _generate_final_report(self, execution_time: float) -> None:
        """Gera relatório final do pipeline."""
        self.logger.info("=" * 60)
        self.logger.info("RELATÓRIO FINAL DO PIPELINE")
        self.logger.info("=" * 60)
        
        self.logger.info(f"Tempo total de execução: {execution_time:.1f} segundos")
        self.logger.info("")
        
        self.logger.info("ESTATÍSTICAS POR FASE:")
        self.logger.info(f"  Fase 1 - Ações líquidas selecionadas: {self.stats['top_liquid_stocks']}")
        self.logger.info(f"  Fase 2 - Ações na matriz de preços: {self.stats['total_stocks_analyzed']}")
        self.logger.info(f"  Fase 3 - Combinações de pares testadas: {self.stats['total_pair_combinations']:,}")
        self.logger.info(f"  Fase 3 - Pares cointegrados encontrados: {self.stats['cointegrated_pairs']}")
        self.logger.info(f"  Fase 4 - Pares após filtro de Hurst: {self.stats['hurst_filtered_pairs']}")
        self.logger.info(f"  Fase 4 - Pares finais selecionados: {self.stats['final_selected_pairs']}")
        self.logger.info("")
        
        # Taxa de conversão
        if self.stats['total_pair_combinations'] > 0:
            conversion_rate = (self.stats['final_selected_pairs'] / self.stats['total_pair_combinations']) * 100
            self.logger.info(f"Taxa de conversão final: {conversion_rate:.4f}% dos pares testados")
        
        # Próximos passos
        if self.stats['final_selected_pairs'] > 0:
            self.logger.info("")
            self.logger.info("PRÓXIMOS PASSOS SUGERIDOS:")
            self.logger.info("  1. Selecionar o melhor par (menor p-valor)")
            self.logger.info("  2. Implementar estratégia de sinais (Z-Score)")
            self.logger.info("  3. Executar backtesting")
            self.logger.info("  4. Avaliar performance da estratégia")
        else:
            self.logger.warning("")
            self.logger.warning("ATENÇÃO: Nenhum par foi selecionado!")
            self.logger.warning("Considere ajustar os parâmetros de filtro nas configurações.")
        
        self.logger.info("=" * 60)
    
    def get_results(self) -> Dict[str, pd.DataFrame]:
        """Retorna todos os resultados do pipeline."""
        return self.results.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas de execução do pipeline."""
        return self.stats.copy()
    
    def clear_cache(self) -> None:
        """Limpa todos os caches do pipeline."""
        self.results = {key: None for key in self.results.keys()}
        self.stats = {key: 0 if isinstance(value, int) else {} for key, value in self.stats.items()}
        
        # Limpar caches dos componentes
        self.data_collector.clear_cache()
        self.data_preparator.clear_cache()
        self.cointegration_analyzer.clear_cache()
        
        self.logger.info("Cache do pipeline limpo")