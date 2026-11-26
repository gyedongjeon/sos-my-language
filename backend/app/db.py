"""SQLite access and seed data."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from .languages import DEFAULT, LANGUAGES, Language
from .paths import DATA_DIR

DB_PATH = DATA_DIR / "app.db"

# The categories the built-in topics are shown under, in this order.
CATEGORIES = ["Everyday", "Work", "School", "Shopping", "Food", "Travel", "Services", "Home", "Opinions"]

# Built-in topics: (title, the situation the tutor plays out, category). Each language being
# taught has the tutor's opening line of every one of them, by its title.
SEED_TOPICS = [
    (
        "Small talk",
        "A relaxed chat between two acquaintances about everyday life.",
        "Everyday",
    ),
    (
        "Introducing yourself",
        "Two people meet for the first time at a social event and get to know each other.",
        "Everyday",
    ),
    (
        "At a café",
        "The tutor is a barista taking the learner's order at a café.",
        "Food",
    ),
    (
        "Travel plans",
        "Two friends talk about a trip the learner is planning or has taken.",
        "Travel",
    ),
    (
        "Weekend and hobbies",
        "A friendly chat about what the learner does in their free time.",
        "Everyday",
    ),
    (
        "A meeting at work",
        "The tutor is a colleague catching up with the learner on a project before a meeting.",
        "Work",
    ),
    # Everyday
    (
        "Talking about the weather",
        "Two neighbours run into each other outside and chat about the weather and their day.",
        "Everyday",
    ),
    (
        "Making plans with a friend",
        "The tutor is a friend of the learner, and the two decide what to do together this weekend.",
        "Everyday",
    ),
    # Work
    (
        "Daily stand-up",
        "The tutor leads a team's short daily meeting, where each person says what they did, "
        "what they will do next, and what is in their way.",
        "Work",
    ),
    (
        "Asking a colleague for help",
        "The tutor is a colleague at the next desk; the learner is stuck on a task and needs their help.",
        "Work",
    ),
    (
        "A status update for your manager",
        "The tutor is the learner's manager in a one-on-one meeting about how a project is going.",
        "Work",
    ),
    (
        "A call with a client",
        "The tutor is a client on a phone call with the learner about what they need and by when.",
        "Work",
    ),
    # School
    (
        "Asking a professor a question",
        "The tutor is a professor in their office hours; the learner is a student with a question "
        "about the course.",
        "School",
    ),
    (
        "A group project",
        "The tutor is a classmate; the two plan a group project and decide who does what.",
        "School",
    ),
    (
        "Introducing yourself in class",
        "The tutor is a teacher on the first day of a class, getting to know a new student.",
        "School",
    ),
    (
        "Chatting with a classmate",
        "The tutor is a classmate chatting with the learner after class about the lecture and "
        "their plans.",
        "School",
    ),
    # Shopping
    (
        "At a market",
        "The tutor sells fruit and vegetables at an outdoor market; the learner wants to buy "
        "some and asks about prices.",
        "Shopping",
    ),
    (
        "Buying clothes",
        "The tutor is a shop assistant in a clothing store, helping the learner find the right "
        "item and size.",
        "Shopping",
    ),
    (
        "Returning an item",
        "The tutor works at a store's customer service desk; the learner wants to return or "
        "exchange something they bought.",
        "Shopping",
    ),
    (
        "At the supermarket checkout",
        "The tutor is a cashier at a supermarket, ringing up the learner's groceries.",
        "Shopping",
    ),
    # Food
    (
        "Ordering at a restaurant",
        "The tutor is a server at a restaurant, taking the learner's order for a meal.",
        "Food",
    ),
    (
        "Booking a table by phone",
        "The tutor answers the phone at a restaurant; the learner calls to book a table.",
        "Food",
    ),
    (
        "A problem with your order",
        "The tutor is a server at a restaurant; something is wrong with what the learner was "
        "served, and the learner says so politely.",
        "Food",
    ),
    # Travel
    (
        "Airport check-in",
        "The tutor works at an airline's check-in desk; the learner is checking in for a flight "
        "with a bag.",
        "Travel",
    ),
    (
        "Hotel check-in",
        "The tutor is a hotel receptionist; the learner arrives with a reservation and has a few "
        "questions about the stay.",
        "Travel",
    ),
    (
        "Asking for directions",
        "The learner is a visitor who is lost in a city; the tutor is a local on the street who "
        "knows the way.",
        "Travel",
    ),
    (
        "At immigration",
        "The tutor is an immigration officer at an airport, asking the learner about their visit.",
        "Travel",
    ),
    # Services
    (
        "At the doctor's",
        "The tutor is a doctor; the learner is a patient who is not feeling well and describes "
        "their symptoms.",
        "Services",
    ),
    (
        "At a pharmacy",
        "The tutor is a pharmacist; the learner needs something for a minor health problem and "
        "asks how to take it.",
        "Services",
    ),
    (
        "At the bank",
        "The tutor works at a bank; the learner wants to open an account or has a question about "
        "theirs.",
        "Services",
    ),
    (
        "Calling customer service",
        "The tutor is a customer service agent on the phone; the learner calls about a problem "
        "with a product or a bill.",
        "Services",
    ),
    # Home
    (
        "Talking to your landlord",
        "The tutor is the learner's landlord; the learner tells them about something in the "
        "apartment that needs fixing.",
        "Home",
    ),
    (
        "Meeting a new neighbour",
        "The learner has just moved in; the tutor is a neighbour who lives next door and says hello.",
        "Home",
    ),
    (
        "Calling a repair service",
        "The tutor answers the phone at a repair company; the learner calls because something at "
        "home is broken and books a visit.",
        "Home",
    ),
    (
        "Viewing an apartment",
        "The tutor is an agent showing the learner an apartment for rent; the learner asks about "
        "the place, the rent, and the area.",
        "Home",
    ),
    # Opinions: no role to play; the learner talks at more length about what they think.
    (
        "A movie or show you watched",
        "A friendly chat in which the learner describes a movie or show they watched and says "
        "what they thought of it. The tutor asks for details and reasons.",
        "Opinions",
    ),
    (
        "Your hometown",
        "A friendly chat in which the learner describes the place they come from and what they "
        "like and dislike about it. The tutor asks for details and reasons.",
        "Opinions",
    ),
    (
        "Working from home or at the office",
        "A friendly discussion of whether it is better to work from home or at the office. The "
        "tutor asks for the learner's opinion and reasons, and sometimes gently takes the other side.",
        "Opinions",
    ),
    (
        "Something you read recently",
        "A friendly chat in which the learner sums up a book or an article they read and says "
        "what they thought of it. The tutor asks for details and reasons.",
        "Opinions",
    ),
    (
        "Your plans for next year",
        "A friendly chat about what the learner wants to do or change next year and why. The "
        "tutor asks for details and reasons.",
        "Opinions",
    ),
]


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """A connection for one block of work: what the block changed is saved when it ends and
    dropped when it fails, and the connection is closed either way. Leaving it open would
    keep the database file locked on Windows."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


