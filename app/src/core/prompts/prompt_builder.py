import os

from config import Config
from core.prompts.prompt_cache import get_prompt

base_path = os.path.join("prompts", "base.md")


SQL_DIALECT_RULES = {
    "starrocks": """- The syntax and functions used must only be compatible with **MySQL SQL dialect** (StarRocks), please do not use any other syntax like SQLite , PostgreSQL .. etc.
    - Month bucket: DATE_FORMAT(t.transaction_date, '%Y-%m')
    - Day bucket: DATE(t.transaction_date)
    - Last 4 characters: RIGHT(col, 4); string concatenation: CONCAT(a, b)
    - Do not use strftime(), date('now', ...) or the || operator.""",
    "sqlite": """- The syntax and functions used must only be compatible with **SQLite SQL dialect**, please do not use any other syntax like MySQL , PostgreSQL .. etc.
    - Month bucket: strftime('%Y-%m', t.transaction_date)
    - Day bucket: date(t.transaction_date); year: strftime('%Y', t.transaction_date)
    - Last 4 characters: substr(col, -4); string concatenation: a || b
    - Do not use DATE_FORMAT(), DATE_TRUNC(), DATE_SUB(), INTERVAL, RIGHT(), CONCAT() or NOW().
    - Prefer literal date strings computed from the current datetime (e.g. t.transaction_date >= '2026-06-01') over date('now').""",
}


def base_prompt() -> str:
    try:
        with open(base_path, "r", encoding="utf-8") as file:
            template = file.read()
    except Exception:
        return ""
    dialect = SQL_DIALECT_RULES.get(Config.DATA_DB_ENGINE, SQL_DIALECT_RULES["starrocks"])
    return template.replace("{SQL_DIALECT_RULES}", dialect)


async def build_prompt(tag: str) -> str:
    """Combine the static base prompt with the pre-built domain prompt from SQLite cache."""
    domain_prompt = await get_prompt(tag)
    return base_prompt() + "\n" + domain_prompt
