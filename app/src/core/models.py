import datetime

from typing import Dict, Optional, List


from pydantic import BaseModel, Field

class CodeBlock(BaseModel):
    sql_query: Optional[str] = None
    python: Optional[str] = None

class Cgen(BaseModel):
    intent: str = Field(default="data-extraction")  # never None
    code: Optional[CodeBlock] = None                 # safe if LLM omits it

class UserRequest(BaseModel):
    user_input: str
    session_id: Optional[str] = None
    message_id: Optional[str] = None
    module_name : str
    request_timestamp: Optional[str] = None
    user_id:Optional[str] = None
    user_tab:Optional[str] = None

class MessageResponse(BaseModel):
    response: list
    response_id : str
    response_timestamp : datetime.datetime
    sql: Optional[str] = None
    # execution_times: list
    # session_id: Optional[str] = None
    # chat_history: list
    
    
    