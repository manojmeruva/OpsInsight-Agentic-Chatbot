

import os

from fastapi import FastAPI




from controllers import (
    feedbackController,
    metadataController,
    queryController,
    speechController,
    SessionController,
    testController,
    translationController
)



from controllers.ErrorHandler import GlobalErrorExecution



from starlette.middleware.base import BaseHTTPMiddleware
import logging

from fastapi.middleware.cors import CORSMiddleware



# Import for service account authentication
from dotenv import load_dotenv

from startup import lifespan

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")

# Ensure logs directory exists
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "app_errors_and_activity.log")

# Configure logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


# Initialize FastAPI app

app = FastAPI(debug=True, root_path="/interact-backend",lifespan=lifespan)

app.add_middleware(GlobalErrorExecution)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



app.include_router(queryController.router, prefix="/api")
app.include_router(translationController.router, prefix="/api")
app.include_router(speechController.router, prefix="/api")
app.include_router(SessionController.router, prefix="/api")
app.include_router(metadataController.router, prefix="/api")
app.include_router(feedbackController.router, prefix="/api")
app.include_router(testController.router, prefix="/api")




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)