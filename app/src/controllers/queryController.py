import logging
import time
import traceback

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from core.models import UserRequest,MessageResponse
from datetime import datetime, timezone
from bson import ObjectId
from core.conversation import MultiTurnConversation


router = APIRouter()



@router.post("/query", response_model=MessageResponse)
async def handle_query(request: UserRequest, state_request:Request):

    start_time = time.time()
    conv = None
    error_message = None

    # CREATE RESPONSE ID & PLACEHOLDER RECORD FIRST
    response_id = str(ObjectId())
    response_timestamp = datetime.utcnow()

    initial_message_doc = {
        "session_id": request.session_id,
        "message_id": request.message_id,
        "response_id": response_id,
        "user_input": request.user_input,
        "translated_input": None,
        "response": None,
        "execution_times": [],
        "input_timestamp": request.request_timestamp,
        "timestamp": response_timestamp,
        "response_time": None,
        "error_message": None,
        "like": None,
        "feedback":None
    }
    session_manager = state_request.app.state.session_manager

    session_manager.add_message_to_session(initial_message_doc)

    try:
        conv = await session_manager.get_session(
            request.request_timestamp,
            request.session_id,
            request.module_name,
            request.user_id,
            request.user_input
        )

        user_input, is_arabic = conv.translate_arabic_to_english(request.user_input)
        response = await conv.chat(user_input)

        for res in response:
            if res["type"] == "text":
                res["content"] = conv.translate_english_to_arabic(res["content"], is_arabic)

        # UPDATE SUCCESS
        session_manager.update_message_after_response(
            response_id=response_id,
            update_data={
                "translated_input": user_input,
                "response": response,
                "execution_times": conv.timing_data,
                "response_time": time.time() - start_time
            }
        )

        session_manager.save_history(
            request.session_id,
            conv.history()
        )

        return MessageResponse(
            response=response,
            response_id=response_id,
            response_timestamp=response_timestamp
        )

    except Exception:
        error_message = traceback.format_exc()
        logging.error(error_message)

        # UPDATE ERROR
        session_manager.update_message_after_response(
            response_id=response_id,
            update_data={
                "response": [{
                    "type": "text",
                    "content": "We acknowledge your question. Energon is in the training phase, and the response will be available soon."
                }],
                "error_message": error_message,
                "response_time": time.time() - start_time
            }
        )

        return MessageResponse(
            response=[{
                "type": "text",
                "content": "We acknowledge your question. Energon is in the training phase, and the response will be available soon."
            }],
            response_id=response_id,
            response_timestamp=response_timestamp
        )




