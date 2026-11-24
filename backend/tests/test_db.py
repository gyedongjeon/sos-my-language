"""Database connections."""

import sqlite3

import pytest

from app.db import get_connection


def test_a_connection_is_closed_when_its_block_ends():
    # An open connection keeps the database file locked on Windows, where it then cannot be
    # replaced or removed.
    with get_connection() as conn:
        conn.execute("SELECT 1")
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1")


def test_changes_are_saved_when_the_block_ends_and_dropped_when_it_fails():
    with get_connection() as conn:
        conn.execute("INSERT INTO settings (key, value) VALUES ('kept', '1')")
    with pytest.raises(RuntimeError), get_connection() as conn:
        conn.execute("INSERT INTO settings (key, value) VALUES ('dropped', '1')")
        raise RuntimeError("Something went wrong.")
    with get_connection() as conn:
        assert [row["key"] for row in conn.execute("SELECT key FROM settings")] == ["kept"]
