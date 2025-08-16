"""
Модуль для работы с AI API и векторным поиском.

Этот модуль обеспечивает взаимодействие с AI для генерации ответов
и использует векторное хранилище для поиска релевантного контекста.
"""

import os
import json
from typing import List, Dict, Tuple, Optional

from openai import AsyncOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from transformers import pipeline

from eora_ai_assistant.logger import logger
from app.core.config import settings


class AIEngine:
    """
    Движок для работы с AI и векторным поиском.

    Обеспечивает загрузку данных, создание векторного хранилища,
    поиск релевантного контекста и генерацию ответов на вопросы.
    """

    def __init__(self, use_local_llm: Optional[bool] = None):
        """
        Инициализация движка AI.

        Args:
            use_local_llm (bool, optional): Использовать локальную модель вместо OpenAI
        """
        self.use_local_llm = (
            use_local_llm if use_local_llm is not None
            else settings.USE_LOCAL_LLM
        )
        self.hf_model: Optional[pipeline] = None
        self.openai_client: Optional[AsyncOpenAI] = None
        self.vector_store: Optional[FAISS] = None

        # Инициализирует OpenAI клиент если нужно
        if not self.use_local_llm:
            if not settings.OPENAI_API_KEY:
                logger.warning(
                    "OpenAI API key not provided, falling back to local LLM"
                )
                self.use_local_llm = True
            else:
                self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info("OpenAI client initialized")

        if self.use_local_llm:
            logger.info(
                f"Local LLM mode enabled. "
                f"Will initialize HuggingFace model when needed."
            )

    def _initialize_hf_model(self) -> None:
        """ Инициализация модели HuggingFace для question-answering. """
        if self.hf_model is not None:
            return

        try:
            model_id = settings.HF_MODEL_ID
            logger.info(f"Initializing HuggingFace model: {model_id}")

            # Создает пайплайн для question-answering
            self.hf_model = pipeline(
                "question-answering",
                model=model_id,
                tokenizer=model_id
            )

            logger.info(
                "HuggingFace question-answering model initialized successfully"
            )

        except Exception as e:
            logger.error(f"Failed to initialize HuggingFace model: {e}")
            self.hf_model = None

    def _get_embeddings(self):
        """Возвращает локальные embeddings для экономии API вызовов."""
        return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    def load_data(self, data_file: str) -> List[Document]:
        """ Загрузка данных из JSON-файла. """
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            documents = [
                Document(
                    page_content=item['text'],
                    metadata={"source": item['url'], "title": item['title']}
                )
                for item in data
            ]

            logger.info(f"Loaded {len(documents)} documents from {data_file}")
            return documents

        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading data: {e}")
            raise

    def create_vector_store(self, documents: List[Document]) -> FAISS:
        """Создание векторного хранилища из документов."""
        # Разбивает документы на чанки
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = text_splitter.split_documents(documents)
        logger.info(f"Split into {len(chunks)} chunks")

        embeddings = self._get_embeddings()
        self.vector_store = FAISS.from_documents(chunks, embeddings)
        return self.vector_store

    def save_vector_store(self, directory: str) -> None:
        """Сохранение векторного хранилища на диск."""
        if not self.vector_store:
            raise ValueError("Vector store not initialized")

        os.makedirs(directory, exist_ok=True)
        self.vector_store.save_local(directory)
        logger.info(f"Vector store saved to {directory}")

    def load_vector_store(self, directory: str) -> None:
        """ Загрузка векторного хранилища с диска. """
        if not os.path.exists(directory):
            raise FileNotFoundError(
                f"Vector store directory {directory} not found"
            )

        embeddings = self._get_embeddings()
        self.vector_store = FAISS.load_local(
            directory,
            embeddings,
            allow_dangerous_deserialization=True
            )
        logger.info(f"Vector store loaded from {directory}")

    def get_relevant_context(
        self, query: str, k: int = 3
    ) -> Tuple[str, List[Dict[str, str]]]:
        """ Поиск релевантного контекста для запроса. """
        if not self.vector_store:
            raise ValueError("Vector store not initialized")

        results = self.vector_store.similarity_search(query, k=k)

        context = "\n\n".join(doc.page_content for doc in results)

        sources = []
        seen_urls = set()

        for doc in results:
            source_url = doc.metadata["source"]
            if source_url not in seen_urls:
                sources.append({
                    "url": source_url,
                    "title": doc.metadata.get("title", source_url)
                })
                seen_urls.add(source_url)

        return context, sources

    def _extract_best_answer(self, result: List[Dict]) -> Optional[Dict]:
        """Извлекает лучший ответ из результатов модели."""
        if not result:
            return None

        # Сортирует по длине ответа (предпочтительны более развернутые)
        sorted_results = sorted(
            result, 
            key=lambda x: len(x.get('answer', '').strip()), 
            reverse=True
        )

        # Ищет ответ с минимальной длиной 30 символов
        for res in sorted_results:
            if len(res.get('answer', '').strip()) >= 30:
                return res

        # Если не найден, берет первый непустой
        return next(
            (res for res in sorted_results if res.get(
                'answer', ''
            ).strip()), None
        )

    async def _generate_huggingface_answer(
        self, query: str, context: str, sources: List[Dict[str, str]]
    ) -> Tuple[str, List[Dict[str, str]]]:
        """Генерация ответа на основе контекста"""
        try:
            if self.hf_model is None:
                self._initialize_hf_model()

            if self.hf_model is None:
                return (
                    "Не удалось инициализировать модель для генерации ответов.",
                    sources
                )

            logger.info(f"Query: {query}")
            logger.info(f"Context length: {len(context)}")            

            max_context_length = 512  # DeBERTa имеет ограничение в 512 токенов
            if len(context) > max_context_length:
                context = context[:max_context_length] + "..."

            logger.info(f"Context length after truncation: {len(context)}")

            # question-answering pipeline
            result = self.hf_model(
                question=query,
                context=context,
                max_answer_length=300,  # Максимальная длина ответа
                handle_impossible_answer=True,  # Обработка случаев без ответа
                top_k=5,
            )

            logger.info(f"QA result: {result}")

            # Извлекает лучший ответ
            best_result = self._extract_best_answer(result)

            if best_result and 'answer' in best_result:
                answer = best_result['answer'].strip()
                logger.info(f"Final answer: '{answer}'")

                if len(answer) < 8:
                    return (
                        "В предоставленном контексте нет информации "
                        "для ответа на этот вопрос.", sources
                    )

                return answer, sources
            else:
                return "Не удалось извлечь ответ из контекста.", sources

        except Exception as e:
            logger.error(f"Error generating HuggingFace response: {e}")
            raise

    async def _generate_openai_answer(self, query: str, context: str, sources: List[Dict[str, str]]) -> Tuple[str, List[Dict[str, str]]]:
        """Генерация ответа через OpenAI API."""
        try:
            if not self.openai_client:
                raise ValueError("OpenAI client not initialized")

            # Формируем промпт для русскоязычного ответа
            system_prompt = """Ты - AI-ассистент компании EORA, специализирующейся на разработке решений с использованием искусственного интеллекта. 

Отвечай на вопросы пользователей на основе предоставленного контекста. Если в контексте нет информации для ответа, скажи, что у тебя недостаточно данных.

Отвечай на русском языке, используя только информацию из контекста. Не придумывай факты, которых нет в контексте.

В конце ответа укажи источники информации в формате: Источники: [1], [2], ..."""

            user_prompt = f"""Контекст: {context}

Вопрос: {query}

Ответь на основе контекста:"""

            response = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=settings.OPENAI_MAX_TOKENS,
                temperature=settings.OPENAI_TEMPERATURE,
                top_p=0.9,
                frequency_penalty=0.1,
                presence_penalty=0.1
            )

            answer = response.choices[0].message.content.strip()
            logger.info(f"OpenAI generated answer: {answer}")

            return answer, sources

        except Exception as e:
            logger.error(f"Error generating OpenAI response: {e}")
            raise

    async def generate_answer(
        self, query: str, context: str, sources: List[Dict[str, str]]
    ) -> Tuple[str, List[Dict[str, str]]]:
        """Генерация ответа на основе контекста."""
        try:
            if self.use_local_llm:
                return await self._generate_huggingface_answer(
                    query, context, sources
                )
            else:
                try:
                    # Попытка использования OpenAI
                    return await self._generate_openai_answer(
                        query, context, sources
                    )
                except Exception as openai_error:
                    logger.error(f"OpenAI failed, falling back to local model: {openai_error}")
                    # Автоматически переключает на локальную модель
                    logger.info("Switching to local HuggingFace model as fallback")
                    return await self._generate_huggingface_answer(
                        query, context, sources
                    )
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"Произошла ошибка при генерации ответа: {str(e)}", sources
