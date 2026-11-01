import json
from types import SimpleNamespace

import pytest

from feedback import (Classification, REVIEW_LABEL, classify_comment, load_feedback,
                      parse_classification, resolve_feedback, retry_feedback,
                      save_feedback, summarize)


def result(label="Speed", confidence=0.95, reason="Long wait for pickup."):
    return json.dumps(dict(label=label, confidence=confidence, reason=reason))


def fake_client(raw=None, error=None):
    def create(**kwargs):
        assert kwargs["response_format"] == {"type": "json_object"}
        assert kwargs["messages"][1]["content"]
        if error:
            raise error
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=raw))])
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def test_llm_classification_and_threshold():
    assert classify_comment("Too slow", client=fake_client(result())).label == "Speed"
    low = classify_comment("Maybe the line?", client=fake_client(result(confidence=0.6)))
    assert low.label == REVIEW_LABEL and "suggested Speed" in low.reason
    assert parse_classification(result(confidence=0.75)).label == "Speed"


@pytest.mark.parametrize("raw", ["not json", "[]", '{}', result(label="Unknown"),
    result(confidence=True), result(confidence=1.1), result(confidence=-0.1),
    result(confidence="0.9"), result(reason=""), result(confidence=float("nan")),
    json.dumps(dict(label=["Speed", "Value"], confidence=0.9, reason="two"))])
def test_bad_llm_outputs_enter_review(raw):
    assert classify_comment("A customer comment", client=fake_client(raw)).label == REVIEW_LABEL


def test_failure_and_missing_key_are_saved_for_review():
    assert classify_comment("slow", api_key="").source == "pending"
    failure = classify_comment("slow", client=fake_client(error=RuntimeError("secret-should-not-leak")))
    assert failure.label == REVIEW_LABEL and "secret" not in failure.reason


@pytest.mark.parametrize("status", [400, 401, 403, 404, 429])
def test_provider_status_is_reported_without_private_error_text(status):
    class ProviderError(Exception):
        status_code = status
    failure = classify_comment("slow", client=fake_client(error=ProviderError("secret-should-not-leak")))
    assert failure.label == REVIEW_LABEL
    assert f"HTTP {status}" in failure.reason
    assert "secret-should-not-leak" not in failure.reason


def test_validation_persistence_and_idempotency(tmp_path):
    db = tmp_path / "feedback.sqlite3"
    c = Classification("Speed", 0.9, "Slow pickup", "llm")
    with pytest.raises(ValueError):
        save_feedback(db, "empty", None, "  ", None)
    with pytest.raises(ValueError):
        save_feedback(db, "unlabeled", None, "Slow", None)
    with pytest.raises(ValueError):
        save_feedback(db, "bad-rating", 0, "", None)
    save_feedback(db, "a", None, "  Too slow  ", c)
    save_feedback(db, "a", None, "Too slow", c)
    save_feedback(db, "b", 5, "", None)
    rows = load_feedback(db)
    assert len(rows) == 2
    assert next(r for r in rows if r["id"] == "a")["comment"] == "Too slow"
    assert next(r for r in rows if r["id"] == "b")["label"] is None


def test_manual_review_resolution_and_retry(tmp_path):
    db = tmp_path / "feedback.sqlite3"
    pending = Classification(REVIEW_LABEL, None, "Needs review", "pending")
    save_feedback(db, "a", 2, "Unclear", pending)
    resolve_feedback(db, "a", "Service")
    row = load_feedback(db)[0]
    assert row["label"] == "Service" and row["source"] == "manual"
    assert row["original_label"] == REVIEW_LABEL and row["reviewed_at"]
    with pytest.raises(ValueError):
        retry_feedback(db, "a", Classification("Speed", 0.9, "Slow", "llm"))
    save_feedback(db, "b", None, "Slow pickup", pending)
    retry_feedback(db, "b", Classification("Speed", 0.9, "Slow", "llm"))
    assert summarize(load_feedback(db))["review_count"] == 0


def test_metric_denominators_exclusions_and_ties():
    rows = [dict(rating=5, label="No improvement requested"),
            dict(rating=1, label="Speed"), dict(rating=None, label="Value"),
            dict(rating=3, label=REVIEW_LABEL), dict(rating=5, label=None)]
    stats = summarize(rows)
    assert stats["submissions"] == 5 and stats["ratings"] == 4
    assert stats["average_rating"] == 3.5 and stats["review_count"] == 1
    assert stats["priorities"] == ["Speed", "Value"]
    assert summarize([])["average_rating"] is None
    assert summarize([])["priorities"] == []
