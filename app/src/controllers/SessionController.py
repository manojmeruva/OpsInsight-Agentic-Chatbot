
import json
import logging
import time
import traceback

from fastapi import APIRouter, Request, Header
from pydantic import BaseModel
from fastapi.responses import JSONResponse



class OrderedJSONResponse(JSONResponse):
    def render(self, content: any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            indent=2,
            sort_keys=False   # change to False if you want insertion order
        ).encode("utf-8")



router = APIRouter()




class LoadSessionHistoryRequest(BaseModel):
    user_email: str
    days: int = 7

class ArchiveSessionDataRequest(BaseModel):
    user_email: str

@router.post("/load-session-history")
async def load_session_history(request: LoadSessionHistoryRequest,state_request:Request):
    """
    Load last N days of session history from Elasticsearch into MongoDB.
    Called by frontend on user login.
    """
    try:
        session_manager = state_request.app.state.session_manager
        result = session_manager.load_session_history_from_es(
            user_email=request.user_email,
            days=request.days
        )
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        logging.error(f"load-session-history failed: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "reason": str(e)})

@router.post("/archive-session-data")
async def archive_session_data(request: ArchiveSessionDataRequest,state_request:Request):
    """
    Archive all of user's session data from MongoDB to Elasticsearch.
    Called by frontend on user logout.
    """
    try:
        session_manager = state_request.app.state.session_manager
        result = session_manager.archive_session_data_to_es(
            user_email=request.user_email
        )
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        logging.error(f"archive-session-data failed: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "reason": str(e)})


@router.delete("/deletesession")
async def delete_session(request:Request,session_id: str = Header(None)):
    
    try:
        print(session_id)
        session_manager = request.app.state.session_manager
        session_manager.delete_session(session_id)
        return {"message": "Session deleted successfully"}
    except Exception as e:
        return {"error":str(e)}

@router.get("/getsession/data")
async def get_session_data(request:Request,session_id: str = Header(None)):

    try:
        session_manager = request.app.state.session_manager
        return session_manager.get_session_messages(session_id)
    except Exception as e:
        return {"error":str(e)}

@router.get("/getsessions")
async def get_sessions(request:Request,user_id: str = Header(None)):

    try:
        session_manager = request.app.state.session_manager
        sessions = session_manager.get_active_sessions(user_id)
        ordered_response = {
                        "Today": sessions["Today"],
                        "Yesterday": sessions["Yesterday"],
                        "Last 7 Days": sessions["Last 7 Days"]
                    }
        return OrderedJSONResponse(content=ordered_response)
    except Exception as e:
        return {"error":str(e)}


class SyncToElkRequest(BaseModel):
    full_sync: bool = False

@router.post("/sync-to-elk")
async def sync_to_elk(request: SyncToElkRequest,state_request:Request):
    """
    Manually trigger incremental sync of updated sessions/messages from MongoDB to Elasticsearch.
    Set full_sync=true to force re-index all data regardless of last sync time.
    """
    try:
        session_manager = state_request.app.state.session_manager
        result = session_manager.sync_to_elk(full_sync=request.full_sync)
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        logging.error(f"sync-to-elk failed: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "reason": str(e)})

