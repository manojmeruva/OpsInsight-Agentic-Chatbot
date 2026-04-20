import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client with mocked session_manager."""
    with patch("main.SessionManager") as MockSM:
        mock_sm = MagicMock()
        MockSM.return_value = mock_sm

        # Patch the module-level session_manager before importing app
        with patch("main.session_manager", mock_sm):
            from main import app
            yield TestClient(app), mock_sm


# -------------------- POST /api/load-session-history --------------------

class TestLoadSessionHistoryEndpoint:
    def test_success_response(self, client):
        test_client, mock_sm = client
        mock_sm.load_session_history_from_es.return_value = {
            "status": "success",
            "sessions_loaded": 3,
            "messages_loaded": 15,
            "time_taken": 1.5,
        }

        response = test_client.post(
            "/api/load-session-history",
            json={"user_email": "test@impresa.com", "days": 7},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["sessions_loaded"] == 3
        assert data["messages_loaded"] == 15
        mock_sm.load_session_history_from_es.assert_called_once_with(
            user_email="test@impresa.com", days=7
        )

    def test_skipped_when_es_unavailable(self, client):
        test_client, mock_sm = client
        mock_sm.load_session_history_from_es.return_value = {
            "status": "skipped",
            "reason": "Elasticsearch unavailable",
            "sessions_loaded": 0,
            "messages_loaded": 0,
        }

        response = test_client.post(
            "/api/load-session-history",
            json={"user_email": "test@impresa.com"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "skipped"

    def test_default_days_is_7(self, client):
        test_client, mock_sm = client
        mock_sm.load_session_history_from_es.return_value = {
            "status": "success", "sessions_loaded": 0, "messages_loaded": 0,
        }

        test_client.post(
            "/api/load-session-history",
            json={"user_email": "test@impresa.com"},
        )

        mock_sm.load_session_history_from_es.assert_called_once_with(
            user_email="test@impresa.com", days=7
        )

    def test_custom_days_parameter(self, client):
        test_client, mock_sm = client
        mock_sm.load_session_history_from_es.return_value = {
            "status": "success", "sessions_loaded": 0, "messages_loaded": 0,
        }

        test_client.post(
            "/api/load-session-history",
            json={"user_email": "test@impresa.com", "days": 30},
        )

        mock_sm.load_session_history_from_es.assert_called_once_with(
            user_email="test@impresa.com", days=30
        )

    def test_missing_user_email_returns_422(self, client):
        test_client, _ = client

        response = test_client.post(
            "/api/load-session-history",
            json={},
        )

        assert response.status_code == 422

    def test_returns_500_on_exception(self, client):
        test_client, mock_sm = client
        mock_sm.load_session_history_from_es.side_effect = Exception("Unexpected error")

        response = test_client.post(
            "/api/load-session-history",
            json={"user_email": "test@impresa.com"},
        )

        assert response.status_code == 500
        assert response.json()["status"] == "error"


# -------------------- POST /api/archive-session-data --------------------

class TestArchiveSessionDataEndpoint:
    def test_success_response(self, client):
        test_client, mock_sm = client
        mock_sm.archive_session_data_to_es.return_value = {
            "status": "success",
            "sessions_archived": 5,
            "messages_archived": 42,
            "messages_cleaned_from_mongo": 42,
            "time_taken": 2.1,
        }

        response = test_client.post(
            "/api/archive-session-data",
            json={"user_email": "test@impresa.com"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["sessions_archived"] == 5
        assert data["messages_archived"] == 42
        assert data["messages_cleaned_from_mongo"] == 42
        mock_sm.archive_session_data_to_es.assert_called_once_with(
            user_email="test@impresa.com"
        )

    def test_skipped_when_es_unavailable(self, client):
        test_client, mock_sm = client
        mock_sm.archive_session_data_to_es.return_value = {
            "status": "skipped",
            "reason": "Elasticsearch unavailable",
            "sessions_archived": 0,
            "messages_archived": 0,
        }

        response = test_client.post(
            "/api/archive-session-data",
            json={"user_email": "test@impresa.com"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "skipped"

    def test_missing_user_email_returns_422(self, client):
        test_client, _ = client

        response = test_client.post(
            "/api/archive-session-data",
            json={},
        )

        assert response.status_code == 422

    def test_returns_500_on_exception(self, client):
        test_client, mock_sm = client
        mock_sm.archive_session_data_to_es.side_effect = Exception("DB crash")

        response = test_client.post(
            "/api/archive-session-data",
            json={"user_email": "test@impresa.com"},
        )

        assert response.status_code == 500
        assert response.json()["status"] == "error"