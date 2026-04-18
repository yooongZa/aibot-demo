import importlib
from pathlib import Path

import pytest


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    import db as db_module
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "test.sqlite")
    importlib.reload(db_module)  # re-bind DB_PATH inside the module
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "test.sqlite")
    db_module.init_db()
    yield db_module


def test_log_session_and_turn(fresh_db):
    db = fresh_db
    db.log_session_start("s1", {"age_band": "40대"})
    db.log_turn(
        session_id="s1",
        turn_index=1,
        stage="PRIMARY",
        user_text="피로해요",
        assistant_text="에너지 부스트업을 추천드립니다.",
        detected_needs=["피로 개선"],
        recommended_products=["뉴트리시파이 에너지 부스트업"],
    )
    summary = db.session_summary("s1")
    assert summary["turns"] == 1
    assert summary["last_stage"] == "PRIMARY"


def test_log_feedback_aggregates(fresh_db):
    db = fresh_db
    db.log_session_start("s2", None)
    db.log_feedback("s2", "PRIMARY-2", "up", ["A"])
    db.log_feedback("s2", "SECONDARY-4", "down", ["B"])
    db.log_feedback("s2", "SECONDARY-4", "down", ["B"])
    summary = db.session_summary("s2")
    assert summary["feedback"] == {"up": 1, "down": 2}


def test_logging_is_idempotent_for_same_session(fresh_db):
    db = fresh_db
    db.log_session_start("s3", {"a": 1})
    db.log_session_start("s3", {"a": 2})  # REPLACE
    summary = db.session_summary("s3")
    assert summary["turns"] == 0
