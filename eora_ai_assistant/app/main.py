import time
from contextlib import asynccontextmanager
from pathlib import Path


from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from eora_ai_assistant.logger import logger
from app.core.config import settings
from app.core.dependencies import ai_engine
from app.api.chat import router as chat_router
from scripts.indexer import main as run_indexer
from scripts.url_extractor import SimpleURLExtractor


# Определение путей
BASE_DIR = Path(__file__).parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
VECTOR_STORE_PATH = DATA_DIR / "vector_store"
DATA_FILE = DATA_DIR / "scraped_data.json"

DATA_UPDATE_INTERVAL = 86400  # 24 часа в секундах


def _should_update_data() -> bool:
    """Проверяет, нужно ли обновлять данные."""
    return not DATA_FILE.exists(
    ) or DATA_FILE.stat().st_mtime < (time.time() - DATA_UPDATE_INTERVAL)


def _update_data() -> None:
    """Обновляет данные через скрипты парсинга."""
    try:
        logger.info("Starting data update process...")

        # Извлекает URLs
        extractor = SimpleURLExtractor()
        case_urls = extractor.extract_case_urls()

        if case_urls:
            logger.info(f"Found {len(case_urls)} URLs, starting scraping...")
            run_indexer()
            logger.info("Data updated successfully")
        else:
            logger.warning("No URLs found, skipping scraping")

    except Exception as e:
        logger.error(f"Failed to update data: {e}")


def _initialize_vector_store() -> None:
    """Инициализирует векторное хранилище."""
    if not DATA_FILE.exists():
        logger.warning(f"Data file {DATA_FILE} not found.")
        return

    index_file = VECTOR_STORE_PATH / "index.faiss"

    if index_file.exists():
        logger.info("Loading existing vector store...")
        ai_engine.load_vector_store(str(VECTOR_STORE_PATH))
    else:
        logger.info("Creating new vector store...")
        documents = ai_engine.load_data(str(DATA_FILE))
        ai_engine.create_vector_store(documents)
        ai_engine.save_vector_store(str(VECTOR_STORE_PATH))


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    """
    Контекстный менеджер жизненного цикла приложения."""
    try:
        # Обновляем данные если нужно
        if _should_update_data():
            _update_data()

        # Инициализируем векторное хранилище
        _initialize_vector_store()

    except Exception as e:
        logger.exception(f"Error during application startup: {e}")

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
