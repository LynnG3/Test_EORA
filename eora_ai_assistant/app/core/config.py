import os
from typing import List

from dotenv import load_dotenv
from pydantic_settings import BaseSettings


load_dotenv()


class Settings(BaseSettings):
    PROJECT_NAME: str = "EORA AI Assistant"
    API_PREFIX: str = "/api"
    OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
    CORS_ORIGINS: List[str] = ["*"]
    DATA_DIR: str = "data"
    VECTOR_STORE_PATH: str = "data/vector_store"

    class Config:
        env_file = ".env"


settings = Settings()
