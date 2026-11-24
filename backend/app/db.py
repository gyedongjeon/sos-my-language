"""SQLite access and seed data."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from .paths import DATA_DIR

DB_PATH = DATA_DIR / "app.db"

# The categories the built-in topics are shown under, in this order.
CATEGORIES = ["Everyday", "Work", "School", "Shopping", "Food", "Travel", "Services", "Home", "Opinions"]

# Built-in topics: (title, the situation the tutor plays out, the tutor's opening line, category).
# New topics go at the end: a topic's place here decides its id in a new database, and the ids of
# the first six are the ones databases of earlier versions already have.
SEED_TOPICS = [
    (
        "Small talk",
        "A relaxed chat between two acquaintances about everyday life.",
        "Hi! It's good to see you. How has your week been so far?",
        "Everyday",
    ),
    (
        "Introducing yourself",
        "Two people meet for the first time at a social event and get to know each other.",
        "Hi, I don't think we've met. I'm Alex. What's your name, and what do you do?",
        "Everyday",
    ),
    (
        "At a café",
        "The tutor is a barista taking the learner's order at a café.",
        "Good morning! Welcome in. What can I get started for you today?",
        "Food",
    ),
    (
        "Travel plans",
        "Two friends talk about a trip the learner is planning or has taken.",
        "I heard you've been thinking about a trip. Where would you like to go?",
        "Travel",
    ),
    (
        "Weekend and hobbies",
        "A friendly chat about what the learner does in their free time.",
        "So, what do you usually like to do on the weekend?",
        "Everyday",
    ),
    (
        "A meeting at work",
        "The tutor is a colleague catching up with the learner on a project before a meeting.",
        "Thanks for joining. Before we start, could you tell me what you've been working on this week?",
        "Work",
    ),
    # Everyday
    (
        "Talking about the weather",
        "Two neighbours run into each other outside and chat about the weather and their day.",
        "Morning! Can you believe this weather? How is it treating you today?",
        "Everyday",
    ),
    (
        "Making plans with a friend",
        "The tutor is a friend of the learner, and the two decide what to do together this weekend.",
        "Hey! Are you free this weekend? I was thinking we could do something together.",
        "Everyday",
    ),
    # Work
    (
        "Daily stand-up",
        "The tutor leads a team's short daily meeting, where each person says what they did, "
        "what they will do next, and what is in their way.",
        "Good morning, everyone. Let's start with you. What did you get done yesterday?",
        "Work",
    ),
    (
        "Asking a colleague for help",
        "The tutor is a colleague at the next desk; the learner is stuck on a task and needs their help.",
        "Hey, you look a bit stuck over there. Is everything okay?",
        "Work",
    ),
    (
        "A status update for your manager",
        "The tutor is the learner's manager in a one-on-one meeting about how a project is going.",
        "Thanks for making time. So, how is the project going? Are we still on schedule?",
        "Work",
    ),
    (
        "A call with a client",
        "The tutor is a client on a phone call with the learner about what they need and by when.",
        "Hi, thanks for calling. I wanted to go over what we need from your team. Is now a good time?",
        "Work",
    ),
    # School
    (
        "Asking a professor a question",
        "The tutor is a professor in their office hours; the learner is a student with a question "
        "about the course.",
        "Come in, have a seat. What can I help you with today?",
        "School",
    ),
    (
        "A group project",
        "The tutor is a classmate; the two plan a group project and decide who does what.",
        "Okay, the project is due in two weeks. How do you think we should split up the work?",
        "School",
    ),
    (
        "Introducing yourself in class",
        "The tutor is a teacher on the first day of a class, getting to know a new student.",
        "Welcome to the class! Could you tell us a little about yourself?",
        "School",
    ),
    (
        "Chatting with a classmate",
        "The tutor is a classmate chatting with the learner after class about the lecture and "
        "their plans.",
        "That lecture was a lot to take in! What did you think of it?",
        "School",
    ),
    # Shopping
    (
        "At a market",
        "The tutor sells fruit and vegetables at an outdoor market; the learner wants to buy "
        "some and asks about prices.",
        "Hello there! Everything is fresh this morning. What are you looking for?",
        "Shopping",
    ),
    (
        "Buying clothes",
        "The tutor is a shop assistant in a clothing store, helping the learner find the right "
        "item and size.",
        "Hi, welcome in! Are you looking for anything in particular today?",
        "Shopping",
    ),
    (
        "Returning an item",
        "The tutor works at a store's customer service desk; the learner wants to return or "
        "exchange something they bought.",
        "Hi, how can I help you today?",
        "Shopping",
    ),
    (
        "At the supermarket checkout",
        "The tutor is a cashier at a supermarket, ringing up the learner's groceries.",
        "Hi there! Did you find everything you were looking for today?",
        "Shopping",
    ),
    # Food
    (
        "Ordering at a restaurant",
        "The tutor is a server at a restaurant, taking the learner's order for a meal.",
        "Good evening, and welcome. Can I get you something to drink while you look at the menu?",
        "Food",
    ),
    (
        "Booking a table by phone",
        "The tutor answers the phone at a restaurant; the learner calls to book a table.",
        "Thank you for calling. How can I help you?",
        "Food",
    ),
    (
        "A problem with your order",
        "The tutor is a server at a restaurant; something is wrong with what the learner was "
        "served, and the learner says so politely.",
        "Hi, how is everything tasting so far?",
        "Food",
    ),
    # Travel
    (
        "Airport check-in",
        "The tutor works at an airline's check-in desk; the learner is checking in for a flight "
        "with a bag.",
        "Good morning! Where are you flying to today? May I see your passport, please?",
        "Travel",
    ),
    (
        "Hotel check-in",
        "The tutor is a hotel receptionist; the learner arrives with a reservation and has a few "
        "questions about the stay.",
        "Good afternoon, and welcome! Do you have a reservation with us?",
        "Travel",
    ),
    (
        "Asking for directions",
        "The learner is a visitor who is lost in a city; the tutor is a local on the street who "
        "knows the way.",
        "Hi there! You look a little lost. Can I help you find something?",
        "Travel",
    ),
    (
        "At immigration",
        "The tutor is an immigration officer at an airport, asking the learner about their visit.",
        "Next, please. Good afternoon. What is the purpose of your visit?",
        "Travel",
    ),
    # Services
    (
        "At the doctor's",
        "The tutor is a doctor; the learner is a patient who is not feeling well and describes "
        "their symptoms.",
        "Hello, please have a seat. So, what brings you in today?",
        "Services",
    ),
    (
        "At a pharmacy",
        "The tutor is a pharmacist; the learner needs something for a minor health problem and "
        "asks how to take it.",
        "Hi there. What can I help you with today?",
        "Services",
    ),
    (
        "At the bank",
        "The tutor works at a bank; the learner wants to open an account or has a question about "
        "theirs.",
        "Good morning! What can I do for you today?",
        "Services",
    ),
    (
        "Calling customer service",
        "The tutor is a customer service agent on the phone; the learner calls about a problem "
        "with a product or a bill.",
        "Thank you for calling customer service. How can I help you today?",
        "Services",
    ),
    # Home
    (
        "Talking to your landlord",
        "The tutor is the learner's landlord; the learner tells them about something in the "
        "apartment that needs fixing.",
        "Hi, good to hear from you. Is everything all right with the apartment?",
        "Home",
    ),
    (
        "Meeting a new neighbour",
        "The learner has just moved in; the tutor is a neighbour who lives next door and says hello.",
        "Hi! You must be the new neighbour. I live next door. How is the move going?",
        "Home",
    ),
    (
        "Calling a repair service",
        "The tutor answers the phone at a repair company; the learner calls because something at "
        "home is broken and books a visit.",
        "Hello, thanks for calling. What seems to be the problem?",
        "Home",
    ),
    (
        "Viewing an apartment",
        "The tutor is an agent showing the learner an apartment for rent; the learner asks about "
        "the place, the rent, and the area.",
        "Hi, thanks for coming! Come on in. This is the living room. What do you think so far?",
        "Home",
    ),
    # Opinions: no role to play; the learner talks at more length about what they think.
    (
        "A movie or show you watched",
        "A friendly chat in which the learner describes a movie or show they watched and says "
        "what they thought of it. The tutor asks for details and reasons.",
        "I'm looking for something good to watch. What's the last movie or show you saw?",
        "Opinions",
    ),
    (
        "Your hometown",
        "A friendly chat in which the learner describes the place they come from and what they "
        "like and dislike about it. The tutor asks for details and reasons.",
        "I'd love to hear about where you're from. What is your hometown like?",
        "Opinions",
    ),
    (
        "Working from home or at the office",
        "A friendly discussion of whether it is better to work from home or at the office. The "
        "tutor asks for the learner's opinion and reasons, and sometimes gently takes the other side.",
        "Some people love working from home, and others can't stand it. What about you?",
        "Opinions",
    ),
    (
        "Something you read recently",
        "A friendly chat in which the learner sums up a book or an article they read and says "
        "what they thought of it. The tutor asks for details and reasons.",
        "Have you read anything interesting lately? What was it about?",
        "Opinions",
    ),
    (
        "Your plans for next year",
        "A friendly chat about what the learner wants to do or change next year and why. The "
        "tutor asks for details and reasons.",
        "The year is going by so fast! Is there anything you'd like to do or change next year?",
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


def _add_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    """Add a column to a table made by an earlier version of the app, unless it is there."""
    if column not in [found["name"] for found in conn.execute(f"PRAGMA table_info({table})")]:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                situation TEXT NOT NULL,
                opener TEXT NOT NULL
            )
            """
        )
        # 1 for a topic the learner added; the built-in ones cannot be removed.
        _add_column(conn, "topics", "custom", "INTEGER NOT NULL DEFAULT 0")
        # The category a built-in topic is shown under; empty for the learner's own topics.
        _add_column(conn, "topics", "category", "TEXT")
        # Adds the built-in topics a database of an earlier version does not have yet. A title the
        # learner already used for a topic of their own is left to them.
        # What the tutor knows besides the situation: the summary of the text a topic was made from.
        _add_column(conn, "topics", "background", "TEXT")
        # Only the missing ones are inserted: an insert that is ignored still uses up an id.
        known = {row["title"] for row in conn.execute("SELECT title FROM topics")}
        conn.executemany(
            "INSERT INTO topics (title, situation, opener, category) VALUES (?, ?, ?, ?)",
            [topic for topic in SEED_TOPICS if topic[0] not in known],
        )
        conn.executemany(
            "UPDATE topics SET category = ? WHERE title = ? AND custom = 0",
            [(category, title) for title, _, _, category in SEED_TOPICS],
        )
        conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        # A conversation keeps its topic's title and situation, so it stays readable (and the
        # tutor can still reply in it) after the topic is changed or removed.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER REFERENCES topics(id) ON DELETE SET NULL,
                title TEXT NOT NULL,
                situation TEXT NOT NULL,
                started_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                review TEXT,
                background TEXT
            )
            """
        )
        # `review` (JSON, written when a conversation is wrapped up) was added after the first
        # conversations were saved.
        _add_column(conn, "conversations", "review", "TEXT")
        # A copy of the topic's background, kept like its title and situation.
        _add_column(conn, "conversations", "background", "TEXT")
        # One line of a conversation, in the order they were said. The delivery columns and the
        # correction columns are filled for the learner's lines only.
        conn.execute(
            """
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
            )
            """
        )
        # How often a correction's better sentence was said correctly afterwards, and when last;
        # added after the first conversations were saved.
        _add_column(conn, "messages", "practiced", "INTEGER NOT NULL DEFAULT 0")
        _add_column(conn, "messages", "practiced_at", "TEXT")
        # The learner's progress on a sentence pattern; the patterns themselves are in the code.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pattern_progress (
                pattern_id TEXT PRIMARY KEY,
                sessions INTEGER NOT NULL DEFAULT 0,
                last_correct INTEGER,
                last_total INTEGER,
                practiced_at TEXT
            )
            """
        )
        # A YouTube video saved to study with. Only its subtitles are kept, as sentences with
        # the seconds between which each is said; the video is played by YouTube's own player.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                channel TEXT NOT NULL DEFAULT '',
                language TEXT NOT NULL,
                generated INTEGER NOT NULL DEFAULT 0,
                added_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            )
            """
        )
        # The CEFR level (A1-C2) of a video's English: estimated when it is added, or set by
        # the learner; empty while neither has happened.
        _add_column(conn, "videos", "level", "TEXT")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS video_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
                position INTEGER NOT NULL,
                start REAL NOT NULL,
                end REAL NOT NULL,
                text TEXT NOT NULL,
                shadowed INTEGER NOT NULL DEFAULT 0,
                best INTEGER
            )
            """
        )
        # How often a sentence was shadowed and the best score (0-100) so far; added after the
        # first videos were saved.
        _add_column(conn, "video_lines", "shadowed", "INTEGER NOT NULL DEFAULT 0")
        _add_column(conn, "video_lines", "best", "INTEGER")
        conn.execute("CREATE INDEX IF NOT EXISTS video_lines_by_video ON video_lines (video, position)")
        # A sentence of a video in the learner's language, written when the learner asks for the
        # translation; one for each language it was asked in.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS line_translations (
                line INTEGER NOT NULL REFERENCES video_lines(id) ON DELETE CASCADE,
                language TEXT NOT NULL,
                text TEXT NOT NULL,
                PRIMARY KEY (line, language)
            )
            """
        )
        # A sentence pattern the learner made from a sentence of a video. The sentence is kept
        # as its example, so the pattern outlives the video.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS own_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT NOT NULL UNIQUE,
                use TEXT NOT NULL,
                example TEXT NOT NULL,
                line INTEGER REFERENCES video_lines(id) ON DELETE SET NULL,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            )
            """
        )
        # A sentence got wrong in pattern practice, kept to be practised again next to the
        # corrections of conversations. One row for each sentence asked for; a new wrong try
        # at it replaces what was said.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pattern_mistakes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id TEXT NOT NULL,
                pattern TEXT NOT NULL,
                prompt TEXT NOT NULL,
                said TEXT NOT NULL,
                improved TEXT NOT NULL,
                explanation TEXT NOT NULL DEFAULT '',
                practiced INTEGER NOT NULL DEFAULT 0,
                practiced_at TEXT,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                UNIQUE (pattern_id, prompt)
            )
            """
        )
        # A sentence of a video not said right after it, kept to be practised again next to the
        # corrections. One row for each sentence; a new wrong try replaces what was said. It keeps
        # the sentence and the video's title, so it outlives the video, without a link to it.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS shadowing_mistakes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                line INTEGER UNIQUE REFERENCES video_lines(id) ON DELETE SET NULL,
                title TEXT NOT NULL,
                said TEXT NOT NULL,
                improved TEXT NOT NULL,
                explanation TEXT NOT NULL,
                practiced INTEGER NOT NULL DEFAULT 0,
                practiced_at TEXT,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            )
            """
        )
        # Every try at saying a sentence after a video, right or not, to find the words the
        # learner is often not heard saying. It keeps the sentence, so it outlives the video.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS shadowing_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                line INTEGER REFERENCES video_lines(id) ON DELETE SET NULL,
                sentence TEXT NOT NULL,
                said TEXT NOT NULL,
                accuracy INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            )
            """
        )
        # When a line's correction was made, to order it among the pattern mistakes, and whether
        # the learner took it off the list of corrections (it stays in its conversation).
        _add_column(conn, "messages", "corrected_at", "TEXT")
        _add_column(conn, "messages", "dismissed", "INTEGER NOT NULL DEFAULT 0")
        conn.execute("CREATE INDEX IF NOT EXISTS messages_by_conversation ON messages (conversation_id, id)")