# The language the learner chose, read from the database once; False until then.
_chosen: str | None | bool = False


def learning_language() -> Language | None:
    """The language the learner chose to practise; None until they have chosen one."""
    global _chosen
    if _chosen is False:
        with get_connection() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = 'learning_language'").fetchone()
        _chosen = row["value"] if row and row["value"] in LANGUAGES else None
    return LANGUAGES[_chosen] if _chosen else None


def current_language() -> Language:
    """The language being practised: every topic, conversation, video, and pattern belongs to
    one, and only those of this one are shown. English until the learner has chosen."""
    return learning_language() or DEFAULT


def choose_language(code: str | None) -> None:
    """Keep a language as the one being practised; None forgets the choice."""
    global _chosen
    if code is not None and code not in LANGUAGES:
        raise ValueError(f"Unknown language: {code}")
    with get_connection() as conn:
        if code is None:
            conn.execute("DELETE FROM settings WHERE key = 'learning_language'")
        else:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('learning_language', ?)", (code,))
    _chosen = code


# `target` is the code of the language a row belongs to ("en", "de"). The tables without it
# belong to a row that has it: a message to its conversation, a sentence to its video.
SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);

-- `custom` is 1 for a topic the learner added; the built-in ones cannot be removed. `category`
-- is what a built-in topic is shown under. `background` is what the tutor knows besides the
-- situation: the summary of the text a topic was made from.
CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target TEXT NOT NULL,
    title TEXT NOT NULL,
    situation TEXT NOT NULL,
    opener TEXT NOT NULL,
    custom INTEGER NOT NULL DEFAULT 0,
    category TEXT,
    background TEXT,
    UNIQUE (target, title)
);

-- A conversation keeps its topic's title, situation, and background, so it stays readable (and
-- the tutor can still reply in it) after the topic is changed or removed. `review` is JSON,
-- written when the conversation is wrapped up.
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target TEXT NOT NULL,
    topic_id INTEGER REFERENCES topics(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    situation TEXT NOT NULL,
    started_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    review TEXT,
    background TEXT
);

-- One line of a conversation, in the order they were said. The delivery columns and the
-- correction columns are filled for the learner's lines only. `practiced` is how often a
-- correction's better sentence was said correctly afterwards; `corrected_at` orders a
-- correction among the other mistakes; `dismissed` is 1 once the learner took it off the list
-- of corrections (it stays in its conversation).
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('tutor', 'learner')),
    text TEXT NOT NULL,
    clarity INTEGER,
    unclear_words TEXT,
    words_per_minute INTEGER,
    correction_original TEXT,
    correction_improved TEXT,
    correction_explanation TEXT,
    practiced INTEGER NOT NULL DEFAULT 0,
    practiced_at TEXT,
    corrected_at TEXT,
    dismissed INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS messages_by_conversation ON messages (conversation_id, id);

