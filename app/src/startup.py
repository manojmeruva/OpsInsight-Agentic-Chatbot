from contextlib import asynccontextmanager
from fastapi import FastAPI
import os
import logging

from core.database import get_engine, dispose_pool
from utils.git_metadata_loader import rebuild_metadata_db
from core.vault_client import VaultClient
from session_management.session_manager_mongo import SessionManager
from config import Config

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ===== STARTUP =====
    try:
        # 1. DB Engine
        engine = get_engine()
        app.state.engine = engine

        # 2. Metadata load (non-blocking failure)
        try:
            rebuild_metadata_db("metadata_vol")
            logging.info("Metadata loaded from git repo on startup")
        except Exception as e:
            logging.error("Metadata load failed, continuing with existing DB: %s", e)

        # 3. Vault + API key
        vault = VaultClient()
        gemini_api_key = vault.get_gemini_key()
        os.environ["GOOGLE_API_KEY"] = gemini_api_key

        # 4. Session Manager
        session_manager = SessionManager(
            api_key=gemini_api_key,
            db_config=Config.get_db_config()
        )

        # 5. Gemini Client (proxy-aware)
        proxy = os.getenv("HTTP_PROXY")

        

        # Store in app state (instead of globals)
        app.state.session_manager = session_manager
        app.state.gemini_api_key = gemini_api_key

        logging.info("Startup completed successfully")

        yield  # ← APP RUNS HERE

    finally:
        # ===== SHUTDOWN =====
        try:
            dispose_pool()
            logging.info("Connection pool disposed")
        except Exception as e:
            logging.error("Error during shutdown: %s", e)
