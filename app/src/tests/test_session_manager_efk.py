import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime


class TestLoadSessionHistoryFromES:
    """Tests for SessionManager.load_session_history_from_es()"""

    @patch("session_management.session_manager_mongo.ElasticsearchRepository")
    @patch("session_management.session_manager_mongo.SessionRepository")
    def _create_manager(self, MockSessionRepo, MockESRepo, es_available=True):
        mock_repo = MagicMock()
        MockSessionRepo.return_value = mock_repo

        mock_es_repo = MagicMock()
        mock_es_repo.is_available.return_value = es_available
        MockESRepo.return_value = mock_es_repo

        from session_management.session_manager_mongo import SessionManager
        manager = SessionManager(api_key="test", db_config={})
        return manager, mock_repo, mock_es_repo

    def test_skipped_when_es_unavailable(self):
        manager, _, _ = self._create_manager(es_available=False)

        result = manager.load_session_history_from_es("test@agentic-designed-chatbot.com")

        assert result["status"] == "skipped"
        assert result["sessions_loaded"] == 0

    def test_returns_zero_when_no_es_sessions(self):
        manager, _, mock_es = self._create_manager()
        mock_es.get_user_sessions_last_n_days.return_value = []

        result = manager.load_session_history_from_es("test@agentic-designed-chatbot.com")

        assert result["status"] == "success"
        assert result["sessions_loaded"] == 0
        assert result["messages_loaded"] == 0

    def test_loads_sessions_and_messages(self):
        manager, mock_repo, mock_es = self._create_manager()

        mock_es.get_user_sessions_last_n_days.return_value = [
            {"session_id": "s1", "user_email": "test@agentic-designed-chatbot.com",
             "created_at": "2026-02-20T10:00:00", "last_updated": "2026-02-20T10:00:00"},
        ]
        mock_es.get_messages_by_session_ids.return_value = [
            {"session_id": "s1", "response_id": "r1", "timestamp": "2026-02-20T10:01:00"},
        ]
        # Session does not exist in MongoDB
        mock_repo.get_by_id.return_value = None
        # Message does not exist in MongoDB
        mock_messages_coll = MagicMock()
        mock_messages_coll.find.return_value.limit.return_value = []
        mock_repo.get_messages_collection.return_value = mock_messages_coll

        result = manager.load_session_history_from_es("test@agentic-designed-chatbot.com")

        assert result["status"] == "success"
        assert result["sessions_loaded"] == 1
        assert result["messages_loaded"] == 1
        mock_repo.create.assert_called_once()
        mock_repo.add_message.assert_called_once()

    def test_skips_existing_sessions(self):
        manager, mock_repo, mock_es = self._create_manager()

        mock_es.get_user_sessions_last_n_days.return_value = [
            {"session_id": "s1", "user_email": "test@agentic-designed-chatbot.com",
             "created_at": "2026-02-20T10:00:00", "last_updated": "2026-02-20T10:00:00"},
        ]
        mock_es.get_messages_by_session_ids.return_value = []
        # Session already exists in MongoDB
        mock_repo.get_by_id.return_value = {"session_id": "s1"}

        result = manager.load_session_history_from_es("test@agentic-designed-chatbot.com")

        assert result["sessions_loaded"] == 0
        mock_repo.create.assert_not_called()

    def test_skips_existing_messages(self):
        manager, mock_repo, mock_es = self._create_manager()

        mock_es.get_user_sessions_last_n_days.return_value = [
            {"session_id": "s1", "user_email": "test@agentic-designed-chatbot.com",
             "created_at": "2026-02-20T10:00:00", "last_updated": "2026-02-20T10:00:00"},
        ]
        mock_es.get_messages_by_session_ids.return_value = [
            {"session_id": "s1", "response_id": "r1", "timestamp": "2026-02-20T10:01:00"},
        ]
        mock_repo.get_by_id.return_value = {"session_id": "s1"}
        # Message already exists
        mock_messages_coll = MagicMock()
        mock_messages_coll.find.return_value.limit.return_value = [{"_id": "existing"}]
        mock_repo.get_messages_collection.return_value = mock_messages_coll

        result = manager.load_session_history_from_es("test@agentic-designed-chatbot.com")

        assert result["messages_loaded"] == 0
        mock_repo.add_message.assert_not_called()

    def test_handles_es_query_error(self):
        manager, _, mock_es = self._create_manager()
        mock_es.get_user_sessions_last_n_days.side_effect = Exception("ES query failed")

        result = manager.load_session_history_from_es("test@agentic-designed-chatbot.com")

        assert result["status"] == "error"
        assert "ES query failed" in result["reason"]


