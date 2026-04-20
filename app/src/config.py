import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    DB_HOST = os.getenv("STARROCKS_IP")
    DB_USER = os.getenv("STARROCKS_USER")
    DB_NAME = os.getenv("STARROCKS_DB")
    DB_PASSWORD = os.getenv("STARROCKS_PASSWORD")
    DB_TYPE = os.getenv("DB_TYPE","mongo")
    DB_PORT = int(os.getenv("STARROCKS_PORT", 3306))
    SESSION_TIMEOUT_SECONDS = int(os.getenv("SESSION_TIMEOUT_SECONDS", 30))

    # Connection pool settings
    POOL_SIZE = int(os.getenv("STARROCKS_POOL_SIZE", 5))
    POOL_MAX_OVERFLOW = int(os.getenv("STARROCKS_POOL_MAX_OVERFLOW", 10))
    POOL_RECYCLE_SECONDS = int(os.getenv("STARROCKS_POOL_RECYCLE", 1800))
    POOL_PRE_PING = True

    

    @classmethod
    def get_db_config(cls):
        return {
            "host": cls.DB_HOST,
            "user": cls.DB_USER,
            "database": cls.DB_NAME,
            "port": cls.DB_PORT,
            "password": cls.DB_PASSWORD or None,
        }
    
    def get_context_from_rag_declaration(tags):
        return {
            "name": "get_context_from_rag",
            "description": "Extracts relevant context from MDM docs",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_query": {
                        "type": "string",
                        "description": "The user's question",
                    },
                     "conversation_history": {
                        "type": "string",
                        "description": "The relevant conversation history question-answer pairs required to answer user's question, including database schema context",
                    },
                    "tag": {
                        "type": "string",
                        "enum": tags,
                        "description": "This is the output classification tag based in user query",
                    },
                },
                "required": ["user_query","conversation_history","tag"],
            },
        }
    def get_data_from_sql_declaration(tags) :
        return {
            "name": "get_data_from_sql",
            "description": (
    "Writes code to extract data from SQL DB **or** plot previously fetched data. "
    "Always use this function when the user asks to get, display, visualize, or plot any data. "
    "If user says 'plot the same', 'show chart', 'display graph', or 'visualize data', "
    "reuse the last query result and generate a plot accordingly."),
            # "description": "Writes code to extract data from sql db and plotting. Uses conversation context to understand database schema, column names, and maintain consistency with previous queries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_query": {
                        "type": "string",
                        "description": "The user's question as described by him in his own words, do not convert it into sql. ",
                    },
                    "conversation_history": {
                        "type": "string",
                        "description": "The relevant conversation history question-answer pairs required to answer user's question, including database schema context",
                    },
                    "tag": {
                        "type": "string",
                        "enum": tags ,
                        "description": "This is the output classification tag based in user query",
                    },
                },
                "required": ["user_query", "conversation_history", "tag"],
            },
        }


    conversation_vars = {
            "text_to_sql_prompt":"""
        {sys_prompt}
        
        IMPORTANT CONTEXT FROM CONVERSATION HISTORY:
        {conversation_history}
        
        When generating SQL queries and Python code:
        1. Use the conversation history to understand previously established:
           - Database schema and available columns
           - Data types and constraints
           - Filtering conditions and business logic
        2. Ensure all necessary Python imports are included:
        3. Handle potential missing columns gracefully with try-catch blocks
        4. Maintain consistency with previous variable names and data structures
        5. Always include proper error handling for database operations

        Now answer the new query:
            {user_query}
        """.strip(),

        "translation_prompt_en_to_ar":"""Translate the following text to Arabic.
    Rules:
    - Provide ONLY the Arabic translation
    - No explanations, notes, or alternatives
    - Keep abbreviations (MRO, KPI, CEO, etc.) as-is
    - No markdown or formatting

    Text to translate:""",

        "translation_prompt_ar_to_en":"""Translate the following text to English.
    Rules:
    - Provide ONLY the English translation
    - No explanations, notes, or alternatives
    - Keep abbreviations (MRO, KPI, CEO, etc.) as-is
    - No markdown or formatting
    - If text is mixed Arabic-English, translate Arabic parts to English

    Text to translate:""",

    "final_error_message":"I am unable to retrieve the data after multiple retries due to a persistent code execution error.",

    "error_message_to_ui":"I'm sorry, I couldn't find relevant data or interpret your question. Can you rephrase it?"
    }


    # --------------------------------------------------
    # Flat prompts table — replaces old multi-table schema
    # --------------------------------------------------
    metadata_sqllite_vars = {
        "prompts": """
    CREATE TABLE IF NOT EXISTS prompts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tag TEXT NOT NULL UNIQUE,
        prompt TEXT NOT NULL,
        description TEXT,
        module TEXT
    );
    """
    }

    starrocks_sqls = {
        "prompts": """
            SELECT tag, prompt, description, module
            FROM prompts
            ORDER BY tag
        """
    }
