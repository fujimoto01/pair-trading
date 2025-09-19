"""
Coletor de Dados COTAHIST

Este módulo contém a classe DataCollector responsável pela coleta e análise
de liquidez dos dados COTAHIST da B3 (Bolsa brasileira).
"""

import pandas as pd
import numpy as np
from datetime import datetime
import re
import os
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

from ..utils.config_manager import ConfigManager
from ..utils.progress_tracker import ProgressTracker, OperationContext
from ..utils.logger import get_logger


class DataCollector:
    """
    Coletor e analisador de dados COTAHIST da B3.
    
    Esta classe encapsula toda a lógica de coleta de dados históricos da bolsa,
    incluindo parsing de arquivos COTAHIST, validação de ações e análise de liquidez.
    """
    
    def __init__(self, config: Optional[ConfigManager] = None):
        """
        Inicializa o coletor de dados.
        
        Args:
            config: Gerenciador de configurações. Se None, usa configuração padrão.
        """
        self.config = config or ConfigManager()
        self.logger = get_logger(f"{__name__}.DataCollector")
        self.tracker = ProgressTracker(show_progress=self.config.get('logging.show_progress', True))
        
        # Cache para otimização
        self._parsed_data: Optional[pd.DataFrame] = None
        self._liquidity_results: Optional[pd.DataFrame] = None
    
    def parse_cotahist_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse uma linha do arquivo COTAHIST formato fixo.
        
        Args:
            line: Linha do arquivo COTAHIST
            
        Returns:
            Dicionário com os campos principais ou None se inválido
        """
        if len(line) < 245:
            return None
        
        try:
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
        except (ValueError, IndexError) as e:
            self.logger.debug(f"Erro ao fazer parse da linha: {str(e)}")
            return None
    
    def is_valid_stock(self, codigo_negociacao: str, codigo_bdi: str, 
                      especificacao_papel: str) -> bool:
        """
        Verifica se é uma ação válida (não ETF, não units, não outros tipos).
        
        Args:
            codigo_negociacao: Código de negociação do ativo
            codigo_bdi: Código BDI (tipo de ativo)
            especificacao_papel: Especificação do papel
            
        Returns:
            True se é uma ação válida, False caso contrário
        """
        codigo = codigo_negociacao.strip()
        
        # Deve ser BDI 02 (ações ordinárias e preferenciais)
        if codigo_bdi != '02':
            return False
        
        # Excluir ETFs (geralmente terminam com 11)
        if codigo.endswith('11'):
            return False
        
        # Excluir BDRs conhecidos
        bdr_prefixes = ['AAPL', 'MSFT', 'GOOGL', 'AMZO', 'TSLA', 'NVDA']
        if any(codigo.startswith(prefix) for prefix in bdr_prefixes):
            return False
        
        # Excluir códigos muito curtos ou muito longos
        if len(codigo) < 4 or len(codigo) > 6:
            return False
        
        # Padrão típico de ações: 4 letras + 1 número ou 5 letras + 1 número
        if not re.match(r'^[A-Z]{4}[34568]$|^[A-Z]{5}[34568]$', codigo):
            return False
        
        return True
    
   
    def load_cotahist_files(self, file_paths: List[str]) -> pd.DataFrame:
        """
        Carrega e processa arquivos COTAHIST.
        
        Args:
            file_paths: Lista de caminhos para arquivos COTAHIST
            
        Returns:
            DataFrame com dados processados e filtrados
            
        Raises:
            FileNotFoundError: Se algum arquivo não for encontrado
            ValueError: Se nenhum dado válido for encontrado
        """
        # Verificar se arquivos existem
        for file_path in file_paths:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Arquivo COTAHIST não encontrado: {file_path}")
        
        data_list = []
        
        with OperationContext(self.tracker, "Carregando arquivos COTAHIST") as tracker:
            for file_path in file_paths:
                tracker.log_milestone(f"Processando arquivo: {os.path.basename(file_path)}")
                
                encoding = self.config.get('data.encoding', 'latin-1')
                
                try:
                    with open(file_path, 'r', encoding=encoding) as file:
                        lines = file.readlines()
                        
                    # Inicializar progresso para este arquivo
                    for line_num, line in enumerate(lines, 1):
                        if line_num % 50000 == 0:
                            tracker.log_milestone(f"Processadas {line_num} linhas de {os.path.basename(file_path)}")
                        
                        # Parse da linha
                        parsed_data = self.parse_cotahist_line(line.strip())
                        
                        # Pular se não conseguiu fazer parse ou não é registro de cotação
                        if not parsed_data or parsed_data['tipo_registro'] != '01':
                            continue
                        
                        # Filtrar apenas mercado à vista
                        if parsed_data['tipo_mercado'] != '010':
                            continue
                        
                        # Verificar se é ação válida
                        if not self.is_valid_stock(
                            parsed_data['codigo_negociacao'],
                            parsed_data['codigo_bdi'],
                            parsed_data['especificacao_papel']
                        ):
                            continue
                        
                        # Filtros de qualidade
                        if (parsed_data['volume_financeiro'] <= 0 or 
                            parsed_data['preco_ultimo'] <= 0):
                            continue
                        
                        data_list.append(parsed_data)
                        
                except Exception as e:
                    self.logger.error(f"Erro ao processar arquivo {file_path}: {str(e)}")
                    raise
        
        if not data_list:
            raise ValueError("Nenhum dado válido encontrado nos arquivos COTAHIST")
        
        self.logger.info(f"Total de registros válidos carregados: {len(data_list)}")
        
        # Converter para DataFrame e cached
        self._parsed_data = pd.DataFrame(data_list)
        return self._parsed_data
    
    def analyze_liquidity(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Analisa liquidez das ações e retorna ranking.
        
        Args:
            df: DataFrame com dados COTAHIST. Se None, usa dados carregados em cache.
            
        Returns:
            DataFrame com top N ações mais líquidas
            
        Raises:
            ValueError: Se não há dados para analisar
        """
        if df is None:
            if self._parsed_data is None:
                raise ValueError("Nenhum dado carregado. Execute load_cotahist_files() primeiro.")
            df = self._parsed_data
        
        # Buscar configurações
        liquidity_config = self.config.get_liquidity_config()
        selection_config = liquidity_config.get('selection', {})
        
        top_n = selection_config.get('top_n_stocks', 100)
        
        liquidity_results = []
        unique_tickers = df['codigo_negociacao'].unique()
        
        with OperationContext(self.tracker, "Analisando liquidez", len(unique_tickers)) as tracker:
            for codigo in unique_tickers:
                df_stock = df[df['codigo_negociacao'] == codigo]
                
                # Substituido por cálculo simplificado do score
                score = df_stock['volume_financeiro'].mean()
                
                # Informações adicionais da ação
                sample_row = df_stock.iloc[0]
                
                result = {
                    'ticker': codigo,
                    'nome_resumido': sample_row['nome_resumido'],
                    'score_liquidez': score
                }
                
                liquidity_results.append(result)
                tracker.update(1, f"Analisado: {codigo}")
        
        # Converter para DataFrame e ordenar por score
        df_liquidity = pd.DataFrame(liquidity_results)
        
        if df_liquidity.empty:
            raise ValueError("Nenhuma ação atendeu aos critérios de liquidez")
        
        df_liquidity = df_liquidity.sort_values('score_liquidez', ascending=False).reset_index(drop=True)
        
        self.logger.info(f"Total de ações analisadas: {len(df_liquidity)}")
        
        # Pegar top N
        top_n_results = df_liquidity.head(top_n).copy()
        top_n_results['ranking'] = range(1, len(top_n_results) + 1)
        
        # Cache resultado
        self._liquidity_results = top_n_results
        
        return top_n_results
    
    def save_results(self, df_results: pd.DataFrame, periodo_str: str) -> Tuple[str, str]:
        """
        Salva resultados da análise de liquidez.
        
        Args:
            df_results: DataFrame com resultados
            periodo_str: String identificando o período (ex: "2014_2015")
            
        Returns:
            Tuple com caminhos dos arquivos salvos (completo, tickers)
        """
        # Configurações de saída
        output_config = self.config.get('data.output', {})
        separator = output_config.get('separator', ';')
        decimal = output_config.get('decimal', ',')
        encoding = output_config.get('encoding_out', 'utf-8-sig')
        
        # Nomes dos arquivos organizados
        arquivo_completo = self.config.get_output_path(f'top_100_acoes_liquidas_{periodo_str}_completo.csv', 'liquidity')
        arquivo_tickers = self.config.get_output_path(f'top_100_acoes_liquidas_{periodo_str}_tickers.txt', 'liquidity')
        
        try:
            # Salvar resultado completo
            df_results.to_csv(arquivo_completo, index=False, sep=separator, 
                            decimal=decimal, encoding=encoding)
            
            # Salvar apenas lista de tickers
            tickers_only = df_results[['ranking', 'ticker']].copy()
            tickers_only.to_csv(arquivo_tickers, index=False, 
                              header=['Ranking', 'Ticker'], sep='\t')
            
            self.logger.info(f"Resultados salvos:")
            self.logger.info(f"  - {arquivo_completo}")
            self.logger.info(f"  - {arquivo_tickers}")
            
            return arquivo_completo, arquivo_tickers
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar resultados: {str(e)}")
            raise
    
    def execute_full_analysis(self) -> pd.DataFrame:
        """
        Executa análise completa de liquidez.
        
        Returns:
            DataFrame com top N ações mais líquidas
            
        Raises:
            FileNotFoundError: Se arquivos COTAHIST não forem encontrados
            ValueError: Se nenhum dado válido for encontrado
        """
        # Buscar arquivos COTAHIST das configurações
        file_paths = self.config.get_cotahist_files()
        
        if not file_paths:
            raise ValueError("Nenhum arquivo COTAHIST configurado")
        
        # Carregar dados
        df_data = self.load_cotahist_files(file_paths)
        
        # Analisar liquidez
        df_results = self.analyze_liquidity(df_data)
        
        # Gerar string do período baseada nos anos configurados
        years = self.config.get('data.years', [])
        periodo_str = "_".join(map(str, years))
        
        # Salvar resultados
        self.save_results(df_results, periodo_str)
        
        # Log do resultado final
        self.logger.info(f"\n=== TOP 20 AÇÕES MAIS LÍQUIDAS {periodo_str.replace('_', '-')} ===")
        top_20_display = df_results[['ranking', 'ticker', 'nome_resumido', 
                                   'volume_medio_diario', 'frequencia_negociacao']].head(20)
        
        # Exibir resultado formatado
        for _, row in top_20_display.iterrows():
            self.logger.info(f"{row['ranking']:2d}. {row['ticker']:8s} - {row['nome_resumido']:20s} - "
                           f"Vol: R$ {row['volume_medio_diario']:12,.0f} - "
                           f"Freq: {row['frequencia_negociacao']:5.1%}")
        
        return df_results
    
    def get_cached_results(self) -> Optional[pd.DataFrame]:
        """
        Retorna resultados em cache da última análise.
        
        Returns:
            DataFrame com resultados ou None se não há cache
        """
        return self._liquidity_results
    
    def clear_cache(self) -> None:
        """Limpa cache de dados e resultados."""
        self._parsed_data = None
        self._liquidity_results = None
        self.logger.debug("Cache limpo")