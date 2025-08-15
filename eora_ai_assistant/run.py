"""
Скрипт для запуска FastAPI приложения.
"""
import sys
from pathlib import Path
import uvicorn

# Добавляет родительскую директорию в sys.path
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from eora_ai_assistant.logger import logger


logger.info("Starting application...")


if __name__ == "__main__":
    logger.info("Starting application from run.py")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
