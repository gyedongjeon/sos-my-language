"""Words the learner saves from a sentence, kept with what they mean there."""

from tests.test_word_lookup import CORTEX, SENTENCE, model  # noqa: F401


def save(client, word="cortex", sentence=SENTENCE):
    return client.post("/api/words", json={"word": word, "sentence": sentence})


def test_a_saved_word_is_listed_with_its_meaning_and_sentence(client, model):
    response = save(client)
    assert response.status_code == 201, response.text
    saved = response.json()
    assert saved["headword"] == "cortex"
    assert saved["forms"] == CORTEX["forms"]
    assert saved["meaning"] == CORTEX["meaning"]
    assert saved["pronunciation"] == CORTEX["pronunciation"]
    assert saved["sentence"] == SENTENCE
    assert client.get("/api/words").json() == [saved]


def test_a_word_saved_again_from_its_sentence_is_kept_once(client, model):
    first = save(client).json()
    assert save(client).json()["id"] == first["id"]
    assert len(client.get("/api/words").json()) == 1


def test_a_word_from_another_sentence_is_saved_apart_with_the_meaning_it_has_there(client, model):
    save(client)
    model.reply = {**CORTEX, "meaning": "나무껍질"}
    save(client, "cortex", "The cortex of the tree is thick.")
    words = client.get("/api/words").json()
    assert [w["meaning"] for w in words] == ["나무껍질", CORTEX["meaning"]]


def test_a_word_in_a_phrase_is_saved_as_the_phrase(client, model, german):
    model.reply = {**CORTEX, "lemma": "fangen", "phrase": "anfangen"}
    saved = save(client, "fängt", "Der Film fängt um acht an.").json()
    assert saved["headword"] == "anfangen"
    assert saved["word"] == "fängt"


def test_the_words_of_another_language_being_learned_are_not_listed(client, model, german):
    save(client)
    client.put("/api/language", json={"language": "en"})
    assert client.get("/api/words").json() == []


def test_a_saved_word_can_be_removed(client, model):
    saved = save(client).json()
    assert client.delete(f"/api/words/{saved['id']}").status_code == 204
    assert client.get("/api/words").json() == []
    assert client.delete(f"/api/words/{saved['id']}").status_code == 404


def test_a_lookup_says_whether_its_word_is_saved_from_that_sentence(client, model):
    assert client.post("/api/lookup", json={"word": "cortex", "sentence": SENTENCE}).json()["saved"] is None
    saved = save(client).json()
    assert client.post("/api/lookup", json={"word": "cortex", "sentence": SENTENCE}).json()["saved"] == saved["id"]
    other = "The cortex of the tree is thick."
    assert client.post("/api/lookup", json={"word": "cortex", "sentence": other}).json()["saved"] is None


def test_a_word_that_cannot_be_explained_is_not_saved(client, model, monkeypatch):
    from app import word_lookup
    from app.llm import LLMError

    def fail(system, user, **params):
        raise LLMError("The model is busy.")

    monkeypatch.setattr(word_lookup, "complete", fail)
    assert save(client).status_code == 502
    assert client.get("/api/words").json() == []
