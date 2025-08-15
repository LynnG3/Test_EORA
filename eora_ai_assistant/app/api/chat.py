import uuid
from typing import Optional, List, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from eora_ai_assistant.logger import logger
from app.core.dependencies import ai_engine, sessions

# Создание экземпляра APIRouter
router = APIRouter(tags=["chat"])


class MessageRequest(BaseModel):
    """
    Модель запроса для отправки сообщения.

    Attributes:
        message (str): Текст сообщения от пользователя
        session_id (str, optional): Идентификатор сессии для продолжения диалога
    """
    message: str
    session_id: Optional[str] = None


class SourceInfo(BaseModel):
    """
    Информация об источнике данных.

    Attributes:
        url (str): URL источника
        title (str): Заголовок источника
    """
    url: str
    title: str


class MessageResponse(BaseModel):
    """
    Модель ответа на сообщение пользователя.

    Attributes:
        session_id (str): Идентификатор сессии
        message (str): Текст ответа ассистента
        sources (List[Dict[str, str]]): Список использованных источников
    """
    session_id: str
    message: str
    sources: List[Dict[str, str]]


@router.post("/chat", response_model=MessageResponse)
async def chat(request: MessageRequest):
    """
    Обработка сообщения пользователя и генерация ответа.

    Args:
        request (MessageRequest): Запрос с сообщением пользователя

    Returns:
        MessageResponse: Ответ ассистента с источниками

    Raises:
        HTTPException: При ошибке генерации ответа
    """
    # Создает или получает сессию
    session_id = request.session_id or str(uuid.uuid4())
    logger.info(f"Processing message for session {session_id}")

    if session_id not in sessions:
        sessions[session_id] = []
        logger.info(f"Created new session {session_id}")

    # Сохраняет сообщение пользователя
    sessions[session_id].append({"role": "user", "content": request.message})
    logger.info(f"Added user message to session {session_id}")

    try:
        # Получает контекст и генерирует ответ
        logger.info(f"Getting context for query: {request.message}")
        context, sources = ai_engine.get_relevant_context(request.message)
        logger.info(f"Found {len(sources)} relevant sources")

        logger.info("Generating answer...")
        ai_response, sources = await ai_engine.generate_answer(request.message, context, sources)
        logger.info("Answer generated successfully")

        # Сохраняет ответ ассистента
        sessions[session_id].append({
            "role": "assistant",
            "content": ai_response,
            "sources": sources
        })
        logger.info(f"Added assistant response to session {session_id}")

        return MessageResponse(
            session_id=session_id,
            message=ai_response,
            sources=sources
        )

    except Exception as e:
        logger.exception(f"Error processing message: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate response: {str(e)}"
        )


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """
    Получение истории сообщений для указанной сессии.

    Args:
        session_id (str): Идентификатор сессии

    Returns:
        dict: Информация о сессии и истории сообщений

    Raises:
        HTTPException: Если сессия не найдена
    """
    logger.info(f"Retrieving session {session_id}")
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    logger.info(f"Returning session {session_id} with {len(sessions[session_id])} messages")
    return {"session_id": session_id, "messages": sessions[session_id]}
