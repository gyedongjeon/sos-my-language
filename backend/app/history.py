"""Conversations, saved line by line as they happen so they can be looked at again."""

import json
import sqlite3
from typing import Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from .conversation import Correction, Message, TutorReply, tutor_reply
from .db import current_language, get_connection
from .llm import LLMError
from .review import Review, write_review

router = APIRouter(prefix="/api")


class Delivery(BaseModel):
    """How a line was spoken, as measured by speech recognition."""

    clarity: int
    unclear_words: list[str] = []
    words_per_minute: int | None = None


class SavedMessage(BaseModel):
    role: Literal["tutor", "learner"]
    text: str
    # Learner lines only: the tutor's fix, and how the line was spoken.
    correction: Correction | None = None
    delivery: Delivery | None = None


class Conversation(BaseModel):
    id: int
    # The code of the language it is held in ("en", "de").
    language: str
    # None once the topic it was held on has been removed.
    topic_id: int | None
    title: str
    situation: str
    started_at: str
    messages: list[SavedMessage]
    # Written when the learner wraps the conversation up; None until then.
    review: Review | None = None
    # What the two know besides the situation, for a topic made from a text; None otherwise.
    background: str | None = None

    def setting(self) -> str:
        """The situation as the tutor is told it, with the background when there is one."""
        if not self.background:
            return self.situation
        return f"{self.situation}\n\nBackground that you and the learner have both read:\n{self.background}"


class ConversationSummary(BaseModel):
    id: int
    language: str
    topic_id: int | None
    title: str
    started_at: str
    # How many times the learner spoke, and how many of those lines were corrected.
    turns: int
    corrections: int


class StartRequest(BaseModel):
    topic_id: int


class SayRequest(BaseModel):
    text: str = Field(min_length=1)
    delivery: Delivery | None = None


def _message(row: sqlite3.Row) -> SavedMessage:
    correction = None
    if row["correction_improved"] is not None:
        correction = Correction(
            original=row["correction_original"],
            improved=row["correction_improved"],
            explanation=row["correction_explanation"],
        )
    delivery = None
    if row["clarity"] is not None:
        delivery = Delivery(
            clarity=row["clarity"],
            unclear_words=json.loads(row["unclear_words"] or "[]"),
            words_per_minute=row["words_per_minute"],
        )
    return SavedMessage(role=row["role"], text=row["text"], correction=correction, delivery=delivery)


def _load(conn: sqlite3.Connection, conversation_id: int) -> Conversation:
    found = conn.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
    if found is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    rows = conn.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY id", (conversation_id,)).fetchall()
    review = Review.model_validate_json(found["review"]) if found["review"] else None
    return Conversation(
        **{**dict(found), "language": found["target"], "review": review}, messages=[_message(row) for row in rows]
    )


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations() -> list[ConversationSummary]:
    """Conversations in the language being practised in which the learner said something,
    newest first."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.target AS language, c.topic_id, c.title, c.started_at,
                   COUNT(m.id) AS turns, COUNT(m.correction_improved) AS corrections
            FROM conversations c JOIN messages m ON m.conversation_id = c.id AND m.role = 'learner'
            WHERE c.target = ?
            GROUP BY c.id ORDER BY c.id DESC
            """,
            (current_language().code,),
        ).fetchall()
    return [ConversationSummary(**dict(row)) for row in rows]


@router.post("/conversations", response_model=Conversation, status_code=201)
def start_conversation(body: StartRequest) -> Conversation:
    """Start a conversation on a topic; the topic's opening line is its first message."""
    with get_connection() as conn:
        topic = conn.execute(
            "SELECT target, title, situation, opener, background FROM topics WHERE id = ?", (body.topic_id,)
        ).fetchone()
        if topic is None:
            raise HTTPException(status_code=404, detail="Topic not found")
        created = conn.execute(
            "INSERT INTO conversations (target, topic_id, title, situation, background) VALUES (?, ?, ?, ?, ?)",
            (topic["target"], body.topic_id, topic["title"], topic["situation"], topic["background"]),
        )
        conn.execute(
            "INSERT INTO messages (conversation_id, role, text) VALUES (?, 'tutor', ?)",
            (created.lastrowid, topic["opener"]),
        )
        return _load(conn, created.lastrowid)


@router.get("/conversations/{conversation_id}", response_model=Conversation)
def get_conversation(conversation_id: int) -> Conversation:
    with get_connection() as conn:
        return _load(conn, conversation_id)


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: int) -> Response:
    with get_connection() as conn:
        deleted = conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    if deleted.rowcount == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return Response(status_code=204)


@router.post("/conversations/{conversation_id}/messages", response_model=SavedMessage, status_code=201)
def say(conversation_id: int, body: SayRequest) -> SavedMessage:
    """Save what the learner just said. The tutor's answer is asked for separately, so a failed
    answer does not lose the line."""
    with get_connection() as conn:
        saved = _load(conn, conversation_id)
        if saved.messages[-1].role == "learner":
            raise HTTPException(status_code=409, detail="The tutor has not replied to the last message yet.")
        delivery = body.delivery
        conn.execute(
            "INSERT INTO messages (conversation_id, role, text, clarity, unclear_words, words_per_minute)"
            " VALUES (?, 'learner', ?, ?, ?, ?)",
            (
                conversation_id,
                body.text,
                delivery.clarity if delivery else None,
                json.dumps(delivery.unclear_words) if delivery else None,
                delivery.words_per_minute if delivery else None,
            ),
        )
        # A review covers the conversation as it was; it is asked for again after more is said.
        conn.execute("UPDATE conversations SET review = NULL WHERE id = ?", (conversation_id,))
    return SavedMessage(role="learner", text=body.text, delivery=delivery)


@router.post("/conversations/{conversation_id}/reply", response_model=TutorReply)
def reply(conversation_id: int) -> TutorReply:
    """The tutor's next line, with a correction for the learner's last message; both are saved."""
    with get_connection() as conn:
        saved = _load(conn, conversation_id)
        last = conn.execute(
            "SELECT id FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT 1", (conversation_id,)
        ).fetchone()
    if saved.messages[-1].role != "learner":
        raise HTTPException(status_code=409, detail="There is nothing new to reply to.")
    try:
        result = tutor_reply(saved.setting(), [Message(role=m.role, text=m.text) for m in saved.messages])
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    fix = result.correction
    with get_connection() as conn:
        if fix:
            conn.execute(
                "UPDATE messages SET correction_original = ?, correction_improved = ?, correction_explanation = ?,"
                " corrected_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
                (fix.original, fix.improved, fix.explanation, last["id"]),
            )
        conn.execute(
            "INSERT INTO messages (conversation_id, role, text) VALUES (?, 'tutor', ?)", (conversation_id, result.reply)
        )
    return result


@router.post("/conversations/{conversation_id}/review", response_model=Review)
def review(conversation_id: int) -> Review:
    """Wrap a conversation up: a review of how it went, saved with it."""
    with get_connection() as conn:
        saved = _load(conn, conversation_id)
    if all(m.role != "learner" for m in saved.messages):
        raise HTTPException(status_code=409, detail="Nothing was said in this conversation yet.")
    try:
        written = write_review(saved.setting(), [(m.role, m.text, m.correction) for m in saved.messages])
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    with get_connection() as conn:
        conn.execute(
            "UPDATE conversations SET review = ? WHERE id = ?", (written.model_dump_json(), conversation_id)
        )
    return written
