import io
import struct
import wave
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _wav_bytes(seconds: float = 0.5, rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack(f"<{int(seconds * rate)}h", *([0] * int(seconds * rate))))
    return buf.getvalue()


@pytest.fixture
def client():
    from main import app
    app.state.session_manager = MagicMock()
    return TestClient(app)


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.invoke.side_effect = [MagicMock(content=" total balance by bank "), MagicMock(content="translated")]
    with patch("controllers.speechController.get_codegen_llm", return_value=llm):
        yield llm


def _post(client, data: bytes, filename="recording.wav", content_type="audio/wav", translate="false"):
    return client.post(
        "/api/speech-to-text",
        files={"file": (filename, data, content_type)},
        data={"translate": translate},
    )


def test_transcribes_wav_without_translation(client, mock_llm):
    res = _post(client, _wav_bytes())
    assert res.status_code == 200
    assert res.json() == {"success": True, "transcription": "total balance by bank", "translation": None}
    assert mock_llm.invoke.call_count == 1
    media = mock_llm.invoke.call_args[0][0][0].content[1]
    assert media["mime_type"] == "audio/wav" and media["data"]


def test_handles_content_block_responses(client):
    """Gemini 3.x returns content as a list of blocks (text + thinking/signature)."""
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content=[
        {"type": "thinking", "thinking": "user asks about balances"},
        {"type": "text", "text": " total balance ", "extras": {"signature": "abc"}},
        {"type": "text", "text": "by bank "},
    ])
    with patch("controllers.speechController.get_codegen_llm", return_value=llm):
        res = _post(client, _wav_bytes())
    assert res.status_code == 200
    assert res.json()["transcription"] == "total balance by bank"


def test_translates_when_requested(client, mock_llm):
    res = _post(client, _wav_bytes(), translate="true")
    assert res.json()["translation"] == "translated"
    assert mock_llm.invoke.call_count == 2


def test_rejects_non_wav_file(client, mock_llm):
    res = _post(client, b"data", filename="clip.webm", content_type="audio/webm")
    assert res.status_code == 400
    mock_llm.invoke.assert_not_called()


def test_rejects_empty_file(client, mock_llm):
    assert _post(client, b"").status_code == 400


def test_rejects_oversized_file(client, mock_llm):
    with patch("controllers.speechController.MAX_AUDIO_BYTES", 100):
        res = _post(client, _wav_bytes())
    assert res.status_code == 413
    mock_llm.invoke.assert_not_called()
