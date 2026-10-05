import json
import logging
import time
import traceback

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from core.models import UserRequest,MessageResponse
from datetime import datetime
from bson import ObjectId


router = APIRouter()

FALLBACK_RESPONSE = [{
    "type": "text",
    "content": "We acknowledge your question. OpsInsight is still learning this type of request, and the response will be available soon."
}]


def _start_message(request: UserRequest, session_manager) -> tuple[str, datetime]:
    """Create the response ID and insert the placeholder message record."""
    response_id = str(ObjectId())
    response_timestamp = datetime.utcnow()

    session_manager.add_message_to_session({
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
    })
    return response_id, response_timestamp


def _generated_sql(conv):
    generated = conv.last_generated_code if conv else None
    return getattr(generated, "sql_query", None) if generated else None


def _save_success(session_manager, request, conv, response_id, user_input, response, start_time):
    session_manager.update_message_after_response(
        response_id=response_id,
        update_data={
            "translated_input": user_input,
            "response": response,
            "sql": _generated_sql(conv),
            "execution_times": conv.timing_data,
            "response_time": time.time() - start_time
        }
    )
    session_manager.save_history(request.session_id, conv.history())


def _save_error(session_manager, response_id, error_message, start_time):
    logging.error(error_message)
    session_manager.update_message_after_response(
        response_id=response_id,
        update_data={
            "response": FALLBACK_RESPONSE,
            "error_message": error_message,
            "response_time": time.time() - start_time
        }
    )


async def _open_conversation(request: UserRequest, session_manager):
    return await session_manager.get_session(
        request.request_timestamp,
        request.session_id,
        request.module_name,
        request.user_id,
        request.user_input
    )


@router.post("/query", response_model=MessageResponse)
async def handle_query(request: UserRequest, state_request:Request):

    start_time = time.time()
    session_manager = state_request.app.state.session_manager
    response_id, response_timestamp = _start_message(request, session_manager)

    try:
        conv = await _open_conversation(request, session_manager)

        user_input, is_arabic = conv.translate_arabic_to_english(request.user_input)
        response = await conv.chat(user_input)

        for res in response:
            if res["type"] == "text":
                res["content"] = conv.translate_english_to_arabic(res["content"], is_arabic)

        _save_success(session_manager, request, conv, response_id, user_input, response, start_time)

        return MessageResponse(
            response=response,
            response_id=response_id,
            response_timestamp=response_timestamp,
            sql=_generated_sql(conv)
        )

    except Exception:
        _save_error(session_manager, response_id, traceback.format_exc(), start_time)

        return MessageResponse(
            response=FALLBACK_RESPONSE,
            response_id=response_id,
            response_timestamp=response_timestamp
        )


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


@router.post("/query/stream")
async def handle_query_stream(request: UserRequest, state_request:Request):
    """
    Server-Sent Events version of /query.

    Events (in order):
        start   {response_id, response_timestamp}
        status  {stage, message}            progress: thinking, generating_sql, running_query, ...
        delta   {index, text}               incremental text for response part `index`
        part    {index, part}               final content of part `index` (text | table | image)
        sql     {sql}                       generated SQL (data questions only)
        done    {response_id, response_timestamp, response, sql}
    """
    start_time = time.time()
    session_manager = state_request.app.state.session_manager
    response_id, response_timestamp = _start_message(request, session_manager)

    async def event_stream():
        yield _sse("start", {"response_id": response_id, "response_timestamp": response_timestamp})
        conv = None
        try:
            conv = await _open_conversation(request, session_manager)

            user_input, is_arabic = conv.translate_arabic_to_english(request.user_input)
            response = []

            # Arabic answers are translated as a whole, so token streaming is
            # only enabled for English questions.
            async for event in conv.chat_stream(user_input, stream_text=not is_arabic):
                if event["event"] == "part":
                    part = event["data"]["part"]
                    if part["type"] == "text":
                        part["content"] = conv.translate_english_to_arabic(part["content"], is_arabic)
                    response.append(part)
                yield _sse(event["event"], event["data"])

            _save_success(session_manager, request, conv, response_id, user_input, response, start_time)
            yield _sse("done", {
                "response_id": response_id,
                "response_timestamp": response_timestamp,
                "response": response,
                "sql": _generated_sql(conv),
            })

        except Exception:
            _save_error(session_manager, response_id, traceback.format_exc(), start_time)
            yield _sse("part", {"index": 0, "part": FALLBACK_RESPONSE[0], "replace_all": True})
            yield _sse("done", {
                "response_id": response_id,
                "response_timestamp": response_timestamp,
                "response": FALLBACK_RESPONSE,
                "sql": None,
            })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
