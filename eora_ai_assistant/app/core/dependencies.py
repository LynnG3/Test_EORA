"""
Модуль с общими зависимостями для приложения.

Содержит экземпляры классов и объекты, которые используются
в разных частях приложения, что позволяет избежать циклических импортов.
"""


from eora_ai_assistant.logger import logger
from app.services.ai_engine import AIEngine
from app.core.config import settings

# Инициализация AI Engine
ai_engine = AIEngine(use_local_llm=settings.USE_LOCAL_LLM)

# Хранилище сессий
sessions = {}
logger.info("Session storage initialized")
