"""
conversation.py
===============
MultiTurnConversation split from multi_turn_langchain.py.
Tool logic lives in tools.py. LLM construction in llm_factory.py.
"""

import re
import time
import asyncio
import json
import base64
import logging
import traceback
from typing import List

from fastapi import HTTPException
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage, message_chunk_to_message

from prompts.sys_domain_prompt import generate_domain_prompt, generate_sys_domain_test_prompt
from .llm_factory import get_llm, get_codegen_llm
from .tools import build_tools


ARABIC_PATTERN = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
)

FALLBACK_MSG = (
    "We acknowledge your question. OpsInsight is still learning this type of request, "
    "and the response will be available soon."
)

MAX_RETRIES = 2


# ==============================================================================
# MultiTurnConversation
# ==============================================================================

class MultiTurnConversation:

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    async def create(
        cls,
        chat_history,
        conversations,
        module_name,
        current_timestamp,
        test=False,
        sys_test_prompt=None,
        tag_list=None,
    ):
        instance = cls.__new__(cls)
        instance._init_sync(current_timestamp)

        if test:
            instance.sys_instruction= generate_sys_domain_test_prompt(
                system_domain_prompt=sys_test_prompt, list_of_domains=tag_list
            )
        else:
            instance.sys_instruction = await generate_domain_prompt(
                module_name=module_name
            )
        instance.module_name = module_name
        instance._init_llm_and_history(chat_history,conversations)
        return instance

    # ── Sync init ─────────────────────────────────────────────────────────────

    def _init_sync(self, current_timestamp):
        self.current_time        = current_timestamp
        self.error_message       = None
        self.timing_data         = []
        self.last_generated_code = None

    # ── LLM + history init ────────────────────────────────────────────────────

    def _init_llm_and_history(self, chat_history,conversations):
        # Tool-bound orchestrator LLM — tools are built fresh per chat() call
        # so we bind lazily inside chat(). Store base LLM here.
        self._base_llm = get_llm()

        # Message history — chat_history is already native LangChain messages
        # loaded from session DB by the caller.
        # Fresh session: seed with SystemMessage.
        # Existing session: use as-is.
        self.message_history: List = [SystemMessage(content=self.sys_instruction)]
        if chat_history:
            self.message_history.extend(chat_history)
        

        self.conversations = conversations
        self.timing_data = []

    # ── Translation helpers ───────────────────────────────────────────────────


    # ── Streaming helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _text_of(content) -> str:
        """Extract plain text from an AIMessage / chunk content (str or list of blocks)."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(
                item.get("text", "") if isinstance(item, dict) and item.get("type") == "text"
                else item if isinstance(item, str) else ""
                for item in content
            )
        return ""

    async def _stream_llm(self, llm, parts: list, stream_text: bool):
        """
        Stream one LLM call. Yields ("event", ...) tuples for text deltas and
        finally ("message", AIMessage) with the aggregated response.
        """
        full  = None
        index = len(parts)
        async for chunk in llm.astream(self.message_history):
            full = chunk if full is None else full + chunk
            delta = self._text_of(chunk.content)
            if stream_text and delta:
                yield "event", {"event": "delta", "data": {"index": index, "text": delta}}
        message = message_chunk_to_message(full) if full is not None else AIMessage(content="")
        yield "message", message

    @staticmethod
    async def _run_with_status(coro, status_queue: asyncio.Queue):
        """Run *coro* while relaying status events it puts on *status_queue*."""
        task = asyncio.create_task(coro)
        while True:
            getter = asyncio.create_task(status_queue.get())
            done, _ = await asyncio.wait({task, getter}, return_when=asyncio.FIRST_COMPLETED)
            if getter in done:
                yield "event", {"event": "status", "data": getter.result()}
                continue
            getter.cancel()
            break
        while not status_queue.empty():
            yield "event", {"event": "status", "data": status_queue.get_nowait()}
        yield "result", task.result()   # re-raises tool exceptions

    @staticmethod
    def _status(stage: str, message: str) -> dict:
        return {"event": "status", "data": {"stage": stage, "message": message}}

    @staticmethod
    def _part(parts: list, part: dict) -> dict:
        parts.append(part)
        return {"event": "part", "data": {"index": len(parts) - 1, "part": part}}

    # ── chat() ────────────────────────────────────────────────────────────────

    async def chat(self, user_input: str) -> list[dict]:
        """Non-streaming wrapper: collects the parts produced by chat_stream()."""
        output_content = []
        async for event in self.chat_stream(user_input, stream_text=False):
            if event["event"] == "part":
                output_content.append(event["data"]["part"])
        return output_content

    async def chat_stream(self, user_input: str, stream_text: bool = True):
        """
        Async generator of UI events:
            {"event": "status", "data": {"stage", "message"}}
            {"event": "delta",  "data": {"index", "text"}}      (only if stream_text)
            {"event": "part",   "data": {"index", "part"}}      (final content of a part)
            {"event": "sql",    "data": {"sql"}}
        """
        self.timing_data   = []
        self.error_message = None
        parts: list        = []

        try:
            logging.info(f"User Query: {user_input}")

            # Per-request mutable state passed into tools via closure
            timing_data          = self.timing_data
            last_generated_code  = []          # mutable ref — tools write, we read back
            status_queue         = asyncio.Queue()
            history_string = ""
            count = 1

            for conv in self.conversations:
                history_string += f"{count}. User : {conv.get('user_input', '')}\n"
                count += 1

            # Return the final string (or a default message if empty)
            conv_history = history_string.strip() if history_string else "No previous history found."

            # Build tools bound to this request's context
            sql_tool, rag_tool = build_tools(
                user_input=user_input,
                conversation_history=conv_history,
                module_name=self.module_name,
                current_time=self.current_time,
                timing_data=timing_data,
                last_generated_code=last_generated_code,
                on_status=status_queue.put_nowait,
            )

            # Bind tools to LLM for this turn
            llm = self._base_llm.bind_tools([sql_tool, rag_tool])

            # 1. Append user message
            self.message_history.append(HumanMessage(content=user_input))

            # ── First LLM call (streamed) ─────────────────────────────────
            yield self._status("thinking", "Understanding your question…")
            t0 = time.time()
            response: AIMessage = None
            async for kind, value in self._stream_llm(llm, parts, stream_text):
                if kind == "event":
                    yield value
                else:
                    response = value
            timing_1 = {"function": "llm_call_1", "time": time.time() - t0, "children": []}

            self.message_history.append(response)
            logging.info(f"First LLM response: {response}")

            # ── No tool call → plain text ─────────────────────────────────
            if not response.tool_calls:
                self.timing_data.append(timing_1)
                text = self._text_of(response.content)
                yield self._part(parts, {"type": "text", "content": text or FALLBACK_MSG})
                return

            # ── Tool call ─────────────────────────────────────────────────
            tool_call    = response.tool_calls[0]
            tool_name    = tool_call["name"]
            tool_call_id = tool_call["id"]
            logging.info(f"Tool called: {tool_name}")

            # ── RAG branch ────────────────────────────────────────────────
            if tool_name == "get_context_from_rag":
                yield self._status("retrieving", "Looking up the business glossary…")
                rag_result = await asyncio.to_thread(rag_tool.invoke, {})
                self.message_history.append(
                    ToolMessage(content=str(rag_result), tool_call_id=tool_call_id)
                )

                yield self._status("writing", "Writing the answer…")
                t2 = time.time()
                final_response = None
                async for kind, value in self._stream_llm(llm, parts, stream_text):
                    if kind == "event":
                        yield value
                    else:
                        final_response = value
                self.message_history.append(final_response)
                timing_2 = {"function": "llm_call_2", "time": time.time() - t2, "children": []}
                self.timing_data.extend([timing_1, timing_2])

                text = self._text_of(final_response.content)
                yield self._part(parts, {"type": "text", "content": text or FALLBACK_MSG})
                return

            # ── SQL / Plotting branch (with retries) ──────────────────────
            if tool_name == "get_data_from_sql":
                final_execution_success = False
                tool_result: dict = None

                for attempt in range(MAX_RETRIES):
                    try:
                        async for kind, value in self._run_with_status(sql_tool.ainvoke({}), status_queue):
                            if kind == "event":
                                yield value
                            else:
                                tool_result = value
                        final_execution_success = True
                        break

                    except HTTPException as e:
                        error_tb = traceback.format_exc()
                        self.error_message = error_tb
                        logging.error(f"Execution failed attempt {attempt + 1}: {error_tb}")

                        if attempt < MAX_RETRIES - 1:
                            yield self._status("retrying", "Query failed — correcting and retrying…")
                            self.message_history.append(
                                ToolMessage(
                                    content=json.dumps({
                                        "error": str(e.detail),
                                        "traceback_snippet": error_tb.splitlines()[-1],
                                        "previous_code": str(
                                            last_generated_code[0] if last_generated_code else None
                                        ),
                                    }),
                                    tool_call_id=tool_call_id,
                                )
                            )
                            correction: AIMessage = await llm.ainvoke(self.message_history)
                            self.message_history.append(correction)

                            if not correction.tool_calls:
                                text = self._text_of(correction.content)
                                if text:
                                    yield self._part(parts, {"type": "text", "content": text})
                                break

                            tool_call    = correction.tool_calls[0]
                            tool_call_id = tool_call["id"]
                        else:
                            yield self._part(parts, {"type": "text", "content": FALLBACK_MSG})
                            self.timing_data.append(timing_1)
                            return

                if final_execution_success:
                    self.last_generated_code = last_generated_code[0] if last_generated_code else None
                    if self.last_generated_code and self.last_generated_code.sql_query:
                        yield {"event": "sql", "data": {"sql": self.last_generated_code.sql_query}}

                    function_output_parts = tool_result["output"]
                    intent                = tool_result["intent"]

                    # Append tool result to history (serialisable)
                    self.message_history.append(
                        ToolMessage(
                            content=json.dumps(
                                [p if isinstance(p, (str, list)) else "image_data"
                                 for p in function_output_parts]
                            ),
                            tool_call_id=tool_call_id,
                        )
                    )

                    if intent in ("data-extraction", "plotting"):
                        for part in function_output_parts:
                            if isinstance(part, list) and intent == "data-extraction":
                                yield self._part(parts, {"type": "table", "content": part})
                            elif isinstance(part, str) and part.strip():
                                yield self._part(parts, {"type": "text", "content": part})
                            elif isinstance(part, dict) and "image_b64" in part:
                                yield self._part(parts, {
                                    "type": "image",
                                    "mime_type": part["mime_type"],
                                    "content": part["image_b64"],
                                })
                    else:
                        yield self._part(parts, {"type": "text", "content": FALLBACK_MSG})

                self.timing_data.append(timing_1)

        except Exception as e:
            self.error_message = traceback.format_exc()
            logging.error("Unhandled error in chat: %s", self.error_message)
            raise HTTPException(status_code=500, detail=str(e))

        if not parts:
            logging.info("No output content generated")
            yield self._part(parts, {"type": "text", "content": FALLBACK_MSG})

    def history(self):
        print(self.message_history)
        return self.message_history
    
    def translate_arabic_to_english(self, text: str) -> tuple[str, bool]:
        if not ARABIC_PATTERN.search(text):
            return text, False
        prompt = (
            "Translate the following text to English.\n"
            "Rules:\n- Provide ONLY the English translation\n"
            "- No explanations, notes, or alternatives\n"
            "- Keep abbreviations (MRO, KPI, CEO, etc.) as-is\n"
            "- No markdown or formatting\n"
            "- If text is mixed Arabic-English, translate Arabic parts to English\n\n"
            f"Text to translate:\n{text}"
        )
        try:
            resp = get_codegen_llm().invoke([HumanMessage(content=prompt)])
            return resp.content.strip(), True
        except Exception as e:
            self.error_message = traceback.format_exc()
            raise Exception(f"Translation error: {e}")

    def translate_english_to_arabic(self, text: str, ip_is_arabic: bool) -> str:
        if not (ip_is_arabic and not ARABIC_PATTERN.search(text)):
            return text
        prompt = (
            "Translate the following text to Arabic.\n"
            "Rules:\n- Provide ONLY the Arabic translation\n"
            "- No explanations, notes, or alternatives\n"
            "- Keep abbreviations (MRO, KPI, CEO, etc.) as-is\n"
            "- No markdown or formatting\n\n"
            f"Text to translate:\n{text}"
        )
        try:
            resp = get_codegen_llm().invoke([HumanMessage(content=prompt)])
            return resp.content.strip()
        except Exception as e:
            self.error_message = traceback.format_exc()
            raise Exception(f"Translation error: {e}")