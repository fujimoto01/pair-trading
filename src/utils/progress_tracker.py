"""
Sistema de Rastreamento de Progresso

Fornece indicadores de progresso e logging user-friendly para operações
de longa duração no pipeline de pair trading.
"""

import time
import sys
from typing import Optional, Any, Callable
from tqdm import tqdm
import logging


class ProgressTracker:
    """
    Sistema de rastreamento de progresso para operações longas.
    
    Fornece barras de progresso visuais, estimativas de tempo e logging
    detalhado para melhorar a experiência do usuário durante o processamento.
    """
    
    def __init__(self, show_progress: bool = True, logger: Optional[logging.Logger] = None):
        """
        Inicializa o rastreador de progresso.
        
        Args:
            show_progress: Se deve mostrar barras de progresso visuais
            logger: Logger para usar. Se None, cria um logger padrão
        """
        self.show_progress = show_progress
        self.logger = logger or logging.getLogger(__name__)
        self.current_operation = None
        self.start_time = None
        
    def start_operation(self, description: str, total_items: Optional[int] = None) -> 'ProgressTracker':
        """
        Inicia uma nova operação com rastreamento de progresso.
        
        Args:
            description: Descrição da operação
            total_items: Número total de itens a processar (para barra de progresso)
            
        Returns:
            Self para permitir method chaining
        """
        self.current_operation = description
        self.start_time = time.time()
        
        self.logger.info(f"Iniciando: {description}")
        
        if self.show_progress and total_items:
            self.progress_bar = tqdm(
                total=total_items,
                desc=description,
                unit="items",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
            )
        else:
            self.progress_bar = None
            
        return self
    
    def update(self, increment: int = 1, message: Optional[str] = None) -> None:
        """
        Atualiza o progresso da operação atual.
        
        Args:
            increment: Número de itens processados
            message: Mensagem adicional para logging
        """
        if self.progress_bar:
            self.progress_bar.update(increment)
            
        if message:
            self.logger.debug(message)
    
    def set_description(self, description: str) -> None:
        """
        Atualiza a descrição da operação atual.
        
        Args:
            description: Nova descrição
        """
        if self.progress_bar:
            self.progress_bar.set_description(description)
    
    def finish_operation(self, success: bool = True, message: Optional[str] = None) -> dict:
        """
        Finaliza a operação atual e retorna estatísticas.
        
        Args:
            success: Se a operação foi bem-sucedida
            message: Mensagem adicional
            
        Returns:
            Dicionário com estatísticas da operação
        """
        if not self.start_time:
            raise ValueError("Nenhuma operação foi iniciada")
        
        elapsed_time = time.time() - self.start_time
        
        if self.progress_bar:
            self.progress_bar.close()
            self.progress_bar = None
        
        status = "concluída com sucesso" if success else "falhou"
        
        if message:
            log_message = f"{self.current_operation} {status} em {elapsed_time:.2f}s - {message}"
        else:
            log_message = f"{self.current_operation} {status} em {elapsed_time:.2f}s"
        
        if success:
            self.logger.info(log_message)
        else:
            self.logger.error(log_message)
        
        stats = {
            'operation': self.current_operation,
            'elapsed_time': elapsed_time,
            'success': success,
            'message': message
        }
        
        # Reset
        self.current_operation = None
        self.start_time = None
        
        return stats
    
    def log_milestone(self, message: str, level: str = "info") -> None:
        """
        Registra um marco importante na operação.
        
        Args:
            message: Mensagem do marco
            level: Nível de log (info, warning, error)
        """
        if self.start_time:
            elapsed = time.time() - self.start_time
            message_with_time = f"[{elapsed:.1f}s] {message}"
        else:
            message_with_time = message
        
        getattr(self.logger, level.lower())(message_with_time)
    
    def estimate_remaining_time(self, completed: int, total: int) -> str:
        """
        Estima o tempo restante baseado no progresso atual.
        
        Args:
            completed: Número de itens completados
            total: Número total de itens
            
        Returns:
            String com estimativa de tempo restante
        """
        if not self.start_time or completed == 0:
            return "desconhecido"
        
        elapsed = time.time() - self.start_time
        rate = completed / elapsed
        remaining_items = total - completed
        
        if rate > 0:
            remaining_seconds = remaining_items / rate
            return self._format_time(remaining_seconds)
        else:
            return "desconhecido"
    
    def _format_time(self, seconds: float) -> str:
        """
        Formata tempo em segundos para formato legível.
        
        Args:
            seconds: Tempo em segundos
            
        Returns:
            Tempo formatado (ex: "2h 30m 15s")
        """
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes:.0f}m {secs:.0f}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours:.0f}h {minutes:.0f}m"


class OperationContext:
    """
    Context manager para operações com rastreamento automático de progresso.
    
    Example:
        >>> tracker = ProgressTracker()
        >>> with OperationContext(tracker, "Processando dados", 1000) as op:
        ...     for i in range(1000):
        ...         # fazer processamento
        ...         op.update()
    """
    
    def __init__(self, tracker: ProgressTracker, description: str, 
                 total_items: Optional[int] = None):
        """
        Inicializa o context manager.
        
        Args:
            tracker: Instância do ProgressTracker
            description: Descrição da operação
            total_items: Número total de itens
        """
        self.tracker = tracker
        self.description = description
        self.total_items = total_items
        self.success = True
        self.error_message = None
    
    def __enter__(self) -> ProgressTracker:
        """Inicia a operação ao entrar no contexto."""
        self.tracker.start_operation(self.description, self.total_items)
        return self.tracker
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Finaliza a operação ao sair do contexto."""
        if exc_type is not None:
            self.success = False
            self.error_message = str(exc_val)
        
        self.tracker.finish_operation(self.success, self.error_message)


def track_function_progress(description: str, show_progress: bool = True):
    """
    Decorator para adicionar rastreamento automático de progresso a funções.
    
    Args:
        description: Descrição da operação
        show_progress: Se deve mostrar barras de progresso
        
    Example:
        >>> @track_function_progress("Calculando cointegração")
        ... def analyze_cointegration(data):
        ...     # função que demora para executar
        ...     pass
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            tracker = ProgressTracker(show_progress)
            
            with OperationContext(tracker, description):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Instância global para conveniência
_global_tracker = None

def get_tracker() -> ProgressTracker:
    """
    Retorna instância global do ProgressTracker.
    
    Returns:
        Instância singleton do ProgressTracker
    """
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = ProgressTracker()
    return _global_tracker