"""
message_serializer.py
=====================
Serialize/deserialize LangChain messages to/from MongoDB-compatible dicts.
Handles: HumanMessage, AIMessage, ToolMessage
- SystemMessage is never stored (passed directly to Gemini at LLM construction)
- Thinking blocks are stripped from AIMessage content before storing
"""

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage


# ── Serialize ─────────────────────────────────────────────────────────────────

def _extract_text_content(content) -> str:
    """Strip thinking blocks, keep only text from AIMessage content."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return ""


def serialize_message(message) -> dict:
    if isinstance(message, HumanMessage):
        return {
            "type": "human",
            "content": message.content,
        }
    elif isinstance(message, AIMessage):
        content = _extract_text_content(message.content)

        if not content.strip():
            return None
        
        return {
            "type": "ai",
            "content": content,
            "tool_calls": message.tool_calls or [],
            
        }
    elif isinstance(message, ToolMessage):
        return {
            "type": "tool",
            "content": message.content,
            "tool_call_id": message.tool_call_id,
        }
    else:
        return None


def serialize_messages(messages: list) -> list[dict]:
    serialized = []

    for m in messages:
        s = serialize_message(m)
        if s is not None:  
            serialized.append(s)

    return serialized


# ── Deserialize ───────────────────────────────────────────────────────────────

def deserialize_message(data: dict):
    msg_type = data.get("type")

    if msg_type == "human":
        return HumanMessage(content=data["content"])

    elif msg_type == "ai":
        return AIMessage(
            content=data["content"],
            tool_calls=data.get("tool_calls", [])
        )

    elif msg_type == "tool":
        return ToolMessage(
            content=data["content"],
            tool_call_id=data["tool_call_id"],
        )

    else:
        return None


def deserialize_messages(data: list[dict]) -> list:
    messages = []

    for d in data:
        if d is None: 
            continue

        msg = deserialize_message(d)
        if msg is not None:
            messages.append(msg)

    return messages