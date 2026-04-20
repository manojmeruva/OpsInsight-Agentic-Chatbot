from pydantic import BaseModel
from typing import Optional, List, Dict
import datetime


class Sessions(BaseModel):
    session_id: str
    user_email: str
    session_name: str
    module_name:str
    avg_response_time: float
    query_exec_time: float
    created_at: datetime.datetime
    last_updated: datetime.datetime
    chat_history: dict  # Gemini native format (list of messages)


class SessionMessages(BaseModel):
    session_id: str
    message_id: str
    user_input: str
    response: List[str]
    execution_times: List[float]
    input_timestamp: datetime.datetime
    timestamp: datetime.datetime
    response_time: float




