"""A few requests to a real LLM, to catch what mocks cannot: a prompt the model no longer
follows, a changed provider API, a retired model name.

Left out of a normal run. With a key in `.env`:

    uv run --env-file .env pytest -m live

Replies differ every time, so these tests check the shape of a reply, never its wording.
"""

import re

import pytest

pytestmark = pytest.mark.live

def reply_to(client, said: str) -> dict:
    conversation = client.post("/api/conversations", json={"topic_id": 1}).json()
    client.post(f"/api/conversations/{conversation['id']}/messages", json={"text": said})
    response = client.post(f"/api/conversations/{conversation['id']}/reply")
    # A reply that does not match the schema is reported as 502 by the endpoint.
    assert response.status_code == 200, response.text
    return response.json()


def test_reply_is_short_and_plain_enough_to_read_aloud(client):
    reply = reply_to(client, "it was busy but good I had many meeting")["reply"]
    assert 2 <= len(reply) <= 400
    assert "\n" not in reply and "*" not in reply


def test_a_mistake_is_corrected_and_explained_in_the_chosen_language(client):
    client.put("/api/settings", json={"feedback_language": "Korean"})
    correction = reply_to(client, "yesterday I go to the beach with my friend and we swimmed")["correction"]
    assert correction is not None
    assert correction["improved"].strip() and correction["improved"] != correction["original"]
    # The explanation is written in the chosen language; the better sentence stays in English.
    assert re.search("[가-힣]", correction["explanation"])
    assert not re.search("[가-힣]", correction["improved"])


def test_missing_punctuation_is_not_corrected(client):
    # Correct when spoken; only the transcript lacks the comma and the question mark.
    assert reply_to(client, "I'm good and you")["correction"] is None


def test_a_review_is_written_in_the_chosen_language_with_english_phrases(client):
    client.put("/api/settings", json={"feedback_language": "Korean"})
    conversation = client.post("/api/conversations", json={"topic_id": 1}).json()
    for said in ("it was busy but good I had many meeting", "yesterday I go to the beach with my friend"):
        client.post(f"/api/conversations/{conversation['id']}/messages", json={"text": said})
        assert client.post(f"/api/conversations/{conversation['id']}/reply").status_code == 200
    response = client.post(f"/api/conversations/{conversation['id']}/review")
    assert response.status_code == 200, response.text
    review = response.json()
    assert re.search("[가-힣]", review["summary"])
    # Both lines have a mistake, so there is something to work on.
    assert review["focus"] and all(re.search("[가-힣]", item) for item in review["focus"])
    assert all(phrase["expression"].strip() and not re.search("[가-힣]", phrase["expression"]) for phrase in review["phrases"])


def test_the_opening_line_of_an_own_topic_is_short_plain_english(client):
    # The learner may describe the situation in their own language.
    topic = {"title": "병원 예약", "situation": "병원 접수처에 전화해서 진료 예약을 잡는 상황. 상대는 접수 직원."}
    response = client.post("/api/topics", json=topic)
    assert response.status_code == 201, response.text
    opener = response.json()["opener"]
    assert 2 <= len(opener) <= 400
    assert "\n" not in opener and "*" not in opener
    assert not re.search("[가-힣]", opener)


def test_a_topic_made_from_an_article_in_another_language_is_in_english(client):
    article = (
        "서울시는 다음 달부터 한강 공원에서 전동 킥보드 운행을 전면 금지한다고 밝혔다. "
        "최근 2년간 공원 내 킥보드 사고가 세 배로 늘어난 데 따른 조치다. "
        "시민단체는 보행자 안전을 위해 필요한 결정이라고 환영했지만, 공유 킥보드 업체들은 "
        "이용자 불편과 매출 감소를 우려하며 전용 도로를 만들어 달라고 요구했다. "
        "서울시는 6개월간 시범 운영한 뒤 계속할지 결정할 계획이다."
    )
    response = client.post("/api/topics/from-text", json={"text": article})
    assert response.status_code == 201, response.text
    topic = response.json()
    for field in ("title", "situation", "background", "opener"):
        assert topic[field].strip() and not re.search("[가-힣]", topic[field]), field
    assert len(topic["title"]) <= 80
    assert "\n" not in topic["opener"] and "*" not in topic["opener"]
    assert topic["opener"].rstrip().endswith("?")


def test_pattern_sentences_are_in_the_learners_language_with_english_answers(client):
    client.put("/api/settings", json={"feedback_language": "Korean"})
    response = client.post("/api/patterns/should-have/exercises")
    assert response.status_code == 200, response.text
    exercises = response.json()
    assert re.search("[가-힣]", exercises["note"])
    assert len(exercises["items"]) == 5
    for item in exercises["items"]:
        assert re.search("[가-힣]", item["prompt"]), item
        assert not re.search("[가-힣]", item["answer"]), item
        assert "should" in item["answer"].lower() and "have" in item["answer"].lower().replace("'ve", " have"), item


