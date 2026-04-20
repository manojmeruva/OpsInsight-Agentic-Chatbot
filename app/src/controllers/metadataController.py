from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from utils.git_metadata_loader import rebuild_metadata_db

router = APIRouter()

@router.get("/refresh-metadata")
async def refresh_metadata():
    try:
        
        metrics = rebuild_metadata_db("metadata_vol")
        return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    
                    "message": "Refreshed metadata from git repo.",
                    "counts": metrics,
                    
                }
            )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=f"Metadata refresh failed due to {str(e)}"
        )
