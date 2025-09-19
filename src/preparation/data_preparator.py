"""
Preparador de Dados

Este módulo contém a classe DataPreparator responsável pela criação de
matrizes de preços e preparação de dados para análise estatística.
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Any
from pathlib import Path
import os

from ..utils.config_manager import ConfigManager
from ..utils.progress_tracker import ProgressTracker, OperationContext
from ..utils.logger import get_logger


class DataPreparator:
    """
    Preparador de dados para análise de pair trading.
    
    Esta classe é responsável por transformar dados brutos COTAHIST em
    matrizes de preços estruturadas para análise estatística.
    """
    
    def __init__(self, config: Optional[ConfigManager] = None):
        """
        Inicializa o preparador de dados.
        
        Args:
            config: Gerenciador de configurações. Se None, usa configuração padrão.
        """
        self.config = config or ConfigManager()
        self.logger = get_logger(f"{__name__}.DataPreparator")
        self.tracker = ProgressTracker(show_progress=self.config.get('logging.show_progress', True))
        
        # Cache para matrizes de preços
        self._price_matrix: Optional[pd.DataFrame] = None
        
    def load_tickers_from_file(self, file_path: str) -> List[str]:
        """
        Carrega lista de tickers de um arquivo CSV.
        
        Args:
            file_path: Caminho para arquivo com tickers
            
        Returns:
            Lista de tickers válidos
            
        Raises:
            FileNotFoundError: Se arquivo não existe
            ValueError: Se arquivo não contém tickers válidos
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo de tickers não encontrado: {file_path}")
        
        try:
            # Detectar separador automaticamente
            separator = ';' if ';' in open(file_path, 'r').read() else ','
            
            df_tickers = pd.read_csv(file_path, sep=separator)
            
            # Buscar coluna com tickers (várias possibilidades)
            ticker_column = None
            possible_columns = ['ticker', 'Ticker', 'TICKER', 'codigo_negociacao', 'symbol']
            
            for col in possible_columns:
                if col in df_tickers.columns:
                    ticker_column = col
                    break
            
            if ticker_column is None:
                raise ValueError(f"Coluna de tickers não encontrada. Colunas disponíveis: {list(df_tickers.columns)}")
            
            tickers = df_tickers[ticker_column].dropna().astype(str).str.strip().tolist()
            
            if not tickers:
                raise ValueError("Nenhum ticker válido encontrado no arquivo")
            
            self.logger.info(f"{len(tickers)} tickers carregados de {file_path}")
            return tickers
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar tickers: {str(e)}")
            raise
    
    def create_price_matrix(self, tickers: List[str], cotahist_files: List[str]) -> pd.DataFrame:
        """
        Cria matriz de preços de fechamento a partir dos arquivos COTAHIST.
        
        Args:
            tickers: Lista de tickers para incluir na matriz
            cotahist_files: Lista de caminhos para arquivos COTAHIST
            
        Returns:
            DataFrame com preços de fechamento (datas x tickers)
            
        Raises:
            FileNotFoundError: Se arquivos COTAHIST não existem
            ValueError: Se não há dados suficientes
        """
        # Verificar arquivos
        for file_path in cotahist_files:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Arquivo COTAHIST não encontrado: {file_path}")
        
        # Especificação de colunas COTAHIST
        colunas = [
            ('TIPO_REGISTRO', 1, 2),
            ('DATA_PREGAO', 3, 10),
            ('COD_BDI', 11, 12),
            ('CODIGO_NEGOCIACAO', 13, 24),
            ('TIPO_MERCADO', 25, 27),
            ('PRECO_FECHAMENTO', 109, 121)
        ]
        
        col_names = [c[0] for c in colunas]
        col_specs = [(c[1]-1, c[2]) for c in colunas]
        
        dfs_anuais = []
        
        with OperationContext(self.tracker, "Processando arquivos COTAHIST") as tracker:
            for caminho in cotahist_files:
                tracker.log_milestone(f"Lendo: {os.path.basename(caminho)}")
                
                encoding = self.config.get('data.encoding', 'latin-1')
                
                try:
                    df_ano = pd.read_fwf(
                        caminho, colspecs=col_specs, names=col_names,
                        header=None, skiprows=1, skipfooter=1, encoding=encoding
                    )
                    dfs_anuais.append(df_ano)
                    tracker.log_milestone(f"Arquivo processado: {len(df_ano)} registros")
                    
                except Exception as e:
                    self.logger.error(f"Erro ao processar {caminho}: {str(e)}")
                    raise
        
        # Concatenar dados
        df_total = pd.concat(dfs_anuais, ignore_index=True)
        self.logger.info(f"Total de registros concatenados: {len(df_total)}")
        
        # Aplicar filtros
        with OperationContext(self.tracker, "Filtrando e limpando dados") as tracker:
            # Filtrar apenas registros de cotação
            df_total = df_total[df_total['TIPO_REGISTRO'] == 1].copy()
            tracker.log_milestone(f"Após filtro tipo_registro: {len(df_total)} registros")
            
            # Formatar código BDI
            df_total['COD_BDI'] = df_total['COD_BDI'].astype(str).str.zfill(2)
            
            # Filtrar apenas ações (BDI 02)
            df_total = df_total[df_total['COD_BDI'] == '02']
            tracker.log_milestone(f"Após filtro BDI 02: {len(df_total)} registros")
            
            # Filtrar apenas mercado à vista (tipo 10)
            df_total = df_total[df_total['TIPO_MERCADO'] == 10]
            tracker.log_milestone(f"Após filtro mercado à vista: {len(df_total)} registros")
            
            # Limpar código de negociação
            df_total['CODIGO_NEGOCIACAO'] = df_total['CODIGO_NEGOCIACAO'].str.strip()
            
            # Converter data
            df_total['DATA_PREGAO'] = pd.to_datetime(df_total['DATA_PREGAO'], format='%Y%m%d')
            
            # Converter preço (dividir por 100)
            df_total['PRECO_FECHAMENTO'] = pd.to_numeric(
                df_total['PRECO_FECHAMENTO'], errors='coerce'
            ) / 100
            
            # Remover preços inválidos
            df_total.dropna(subset=['PRECO_FECHAMENTO'], inplace=True)
            df_total = df_total[df_total['PRECO_FECHAMENTO'] > 0]
            tracker.log_milestone(f"Após limpeza de preços: {len(df_total)} registros")
            
            # Filtrar apenas tickers desejados
            df_filtrado = df_total[df_total['CODIGO_NEGOCIACAO'].isin(tickers)].copy()
            tracker.log_milestone(f"Após filtro de tickers: {len(df_filtrado)} registros")
        
        if df_filtrado.empty:
            raise ValueError("Nenhum dado encontrado para os tickers especificados")
        
        # Criar matriz de preços
        with OperationContext(self.tracker, "Criando matriz de preços") as tracker:
            matriz_precos = df_filtrado.pivot_table(
                index='DATA_PREGAO',
                columns='CODIGO_NEGOCIACAO',
                values='PRECO_FECHAMENTO'
            )
            
            tracker.log_milestone(f"Matriz criada: {matriz_precos.shape[0]} dias x {matriz_precos.shape[1]} ativos")
            
            # Tratar valores ausentes
            initial_na_count = matriz_precos.isna().sum().sum()
            
            if initial_na_count > 0:
                tracker.log_milestone(f"Tratando {initial_na_count} valores ausentes")
                
                # Forward fill (usar último preço válido)
                matriz_precos.ffill(inplace=True)
                
                # Backward fill (para NaNs no início)
                matriz_precos.bfill(inplace=True)
                
                final_na_count = matriz_precos.isna().sum().sum()
                tracker.log_milestone(f"Valores ausentes após tratamento: {final_na_count}")
        
        # Cache resultado
        self._price_matrix = matriz_precos
        
        self.logger.info(f"Matriz de preços criada com sucesso: {matriz_precos.shape}")
        return matriz_precos
    
    def validate_price_matrix(self, price_matrix: pd.DataFrame) -> Dict[str, Any]:
        """
        Valida matriz de preços e retorna estatísticas.
        
        Args:
            price_matrix: Matriz de preços para validar
            
        Returns:
            Dicionário com estatísticas e problemas encontrados
        """
        stats = {
            'shape': price_matrix.shape,
            'date_range': (price_matrix.index.min(), price_matrix.index.max()),
            'total_observations': price_matrix.size,
            'missing_values': price_matrix.isna().sum().sum(),
            'zero_prices': (price_matrix == 0).sum().sum(),
            'negative_prices': (price_matrix < 0).sum().sum(),
            'tickers_with_data': price_matrix.notna().any().sum(),
            'problems': []
        }
        
        # Verificar problemas
        if stats['missing_values'] > 0:
            stats['problems'].append(f"{stats['missing_values']} valores ausentes")
        
        if stats['zero_prices'] > 0:
            stats['problems'].append(f"{stats['zero_prices']} preços zero")
        
        if stats['negative_prices'] > 0:
            stats['problems'].append(f"{stats['negative_prices']} preços negativos")
        
        # Verificar tickers sem dados
        tickers_sem_dados = price_matrix.columns[~price_matrix.notna().any()].tolist()
        if tickers_sem_dados:
            stats['problems'].append(f"Tickers sem dados: {tickers_sem_dados}")
        
        # Verificar continuidade temporal
        expected_business_days = pd.bdate_range(
            start=price_matrix.index.min(),
            end=price_matrix.index.max()
        )
        
        missing_dates = expected_business_days.difference(price_matrix.index)
        if len(missing_dates) > 0:
            stats['problems'].append(f"{len(missing_dates)} dias úteis ausentes")
        
        # Log dos resultados
        self.logger.info("Validação da matriz de preços:")
        self.logger.info(f"  - Dimensões: {stats['shape'][0]} dias x {stats['shape'][1]} ativos")
        self.logger.info(f"  - Período: {stats['date_range'][0].strftime('%Y-%m-%d')} a {stats['date_range'][1].strftime('%Y-%m-%d')}")
        self.logger.info(f"  - Valores ausentes: {stats['missing_values']}")
        
        if stats['problems']:
            self.logger.warning("Problemas encontrados:")
            for problem in stats['problems']:
                self.logger.warning(f"  - {problem}")
        else:
            self.logger.info("Nenhum problema encontrado na matriz")
        
        return stats
    
    def save_price_matrix(self, price_matrix: pd.DataFrame, output_file: str) -> str:
        """
        Salva matriz de preços em arquivo CSV.
        
        Args:
            price_matrix: Matriz de preços para salvar
            output_file: Nome do arquivo de saída
            
        Returns:
            Caminho completo do arquivo salvo
        """
        # Configurações de saída
        output_config = self.config.get('data.output', {})
        separator = output_config.get('separator', ';')
        decimal = output_config.get('decimal', ',')
        encoding = output_config.get('encoding_out', 'utf-8-sig')
        
        output_path = self.config.get_output_path(output_file, 'price_matrix')
        
        try:
            price_matrix.to_csv(output_path, sep=separator, decimal=decimal, encoding=encoding)
            self.logger.info(f"Matriz de preços salva em: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar matriz de preços: {str(e)}")
            raise
    
    def create_matrix_from_ticker_file(self, ticker_file: str, 
                                     output_file: Optional[str] = None) -> pd.DataFrame:
        """
        Cria matriz de preços a partir de arquivo de tickers.
        
        Args:
            ticker_file: Arquivo contendo lista de tickers
            output_file: Nome do arquivo de saída (opcional)
            
        Returns:
            DataFrame com matriz de preços
        """
        # Carregar tickers
        tickers = self.load_tickers_from_file(ticker_file)
        
        # Buscar arquivos COTAHIST das configurações
        cotahist_files = self.config.get_cotahist_files()
        
        if not cotahist_files:
            raise ValueError("Nenhum arquivo COTAHIST configurado")
        
        # Criar matriz
        price_matrix = self.create_price_matrix(tickers, cotahist_files)
        
        # Validar
        self.validate_price_matrix(price_matrix)
        
        # Salvar se especificado
        if output_file:
            self.save_price_matrix(price_matrix, output_file)
        
        return price_matrix
    
    def execute_full_preparation(self, ticker_file: str = None) -> pd.DataFrame:
        """
        Executa preparação completa de dados.
        
        Args:
            ticker_file: Arquivo com tickers. Se None, usa padrão das configurações.
            
        Returns:
            DataFrame com matriz de preços
        """
        # Definir arquivo de tickers padrão se não especificado
        if ticker_file is None:
            years = self.config.get('data.years', [])
            periodo_str = "_".join(map(str, years))
            ticker_filename = f'top_100_acoes_liquidas_{periodo_str}_completo.csv'
            # Usar caminho organizado para arquivo de liquidez
            ticker_file = self.config.get_output_path(ticker_filename, 'liquidity')
        
        # Nome padrão do arquivo de saída
        years = self.config.get('data.years', [])
        periodo_str = "_".join(map(str, years))
        output_file = f'matriz_precos_{periodo_str}.csv'
        
        # Executar preparação
        price_matrix = self.create_matrix_from_ticker_file(ticker_file, output_file)
        
        self.logger.info("Preparação de dados concluída com sucesso")
        return price_matrix
    
    def get_cached_matrix(self) -> Optional[pd.DataFrame]:
        """
        Retorna matriz de preços em cache.
        
        Returns:
            DataFrame com matriz ou None se não há cache
        """
        return self._price_matrix
    
    def clear_cache(self) -> None:
        """Limpa cache da matriz de preços."""
        self._price_matrix = None
        self.logger.debug("Cache da matriz de preços limpo")