def test_a_pattern_sentence_is_judged_by_its_meaning_and_grammar_not_by_the_model_answer(client):
    client.put("/api/settings", json={"feedback_language": "Korean"})
    shown = {"prompt": "더 일찍 떠났어야 했어.", "answer": "I should have left earlier."}

    def judge(said: str) -> dict:
        response = client.post("/api/patterns/should-have/check", json={**shown, "said": said})
        assert response.status_code == 200, response.text
        return response.json()

    wrong = judge("I should have leave more early")
    assert wrong["correct"] is False
    assert re.search("[가-힣]", wrong["explanation"]) and not re.search("[가-힣]", wrong["improved"])
    # Other words than the model answer's, but right.
    assert judge("I should have gone sooner")["correct"] is True


def test_a_marked_part_of_a_sentence_becomes_a_short_pattern(client, monkeypatch):
    from app import videos
    from app.videos import Snippet

    sentence = "This is the closest I've ever gotten to a college graduation."
    monkeypatch.setattr(videos, "_transcript", lambda video_id: ([Snippet(0.0, 5.0, sentence)], "en", False))
    monkeypatch.setattr(videos, "_about", lambda video_id: ("A speech", "A channel"))
    line = client.post("/api/videos", json={"url": "https://youtu.be/UF8uR6Z6KLc"}).json()["lines"][0]
    response = client.post("/api/patterns", json={"line": line["id"], "phrase": "the closest I've ever gotten to"})
    assert response.status_code == 201, response.text
    made = response.json()
    # Which words stay and which become a slot is the model's call; only the shape is checked.
    assert 2 <= len(made["pattern"].split()) <= 14
    # A formula, not the sentence again.
    assert "college graduation" not in made["pattern"].lower()
    assert made["use"].strip() and made["example"] == sentence


def test_searches_for_videos_like_a_saved_one_are_a_few_short_phrases(client, monkeypatch):
    from app import similar_videos, videos
    from app.videos import Snippet

    said = ["Stay hungry. Stay foolish.", "You can't connect the dots looking forward.", "Death is very likely the single best invention of life."]
    monkeypatch.setattr(videos, "_transcript", lambda video_id: ([Snippet(i * 4.0, 4.0, s) for i, s in enumerate(said)], "en", False))
    monkeypatch.setattr(videos, "_about", lambda video_id: ("Commencement address", "Stanford"))
    video = client.post("/api/videos", json={"url": "https://youtu.be/UF8uR6Z6KLc"}).json()
    searched = []
    monkeypatch.setattr(similar_videos, "_search", lambda query, count: searched.append(query) or [])
    response = client.post(f"/api/videos/{video['id']}/suggestions")
    assert response.status_code == 200, response.text
    assert 1 <= len(searched) <= 3
    assert all(1 <= len(query.split()) <= 10 for query in searched)


def test_the_sentences_of_a_video_are_translated_into_the_learners_language(client, monkeypatch):
    from app import videos
    from app.videos import Snippet

    client.put("/api/settings", json={"feedback_language": "Korean"})
    said = ["Good morning and welcome back.", "Today we learn how to say goodbye.", "See you soon!"]
    monkeypatch.setattr(videos, "_transcript", lambda video_id: ([Snippet(i * 4.0, 4.0, s) for i, s in enumerate(said)], "en", False))
    monkeypatch.setattr(videos, "_about", lambda video_id: ("Greetings", "A channel"))
    video = client.post("/api/videos", json={"url": "https://youtu.be/UF8uR6Z6KLc"}).json()
    response = client.post(f"/api/videos/{video['id']}/translations")
    assert response.status_code == 200, response.text
    lines = response.json()["lines"]
    assert [line["line"] for line in lines] == [line["id"] for line in video["lines"]]
    assert all(re.search("[가-힣]", line["text"]) for line in lines), lines


