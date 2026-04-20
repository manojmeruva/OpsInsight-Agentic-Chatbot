import os

from core.prompts.prompt_cache import get_prompt

base_path = os.path.join("prompts", "base.md")


def base_prompt() -> str:
    try:
        with open(base_path, "r") as file:
            return file.read()
    except Exception:
        return ""


async def build_prompt(tag: str) -> str:
    """Combine the static base prompt with the pre-built domain prompt from SQLite cache."""
    domain_prompt = await get_prompt(tag)
    return base_prompt() + "\n" + domain_prompt
