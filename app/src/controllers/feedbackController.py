

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel


router = APIRouter()

class LikeRequest(BaseModel):
    session_id: str
    response_id: str
    is_like: bool

class FeedbackRequest(BaseModel):
    session_id: str
    response_id: str
    feedback: str

@router.post("/like-feedback")
async def update_like_reaction(request: LikeRequest,state_request:Request):

    session_manager = state_request.app.state.session_manager

    result = session_manager.update_like_feedback(
        session_id=request.session_id,
        response_id=request.response_id,
        like=request.is_like        
    )

    if result == 0:
        raise HTTPException(status_code=404, detail="Message not found")

    return {"status": "success", "message": "Reaction saved"}

@router.post("/message-feedback")
async def update_message_reaction(request: FeedbackRequest,state_request:Request):

    session_manager = state_request.app.state.session_manager

    result = session_manager.update_message_feedback(
        session_id=request.session_id,
        response_id=request.response_id,
        feedback=request.feedback
    )

    if result == 0:
        raise HTTPException(status_code=404, detail="Message not found")

    return {"status": "success", "message": "Feedback saved"}

