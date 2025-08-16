"""API эндпоинты для работы с чатом."""
import uuid
from typing import Optional, List, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from eora_ai_assistant.logger import logger
from app.core.dependencies import ai_engine, sessions


router = APIRouter(tags=["chat"])


class MessageRequest(BaseModel):
    """ Модель запроса для отправки сообщения. """

    message: str
    session_id: Optional[str] = None


class SourceInfo(BaseModel):
    """Информация об источнике данных."""

    url: str
    title: str


class MessageResponse(BaseModel):
    """ Модель ответа на сообщение пользователя. """
    session_id: str
    message: str
    sources: List[Dict[str, str]]


def _get_or_create_session(session_id: Optional[str]) -> str:
    """Создает или получает существующую сессию."""
    if session_id is None:
        session_id = str(uuid.uuid4())
        logger.info(f"Created new session {session_id}")

    if session_id not in sessions:
        sessions[session_id] = []

    return session_id


def _add_message_to_session(
        session_id: str,
        role: str,
        content: str,
        sources: Optional[List] = None
    ) -> None:
    """Добавляет сообщение в сессию."""
    message_data = {"role": role, "content": content}
    if sources:
        message_data["sources"] = sources

    sessions[session_id].append(message_data)
    logger.info(f"Added {role} message to session {session_id}")


@router.post("/chat", response_model=MessageResponse)
async def chat(request: MessageRequest):
    """ Обработка сообщения пользователя и генерация ответа.  """
    session_id = _get_or_create_session(request.session_id)
    logger.info(f"Processing message for session {session_id}")

    _add_message_to_session(session_id, "user", request.message)

    try:
        # Получает контекст и генерирует ответ
        logger.info(f"Getting context for query: {request.message}")
        context, sources = ai_engine.get_relevant_context(request.message)
        logger.info(f"Found {len(sources)} relevant sources")

        logger.info("Generating answer...")
        ai_response, sources = await ai_engine.generate_answer(
            request.message,
            context, sources
        )
        logger.info("Answer generated successfully")

        # Сохраняет ответ ассистента
        _add_message_to_session(
            session_id,
            "assistant",
            ai_response, sources
        )

        return MessageResponse(
            session_id=session_id,
            message=ai_response,
            sources=sources
        )

    except Exception as e:
        logger.exception(f"Error processing message: {e}")
        # Обобщенное сообщение об ошибке для пользователя
        error_message = (
            f"Произошла ошибка при обработке вашего запроса. "
            f"Пожалуйста, попробуйте позже."
        )
        _add_message_to_session(session_id, "assistant", error_message)

        return MessageResponse(
            session_id=session_id,
            message=error_message,
            sources=[]
        )


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """ Получение истории сообщений для указанной сессии. """
    logger.info(f"Retrieving session {session_id}")
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    logger.info(
        f"Returning session {session_id} "
        f"with {len(sessions[session_id])} messages"
    )
    return {"session_id": session_id, "messages": sessions[session_id]}
