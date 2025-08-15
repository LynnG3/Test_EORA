import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from eora_ai_assistant.logger import logger
from app.core.config import settings
from app.core.dependencies import ai_engine, sessions
from app.api.chat import router as chat_router


# Определение путей к директориям
BASE_DIR = Path(__file__).parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    """
    Контекстный менеджер жизненного цикла приложения."""
    try:
        data_dir = BASE_DIR / "data"
        vector_store_path = data_dir / "vector_store"
        data_file = data_dir / "scraped_data.json"

        if not data_file.exists():
            logger.warning(f"Data file {data_file} not found.")
        else:
            # Проверяем наличие индексного файла, а не просто директории
            index_file = vector_store_path / "index.faiss"
            if index_file.exists():
                logger.info("Loading existing vector store...")
                ai_engine.load_vector_store(str(vector_store_path))
            else:
                logger.info("Creating new vector store...")
                documents = ai_engine.load_data(str(data_file))
                ai_engine.create_vector_store(documents)
                ai_engine.save_vector_store(str(vector_store_path))
    except Exception as e:
        logger.exception(f"Error initializing vector store: {e}")

    yield


# Инициализация FastAPI приложения с менеджером жизненного цикла
app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение статических файлов
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Инициализация шаблонизатора
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# Маршрут для главной страницы
@app.get("/")
async def root(request: Request):
    """
    Отображение главной страницы с чат-интерфейсом.
    """
    logger.info("Rendering index page")
    return templates.TemplateResponse("index.html", {"request": request})

# API эндпоинты для работы с чатом
app.include_router(chat_router, prefix="/api")
logger.info("API routes registered")
