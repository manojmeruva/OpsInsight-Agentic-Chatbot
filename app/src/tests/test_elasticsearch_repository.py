import base64
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from repositories.ElasticsearchRepository import ElasticsearchRepository


@pytest.fixture
def mock_es_client():
    """Patch Elasticsearch client so no real connection is made."""
    with patch("repositories.ElasticsearchRepository.Elasticsearch") as MockES:
        mock_client = MagicMock()
        MockES.return_value = mock_client
        mock_client.indices.exists.return_value = True  # skip index creation
        yield mock_client


@pytest.fixture
def es_repo(mock_es_client):
    """Create an ElasticsearchRepository with mocked client."""
    repo = ElasticsearchRepository()
    return repo


# -------------------- is_available --------------------

class TestIsAvailable:
    def test_returns_true_when_es_responds(self, es_repo, mock_es_client):
        mock_es_client.info.return_value = {"name": "node1", "version": {"number": "8.12.0"}}
        assert es_repo.is_available() is True

    def test_returns_false_when_es_down(self, es_repo, mock_es_client):
        mock_es_client.info.side_effect = Exception("Connection refused")
        assert es_repo.is_available() is False


# -------------------- get_user_sessions_last_n_days --------------------

class TestGetUserSessions:
    def test_returns_sessions_from_es(self, es_repo, mock_es_client):
        mock_es_client.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"session_id": "s1", "user_email": "test@agentic-designed-chatbot.com"}},
                    {"_source": {"session_id": "s2", "user_email": "test@agentic-designed-chatbot.com"}},
                ]
            }
        }

        result = es_repo.get_user_sessions_last_n_days("test@agentic-designed-chatbot.com", days=7)

        assert len(result) == 2
        assert result[0]["session_id"] == "s1"
        mock_es_client.search.assert_called_once()

    def test_returns_empty_when_no_hits(self, es_repo, mock_es_client):
        mock_es_client.search.return_value = {"hits": {"hits": []}}

        result = es_repo.get_user_sessions_last_n_days("nobody@agentic-designed-chatbot.com", days=7)

        assert result == []


# -------------------- get_messages_by_session_ids --------------------

class TestGetMessagesBySessionIds:
    def test_returns_messages(self, es_repo, mock_es_client):
        mock_es_client.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"session_id": "s1", "response_id": "r1", "user_input": "hello"}},
                ]
            }
        }

        result = es_repo.get_messages_by_session_ids(["s1"])

        assert len(result) == 1
        assert result[0]["response_id"] == "r1"

    def test_returns_empty_for_empty_session_ids(self, es_repo, mock_es_client):
        result = es_repo.get_messages_by_session_ids([])

        assert result == []
        mock_es_client.search.assert_not_called()


# -------------------- bulk_index_sessions --------------------

class TestBulkIndexSessions:
    @patch("repositories.ElasticsearchRepository.helpers")
    def test_indexes_sessions_with_correct_ids(self, mock_helpers, es_repo):
        mock_helpers.bulk.return_value = (2, [])

        sessions = [
            {
                "_id": "mongo_id_1",
                "session_id": "s1",
                "user_email": "test@agentic-designed-chatbot.com",
                "created_at": datetime(2026, 2, 20),
                "last_updated": datetime(2026, 2, 21),
                "chat_history": [],
            },
            {
                "_id": "mongo_id_2",
                "session_id": "s2",
                "user_email": "test@agentic-designed-chatbot.com",
                "created_at": datetime(2026, 2, 19),
                "last_updated": datetime(2026, 2, 20),
                "chat_history": [],
            },
        ]

        result = es_repo.bulk_index_sessions(sessions)

        assert result == 2
        mock_helpers.bulk.assert_called_once()
        actions = mock_helpers.bulk.call_args[0][1]
        # Verify _id is session_id (not mongo _id)
        assert actions[0]["_id"] == "s1"
        assert actions[1]["_id"] == "s2"
        # Verify mongo _id is excluded
        assert "_id" not in actions[0]["_source"]

    @patch("repositories.ElasticsearchRepository.helpers")
    def test_handles_bytes_in_chat_history(self, mock_helpers, es_repo):
        mock_helpers.bulk.return_value = (1, [])

        sessions = [
            {
                "session_id": "s1",
                "user_email": "test@agentic-designed-chatbot.com",
                "created_at": datetime(2026, 2, 20),
                "last_updated": datetime(2026, 2, 21),
                "chat_history": [
                    {
                        "parts": [{"thought_signature": b"\x01\x02\x03", "text": "hello"}],
                        "role": "model",
                    }
                ],
            }
        ]

        result = es_repo.bulk_index_sessions(sessions)

        assert result == 1
        actions = mock_helpers.bulk.call_args[0][1]
        chat_history = actions[0]["_source"]["chat_history"]
        # bytes should be base64-encoded
        assert chat_history[0]["parts"][0]["thought_signature"] == base64.b64encode(b"\x01\x02\x03").decode("ascii")

    def test_returns_zero_for_empty_list(self, es_repo):
        result = es_repo.bulk_index_sessions([])
        assert result == 0


