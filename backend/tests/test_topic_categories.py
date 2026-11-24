"""The built-in topics are grouped into categories."""

from collections import Counter

from app.db import CATEGORIES, SEED_TOPICS, get_connection, init_db
from app.languages import LANGUAGES

def test_every_built_in_topic_is_complete_and_in_a_known_category():
    for title, situation, category in SEED_TOPICS:
        assert title and situation
        assert category in CATEGORIES, title
    assert len({title for title, *_ in SEED_TOPICS}) == len(SEED_TOPICS)


def test_every_category_has_a_few_topics():
    sizes = Counter(category for *_, category in SEED_TOPICS)
    assert set(sizes) == set(CATEGORIES)
    assert all(size >= 4 for size in sizes.values()), sizes


def test_topics_are_listed_category_by_category_with_own_topics_last(client):
    own = {"title": "Renting a car", "situation": "At the rental desk.", "opener": "Hello!"}
    client.post("/api/topics", json=own)
    listed = client.get("/api/topics").json()
    assert listed[-1]["title"] == "Renting a car" and listed[-1]["category"] is None
    built_in = [topic["category"] for topic in listed[:-1]]
    # Each category in one run, in the order the categories are shown.
    assert list(dict.fromkeys(built_in)) == CATEGORIES
    assert built_in == sorted(built_in, key=CATEGORIES.index)
    assert listed[0]["title"] == "Small talk"


def test_an_own_topic_named_like_a_new_built_in_one_stays_the_learners(client):
    with get_connection() as conn:
        conn.execute("DELETE FROM topics WHERE title = 'At the bank' AND target = 'en'")
        conn.execute(
            "INSERT INTO topics (target, title, situation, opener, custom) VALUES ('en', 'At the bank', 'Mine.', 'Hi!', 1)"
        )
    init_db()
    mine = [topic for topic in client.get("/api/topics").json() if topic["title"] == "At the bank"]
    assert len(mine) == 1
    assert mine[0]["custom"] is True and mine[0]["category"] is None and mine[0]["situation"] == "Mine."


def test_starting_the_app_again_does_not_use_up_topic_ids(client):
    for _ in range(3):
        init_db()
    own = {"title": "Renting a car", "situation": "At the rental desk.", "opener": "Hello!"}
    assert client.post("/api/topics", json=own).json()["id"] == len(SEED_TOPICS) * len(LANGUAGES) + 1
