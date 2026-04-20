import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional
# import google.genai as genai
# from google.genai import types
# from google.genai.types import Tool, GenerateContentConfig, UserContent, Part


from core.conversation import MultiTurnConversation
from repositories.SessionRepository import SessionRepository
from repositories.ElasticsearchRepository import ElasticsearchRepository
from core.message_serializer import serialize_messages,deserialize_messages

class SessionManager:
    def __init__(self, api_key: str, db_config: dict, session_timeout_seconds: int = 30):
        self.api_key = api_key
        self.db_config = db_config
        self.session_timeout = timedelta(seconds=session_timeout_seconds)
        self.repo = SessionRepository()
        try:
            self.es_repo = ElasticsearchRepository()
        except Exception as e:
            logging.warning(f"Elasticsearch initialization failed (will operate without ES): {e}")
            self.es_repo = None

    def add_message_to_session(self,message):
        try:
            self.repo.add_message(message)
            logging.info(f"message created : {message}")
        except Exception as e:
            logging.info(f"{str(e)}")

    def create_session(self, user_email: str = "sample", session_name: str = "sample", session_id: Optional[str] = None) -> str:
        """Create or reuse a session in MongoDB"""
        pass



    async def get_session(
                        self,
                        current_timestamp,
                        session_id: Optional[str],
                        module_name:str ="ELOSS",
                        user_email: Optional[str] = "sample",
                        session_name: str = "sample",
                    ) -> MultiTurnConversation:
        """Rebuild a conversation with its history if session exists and is not expired"""
            #TODO
        # 1. MongoDB Exception Handling needs to be done.
            # Generate ID if missing
        session_id = session_id or str(uuid.uuid4())

        # Check if session already exists
        session = self.repo.get_by_id(session_id)

        print(session)

        if not session:
            # Create new record
            session_data = {
                "session_id": session_id,
                "user_email": user_email,
                "session_name": session_name,
                "module_name":module_name,
                "avg_response_time": 0.0,
                "query_exec_time": 0.0,
                "created_at": datetime.utcnow(),
                "last_updated": datetime.utcnow(),
                "chat_history": []
            }
            self.repo.create(session_data)
            return await MultiTurnConversation.create([],[],module_name,current_timestamp)

        conversations = self.repo.text_to_sql_messages(session_id=session_id)
        # If session exists, update timestamp
        self.repo.update(session_id, {"last_updated": datetime.utcnow()})

        # Load history
        history = self.repo.load_history(session_id)

        return await MultiTurnConversation.create(history,conversations,module_name,current_timestamp)
    

    def get_active_sessions(self,user_email,past_days=7):
        now = datetime.utcnow().replace(microsecond=0)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)
        past_days_start = today_start - timedelta(days=past_days)

        sessions = list(self.repo.get_all_sessions(user_email,past_days_start))
        categorized_sessions = {"Today": [], "Yesterday": [], "Last 7 Days": []}

        for session in sessions:
            session_id = session["session_id"]
            session_name = session.get("session_name", "")
            created_at = session["last_updated"]
            module_name = session.get("module_name","")
            
            # Categorize session
            if created_at >= today_start:
                category = "Today"
            elif created_at >= yesterday_start:
                category = "Yesterday"
            else:
                category = "Last 7 Days"

            
            # Append to the appropriate category
            categorized_sessions[category].append({
                "sessionId": session_id,
                "sessionName": session_name,
                "createdAt": created_at.isoformat(),
                "module_name":module_name
            })

        return categorized_sessions





    def save_history(self,session_id,chat_history):

        self.repo.save_history(session_id,serialize_messages(chat_history))
    
    def delete_session(self, session_id: str):
        """Delete session and its messages"""
        self.repo.delete(session_id)




    def get_session_messages(self, session_id: str):
        try:
            messages = self.repo.get_messages(session_id)
            logging.info(f"session_id : {session_id} messages retrieved.")
            if not messages:
                return {"error": "No messages found for this session."}

            formatted_messages = [
            {
                "request": {
                    "id": message.get("message_id", ""),
                    "message": message.get("user_input", ""),
                    "timestamp": message.get("input_timestamp", "")
                },
                "response": {  # Corrected typo to 'response'
                    "id": message.get("response_id", ""),
                    "message": message.get("response", {}),
                    "feedback": message.get("feedback", None),
                    "is_like": message.get("like", None),
                    "timestamp": message.get("timestamp", "").isoformat() if message.get("timestamp") else None
                }
            }
            for message in messages
            ]

            return {"messages": formatted_messages}

        except Exception as e:
            return {"error": str(e)}


    def update_message_after_response(self, response_id, update_data):
        try:
            self.repo.update_message(response_id, update_data)
        except Exception as e:
            logging.error(f"Message update failed: {e}")

    
    def update_like_feedback(self, session_id, response_id, like):

        update_result = self.repo.update_like_feedback(      
            session_id=session_id, response_id=response_id, like=like
        )

        return update_result.modified_count
    
    def update_message_feedback(self, session_id, response_id, feedback):

        update_result = self.repo.update_message_feedback(
            session_id=session_id, response_id=response_id, feedback=feedback
        )

        return update_result.modified_count

    # -------------------- ELK Sync --------------------

    def sync_to_elk(self, full_sync: bool = False, since_hours: int = 24) -> dict:
        """
        Sync updated sessions and messages from MongoDB to Elasticsearch.
        - full_sync=True: re-index everything
        - full_sync=False: only data updated in the last `since_hours` hours (default 24h)
        """
        start_time = time.time()

        if not self.es_repo or not self.es_repo.is_available():
            logging.warning("Elasticsearch unavailable for sync")
            return {"status": "skipped", "reason": "Elasticsearch unavailable", "sessions_synced": 0, "messages_synced": 0}

        try:
            if full_sync:
                logging.info("Starting full sync from MongoDB to Elasticsearch")
                sessions = self.repo.get_all_sessions_full()
                messages = self.repo.get_all_messages_full()
            else:
                since = datetime.utcnow() - timedelta(hours=since_hours)
                logging.info(f"Incremental sync: fetching data updated since {since.isoformat()}")
                sessions = self.repo.get_sessions_updated_since(since)
                messages = self.repo.get_messages_since(since)

            sessions_synced = 0
            messages_synced = 0

            if sessions:
                sessions_synced = self.es_repo.bulk_index_sessions(sessions)
                logging.info(f"Synced {sessions_synced} sessions to Elasticsearch")

            if messages:
                messages_synced = self.es_repo.bulk_index_messages(messages)
                logging.info(f"Synced {messages_synced} messages to Elasticsearch")

            elapsed = time.time() - start_time
            logging.info(f"Sync completed: {sessions_synced} sessions, {messages_synced} messages in {elapsed:.2f}s")

            return {
                "status": "success",
                "sessions_synced": sessions_synced,
                "messages_synced": messages_synced,
                "time_taken": round(elapsed, 2),
            }

        except Exception as e:
            elapsed = time.time() - start_time
            logging.error(f"Sync to Elasticsearch failed: {e}")
            return {"status": "error", "reason": str(e), "sessions_synced": 0, "messages_synced": 0, "time_taken": round(elapsed, 2)}

    # -------------------- EFK Integration --------------------

    def load_session_history_from_es(self, user_email: str, days: int = 7) -> dict:
        """
        Load last N days of session history from Elasticsearch into MongoDB.
        Called on user login. Returns summary of loaded data.
        """
        start_time = time.time()

        if not self.es_repo or not self.es_repo.is_available():
            logging.warning(f"ES unavailable for load_session_history, user: {user_email}")
            return {"status": "skipped", "reason": "Elasticsearch unavailable", "sessions_loaded": 0, "messages_loaded": 0}

        try:
            # 1. Query ES for user's sessions from last N days
            es_sessions = self.es_repo.get_user_sessions_last_n_days(user_email, days)
            if not es_sessions:
                logging.info(f"No ES sessions found for {user_email} in last {days} days")
                return {"status": "success", "sessions_loaded": 0, "messages_loaded": 0}

            session_ids = [s["session_id"] for s in es_sessions]

            # 2. Query ES for messages belonging to those sessions
            es_messages = self.es_repo.get_messages_by_session_ids(session_ids)

            # 3. Upsert sessions into MongoDB (skip if already exists)
            sessions_loaded = 0
            for session in es_sessions:
                existing = self.repo.get_by_id(session["session_id"])
                if not existing:
                    # Convert ISO date strings back to datetime
                    for key in ("created_at", "last_updated"):
                        if key in session and isinstance(session[key], str):
                            session[key] = datetime.fromisoformat(session[key])
                    self.repo.create(session)
                    sessions_loaded += 1

            # 4. Upsert messages into MongoDB (skip duplicates by response_id)
            messages_loaded = 0
            for msg in es_messages:
                existing_msgs = list(self.repo.get_messages_collection().find(
                    {"response_id": msg.get("response_id")}, {"_id": 1}
                ).limit(1))
                if not existing_msgs:
                    if "timestamp" in msg and isinstance(msg["timestamp"], str):
                        msg["timestamp"] = datetime.fromisoformat(msg["timestamp"])
                    self.repo.add_message(msg)
                    messages_loaded += 1

            elapsed = time.time() - start_time
            logging.info(f"Loaded from ES for {user_email}: {sessions_loaded} sessions, {messages_loaded} messages in {elapsed:.2f}s")

            return {
                "status": "success",
                "sessions_loaded": sessions_loaded,
                "messages_loaded": messages_loaded,
                "time_taken": round(elapsed, 2),
            }

        except Exception as e:
            logging.error(f"Error loading session history from ES for {user_email}: {e}")
            return {"status": "error", "reason": str(e), "sessions_loaded": 0, "messages_loaded": 0}

    def archive_session_data_to_es(self, user_email: str) -> dict:
        """
        Archive all of user's session data from MongoDB to Elasticsearch.
        Called on user logout. Archives ALL sessions for the user.
        After successful archival, cleans up session_messages from MongoDB
        but keeps session metadata.
        """
        start_time = time.time()

        if not self.es_repo or not self.es_repo.is_available():
            logging.warning(f"ES unavailable for archive_session_data, user: {user_email}")
            return {"status": "skipped", "reason": "Elasticsearch unavailable", "sessions_archived": 0, "messages_archived": 0}

        try:
            # 1. Fetch ALL user's sessions from MongoDB
            cutoff = datetime(2000, 1, 1)  # far past to get all sessions
            mongo_sessions = list(self.repo.get_all_sessions(user_email, cutoff))

            if not mongo_sessions:
                logging.info(f"No sessions to archive for {user_email}")
                return {"status": "success", "sessions_archived": 0, "messages_archived": 0}

            session_ids = [s["session_id"] for s in mongo_sessions]

            # 2. Fetch full session documents (with chat_history) for archival
            full_sessions = []
            for sid in session_ids:
                session = self.repo.get_by_id(sid)
                if session:
                    full_sessions.append(session)

            # 3. Fetch all messages for these sessions
            all_messages = []
            for sid in session_ids:
                messages = self.repo.get_messages(sid)
                all_messages.extend(messages)

            # 4. Bulk index sessions to ES (session_id as _id prevents duplicates)
            sessions_archived = self.es_repo.bulk_index_sessions(full_sessions)

            # 5. Bulk index messages to ES (response_id as _id prevents duplicates)
            messages_archived = self.es_repo.bulk_index_messages(all_messages)

            logging.info(f"Archived to ES for {user_email}: {sessions_archived} sessions, {messages_archived} messages")

            # 6. Only cleanup MongoDB after successful ES write
            messages_cleaned = 0
            for sid in session_ids:
                # Delete session_messages from MongoDB
                delete_result = self.repo.get_messages_collection().delete_many({"session_id": sid})
                messages_cleaned += delete_result.deleted_count

                # Clear chat_history from session doc to save space, but keep metadata
                self.repo.update(sid, {"chat_history": []})

            logging.info(f"Cleaned up MongoDB for {user_email}: {messages_cleaned} messages removed, session metadata retained")

            elapsed = time.time() - start_time
            logging.info(f"Archive completed for {user_email} in {elapsed:.2f}s")

            return {
                "status": "success",
                "sessions_archived": sessions_archived,
                "messages_archived": messages_archived,
                "messages_cleaned_from_mongo": messages_cleaned,
                "time_taken": round(elapsed, 2),
            }

        except Exception as e:
            logging.error(f"Error archiving session data to ES for {user_email}: {e}")
            return {"status": "error", "reason": str(e), "sessions_archived": 0, "messages_archived": 0}


