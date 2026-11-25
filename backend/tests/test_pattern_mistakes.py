"""A sentence got wrong in pattern practice is kept with the corrections, to be practised again."""

import json

import pytest

from app import conversation, patterns

WRONG = {"correct": False, "improved": "I should have left earlier.", "explanation": "have 뒤에는 과거분사를 씁니다."}
ATTEMPT = {"prompt": "더 일찍 떠났어야 했어.", "answer": "I should have left earlier.", "said": "I should have leave earlier."}


@pytest.fixture
def judge(monkeypatch):
    """The model judges every sentence with `judge.verdict`."""

    def complete(system, user, **params):
        return json.dumps(complete.verdict)

    complete.verdict = dict(WRONG)
    monkeypatch.setattr(patterns, "complete", complete)
    return complete


def check(client, **changes) -> dict:
    response = client.post("/api/patterns/should-have/check", json={**ATTEMPT, **changes})
    assert response.status_code == 200, response.text
    return response.json()


def test_a_sentence_got_wrong_is_listed_with_the_corrections(client, judge):
    check(client)
    listed = client.get("/api/corrections").json()
    assert len(listed) == 1
    mistake = listed[0]
    assert (mistake["original"], mistake["improved"], mistake["explanation"]) == (
        "I should have leave earlier.",
        "I should have left earlier.",
        WRONG["explanation"],
    )
    # It names the pattern it comes from, and shows the sentence that was asked for.
    assert mistake["pattern_id"] == "should-have" and mistake["conversation_id"] is None
    # Like a correction of a conversation, it is a better way of saying something.
    assert mistake["kind"] == "expression"
    assert mistake["title"] == "should have + past participle"
    assert mistake["prompt"] == ATTEMPT["prompt"]
    assert mistake["practiced"] == 0 and mistake["practiced_at"] is None


def test_a_sentence_got_right_is_not_listed(client, judge):
    judge.verdict = {"correct": True, "improved": "I should have gone sooner.", "explanation": None}
    check(client, said="I should have gone sooner.")
    # Nor is the model answer said as it is, which needs no model.
    check(client, said="I should have left earlier")
    assert client.get("/api/corrections").json() == []


def test_trying_the_same_sentence_again_keeps_one_entry_with_the_last_try(client, judge):
    check(client)
    judge.verdict = {**WRONG, "explanation": "과거분사 left를 씁니다."}
    check(client, said="I should left earlier.")
    listed = client.get("/api/corrections").json()
    assert len(listed) == 1
    assert listed[0]["original"] == "I should left earlier." and listed[0]["explanation"] == "과거분사 left를 씁니다."
    # Another sentence of the same pattern is another entry.
    check(client, prompt="그에게 말했어야 했어.", answer="I should have told him.", said="I should have tell him.")
    assert len(client.get("/api/corrections").json()) == 2


def test_getting_it_right_later_in_the_round_keeps_the_entry(client, judge):
    """Right at the second try is still a sentence worth practising again."""
    check(client)
    check(client, said="I should have left earlier.")
    assert len(client.get("/api/corrections").json()) == 1


def test_a_mistake_is_practised_by_saying_the_better_sentence(client, judge):
    check(client)
    mistake = client.get("/api/corrections").json()[0]
    missed = client.post(f"/api/corrections/{mistake['id']}/attempts", json={"text": "I should have leave earlier"})
    assert missed.json() == {"matched": False, "missing": ["left"], "practiced": 0}
    said = client.post(f"/api/corrections/{mistake['id']}/attempts", json={"text": "I should've left earlier."})
    assert said.json() == {"matched": True, "missing": [], "practiced": 1}
    kept = client.get("/api/corrections").json()[0]
    assert kept["practiced"] == 1 and kept["practiced_at"].endswith("Z")


def test_mistakes_and_conversation_corrections_are_listed_together_newest_first(client, judge, monkeypatch):
    fix = {"original": "I go", "improved": "I went", "explanation": "Past tense."}
    monkeypatch.setattr(
        conversation, "complete", lambda system, user, **params: json.dumps({"reply": "I see!", "correction": fix})
    )
    started = client.post("/api/conversations", json={"topic_id": 1}).json()
    client.post(f"/api/conversations/{started['id']}/messages", json={"text": "I go to the beach."})
    client.post(f"/api/conversations/{started['id']}/reply")
    check(client)
    listed = client.get("/api/corrections").json()
    assert [(c["conversation_id"], c["pattern_id"]) for c in listed] == [(None, "should-have"), (started["id"], None)]
    assert len({c["id"] for c in listed}) == 2
    # Each is practised under its own id.
    for correction in listed:
        attempt = client.post(f"/api/corrections/{correction['id']}/attempts", json={"text": correction["improved"]})
        assert attempt.json()["matched"] is True


def test_a_correction_can_be_removed_from_the_list(client, judge):
    check(client)
    mistake = client.get("/api/corrections").json()[0]
    assert client.delete(f"/api/corrections/{mistake['id']}").status_code == 204
    assert client.get("/api/corrections").json() == []
    assert client.delete(f"/api/corrections/{mistake['id']}").status_code == 404
    assert client.delete("/api/corrections/nonsense").status_code == 404
