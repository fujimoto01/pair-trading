"""
Gerenciador de Configurações

Este módulo fornece uma interface centralizada para gerenciar todas as configurações
do pipeline de pair trading, incluindo validação de parâmetros e valores padrão.
"""

import os
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging


class ConfigManager:
    """
    Gerenciador centralizado de configurações para o pipeline de pair trading.
    
    Carrega configurações do arquivo config.yaml e fornece validação e
    acesso fácil aos parâmetros em toda a aplicação.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa o gerenciador de configurações.
        
        Args:
            config_path: Caminho para o arquivo de configuração. Se None,
                        usa o arquivo padrão em config/config.yaml
        """
        self.logger = logging.getLogger(__name__)
        
        if config_path is None:
            # Detectar automaticamente o diretório raiz do projeto
            current_dir = Path(__file__).parent.parent.parent
            config_path = current_dir / "config" / "config.yaml"
        
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        
        self._load_config()
        self._validate_config()
    
    def _load_config(self) -> None:
        """Carrega as configurações do arquivo YAML."""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Arquivo de configuração não encontrado: {self.config_path}")
            
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self.config = yaml.safe_load(file)
            
            self.logger.info(f"Configurações carregadas de: {self.config_path}")
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar configurações: {str(e)}")
            raise
    
    def _validate_config(self) -> None:
        """Valida as configurações carregadas."""
        required_sections = ['data', 'liquidity', 'analysis', 'strategy', 'backtesting']
        
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Seção obrigatória '{section}' não encontrada nas configurações")
        
        # Validações específicas
        self._validate_data_config()
        self._validate_liquidity_config()
        self._validate_analysis_config()
        
        self.logger.info("Configurações validadas com sucesso")
    
    def _validate_data_config(self) -> None:
        """Valida configurações de dados."""
        data_config = self.config['data']
        
        # Verificar se os anos são válidos
        years = data_config.get('years', [])
        if not years or not all(isinstance(y, int) and 2000 <= y <= 2030 for y in years):
            raise ValueError("Anos deve ser uma lista de inteiros entre 2000 e 2030")
        
        # Verificar se os arquivos COTAHIST existem
        cotahist_files = data_config.get('cotahist_files', [])
        project_root = self.config_path.parent.parent
        
        for file_name in cotahist_files:
            file_path = project_root / file_name
            if not file_path.exists():
                self.logger.warning(f"Arquivo COTAHIST não encontrado: {file_path}")
    
    def _validate_liquidity_config(self) -> None:
        """Valida configurações de liquidez."""
        liquidity_config = self.config['liquidity']
        
        # Validar critérios de seleção
        selection = liquidity_config.get('selection', {})
        
        if selection.get('top_n_stocks', 0) <= 0:
            raise ValueError("top_n_stocks deve ser um número positivo")
        
        if selection.get('min_daily_volume', 0) < 0:
            raise ValueError("min_daily_volume não pode ser negativo")
        
        if not (0 <= selection.get('min_trading_frequency', 0) <= 1):
            raise ValueError("min_trading_frequency deve estar entre 0 e 1")
        
        # Validar pesos do score
        weights = liquidity_config.get('score_weights', {})
        total_weight = sum(weights.values())
        
        if abs(total_weight - 1.0) > 0.01:
            self.logger.warning(f"Soma dos pesos de liquidez não é 1.0: {total_weight}")
    
    def _validate_analysis_config(self) -> None:
        """Valida configurações de análise."""
        analysis_config = self.config['analysis']
        
        # Validar cointegração
        coint_config = analysis_config.get('cointegration', {})
        sig_level = coint_config.get('significance_level', 0.05)
        
        if not (0 < sig_level < 1):
            raise ValueError("significance_level deve estar entre 0 e 1")
        
        # Validar Hurst
        hurst_config = analysis_config.get('hurst', {})
        max_hurst = hurst_config.get('max_hurst_exponent', 0.5)
        
        if not (0 < max_hurst < 1):
            raise ValueError("max_hurst_exponent deve estar entre 0 e 1")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Obtém um valor das configurações usando notação de ponto.
        
        Args:
            key_path: Caminho para o valor (ex: "data.years")
            default: Valor padrão se a chave não existir
            
        Returns:
            Valor da configuração ou default
            
        Example:
            >>> config = ConfigManager()
            >>> years = config.get("data.years")
            >>> volume_weight = config.get("liquidity.score_weights.volume")
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any) -> None:
        """
        Define um valor nas configurações usando notação de ponto.
        
        Args:
            key_path: Caminho para o valor (ex: "data.years")
            value: Novo valor
        """
        keys = key_path.split('.')
        config_section = self.config
        
        # Navegar até a penúltima chave
        for key in keys[:-1]:
            if key not in config_section:
                config_section[key] = {}
            config_section = config_section[key]
        
        # Definir o valor final
        config_section[keys[-1]] = value
        
        self.logger.debug(f"Configuração atualizada: {key_path} = {value}")
    
    def save(self, file_path: Optional[str] = None) -> None:
        """
        Salva as configurações atuais em arquivo.
        
        Args:
            file_path: Caminho do arquivo. Se None, usa o arquivo original.
        """
        if file_path is None:
            file_path = self.config_path
        else:
            file_path = Path(file_path)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                yaml.dump(self.config, file, default_flow_style=False, 
                         allow_unicode=True, indent=2)
            
            self.logger.info(f"Configurações salvas em: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar configurações: {str(e)}")
            raise
    
    def get_data_config(self) -> Dict[str, Any]:
        """Retorna configurações de dados."""
        return self.config.get('data', {})
    
    def get_liquidity_config(self) -> Dict[str, Any]:
        """Retorna configurações de liquidez."""
        return self.config.get('liquidity', {})
    
    def get_analysis_config(self) -> Dict[str, Any]:
        """Retorna configurações de análise."""
        return self.config.get('analysis', {})
    
    def get_strategy_config(self) -> Dict[str, Any]:
        """Retorna configurações de estratégia."""
        return self.config.get('strategy', {})
    
    def get_backtesting_config(self) -> Dict[str, Any]:
        """Retorna configurações de backtesting."""
        return self.config.get('backtesting', {})
    
    def get_cotahist_files(self) -> List[str]:
        """
        Retorna lista de arquivos COTAHIST com caminhos completos.
        
        Returns:
            Lista de caminhos para arquivos COTAHIST
        """
        project_root = self.config_path.parent.parent
        cotahist_files = self.get('data.cotahist_files', [])
        
        # Criar diretório data/ se não existir
        data_dir = project_root / 'data'
        data_dir.mkdir(exist_ok=True)
        
        return [str(project_root / file_name) for file_name in cotahist_files]
    
    def get_output_path(self, filename: str, category: str = None) -> str:
        """
        Gera caminho de saída para um arquivo em diretório organizado.
        
        Args:
            filename: Nome do arquivo
            category: Categoria do arquivo (liquidity, price_matrix, cointegration, etc.)
            
        Returns:
            Caminho completo para o arquivo de saída
        """
        from pathlib import Path
        
        project_root = self.config_path.parent.parent
        
        # Se categoria especificada, usar diretório organizado
        if category:
            output_dir = self.get(f'data.output.directories.{category}', f'outputs/{category}')
            full_path = project_root / output_dir
            
            # Criar diretório se não existir
            full_path.mkdir(parents=True, exist_ok=True)
            
            return str(full_path / filename)
        
        # Fallback para comportamento original
        return str(project_root / filename)
    
    def __str__(self) -> str:
        """Representação string das configurações."""
        return f"ConfigManager(config_path={self.config_path})"
    
    def __repr__(self) -> str:
        """Representação detalhada das configurações."""
        return f"ConfigManager(config_path={self.config_path}, sections={list(self.config.keys())})"


# Função de conveniência para criar uma instância global
_global_config = None

def get_config() -> ConfigManager:
    """
    Retorna uma instância global do ConfigManager.
    
    Returns:
        Instância singleton do ConfigManager
    """
    global _global_config
    if _global_config is None:
        _global_config = ConfigManager()
    return _global_config


def reload_config() -> ConfigManager:
    """
    Recarrega as configurações e retorna nova instância.
    
    Returns:
        Nova instância do ConfigManager
    """
    global _global_config
    _global_config = ConfigManager()
    return _global_config