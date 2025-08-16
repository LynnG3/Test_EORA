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
    USE_LOCAL_LLM: bool = os.environ.get(
        "USE_LOCAL_LLM", "True"
    ).lower() == "true"
    HF_MODEL_ID: str = os.environ.get(
        "HF_MODEL_ID", "timpal0l/mdeberta-v3-base-squad2"
    )
    CORS_ORIGINS: List[str] = ["*"]
    DATA_DIR: str = "data"
    VECTOR_STORE_PATH: str = "data/vector_store"

    # OpenAI настройки
    OPENAI_MAX_TOKENS: int = int(
        os.environ.get("OPENAI_MAX_TOKENS", "500")
    )
    OPENAI_TEMPERATURE: float = float(
        os.environ.get("OPENAI_TEMPERATURE", "0.3")
    )

    class Config:

        env_file = ".env"


settings = Settings()
