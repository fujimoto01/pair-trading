"""
Sistema de Logging

Configuração centralizada de logging para o pipeline de pair trading.
"""

import logging
import sys
from typing import Optional
from pathlib import Path


def setup_logger(name: str = "pair_trading", 
                level: str = "INFO",
                log_file: Optional[str] = None,
                format_string: Optional[str] = None) -> logging.Logger:
    """
    Configura e retorna um logger para o projeto.
    
    Args:
        name: Nome do logger
        level: Nível de logging (DEBUG, INFO, WARNING, ERROR)
        log_file: Arquivo para salvar logs (opcional)
        format_string: Formato personalizado dos logs
        
    Returns:
        Logger configurado
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Criar logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Evitar duplicação de handlers
    if logger.handlers:
        return logger
    
    # Formatter
    formatter = logging.Formatter(format_string)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (opcional)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "pair_trading") -> logging.Logger:
    """
    Retorna um logger existente ou cria um novo com configuração padrão.
    
    Args:
        name: Nome do logger
        
    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # Se não tem handlers, configurar com padrões
        return setup_logger(name)
    
    return logger