# -------------------- bulk_index_messages --------------------

class TestBulkIndexMessages:
    @patch("repositories.ElasticsearchRepository.helpers")
    def test_indexes_messages_with_response_id(self, mock_helpers, es_repo):
        mock_helpers.bulk.return_value = (1, [])

        messages = [
            {
                "_id": "mongo_id",
                "session_id": "s1",
                "response_id": "r1",
                "user_input": "test query",
                "timestamp": datetime(2026, 2, 21, 10, 30),
            }
        ]

        result = es_repo.bulk_index_messages(messages)

        assert result == 1
        actions = mock_helpers.bulk.call_args[0][1]
        assert actions[0]["_id"] == "r1"
        assert "_id" not in actions[0]["_source"]

    def test_returns_zero_for_empty_list(self, es_repo):
        result = es_repo.bulk_index_messages([])
        assert result == 0


# -------------------- _make_json_serializable --------------------

class TestMakeJsonSerializable:
    def test_converts_bytes_to_base64(self):
        result = ElasticsearchRepository._make_json_serializable(b"\xff\xfe")
        assert result == base64.b64encode(b"\xff\xfe").decode("ascii")

    def test_converts_datetime_to_isoformat(self):
        dt = datetime(2026, 2, 21, 15, 30)
        result = ElasticsearchRepository._make_json_serializable(dt)
        assert result == "2026-02-21T15:30:00"

    def test_handles_nested_dict(self):
        data = {"key": {"nested": b"\x01"}}
        result = ElasticsearchRepository._make_json_serializable(data)
        assert result["key"]["nested"] == base64.b64encode(b"\x01").decode("ascii")

    def test_handles_list_with_mixed_types(self):
        data = [b"\x01", "text", 42, datetime(2026, 1, 1)]
        result = ElasticsearchRepository._make_json_serializable(data)
        assert result[0] == base64.b64encode(b"\x01").decode("ascii")
        assert result[1] == "text"
        assert result[2] == 42
        assert result[3] == "2026-01-01T00:00:00"

    def test_leaves_regular_types_unchanged(self):
        assert ElasticsearchRepository._make_json_serializable("hello") == "hello"
        assert ElasticsearchRepository._make_json_serializable(42) == 42
        assert ElasticsearchRepository._make_json_serializable(True) is True
        assert ElasticsearchRepository._make_json_serializable(None) is None


# -------------------- Index Creation --------------------

class TestIndexCreation:
    @patch("repositories.ElasticsearchRepository.Elasticsearch")
    def test_creates_indices_when_not_exist(self, MockES):
        mock_client = MagicMock()
        MockES.return_value = mock_client
        mock_client.indices.exists.return_value = False

        ElasticsearchRepository()

        assert mock_client.indices.create.call_count == 2

    @patch("repositories.ElasticsearchRepository.Elasticsearch")
    def test_skips_creation_when_indices_exist(self, MockES):
        mock_client = MagicMock()
        MockES.return_value = mock_client
        mock_client.indices.exists.return_value = True

        ElasticsearchRepository()

        mock_client.indices.create.assert_not_called()