-- The learner's progress on a sentence pattern; the built-in patterns themselves are in the code.
CREATE TABLE IF NOT EXISTS pattern_progress (
    target TEXT NOT NULL,
    pattern_id TEXT NOT NULL,
    sessions INTEGER NOT NULL DEFAULT 0,
    last_correct INTEGER,
    last_total INTEGER,
    practiced_at TEXT,
    PRIMARY KEY (target, pattern_id)
);

-- A YouTube video saved to study with. Only its subtitles are kept, as sentences with the
-- seconds between which each is said; the video is played by YouTube's own player. `language`
-- is the code of the subtitle track ("en-GB"). `level` is its CEFR level (A1-C2): estimated
-- when it is added, or set by the learner; empty while neither has happened.
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target TEXT NOT NULL,
    video_id TEXT NOT NULL,
    title TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT '',
    language TEXT NOT NULL,
    generated INTEGER NOT NULL DEFAULT 0,
    added_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    level TEXT,
    UNIQUE (target, video_id)
);

-- `shadowed` is how often a sentence was said after the video, `best` the best score (0-100).
CREATE TABLE IF NOT EXISTS video_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    start REAL NOT NULL,
    end REAL NOT NULL,
    text TEXT NOT NULL,
    shadowed INTEGER NOT NULL DEFAULT 0,
    best INTEGER
);
CREATE INDEX IF NOT EXISTS video_lines_by_video ON video_lines (video, position);

-- A sentence of a video in the learner's own language, written when the learner asks for the
-- translation; one for each language it was asked in.
CREATE TABLE IF NOT EXISTS line_translations (
    line INTEGER NOT NULL REFERENCES video_lines(id) ON DELETE CASCADE,
    language TEXT NOT NULL,
    text TEXT NOT NULL,
    PRIMARY KEY (line, language)
);

-- A word the learner tapped in a sentence, as the model explained it in their language (JSON);
-- one for each sentence, so the meaning is the one the word has there.
CREATE TABLE IF NOT EXISTS word_lookups (
    target TEXT NOT NULL,
    language TEXT NOT NULL,
    word TEXT NOT NULL,
    sentence TEXT NOT NULL,
    explained TEXT NOT NULL,
    PRIMARY KEY (target, language, word, sentence)
);

-- A sentence pattern the learner made from a sentence of a video. The sentence is kept as its
-- example, so the pattern outlives the video.
CREATE TABLE IF NOT EXISTS own_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target TEXT NOT NULL,
    pattern TEXT NOT NULL,
    use TEXT NOT NULL,
    example TEXT NOT NULL,
    line INTEGER REFERENCES video_lines(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (target, pattern)
);

-- A sentence got wrong in pattern practice, kept to be practised again next to the corrections
-- of conversations. One row for each sentence asked for; a new wrong try at it replaces what
-- was said.
CREATE TABLE IF NOT EXISTS pattern_mistakes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target TEXT NOT NULL,
    pattern_id TEXT NOT NULL,
    pattern TEXT NOT NULL,
    prompt TEXT NOT NULL,
    said TEXT NOT NULL,
    improved TEXT NOT NULL,
    explanation TEXT NOT NULL DEFAULT '',
    practiced INTEGER NOT NULL DEFAULT 0,
    practiced_at TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (target, pattern_id, prompt)
);

-- A sentence of a video not said right after it, kept to be practised again next to the
-- corrections. One row for each sentence; a new wrong try replaces what was said. It keeps the
-- sentence and the video's title, so it outlives the video, without a link to it.
CREATE TABLE IF NOT EXISTS shadowing_mistakes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target TEXT NOT NULL,
    line INTEGER UNIQUE REFERENCES video_lines(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    said TEXT NOT NULL,
    improved TEXT NOT NULL,
    explanation TEXT NOT NULL,
    practiced INTEGER NOT NULL DEFAULT 0,
    practiced_at TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Every try at saying a sentence after a video, right or not, to find the words the learner is
-- often not heard saying. It keeps the sentence, so it outlives the video.
CREATE TABLE IF NOT EXISTS shadowing_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target TEXT NOT NULL,
    line INTEGER REFERENCES video_lines(id) ON DELETE SET NULL,
    sentence TEXT NOT NULL,
    said TEXT NOT NULL,
    accuracy INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
"""


def init_db() -> None:
    global _chosen
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # The file may be another one than when the choice was last read (the tests' is).
    _chosen = False
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        # Every language has the built-in topics, each with its own opening lines. Only the
        # missing ones are inserted: an insert that is ignored still uses up an id. A title the
        # learner already used for a topic of their own is left to them.
        for language in LANGUAGES.values():
            known = {
                row["title"] for row in conn.execute("SELECT title FROM topics WHERE target = ?", (language.code,))
            }
            conn.executemany(
                "INSERT INTO topics (target, title, situation, opener, category) VALUES (?, ?, ?, ?, ?)",
                [
                    (language.code, title, situation, language.openers[title], category)
                    for title, situation, category in SEED_TOPICS
                    if title not in known
                ],
            )
