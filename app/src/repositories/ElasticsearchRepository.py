import os
import json
import base64
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from elasticsearch import Elasticsearch, helpers


logger = logging.getLogger(__name__)


class ElasticsearchRepository:
    """Repository for archiving and retrieving session data from Elasticsearch."""

    SESSIONS_INDEX = "interact_sessions"
    MESSAGES_INDEX = "interact_session_messages"

    def __init__(self):
        es_host = os.getenv("ES_HOST", "localhost")
        es_port = int(os.getenv("ES_PORT", 9200))
        es_username = os.getenv("ES_USERNAME", "")
        es_password = os.getenv("ES_PASSWORD", "")
        es_scheme = os.getenv("ES_SCHEME", "http")

        connection_params = {
            "hosts": [f"{es_scheme}://{es_host}:{es_port}"],
            "request_timeout": 10,
        }

        if es_username and es_password:
            connection_params["basic_auth"] = (es_username, es_password)

        # Disable SSL verification for dev environments
        if es_scheme == "https":
            connection_params["verify_certs"] = os.getenv("ES_VERIFY_CERTS", "true").lower() == "true"

        self.__client = Elasticsearch(**connection_params)
        self._ensure_indices()

    def _ensure_indices(self):
        """Create indices with mappings if they don't exist."""
        try:
            if not self.__client.indices.exists(index=self.SESSIONS_INDEX):
                self.__client.indices.create(
                    index=self.SESSIONS_INDEX,
                    body={
                        "mappings": {
                            "properties": {
                                "session_id": {"type": "keyword"},
                                "user_email": {"type": "keyword"},
                                "session_name": {"type": "text"},
                                "module_name": {"type": "keyword"},
                                "session_type": {"type": "keyword"},
                                "avg_response_time": {"type": "float"},
                                "query_exec_time": {"type": "float"},
                                "created_at": {"type": "date"},
                                "last_updated": {"type": "date"},
                                "chat_history": {"type": "object", "enabled": False},
                            }
                        }
                    },
                )
                logger.info(f"Created Elasticsearch index: {self.SESSIONS_INDEX}")

            if not self.__client.indices.exists(index=self.MESSAGES_INDEX):
                self.__client.indices.create(
                    index=self.MESSAGES_INDEX,
                    body={
                        "mappings": {
                            "properties": {
                                "session_id": {"type": "keyword"},
                                "message_id": {"type": "keyword"},
                                "response_id": {"type": "keyword"},
                                "user_input": {"type": "text"},
                                "translated_input": {"type": "text"},
                                "response": {"type": "object", "enabled": False},
                                "execution_times": {"type": "object", "enabled": False},
                                "input_timestamp": {"type": "keyword"},
                                "timestamp": {"type": "date"},
                                "response_time": {"type": "float"},
                                "error_message": {"type": "text"},
                                "like": {"type": "boolean"},
                                "feedback": {"type": "text"},
                            }
                        }
                    },
                )
                logger.info(f"Created Elasticsearch index: {self.MESSAGES_INDEX}")
        except Exception as e:
            logger.warning(f"Could not ensure ES indices (ES may be unavailable): {e}")

    def is_available(self) -> bool:
        """Check if Elasticsearch is reachable."""
        try:
            info = self.__client.info()
            return info is not None
        except Exception:
            return False

    # -------------------- Query (for Login) --------------------

    def get_user_sessions_last_n_days(self, user_email: str, days: int = 7) -> List[Dict]:
        """Retrieve sessions for a user from the last N days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = {
            "bool": {
                "must": [
                    {"term": {"user_email": user_email}},
                    {"range": {"last_updated": {"gte": cutoff.isoformat()}}},
                ]
            }
        }

        result = self.__client.search(
            index=self.SESSIONS_INDEX,
            body={"query": query, "size": 1000, "sort": [{"last_updated": "desc"}]},
        )

        sessions = []
        for hit in result["hits"]["hits"]:
            doc = hit["_source"]
            sessions.append(doc)
        return sessions

    def get_messages_by_session_ids(self, session_ids: List[str]) -> List[Dict]:
        """Retrieve all messages for a list of session IDs."""
        if not session_ids:
            return []

        query = {"terms": {"session_id": session_ids}}

        result = self.__client.search(
            index=self.MESSAGES_INDEX,
            body={"query": query, "size": 10000, "sort": [{"timestamp": "asc"}]},
        )

        messages = []
        for hit in result["hits"]["hits"]:
            messages.append(hit["_source"])
        return messages

    # -------------------- Bulk Index (for Logout) --------------------

    @staticmethod
    def _make_json_serializable(obj):
        """Recursively convert non-JSON-serializable types (e.g. bytes from Gemini thought_signature)."""
        if isinstance(obj, dict):
            return {k: ElasticsearchRepository._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [ElasticsearchRepository._make_json_serializable(item) for item in obj]
        elif isinstance(obj, bytes):
            return base64.b64encode(obj).decode("ascii")
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return obj

    def bulk_index_sessions(self, sessions: List[Dict]) -> int:
        """Bulk index sessions to ES. Uses session_id as document _id to prevent duplicates."""
        if not sessions:
            return 0

        actions = []
        for session in sessions:
            doc = {k: v for k, v in session.items() if k != "_id"}
            # Convert datetime objects to ISO strings
            for key in ("created_at", "last_updated"):
                if key in doc and isinstance(doc[key], datetime):
                    doc[key] = doc[key].isoformat()

            # Sanitize chat_history to handle non-JSON-serializable types (e.g. bytes)
            if "chat_history" in doc:
                doc["chat_history"] = self._make_json_serializable(doc["chat_history"])

            actions.append({
                "_index": self.SESSIONS_INDEX,
                "_id": doc["session_id"],
                "_source": doc,
            })

        success, errors = helpers.bulk(self.__client, actions, raise_on_error=False)
        if errors:
            logger.error(f"ES bulk index sessions errors: {errors}")
        return success

    def bulk_index_messages(self, messages: List[Dict]) -> int:
        """Bulk index messages to ES. Uses response_id as document _id to prevent duplicates."""
        if not messages:
            return 0

        actions = []
        for msg in messages:
            doc = {k: v for k, v in msg.items() if k != "_id"}
            # Convert datetime objects to ISO strings
            if "timestamp" in doc and isinstance(doc["timestamp"], datetime):
                doc["timestamp"] = doc["timestamp"].isoformat()

            doc_id = doc.get("response_id", doc.get("message_id"))
            actions.append({
                "_index": self.MESSAGES_INDEX,
                "_id": doc_id,
                "_source": doc,
            })

        success, errors = helpers.bulk(self.__client, actions, raise_on_error=False)
        if errors:
            logger.error(f"ES bulk index messages errors: {errors}")
        return success