def test_automatic_subtitles_without_punctuation_are_cut_into_sentences(client, monkeypatch):
    from app import videos
    from app.videos import Snippet

    # As YouTube's automatic subtitles sometimes come: no punctuation, a recognition error ("there").
    said = [
        "richard feynman was a leading theoretical physicist who received a",
        "nobel prize for his work in quantum electrodynamics he was also",
        "a famous teacher and there lectures are still",
        "watched today let's take a look",
    ]
    monkeypatch.setattr(videos, "_transcript", lambda video_id: ([Snippet(i * 3.0, 3.0, s) for i, s in enumerate(said)], "en", True))
    monkeypatch.setattr(videos, "_about", lambda video_id: ("Feynman", "A channel"))
    response = client.post("/api/videos", json={"url": "https://youtu.be/aRlakaPVrEw"})
    assert response.status_code == 201, response.text
    lines = [line["text"] for line in response.json()["lines"]]
    # Cut at sentence ends, not at the subtitle lines, with every word said kept as it was.
    assert lines != said and any(re.search(r"[.!?]$", line) for line in lines), lines
    assert [w.strip(".,!?:;").lower() for line in lines for w in line.split()] == " ".join(said).lower().split()


# --- German: the same prompts with another language to practise ---------------------------------

GERMAN_WORD = re.compile(r"\b(ich|du|sie|der|die|das|und|ist|nicht|ein|eine|mit|was|wie|hast|haben|bin|war)\b", re.I)


def german_reply_to(client, said: str) -> dict:
    topic = client.get("/api/topics").json()[0]["id"]
    conversation = client.post("/api/conversations", json={"topic_id": topic}).json()
    client.post(f"/api/conversations/{conversation['id']}/messages", json={"text": said})
    response = client.post(f"/api/conversations/{conversation['id']}/reply")
    assert response.status_code == 200, response.text
    return {**response.json(), "conversation": conversation["id"]}


def test_the_partner_answers_in_german_and_explains_in_the_chosen_language(client, german):
    client.put("/api/settings", json={"feedback_language": "Korean"})
    reply = german_reply_to(client, "gestern ich gehe an den Strand mit mein Freund")
    assert GERMAN_WORD.search(reply["reply"]) and not re.search("[가-힣]", reply["reply"])
    correction = reply["correction"]
    assert correction is not None and correction["improved"] != correction["original"]
    # The explanation is in the learner's language, not in the language of the conversation.
    assert re.search("[가-힣]", correction["explanation"])
    assert GERMAN_WORD.search(correction["improved"]) and not re.search("[가-힣]", correction["improved"])


def test_a_review_of_a_german_conversation_is_written_in_the_chosen_language(client, german):
    client.put("/api/settings", json={"feedback_language": "Korean"})
    conversation = german_reply_to(client, "gestern ich gehe an den Strand mit mein Freund")["conversation"]
    response = client.post(f"/api/conversations/{conversation}/review")
    assert response.status_code == 200, response.text
    review = response.json()
    assert re.search("[가-힣]", review["summary"])
    assert all(re.search("[가-힣]", item) for item in review["focus"])
    assert all(phrase["expression"].strip() and not re.search("[가-힣]", phrase["expression"]) for phrase in review["phrases"])


def test_german_pattern_sentences_are_in_the_learners_language_with_german_answers(client, german):
    client.put("/api/settings", json={"feedback_language": "Korean"})
    response = client.post("/api/patterns/weil/exercises")
    assert response.status_code == 200, response.text
    exercises = response.json()
    assert re.search("[가-힣]", exercises["note"]) and len(exercises["items"]) == 5
    for item in exercises["items"]:
        assert re.search("[가-힣]", item["prompt"]), item
        assert "weil" in item["answer"].lower() and not re.search("[가-힣]", item["answer"]), item


def test_the_opening_line_of_an_own_german_topic_is_in_german(client, german):
    own = {"title": "Renting a car", "situation": "공항 렌터카 창구에서 예약한 차를 찾는다. 상대는 직원이다."}
    response = client.post("/api/topics", json=own)
    assert response.status_code == 201, response.text
    opener = response.json()["opener"]
    assert GERMAN_WORD.search(opener) and not re.search("[가-힣]", opener)


def test_a_tapped_word_is_explained_in_the_chosen_language(client):
    client.put("/api/settings", json={"feedback_language": "Korean"})
    response = client.post(
        "/api/lookup",
        json={"word": "cortex", "sentence": "It involves activation and all four lobes of the cortex."},
    )
    assert response.status_code == 200, response.text
    found = response.json()
    assert found["lemma"].strip() and not re.search("[가-힣]", found["lemma"])
    assert re.search("[가-힣]", found["meaning"]) and re.search("[가-힣]", found["translation"])
    # The words standing for it in the translation are found, to be shown in another color.
    assert found["in_translation"] and found["in_translation"] in found["translation"]


def test_a_word_of_a_verb_in_two_parts_names_the_whole_verb(client, german):
    response = client.post("/api/lookup", json={"word": "fängt", "sentence": "Der Film fängt um acht Uhr an."})
    assert response.status_code == 200, response.text
    assert "anfangen" in response.json()["phrase"]
