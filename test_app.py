from pathlib import Path

from streamlit.testing.v1 import AppTest

from feedback import Classification, REVIEW_LABEL, load_feedback, save_feedback

APP = str(Path(__file__).with_name("app.py"))


def start(monkeypatch, tmp_path):
    monkeypatch.setenv("FEEDBACK_DB_PATH", str(tmp_path / "feedback.sqlite3"))
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    return AppTest.from_file(APP).run(timeout=20)


def test_empty_form_rejected(monkeypatch, tmp_path):
    app = start(monkeypatch, tmp_path)
    assert not app.exception
    app.button[0].click().run()
    assert "Please add" in app.error[0].value
    assert not load_feedback(tmp_path / "feedback.sqlite3")


def test_comment_without_api_key_is_saved(monkeypatch, tmp_path):
    app = start(monkeypatch, tmp_path)
    app.text_area[0].set_value("I waited 20 minutes for my drink.")
    app.button[0].click().run()
    assert not app.exception and app.success
    row = load_feedback(tmp_path / "feedback.sqlite3")[0]
    assert row["label"] == REVIEW_LABEL and row["rating"] is None


def test_owner_live_example_and_about_pages(monkeypatch, tmp_path):
    app = start(monkeypatch, tmp_path)
    app.sidebar.radio[0].set_value("Owner dashboard").run()
    assert not app.exception
    assert [m.value for m in app.metric] == ["0", "—", "0"]
    app.radio[0].set_value("Example dataset").run()
    assert not app.exception
    assert app.metric[0].value == "18" and app.metric[2].value == "2"
    assert any("usual thing" in text.value for text in app.text)
    app.sidebar.radio[0].set_value("Question & labels").run()
    assert not app.exception and app.table


def test_owner_resolves_full_comment(monkeypatch, tmp_path):
    db = tmp_path / "feedback.sqlite3"
    long_comment = "The line is too long. " * 70
    save_feedback(db, "review-test", 2, long_comment,
                  Classification(REVIEW_LABEL, None, "Needs review", "pending"))
    app = start(monkeypatch, tmp_path)
    app.sidebar.radio[0].set_value("Owner dashboard").run()
    assert app.text[0].value == long_comment.strip()
    app.selectbox[0].set_value("Speed").run()
    next(b for b in app.button if b.label == "Save verified label").click().run()
    assert not app.exception
    assert app.metric[2].value == "0"
    assert load_feedback(db)[0]["label"] == "Speed"
