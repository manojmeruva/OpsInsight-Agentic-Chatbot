
from app.src.repositories.SessionRepository import SessionRepository
from config import Config

class RepositoryFactory:
    @staticmethod
    def create_session_repository():
        if Config.DB_TYPE == "mongo":
            return SessionRepository()
        # elif Config.DB_TYPE == "sqlite":
        #     return SQLiteSessionRepository()
        else:
            raise ValueError("Unsupported database type!")

