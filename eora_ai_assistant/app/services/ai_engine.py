"""
Модуль для работы с OpenAI API и векторным поиском.

Этот модуль обеспечивает взаимодействие с API OpenAI для генерации ответов
и использует векторное хранилище для поиска релевантного контекста.
"""

import os
import json
from typing import List, Dict, Tuple

from openai import AsyncOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
# from langchain_openai import OpenAIEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings

from eora_ai_assistant.logger import logger
from app.core.config import settings


class AIEngine:
    """
    Движок для работы с OpenAI API и векторным поиском.

    Обеспечивает загрузку данных, создание векторного хранилища,
    поиск релевантного контекста и генерацию ответов на вопросы.
    """

    def __init__(self, api_key=None, model=None):
        """
        Инициализация движка AI.

        Args:
            api_key (str, optional): API ключ для OpenAI
            model (str, optional): Название модели OpenAI
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.vector_store = None

    def load_data(self, data_file: str) -> List[Document]:
        """
        Загрузка данных из JSON-файла.

        Args:
            data_file (str): Путь к файлу с данными

        Returns:
            List[Document]: Список документов для индексации

        Raises:
            FileNotFoundError: Если файл не найден
            json.JSONDecodeError: При ошибке парсинга JSON
        """
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        documents = []
        for item in data:
            doc = Document(
                page_content=item['text'],
                metadata={"source": item['url'], "title": item['title']}
            )
            documents.append(doc)

        print(f"Loaded {len(documents)} documents from {data_file}")
        return documents

    def create_vector_store(self, documents: List[Document]) -> FAISS:
        """
        Создание векторного хранилища из документов.

        Args:
            documents (List[Document]): Список документов для индексации

        Returns:
            FAISS: Векторное хранилище
        """
        # Разбиваем документы на чанки
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = text_splitter.split_documents(documents)
        print(f"Split into {len(chunks)} chunks")

        # Создаем векторное хранилище
        # embeddings = OpenAIEmbeddings(openai_api_key=self.api_key)
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_store = FAISS.from_documents(chunks, embeddings)

        return self.vector_store

    def save_vector_store(self, directory: str) -> None:
        """
        Сохранение векторного хранилища на диск.

        Args:
            directory (str): Директория для сохранения

        Raises:
            ValueError: Если векторное хранилище не инициализировано
        """
        if not self.vector_store:
            raise ValueError("Vector store not initialized")

        # Создаем директорию, если она не существует
        os.makedirs(directory, exist_ok=True)

        self.vector_store.save_local(directory)
        print(f"Vector store saved to {directory}")

    def load_vector_store(self, directory: str) -> None:
        """
        Загрузка векторного хранилища с диска.

        Args:
            directory (str): Директория с сохраненным хранилищем

        Raises:
            FileNotFoundError: Если директория не существует
        """
        if not os.path.exists(directory):
            raise FileNotFoundError(f"Vector store directory {directory} not found")

        # embeddings = OpenAIEmbeddings(openai_api_key=self.api_key)
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_store = FAISS.load_local(
            directory,
            embeddings,
            allow_dangerous_deserialization=True
            )
        logger.info(f"Vector store loaded from {directory}")

    def get_relevant_context(self, query: str, k: int = 3) -> Tuple[str, List[Dict[str, str]]]:
        """
        Поиск релевантного контекста для запроса.

        Args:
            query (str): Текст запроса
            k (int, optional): Количество результатов. По умолчанию 3.

        Returns:
            Tuple[str, List[Dict[str, str]]]: Контекст и список источников

        Raises:
            ValueError: Если векторное хранилище не инициализировано
        """
        if not self.vector_store:
            raise ValueError("Vector store not initialized")

        results = self.vector_store.similarity_search(query, k=k)

        context = ""
        sources = []

        for doc in results:
            context += doc.page_content + "\n\n"
            source_url = doc.metadata["source"]

            # Добавляем источник только если его еще нет в списке
            if not any(s["url"] == source_url for s in sources):
                sources.append({
                    "url": source_url,
                    "title": doc.metadata.get("title", source_url)
                })

        return context, sources

    async def generate_answer(
            self, query: str, context: str, sources: List[Dict[str, str]]
        ) -> Tuple[str, List[Dict[str, str]]]:
        """
        Генерация ответа на основе контекста.

        Args:
            query (str): Вопрос пользователя
            context (str): Релевантный контекст
            sources (List[Dict[str, str]]): Список источников

        Returns:
            Tuple[str, List[Dict[str, str]]]: Ответ и список использованных источников
        """
        source_text = "\n".join([f"[{i+1}] {s['title']} - {s['url']}" for i, s in enumerate(sources)])

        system_prompt = f"""
        Ты - AI-ассистент компании EORA, специализирующейся на разработке
        решений с использованием искусственного интеллекта.
        Отвечай на вопросы пользователей на основе предоставленного контекста.
        Если в контексте нет информации для ответа,
        скажи, что у тебя недостаточно данных.
        В конце ответа укажи источники информации в формате:

        Источники: [1], [2], ...

        Контекст:
        {context}

        Доступные источники:
        {source_text}
        """

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.7,
            max_tokens=500
        )

        return response.choices[0].message.content, sources
