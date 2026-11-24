"""The built-in topics are grouped into categories."""

from collections import Counter

from app.db import CATEGORIES, SEED_TOPICS, get_connection, init_db

# The topics the first versions shipped with, in the order of their ids.
FIRST_SIX = [
    "Small talk",
    "Introducing yourself",
    "At a café",
    "Travel plans",
    "Weekend and hobbies",
    "A meeting at work",
]


def test_every_built_in_topic_is_complete_and_in_a_known_category():
    for title, situation, opener, category in SEED_TOPICS:
        assert title and situation and opener
        assert category in CATEGORIES, title
    assert len({title for title, *_ in SEED_TOPICS}) == len(SEED_TOPICS)


def test_every_category_has_a_few_topics():
    sizes = Counter(category for *_, category in SEED_TOPICS)
    assert set(sizes) == set(CATEGORIES)
    assert all(size >= 4 for size in sizes.values()), sizes


def test_the_first_topics_keep_their_ids(client):
    # Saved conversations and bookmarks of earlier versions point at these ids.
    by_id = {topic["id"]: topic["title"] for topic in client.get("/api/topics").json()}
    assert [by_id[i] for i in range(1, 7)] == FIRST_SIX


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


def test_a_database_with_only_the_first_topics_gains_the_rest_and_their_categories(client):
    own = {"title": "Renting a car", "situation": "At the rental desk.", "opener": "Hello!"}
    added = client.post("/api/topics", json=own).json()
    with get_connection() as conn:
        conn.execute("DELETE FROM topics WHERE custom = 0 AND id > 6")
        conn.execute("ALTER TABLE topics DROP COLUMN category")
    init_db()
    listed = client.get("/api/topics").json()
    assert len(listed) == len(SEED_TOPICS) + 1
    categories = {topic["title"]: topic["category"] for topic in listed}
    assert categories["At a café"] == "Food" and categories["A meeting at work"] == "Work"
    assert all(topic["category"] for topic in listed if not topic["custom"])
    assert listed[-1] == {**added, "category": None}


def test_an_own_topic_named_like_a_new_built_in_one_stays_the_learners(client):
    with get_connection() as conn:
        conn.execute("DELETE FROM topics WHERE title = 'At the bank'")
        conn.execute(
            "INSERT INTO topics (title, situation, opener, custom) VALUES ('At the bank', 'Mine.', 'Hi!', 1)"
        )
    init_db()
    mine = [topic for topic in client.get("/api/topics").json() if topic["title"] == "At the bank"]
    assert len(mine) == 1
    assert mine[0]["custom"] is True and mine[0]["category"] is None and mine[0]["situation"] == "Mine."


def test_starting_the_app_again_does_not_use_up_topic_ids(client):
    for _ in range(3):
        init_db()
    own = {"title": "Renting a car", "situation": "At the rental desk.", "opener": "Hello!"}
    assert client.post("/api/topics", json=own).json()["id"] == len(SEED_TOPICS) + 1
