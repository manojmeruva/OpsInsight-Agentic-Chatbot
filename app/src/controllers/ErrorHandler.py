from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import traceback

class GlobalErrorExecution(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            return await call_next(request)
        except Exception:
            logging.error("Unhandled error", exc_info=True)

            # IMPORTANT: never break the HTTP connection
            return JSONResponse(
                status_code=200,
                content={
                    "success": False,
                    "error_type": "INTERNAL_ERROR",
                    "message": "Something went wrong while processing your request. Please retry.",
                    "path": request.url.path,
                },
            )
