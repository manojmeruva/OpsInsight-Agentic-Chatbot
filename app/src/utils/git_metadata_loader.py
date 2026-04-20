"""
Git-based metadata loader.

Reads module metadata from a cloned Git repo folder structure and rebuilds
the local metadata.db (SQLite) using an atomic swap.

Expected repo structure (nested: module/tag):
    <repo_root>/
        <module_name>/              # e.g. SMOP, dm
            <tag_name>/             # e.g. billing_efficiency, ld
                prompt.md           # Full prompt text
                description.txt     # One-line plain text description
"""

import os
import sqlite3
import logging
from filelock import FileLock
from config import Config

logger = logging.getLogger(__name__)

DB_PATH = "metadata.db"
TMP_DB_PATH = "metadata_new.db"
LOCK_PATH = "metadata_refresh.lock"


def load_metadata_from_repo(repo_path: str) -> list[dict]:
    """
    Walk the cloned metadata repo (module/tag/ structure) and return a list
    of prompt dicts. Folder hierarchy encodes module and tag — no config
    files needed.
    """
    entries = []
    if not os.path.isdir(repo_path):
        raise FileNotFoundError(f"Metadata repo path does not exist: {repo_path}")

    for module_name in sorted(os.listdir(repo_path)):
        module_path = os.path.join(repo_path, module_name)

        # Skip non-directories and hidden folders (like .git)
        if not os.path.isdir(module_path) or module_name.startswith("."):
            continue

        for tag_name in sorted(os.listdir(module_path)):
            tag_path = os.path.join(module_path, tag_name)

            if not os.path.isdir(tag_path):
                continue

            prompt_path = os.path.join(tag_path, "prompt.md")
            desc_path = os.path.join(tag_path, "description.txt")

            if not os.path.exists(prompt_path):
                logger.debug("Skipping %s/%s (no prompt.md)", module_name, tag_name)
                continue

            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_text = f.read()

            description = ""
            if os.path.exists(desc_path):
                with open(desc_path, "r", encoding="utf-8") as f:
                    description = f.read().strip()

            entries.append({
                "tag": tag_name,
                "prompt": prompt_text,
                "description": description,
                "module": module_name,
            })

    return entries


def validate_and_filter(entries: list[dict]) -> list[dict]:
    """
    Validate metadata entries. Skip entries with empty prompts (warn only),
    reject duplicates. Returns the list of valid entries ready to load.
    """
    valid = []
    tags_seen = set()
    skipped = 0

    for entry in entries:
        tag = entry.get("tag", "")

        if not tag:
            logger.warning("Skipping entry with no tag: %s", entry)
            skipped += 1
            continue

        if tag in tags_seen:
            logger.warning("Skipping duplicate tag: %s", tag)
            skipped += 1
            continue

        if not entry.get("prompt", "").strip():
            logger.warning("Skipping tag '%s' (empty prompt.md)", tag)
            skipped += 1
            continue

        tags_seen.add(tag)
        valid.append(entry)

    if skipped:
        logger.info("Skipped %d entries with issues, %d valid entries loaded", skipped, len(valid))

    return valid


def rebuild_metadata_db(repo_path: str) -> dict:
    """
    Load metadata from repo, validate, build new DB, atomic swap.
    Returns metrics dict with counts.
    Raises on failure — existing metadata.db is preserved.
    """
    entries = load_metadata_from_repo(repo_path)

    if not entries:
        raise ValueError(f"No metadata entries found in {repo_path}")

    entries = validate_and_filter(entries)

    if not entries:
        raise ValueError("All entries were invalid — nothing to load")

    lock = FileLock(LOCK_PATH)
    with lock:
        if os.path.exists(TMP_DB_PATH):
            os.remove(TMP_DB_PATH)

        conn = sqlite3.connect(TMP_DB_PATH, timeout=30)

        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA busy_timeout = 30000;")

            # Create table
            conn.execute(Config.metadata_sqllite_vars["prompts"])

            # Insert all entries
            conn.executemany(
                "INSERT INTO prompts (tag, prompt, description, module) VALUES (?, ?, ?, ?);",
                [(e["tag"], e["prompt"], e["description"], e["module"]) for e in entries]
            )
            conn.commit()
            conn.close()

            # Atomic swap — only after success
            os.replace(TMP_DB_PATH, DB_PATH)
            logger.info("Metadata DB rebuilt from git repo: %d entries", len(entries))

            return {"prompts": len(entries)}

        except Exception:
            conn.close()
            if os.path.exists(TMP_DB_PATH):
                os.remove(TMP_DB_PATH)
            logger.error("Metadata DB rebuild failed. Existing DB preserved.")
            raise