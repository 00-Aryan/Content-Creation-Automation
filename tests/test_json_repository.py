"""Unit tests for JsonRepository resilience, atomic writes, and encoding."""

import logging
from pathlib import Path
from pydantic import BaseModel
import pytest

from content_creation.platform.storage.json_repository import JsonRepository


class SampleModel(BaseModel):
    topic_id: str
    title: str
    content: str = ""


@pytest.fixture
def repo_dir(tmp_path: Path) -> Path:
    d = tmp_path / "entities"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def repo(repo_dir: Path) -> JsonRepository[SampleModel]:
    return JsonRepository(SampleModel, repo_dir, id_field="topic_id")


def test_save_atomic_and_get(repo: JsonRepository[SampleModel], repo_dir: Path) -> None:
    entity = SampleModel(topic_id="topic-1", title="Test Title", content="Hello UTF-8 — em dash")
    saved_path = repo.save(entity)
    assert saved_path.exists()
    assert saved_path.name == "topic-1.json"

    # Ensure no leftover temp files
    assert list(repo_dir.glob(".*.tmp")) == []

    loaded = repo.get("topic-1")
    assert loaded is not None
    assert loaded.topic_id == "topic-1"
    assert loaded.title == "Test Title"
    assert loaded.content == "Hello UTF-8 — em dash"


def test_get_nonexistent_returns_none(repo: JsonRepository[SampleModel]) -> None:
    assert repo.get("nonexistent") is None


def test_get_zero_byte_file_returns_none_and_warns(
    repo: JsonRepository[SampleModel], repo_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    zero_file = repo_dir / "zero.json"
    zero_file.write_bytes(b"")

    with caplog.at_level(logging.WARNING):
        result = repo.get("zero")

    assert result is None
    assert any("0-byte JSON file" in record.message for record in caplog.records)
    assert any("Failed to load" in record.message for record in caplog.records)


def test_get_corrupted_json_returns_none_and_warns(
    repo: JsonRepository[SampleModel], repo_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    corrupt_file = repo_dir / "corrupt.json"
    corrupt_file.write_text("{not valid json: true", encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        result = repo.get("corrupt")

    assert result is None
    assert any("Failed to parse" in record.message for record in caplog.records)
    assert any("Failed to load" in record.message for record in caplog.records)


def test_list_all_skips_zero_byte_and_corrupt(
    repo: JsonRepository[SampleModel], repo_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    # 1 valid file
    repo.save(SampleModel(topic_id="valid", title="Valid Entity"))

    # 1 zero-byte file
    (repo_dir / "zero.json").write_bytes(b"")

    # 1 corrupted file
    (repo_dir / "corrupted.json").write_text("not json at all", encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        items = repo.list_all()

    assert len(items) == 1
    assert items[0].topic_id == "valid"


def test_cp1252_fallback_decoding(
    repo: JsonRepository[SampleModel], repo_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    # 0x93 and 0x94 are smart quotes in cp1252 that are invalid UTF-8
    cp1252_bytes = b'{"topic_id": "legacy", "title": "Test \x93quoted\x94 title"}'
    (repo_dir / "legacy.json").write_bytes(cp1252_bytes)

    with caplog.at_level(logging.WARNING):
        loaded = repo.get("legacy")

    assert loaded is not None
    assert loaded.topic_id == "legacy"
    assert "quoted" in loaded.title
    assert any("UTF-8 decoding failed" in record.message for record in caplog.records)


def test_exists(repo: JsonRepository[SampleModel]) -> None:
    assert not repo.exists("test-exist")
    repo.save(SampleModel(topic_id="test-exist", title="Exist"))
    assert repo.exists("test-exist")
