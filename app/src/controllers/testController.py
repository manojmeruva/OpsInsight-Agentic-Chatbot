import logging
import time
import traceback
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from core.models import UserRequest,MessageResponse
from datetime import datetime
from bson import ObjectId
from core.conversation import MultiTurnConversation


router = APIRouter()






class AutoTestRequest(BaseModel):
    user_input: str
    module_name: str
    history: Optional[list] = []

class AutoTagTestRequest(BaseModel):
    user_input: str
    module_name: str
    history: Optional[list] = []
    test: bool = True
    tag_list: Optional[list] = []
    system_domain_prompt: Optional[str] = None

# @router.post("/auto-test-tag")
# async def auto_test_tag_api(payload:AutoTagTestRequest):
#     try:
#         conv = await MultiTurnConversation.create(
#             payload.history,
#             [],
#             payload.module_name,
#             current_timestamp=datetime.utcnow(),
#             test=payload.test,
#             sys_test_prompt=payload.system_domain_prompt,
#             tag_list=payload.tag_list
#         )

#         # FIX HERE
#         response, timing = conv._send_message_with_timing(message=payload.user_input)

#         tool_call = conv._extract_tool_call(response)

#         hist = conv.history()
#         history_to_save = [message.model_dump() for message in hist]

#         return JSONResponse(
#             status_code=200,
#             content={
#                 "tag": tool_call.args.get("tag"),
#                 "history": history_to_save,
#                 "timing": timing
#             }
#         )

#     except Exception as e:
#         return JSONResponse(
#             status_code=500,
#             content={"success": False, "error": str(e)}
#         )

@router.post("/auto-test")
async def auto_test_api(payload: AutoTestRequest):
    try:
        

        conv = await MultiTurnConversation.create(payload.history,[],payload.module_name,current_timestamp=datetime.utcnow())
        response = await conv.chat(payload.user_input)
        hist = conv.history()
        history_to_save = [message.model_dump() for message in hist]
        def extract_sql_from_trace(trace):
            """
            Recursively search execution tree and return all SQL queries found.
            """
            sql_queries = []

            def walk(nodes):
                for node in nodes:
                    # If this node has SQL, capture it
                    if "sql" in node and node["sql"]:
                        sql_queries.append(node["sql"])

                    # Recurse into children
                    if "children" in node and node["children"]:
                        walk(node["children"])

            walk(trace)
            return sql_queries

        return JSONResponse(status_code=200,
                            content={"sql": extract_sql_from_trace(conv.timing_data),"response":response,"history": history_to_save})

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )



sessions = {}
messages = {}

@router.post("/test-langchain", response_model=MessageResponse)
async def test_query(request: UserRequest):
    # Initialize before try so they're always defined
    response_id = str(ObjectId())
    response_timestamp = datetime.utcnow()
    

    try:
        # Use .get() with empty list fallback instead of direct key access
        conv = await MultiTurnConversation.create(
            sessions.get(request.session_id, []),
            messages.get(request.session_id, []),
            request.module_name,
            request.request_timestamp
        )

        user_input, is_arabic = conv.translate_arabic_to_english(request.user_input)
        response = await conv.chat(user_input)

        for res in response:
            if res["type"] == "text":
                res["content"] = conv.translate_english_to_arabic(res["content"], is_arabic)

        sessions[request.session_id] = conv.history()
        
        messages.get(request.session_id,[]).append(request.user_input)
        
        return MessageResponse(
            response=response,
            response_id=response_id,
            response_timestamp=response_timestamp
        )

    except Exception:
        error_message = traceback.format_exc()
        logging.error(error_message)

        return MessageResponse(
            response=[{
                "type": "text",
                "content": "We acknowledge your question. Energon is in the training phase, and the response will be available soon."
            }],
            response_id=response_id,
            response_timestamp=response_timestamp
        )


