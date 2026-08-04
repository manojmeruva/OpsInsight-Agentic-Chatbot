"""
tools.py
========
Tool definitions split from multi_turn_langchain.py.
All LLM access goes through llm_factory. No env vars read here.
"""

import logging
import os
import base64
import time
import traceback

from fastapi import HTTPException
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage

from core.database import get_connection
from core.prompts.prompt_builder import build_prompt
from .llm_factory import get_codegen_llm
from .models import Cgen


BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
Electricity_Domain_Sector_PATH = os.path.join(BASE_DIR, "Electricity_Domain_Sector.txt")


# ==============================================================================
# text_to_sql
# ==============================================================================

def text_to_sql(user_input: str, conversation_history:str,sys_prompt: str, current_time: str) -> list[Cgen]:
    """
    Calls the code-gen LLM with structured output to produce a Cgen object
    (SQL + Python) for the given user question.
    """
    if not user_input or not user_input.strip():
        raise HTTPException(status_code=400, detail="User query is empty.")

    enhanced_sys_prompt = f"""
    {sys_prompt}
 
    - Always keep in mind the current datetime - {current_time}
    
    IMPORTANT CONTEXT FROM CONVERSATION HISTORY:
        {conversation_history}

    When generating SQL queries and Python code:
    1. Ensure all necessary Python imports are included.
    2. Handle potential missing columns gracefully with try-catch blocks.
    3. Always include proper error handling for database operations.
    4. ALWAYS filter out NULL/None values before plotting:
       - For categorical x-axis columns: df = df.dropna(subset=[<x_column>])
       - For numeric columns: df = df.fillna(0) or df.dropna()
       - Never pass a column containing None to matplotlib bar/plot functions.
    5. In SQL, use WHERE <column> IS NOT NULL for any column used as a plot axis or label.
 
    Now answer the user's question:
        {user_input}
    """

    try:
        structured_llm = get_codegen_llm().with_structured_output(Cgen)
        messages = [
            SystemMessage(content=enhanced_sys_prompt),
            HumanMessage(content=user_input),
        ]
        parsed: Cgen = structured_llm.invoke(messages)
        logging.info(f"SQL - PYTHON - Code : {[parsed]}")
        return [parsed]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# execute_dynamic_code
# ==============================================================================

def execute_dynamic_code(my_output: list[Cgen]) -> tuple[list, list]:
    import numpy as np          # noqa — available in exec'd code via globals()
    import pandas as pd
    import matplotlib.pyplot as plt
    import pymysql

    children_timings = []
    try:
        with get_connection() as connection:
            local_vars = {"connection": connection}
            code_output     = my_output[0].code
            code_block_dict = code_output.model_dump()
            sql_block       = f'''sql_query="""{code_block_dict['sql_query']}"""\n{code_block_dict['python']}'''

            t_sql = time.time()
            exec(sql_block, globals(), local_vars)
            children_timings.append({
                "function": "sql_query_execution",
                "time": time.time() - t_sql,
                "children": [],
            })

            final_answer = local_vars.get("final_answer")

            if my_output[0].intent == "data-extraction":
                if final_answer["table"] is not None:
                    df      = final_answer["table"]
                    summary = final_answer.get("text", "")
                    return [summary, df.to_dict(orient="records")], children_timings
                elif final_answer["text"]:
                    return [final_answer["text"]], children_timings
                else:
                    return [""], children_timings

            elif my_output[0].intent == "plotting":
                img = final_answer["image"]
                if img:
                    image_b64 = img if isinstance(img, str) else base64.b64encode(img).decode("utf-8")
                    return [
                        final_answer["text"],
                        {"image_b64": image_b64, "mime_type": "image/jpeg"},
                    ], children_timings
                elif final_answer["text"]:
                    return [final_answer["text"]], children_timings
                else:
                    return [""], children_timings

            else:
                return [f"Could not process intent: {my_output[0].intent}"], children_timings

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ["Error: Execution path completed without returning data."], children_timings


# ==============================================================================
# get_context_from_rag
# ==============================================================================

def get_context_from_rag(user_input: str) -> tuple[str, dict]:
    try:
        lowered = user_input.lower()
        t0      = time.time()

        if any(k in lowered for k in domains):
            with open(Electricity_Domain_Sector_PATH, "r") as f:
                content = f.read()
    

        timing = {"function": "get_context_from_rag", "time": time.time() - t0, "children": []}
        return content, timing

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# build_tools — returns (sql_tool, rag_tool) closed over per-request state
# ==============================================================================

def build_tools(user_input: str, conversation_history:str,module_name:str,current_time: str, timing_data: list, last_generated_code: list):
    """
    Returns two LangChain @tool functions bound to the current request's state.
    `timing_data` and `last_generated_code` are mutable lists so chat() can
    read timing/code back after the tools run.
    """

    @tool
    async def get_data_from_sql() -> dict:
        """
        Call this tool whenever the user wants to retrieve, display, visualize,
        or plot any data from the database. Also use it when the user says
        'plot the same', 'show chart', 'display graph', or 'visualize data'.
        """
        t0 = time.time()

        sys_prompt = await build_prompt(tag=module_name)

        t_sql = time.time()
        parsed = text_to_sql(user_input,conversation_history,sys_prompt, current_time)
        if parsed and parsed[0].code:
            last_generated_code.clear()
            last_generated_code.append(parsed[0].code)

        timing_data.append({
            "function": "text_to_sql",
            "sql": parsed[0].code.sql_query if parsed and parsed[0].code else "",
            "time": time.time() - t_sql,
            "children": [],
        })

        function_output_parts, exec_children = execute_dynamic_code(parsed)

        timing_data.append({
            "function": "get_data_from_sql",
            "time": time.time() - t0,
            "children": exec_children,
        })

        return {"output": function_output_parts, "intent": parsed[0].intent}

    @tool
    def get_context_from_rag_tool() -> str:
        """
        Call this tool when the user asks a conceptual, definitional, or
        policy question that requires context from MDM / Smart-meter
        documentation rather than live database data.
        """
        content, timing = get_context_from_rag(user_input)
        timing_data.append(timing)
        return content

    # Rename the RAG tool to match the original name the LLM expects
    get_context_from_rag_tool.name = "get_context_from_rag"

    return get_data_from_sql, get_context_from_rag_tool