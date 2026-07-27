from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.app.infrastructure.models import Base
from src.scripts.verify_database import verify_database_schema


def test_verify_database_schema_reports_empty_valid_schema(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr("src.scripts.verify_database.get_engine", lambda: engine)
    monkeypatch.setattr(
        "src.scripts.verify_database.get_session_factory",
        lambda: factory,
    )

    assert verify_database_schema() == {
        "transcripts": 0,
        "transcript_revisions": 0,
        "orphan_revisions": 0,
    }
