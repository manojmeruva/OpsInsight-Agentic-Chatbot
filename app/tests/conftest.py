"""
Test bootstrap: tests live in app/tests, the application in app/src.

The app imports its modules as top-level packages (e.g. `from core.tools import ...`)
and opens metadata.db / prompts with paths relative to app/src, so put app/src on
sys.path and run tests from that directory.
"""

import os
import sys

SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

os.chdir(SRC_DIR)

# Tests must never touch real infrastructure
os.environ.setdefault("DB_TYPE", "sqlite")
os.environ.setdefault("DATA_DB_ENGINE", "sqlite")
os.environ.setdefault("ES_ENABLED", "true")
