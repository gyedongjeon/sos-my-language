"""A topic can be made from a text the learner pastes in, such as a news article."""

import json

import pytest

from app import conversation, review, topics
from app.db import SEED_TOPICS
from app.llm import LLMError

ARTICLE = (
    "The city council voted on Tuesday to close the main street to cars on weekends. "
    "Shop owners are divided: some expect more visitors on foot, others fear losing customers "
    "who drive in from the suburbs. The trial starts next month and runs until the end of the year."
)
WRITTEN = {
    "title": "A car-free main street",
    "situation": "A friendly discussion of a news article that both have read.",
    "background": "The city council will close the main street to cars on weekends. Shop owners are divided.",
    "opener": "Did you read about the car-free weekends? What do you think of the idea?",
}


@pytest.fixture
def writer(monkeypatch):
    """The model turns a text into the topic `writer.topic`."""

    def complete(system, user, **params):
        complete.system, complete.user = system, user
        return json.dumps(complete.topic)

    complete.topic = dict(WRITTEN)
    monkeypatch.setattr(topics, "complete", complete)
    return complete


def make(client, text=ARTICLE) -> dict:
    response = client.post("/api/topics/from-text", json={"text": text})
    assert response.status_code == 201, response.text
    return response.json()


def test_a_topic_is_made_from_a_text_and_saved_as_the_learners_own(client, writer):
    made = make(client)
    assert made == {"id": made["id"], **WRITTEN, "custom": True, "category": None}
    assert client.get("/api/topics").json()[-1] == made
    # The model got the text itself.
    assert ARTICLE in writer.user


def test_built_in_and_described_topics_have_no_background(client):
    listed = client.get("/api/topics").json()
    assert all(topic["background"] is None for topic in listed)
    own = {"title": "Renting a car", "situation": "At the rental desk.", "opener": "Hello!"}
    assert client.post("/api/topics", json=own).json()["background"] is None


def test_a_second_topic_with_the_same_title_gets_a_number(client, writer):
    make(client)
    assert make(client)["title"] == "A car-free main street (2)"
    assert make(client)["title"] == "A car-free main street (3)"
    writer.topic["title"] = SEED_TOPICS[0][0]
    assert make(client)["title"] == f"{SEED_TOPICS[0][0]} (2)"


def test_the_text_must_be_long_enough_to_talk_about(client, writer):
    assert client.post("/api/topics/from-text", json={"text": "Too short."}).status_code == 422
    assert client.post("/api/topics/from-text", json={"text": "   " * 100}).status_code == 422
    assert client.post("/api/topics/from-text", json={"text": "x" * 30001}).status_code == 422


def test_nothing_is_added_when_the_topic_cannot_be_written(client, monkeypatch):
    def fail(system, user, **params):
        raise LLMError("The LLM provider is not responding.")

    monkeypatch.setattr(topics, "complete", fail)
    response = client.post("/api/topics/from-text", json={"text": ARTICLE})
    assert response.status_code == 502
    assert "not responding" in response.json()["detail"]
    assert len(client.get("/api/topics").json()) == len(SEED_TOPICS)


def test_the_tutor_knows_the_background_during_the_conversation_and_in_the_review(client, writer, monkeypatch):
    made = make(client)
    seen = {}

    def reply(system, user, **params):
        seen["reply"] = system
        return json.dumps({"reply": "Interesting! Why do you think so?"})

    def write(system, user, **params):
        seen["review"] = system
        return json.dumps({"summary": "You explained your view."})

    monkeypatch.setattr(conversation, "complete", reply)
    monkeypatch.setattr(review, "complete", write)
    started = client.post("/api/conversations", json={"topic_id": made["id"]}).json()
    assert started["background"] == WRITTEN["background"]
    client.post(f"/api/conversations/{started['id']}/messages", json={"text": "I think it is good idea."})
    assert client.post(f"/api/conversations/{started['id']}/reply").status_code == 200
    assert client.post(f"/api/conversations/{started['id']}/review").status_code == 200
    for system in seen.values():
        assert WRITTEN["situation"] in system and WRITTEN["background"] in system