class TestArchiveSessionDataToES:
    """Tests for SessionManager.archive_session_data_to_es()"""

    @patch("session_management.session_manager_mongo.ElasticsearchRepository")
    @patch("session_management.session_manager_mongo.SessionRepository")
    def _create_manager(self, MockSessionRepo, MockESRepo, es_available=True):
        mock_repo = MagicMock()
        MockSessionRepo.return_value = mock_repo

        mock_es_repo = MagicMock()
        mock_es_repo.is_available.return_value = es_available
        MockESRepo.return_value = mock_es_repo

        from session_management.session_manager_mongo import SessionManager
        manager = SessionManager(api_key="test", db_config={})
        return manager, mock_repo, mock_es_repo

    def test_skipped_when_es_unavailable(self):
        manager, _, _ = self._create_manager(es_available=False)

        result = manager.archive_session_data_to_es("test@agentic-designed-chatbot.com")

        assert result["status"] == "skipped"
        assert result["sessions_archived"] == 0

    def test_returns_zero_when_no_sessions(self):
        manager, mock_repo, _ = self._create_manager()
        mock_repo.get_all_sessions.return_value = []

        result = manager.archive_session_data_to_es("test@agentic-designed-chatbot.com")

        assert result["status"] == "success"
        assert result["sessions_archived"] == 0

    def test_archives_sessions_and_messages(self):
        manager, mock_repo, mock_es = self._create_manager()

        mock_repo.get_all_sessions.return_value = [
            {"session_id": "s1"},
            {"session_id": "s2"},
        ]
        mock_repo.get_by_id.side_effect = [
            {"session_id": "s1", "chat_history": []},
            {"session_id": "s2", "chat_history": []},
        ]
        mock_repo.get_messages.side_effect = [
            [{"response_id": "r1"}, {"response_id": "r2"}],
            [{"response_id": "r3"}],
        ]
        mock_es.bulk_index_sessions.return_value = 2
        mock_es.bulk_index_messages.return_value = 3

        mock_delete_result = MagicMock()
        mock_delete_result.deleted_count = 2
        mock_messages_coll = MagicMock()
        mock_messages_coll.delete_many.return_value = mock_delete_result
        mock_repo.get_messages_collection.return_value = mock_messages_coll

        result = manager.archive_session_data_to_es("test@agentic-designed-chatbot.com")

        assert result["status"] == "success"
        assert result["sessions_archived"] == 2
        assert result["messages_archived"] == 3
        mock_es.bulk_index_sessions.assert_called_once()
        mock_es.bulk_index_messages.assert_called_once()

    def test_cleans_up_mongo_after_archive(self):
        manager, mock_repo, mock_es = self._create_manager()

        mock_repo.get_all_sessions.return_value = [{"session_id": "s1"}]
        mock_repo.get_by_id.return_value = {"session_id": "s1", "chat_history": [{"role": "user"}]}
        mock_repo.get_messages.return_value = [{"response_id": "r1"}]
        mock_es.bulk_index_sessions.return_value = 1
        mock_es.bulk_index_messages.return_value = 1

        mock_delete_result = MagicMock()
        mock_delete_result.deleted_count = 1
        mock_messages_coll = MagicMock()
        mock_messages_coll.delete_many.return_value = mock_delete_result
        mock_repo.get_messages_collection.return_value = mock_messages_coll

        result = manager.archive_session_data_to_es("test@agentic-designed-chatbot.com")

        # Verify messages deleted from MongoDB
        mock_messages_coll.delete_many.assert_called_once_with({"session_id": "s1"})
        # Verify chat_history cleared but metadata kept
        mock_repo.update.assert_called_once_with("s1", {"chat_history": []})
        assert result["messages_cleaned_from_mongo"] == 1

    def test_handles_archive_error(self):
        manager, mock_repo, mock_es = self._create_manager()
        mock_repo.get_all_sessions.side_effect = Exception("MongoDB connection lost")

        result = manager.archive_session_data_to_es("test@agentic-designed-chatbot.com")

        assert result["status"] == "error"
        assert "MongoDB connection lost" in result["reason"]

    def test_skipped_when_es_repo_is_none(self):
        manager, _, _ = self._create_manager()
        manager.es_repo = None

        result = manager.archive_session_data_to_es("test@agentic-designed-chatbot.com")

        assert result["status"] == "skipped"