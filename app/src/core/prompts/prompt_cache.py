import aiosqlite
import logging

DB_PATH = "metadata.db"


async def get_prompt(tag: str) -> str:
    """Fetch the full pre-built prompt text for a given domain tag."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT prompt FROM prompts WHERE LOWER(tag) = ?", (tag.lower(),)
        )
        row = await cursor.fetchone()
        if row is None:
            logging.warning("No prompt found for tag: %s", tag)
            return ""
        return row[0]


async def get_all_tags_and_descriptions(module: str = None) -> list[tuple[str, str]]:
    """Fetch (tag, description) pairs for domain classification.

    If *module* is provided, only tags belonging to that module are returned.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        if module:
            cursor = await db.execute(
                "SELECT tag, description FROM prompts WHERE LOWER(module) = ? ORDER BY tag",
                (module.lower(),)
            )
        else:
            cursor = await db.execute("SELECT tag, description FROM prompts ORDER BY tag")
        rows = await cursor.fetchall()
        return [(r[0], r[1]) for r in rows]
