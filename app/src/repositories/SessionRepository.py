import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pymongo import MongoClient
from repositories.RepositoryBase import RepositoryBase
from core.message_serializer import deserialize_messages

class SessionRepository(RepositoryBase):
    def __init__(self):
        self.__client = MongoClient(os.getenv("MONGO_URI"))
        self.__db = self.__client[os.getenv("DB_NAME")]
        self.__sessions_collection = self.__db['sessions']
        self.__messages_collection = self.__db['session_messages']

    def get_sessions_collection(self):
        return self.__sessions_collection
    
    def get_messages_collection(self):
        return self.__messages_collection
    
    # -------------------- CRUD --------------------
    def create(self, data: dict) -> str:
        """Create a new session"""
        result = self.__sessions_collection.insert_one(data)
        return str(result.inserted_id)

    def aggregate(self, pipeline):
        return list(self.__sessions_collection.aggregate(pipeline))

    def get_all(self, limit: int = 50) -> List[Dict]:
        return list(self.__sessions_collection.find().limit(limit))

    def get_by_id(self, session_id: str) -> Optional[Dict]:
        return self.__sessions_collection.find_one({"session_id": session_id})

    def update(self, session_id: str, data: dict):
        # prevent conflict
        data.pop("last_updated", None)

        self.__sessions_collection.update_one(
            {"session_id": session_id},
            {"$set": data, "$currentDate": {"last_updated": True}}
        )

    def get_all_sessions(self,user_email,limit):
        return self.__sessions_collection.find(
            {"user_email":{"$eq":user_email,"$exists":True},"last_updated": {"$gte": limit}},
            {"session_id": 1, "session_name": 1,"module_name":1,"session_type":1, "last_updated": 1,"_id":0}
        ).sort("last_updated", -1)
    
    def delete(self, session_id: str):
        self.__sessions_collection.delete_one({"session_id": session_id})
        self.__messages_collection.delete_many({"session_id": session_id})

    # -------------------- Session Messages --------------------
    def add_message(self, message: dict):
        """Save a message to session_messages"""
        self.__messages_collection.insert_one(message)

    def get_messages(self, session_id: str) -> List[Dict]:
        """Fetch all messages for a session (chat history)"""
        return list(
            self.__messages_collection.find({"session_id": session_id}).sort("timestamp", 1)
        )
    

    def save_history(self, session_id: str, history: List[Dict]):
        """Replace history with new one (overwrite mode)"""
        self.update(session_id,{"chat_history":history,"last_updated": datetime.utcnow()})

    def load_history(self, session_id: str) -> List[Dict]:
        """Load history for Gemini chat resume"""
        session = self.get_by_id(session_id)
        return deserialize_messages(session["chat_history"])
        # convert to Gemini-compatible format
    
    def text_to_sql_messages(self,session_id:str) :
        messages = self.__messages_collection.find({"session_id":session_id}).sort("timestamp",1).limit(10)
        return list(messages)

    def update_message(self, response_id, update_data):
        self.__messages_collection.update_one(
            {"response_id": response_id},
            {"$set": update_data}
        )
    
    def update_like_feedback(self, session_id, response_id, like):

        update_result = self.__messages_collection.update_one(
            {
                "response_id": response_id,
                "session_id": session_id
            },
            {
                "$set": {
                    "like": like,
                    "timestamp":datetime.utcnow()
                }
            }
        )

        return update_result
    
    def update_message_feedback(self, session_id, response_id, feedback):

        update_result = self.__messages_collection.update_one(
            {
                "response_id": response_id,
                "session_id": session_id
            },
            {
                "$set": {
                    "feedback":feedback,
                    "timestamp":datetime.utcnow()
                }
            }
        )

        return update_result

    # -------------------- Sync Queries --------------------
    def get_sessions_updated_since(self, since: datetime) -> List[Dict]:
        """Fetch sessions updated after the given timestamp."""
        return list(self.__sessions_collection.find({"last_updated": {"$gt": since}}))

    def get_messages_since(self, since: datetime) -> List[Dict]:
        """Fetch session messages created after the given timestamp."""
        return list(self.__messages_collection.find({"timestamp": {"$gt": since}}))

    def get_all_sessions_full(self) -> List[Dict]:
        """Fetch all sessions (for full sync)."""
        return list(self.__sessions_collection.find())

    def get_all_messages_full(self) -> List[Dict]:
        """Fetch all messages (for full sync)."""
        return list(self.__messages_collection.find())

    