def test_a_conversation_keeps_its_background_after_the_topic_is_deleted(client, writer):
    made = make(client)
    started = client.post("/api/conversations", json={"topic_id": made["id"]}).json()
    client.delete(f"/api/topics/{made['id']}")
    assert client.get(f"/api/conversations/{started['id']}").json()["background"] == WRITTEN["background"]


def test_a_conversation_on_a_built_in_topic_has_no_background(client, monkeypatch):
    seen = {}

    def reply(system, user, **params):
        seen["system"] = system
        return json.dumps({"reply": "Nice!"})

    monkeypatch.setattr(conversation, "complete", reply)
    started = client.post("/api/conversations", json={"topic_id": 1}).json()
    assert started["background"] is None
    client.post(f"/api/conversations/{started['id']}/messages", json={"text": "It was good."})
    client.post(f"/api/conversations/{started['id']}/reply")
    assert "Background" not in seen["system"]


PAGE = "<html><head><title>Council closes main street</title></head><body><article><p>%s</p></article></body></html>"


@pytest.fixture
def web(monkeypatch):
    """The web serves `web.pages[url]`; any other address cannot be reached."""

    def fetch_url(url, **kwargs):
        fetch_url.asked.append(url)
        return fetch_url.pages.get(url)

    fetch_url.pages, fetch_url.asked = {"https://news.example/street": PAGE % ARTICLE}, []
    monkeypatch.setattr(topics.trafilatura, "fetch_url", fetch_url)
    return fetch_url


def test_a_topic_is_made_from_the_text_of_a_linked_page(client, writer, web):
    response = client.post("/api/topics/from-text", json={"url": " https://news.example/street "})
    assert response.status_code == 201, response.text
    assert response.json()["title"] == WRITTEN["title"]
    assert web.asked == ["https://news.example/street"]
    # The model got the page's readable text, not its markup.
    assert ARTICLE in writer.user and "<article>" not in writer.user


def test_a_link_that_cannot_be_read_is_reported_and_the_model_is_not_asked(client, web, monkeypatch):
    monkeypatch.setattr(topics, "complete", lambda *args, **kwargs: pytest.fail("The model was asked."))
    web.pages["https://video.example/watch"] = "<html><body><div id='player'></div></body></html>"
    for url in ("https://video.example/watch", "https://gone.example/"):
        response = client.post("/api/topics/from-text", json={"url": url})
        assert response.status_code == 422
        assert "Paste the text instead" in response.json()["detail"]


def test_only_web_links_are_followed(client, writer, web):
    for url in ("file:///etc/hosts", "ftp://news.example/street", "news.example/street"):
        assert client.post("/api/topics/from-text", json={"url": url}).status_code == 422
    assert web.asked == []


def test_a_very_long_page_is_cut_to_what_the_model_is_given(client, writer, web):
    web.pages["https://news.example/long"] = PAGE % ("A sentence about the street. " * 3000)
    assert client.post("/api/topics/from-text", json={"url": "https://news.example/long"}).status_code == 201
    assert len(writer.user) < topics.MAX_SOURCE + 100


def test_a_text_or_a_link_is_needed_but_not_both(client, writer, web):
    assert client.post("/api/topics/from-text", json={}).status_code == 422
    both = {"text": ARTICLE, "url": "https://news.example/street"}
    assert client.post("/api/topics/from-text", json=both).status_code == 422


def test_a_link_to_a_video_is_refused_because_only_the_page_around_it_can_be_read(client, web, monkeypatch):
    monkeypatch.setattr(topics, "complete", lambda *args, **kwargs: pytest.fail("The model was asked."))
    for url in ("https://www.youtube.com/watch?v=abc", "https://youtu.be/abc", "https://m.youtube.com/watch?v=abc"):
        response = client.post("/api/topics/from-text", json={"url": url})
        assert response.status_code == 422
        assert "video" in response.json()["detail"] and "transcript" in response.json()["detail"]
    assert web.asked == []
