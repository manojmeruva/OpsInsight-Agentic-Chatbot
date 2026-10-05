from config import Config

class RepositoryFactory:
    @staticmethod
    def create_session_repository():
        if Config.DB_TYPE == "mongo":
            from repositories.SessionRepository import SessionRepository
            return SessionRepository()
        elif Config.DB_TYPE == "sqlite":
            from repositories.SQLiteSessionRepository import SQLiteSessionRepository
            return SQLiteSessionRepository()
        else:
            raise ValueError("Unsupported database type!")
