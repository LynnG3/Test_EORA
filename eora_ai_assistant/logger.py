"""
Модуль для настройки логирования.

Предоставляет единую точку настройки логирования для всего приложения.
"""

import logging
import sys

def setup_logging():
    """
    Настраивает логирование для приложения.
    
    Выводит логи в консоль с уровнем INFO.
    """
    # Сбрасываем существующие обработчики
    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)

    # Настройки базового логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)

    return logging.getLogger(__name__)


# Создаетлоггер при импорте модуля
logger = setup_logging()
