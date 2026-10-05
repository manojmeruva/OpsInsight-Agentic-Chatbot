from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from utils.git_metadata_loader import rebuild_metadata_db
from config import Config

router = APIRouter()

@router.get("/modules")
async def get_modules():
    """Business domains for the UI: active domain first, then placeholders."""
    public_keys = ("module", "tag", "display_name", "short_name", "description", "status", "icon", "sample_questions")
    return {
        "data_engine": Config.DATA_DB_ENGINE,
        "modules": [{k: d[k] for k in public_keys} for d in Config.DOMAINS],
    }

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
