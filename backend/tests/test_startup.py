"""The server starts quickly: the LLM library, slow to load, is loaded after the server is up."""

import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).parent.parent


def run(code: str) -> str:
    """Runs Python code in a fresh interpreter, which has loaded nothing yet, and returns its output."""
    done = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def test_the_server_is_ready_before_the_llm_library_is_loaded():
    assert run("import sys, app.main; print('litellm' in sys.modules)") == "False"


def test_the_llm_library_is_loaded_in_the_background_once_the_server_is_up():
    code = """
import sys, time
from fastapi.testclient import TestClient
from app.main import app
from app import llm
with TestClient(app):
    print(llm.loaded.wait(60))
"""
    assert run(code) == "True"


def test_the_llm_library_uses_the_price_list_it_ships_with_instead_of_downloading_one():
    assert run("import os, app.llm; print(os.environ.get('LITELLM_LOCAL_MODEL_COST_MAP'))") == "True"
