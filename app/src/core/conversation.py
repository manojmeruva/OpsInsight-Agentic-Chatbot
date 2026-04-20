"""
conversation.py
===============
MultiTurnConversation split from multi_turn_langchain.py.
Tool logic lives in tools.py. LLM construction in llm_factory.py.
"""

import re
import time
import json
import base64
import logging
import traceback
from typing import List

from fastapi import HTTPException
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

from prompts.sys_domain_prompt import generate_smart_meter_prompt, generate_sys_domain_test_prompt
from .llm_factory import get_llm, get_codegen_llm
from .tools import build_tools


ARABIC_PATTERN = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
)

FALLBACK_MSG = (
    "We acknowledge your question. Energon is in the training phase, "
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
            instance.sys_instruction = await generate_smart_meter_prompt(
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


    # ── chat() ────────────────────────────────────────────────────────────────

    async def chat(self, user_input: str) -> list[dict]:
        self.timing_data   = []
        self.error_message = None
        output_content     = []

        try:
            logging.info(f"User Query: {user_input}")

            # Per-request mutable state passed into tools via closure
            timing_data          = self.timing_data
            last_generated_code  = []          # mutable ref — tools write, we read back
            history_string = ""
            count = 1
            
            for conv in self.conversations:
                
                history_string += f"{count}. User : {conv.get('user_input',"")}\n"
                count += 1
                print(f"Captured: {conv.get('user_input',"")}")

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
            )

            # Bind tools to LLM for this turn
            llm = self._base_llm.bind_tools([sql_tool, rag_tool])

            # 1. Append user message
            self.message_history.append(HumanMessage(content=user_input))

            # ── First LLM call ────────────────────────────────────────────
            t0       = time.time()
            response: AIMessage = llm.invoke(self.message_history)
            duration = time.time() - t0
            timing_1 = {"function": "llm_call_1", "time": duration, "children": []}

            self.message_history.append(response)
            logging.info(f"First LLM response: {response}")

            # ── No tool call → plain text ─────────────────────────────────
            if not response.tool_calls:
                self.timing_data.append(timing_1)
                content = response.content
                if isinstance(content, str):
                    output_content.append({"type": "text", "content": content})
                elif isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            output_content.append({"type": "text", "content": item.get("text", "")})
                        elif isinstance(item, str):
                            output_content.append({"type": "text", "content": item})
                return output_content

            # ── Tool call ─────────────────────────────────────────────────
            tool_call    = response.tool_calls[0]
            tool_name    = tool_call["name"]
            tool_call_id = tool_call["id"]
            logging.info(f"Tool called: {tool_name}")

            # ── RAG branch ────────────────────────────────────────────────
            if tool_name == "get_context_from_rag":
                rag_result = rag_tool.invoke({})
                self.message_history.append(
                    ToolMessage(content=str(rag_result), tool_call_id=tool_call_id)
                )

                t2             = time.time()
                final_response = llm.invoke(self.message_history)
                self.message_history.append(final_response)
                timing_2 = {"function": "llm_call_2", "time": time.time() - t2, "children": []}
                self.timing_data.extend([timing_1, timing_2])

                content = final_response.content
                if isinstance(content, str):
                    output_content.append({"type": "text", "content": content})
                elif isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            output_content.append({"type": "text", "content": item.get("text", "")})
                return output_content

            # ── SQL / Plotting branch (with retries) ──────────────────────
            if tool_name == "get_data_from_sql":
                final_execution_success = False

                for attempt in range(MAX_RETRIES):
                    try:
                        tool_result: dict = await sql_tool.ainvoke({})
                        final_execution_success = True
                        break

                    except HTTPException as e:
                        error_tb = traceback.format_exc()
                        self.error_message = error_tb
                        logging.error(f"Execution failed attempt {attempt + 1}: {error_tb}")

                        if attempt < MAX_RETRIES - 1:
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
                            correction: AIMessage = llm.invoke(self.message_history)
                            self.message_history.append(correction)

                            if not correction.tool_calls:
                                content = correction.content
                                if isinstance(content, str):
                                    output_content.append({"type": "text", "content": content})
                                break

                            tool_call    = correction.tool_calls[0]
                            tool_call_id = tool_call["id"]
                        else:
                            output_content.append({"type": "text", "content": FALLBACK_MSG})
                            self.timing_data.append(timing_1)
                            return output_content

                if final_execution_success:
                    self.last_generated_code = last_generated_code[0] if last_generated_code else None

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

                    if intent == "data-extraction":
                        for part in function_output_parts:
                            if isinstance(part, list):
                                output_content.append({"type": "table", "content": part})
                            elif isinstance(part, str) and part.strip():
                                output_content.append({"type": "text", "content": part})
                            elif isinstance(part, dict) and "image_b64" in part:
                                output_content.append({
                                    "type": "image",
                                    "mime_type": part["mime_type"],
                                    "content": part["image_b64"],
                                })

                    elif intent == "plotting":
                        for part in function_output_parts:
                            if not part:
                                continue
                            if isinstance(part, str):
                                output_content.append({"type": "text", "content": part})
                            elif isinstance(part, dict) and "image_b64" in part:
                                output_content.append({
                                    "type": "image",
                                    "mime_type": part["mime_type"],
                                    "content": part["image_b64"],
                                })
                    else:
                        output_content.append({"type": "text", "content": FALLBACK_MSG})

                self.timing_data.append(timing_1)
                return output_content

        except Exception as e:
            self.error_message = traceback.format_exc()
            logging.error("Unhandled error in chat: %s", self.error_message)
            output_content.append({"type": "text", "content": FALLBACK_MSG})
            raise HTTPException(status_code=500, detail=str(e))

        if not output_content:
            output_content.append({"type": "text", "content": FALLBACK_MSG})
            logging.info("No output content generated")
        return output_content

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