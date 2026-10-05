from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage

from core.message_serializer import content_text, serialize_message


def test_plain_string_content():
    assert content_text("hello") == "hello"


def test_content_blocks_keep_only_text():
    content = [
        {"type": "thinking", "thinking": "internal"},
        {"type": "text", "text": "Total "},
        {"type": "text", "text": "balance", "extras": {"signature": "abc"}},
        "!",
    ]
    assert content_text(content) == "Total balance!"


def test_unknown_content_is_empty():
    assert content_text(None) == ""


def test_serializer_stores_text_of_block_content():
    msg = AIMessage(content=[{"type": "thinking", "thinking": "x"}, {"type": "text", "text": "Answer"}])
    assert serialize_message(msg)["content"] == "Answer"


def test_translation_helpers_handle_block_content():
    from core.conversation import MultiTurnConversation

    conv = MultiTurnConversation.__new__(MultiTurnConversation)
    conv.error_message = None
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content=[{"type": "text", "text": " What is the balance? "}])
    with patch("core.conversation.get_codegen_llm", return_value=llm):
        assert conv.translate_arabic_to_english("ما هو الرصيد؟") == ("What is the balance?", True)
        assert conv.translate_english_to_arabic("Balance", True) == "What is the balance?"
