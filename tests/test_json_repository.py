"""Unit tests for JsonRepository resilience, atomic writes, and encoding."""

import logging
from pathlib import Path
from typing import Any, Dict
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
    """Verify exists returns True only when file is present on disk."""
    assert not repo.exists("test-exist")
    repo.save(SampleModel(topic_id="test-exist", title="Exist"))
    assert repo.exists("test-exist")


def test_exists_on_zero_byte_file_vs_get(
    repo: JsonRepository[SampleModel], repo_dir: Path
) -> None:
    """ERR-006 / UI-001: exists() reports True for 0-byte file, while get() returns None."""
    zero_file = repo_dir / "empty-file.json"
    zero_file.write_bytes(b"")

    assert repo.exists("empty-file") is True
    assert repo.get("empty-file") is None


def test_get_truncated_json_returns_none(
    repo: JsonRepository[SampleModel], repo_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """ERR-006 / RISK-002: Truncated JSON returns None with parse and error logs."""
    trunc_file = repo_dir / "truncated.json"
    trunc_file.write_text('{"topic_id": "truncated", "title": "Incom', encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        result = repo.get("truncated")

    assert result is None
    assert any("Failed to parse" in r.message for r in caplog.records)
    assert any("Failed to load" in r.message for r in caplog.records)


@pytest.mark.parametrize(
    "raw_json_bytes,description",
    [
        (b"[]", "empty JSON list"),
        (b'[{"topic_id": "list-item", "title": "Item"}]', "JSON list of objects"),
        (b"123456", "raw JSON integer"),
        (b"98.76", "raw JSON float"),
        (b'"just a raw string"', "raw JSON string"),
        (b"true", "raw JSON boolean"),
        (b"null", "raw JSON null"),
    ],
)
def test_get_non_object_json_returns_none(
    repo: JsonRepository[SampleModel],
    repo_dir: Path,
    raw_json_bytes: bytes,
    description: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """ERR-006 / UI-001: Non-dict JSON payloads return None and are skipped by list_all."""
    file_path = repo_dir / "non-object.json"
    file_path.write_bytes(raw_json_bytes)

    with caplog.at_level(logging.WARNING):
        result = repo.get("non-object")

    assert result is None
    assert any(
        ("is not an object" in r.message) or ("Failed to parse" in r.message)
        for r in caplog.records
    )

    # list_all also cleanly skips non-object files
    items = repo.list_all()
    assert items == []


@pytest.mark.parametrize(
    "invalid_data,description",
    [
        ({"topic_id": "missing-title"}, "missing required title field"),
        ({"topic_id": 1234, "title": ["not", "a", "string"]}, "incorrect field types"),
    ],
)
def test_get_pydantic_validation_error_returns_none(
    repo: JsonRepository[SampleModel],
    repo_dir: Path,
    invalid_data: dict,
    description: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """ERR-006: Pydantic ValidationError returns None and logs warning/error."""
    import json

    file_path = repo_dir / "invalid-schema.json"
    file_path.write_text(json.dumps(invalid_data), encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        result = repo.get("invalid-schema")

    assert result is None
    assert any("Failed to parse" in r.message for r in caplog.records)
    assert any("Failed to load" in r.message for r in caplog.records)


def test_utf8_multibyte_unicode_roundtrip(repo: JsonRepository[SampleModel]) -> None:
    """ERR-006: Verify full Unicode roundtrip (emojis, CJK, smart quotes, math symbols)."""
    rich_unicode_content = (
        "Emojis: 🚀 🤖 🧠 📈 | CJK: 自然语言处理 / 機械学習 | "
        "Quotes: “curly quotes” & ‘single quotes’ — em-dash | Math: ∑(x_i) ≥ ∫ f(x)dx"
    )
    entity = SampleModel(
        topic_id="unicode-test",
        title="Unicode Title: 🌐 世界",
        content=rich_unicode_content,
    )
    repo.save(entity)

    loaded = repo.get("unicode-test")
    assert loaded is not None
    assert loaded.title == "Unicode Title: 🌐 世界"
    assert loaded.content == rich_unicode_content


@pytest.mark.parametrize(
    "byte_sequence,expected_substring",
    [
        (b'{"topic_id": "c1", "title": "Test \x91single quoted\x92"}', "single quoted"),
        (b'{"topic_id": "c2", "title": "Test \x93double quoted\x94"}', "double quoted"),
        (b'{"topic_id": "c3", "title": "Range 10\x9620"}', "Range 10"),
        (b'{"topic_id": "c4", "title": "Clause\x97dash"}', "Clause"),
    ],
)
def test_cp1252_fallback_all_common_smart_punctuation(
    repo: JsonRepository[SampleModel],
    repo_dir: Path,
    byte_sequence: bytes,
    expected_substring: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """ERR-006 / ERR-011: Verify fallback for cp1252 smart quotes and dashes."""
    test_file = repo_dir / "cp1252_test.json"
    test_file.write_bytes(byte_sequence)

    with caplog.at_level(logging.WARNING):
        loaded = repo.get("cp1252_test")

    assert loaded is not None
    assert expected_substring in loaded.title
    assert any("UTF-8 decoding failed" in r.message for r in caplog.records)


def test_binary_garbage_unparseable_returns_none(
    repo: JsonRepository[SampleModel], repo_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """ERR-006: Random non-JSON binary bytes return None without uncaught exception."""
    garbage = repo_dir / "garbage.json"
    garbage.write_bytes(b"\x00\xff\xfe\x12\x34\x56\x78\x9a\xbc\xde")

    with caplog.at_level(logging.WARNING):
        loaded = repo.get("garbage")

    assert loaded is None
    assert any("Failed to load" in r.message for r in caplog.records)


def test_save_atomic_failure_cleans_up_tmp_file(
    repo: JsonRepository[SampleModel],
    repo_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ERR-018: Failure during atomic replace cleans up .tmp file and leaves original intact."""
    # Seed original valid file
    original = SampleModel(topic_id="atomic-target", title="Original Title")
    repo.save(original)

    # Simulate an error during os.replace
    def failing_replace(src: Any, dst: Any) -> None:
        raise OSError("Simulated disk replacement failure")

    monkeypatch.setattr("os.replace", failing_replace)

    update = SampleModel(topic_id="atomic-target", title="New Title")
    with pytest.raises(OSError, match="Simulated disk replacement failure"):
        repo.save(update)

    # Assert no stray .tmp files left in the directory
    tmp_files = list(repo_dir.glob(".*.tmp"))
    assert tmp_files == []

    # Original file is preserved unchanged
    loaded = repo.get("atomic-target")
    assert loaded is not None
    assert loaded.title == "Original Title"


def test_save_creates_nested_directory_if_missing(tmp_path: Path) -> None:
    """ERR-018: JsonRepository.save creates parent directories if not already created."""
    nested_dir = tmp_path / "deeply" / "nested" / "storage"
    assert not nested_dir.exists()

    nested_repo = JsonRepository(SampleModel, nested_dir, id_field="topic_id")
    entity = SampleModel(topic_id="nested-1", title="Nested Entity")
    saved_path = nested_repo.save(entity)

    assert saved_path.exists()
    assert nested_dir.exists()
    loaded = nested_repo.get("nested-1")
    assert loaded is not None
    assert loaded.title == "Nested Entity"


def test_list_all_nonexistent_directory_returns_empty(tmp_path: Path) -> None:
    """Verify list_all returns an empty list if directory does not exist on disk."""
    nonexistent_dir = tmp_path / "missing_dir"
    repo = JsonRepository(SampleModel, nonexistent_dir, id_field="topic_id")
    assert repo.list_all() == []


def test_load_file_nonexistent_returns_none(repo: JsonRepository[SampleModel], repo_dir: Path) -> None:
    """Verify _load_file directly returns None when target path does not exist."""
    assert repo._load_file(repo_dir / "ghost.json") is None


def test_cp1252_read_exception_handling(
    repo: JsonRepository[SampleModel],
    repo_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """ERR-006 / ERR-011: When cp1252 read itself fails, structured warning is logged."""
    from unittest.mock import MagicMock

    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = True
    mock_path.stat.return_value.st_size = 50

    call_count = 0

    def mock_read_text(encoding: str = "utf-8") -> str:
        nonlocal call_count
        call_count += 1
        if encoding == "utf-8":
            raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")
        raise RuntimeError("Simulated cp1252 reading crash")

    mock_path.read_text.side_effect = mock_read_text

    with caplog.at_level(logging.WARNING):
        result = repo._load_file(mock_path)

    assert result is None
    assert any("Failed to decode" in r.message for r in caplog.records)


def test_save_unlink_oserror_suppression(
    repo: JsonRepository[SampleModel],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ERR-018: When tmp_file.unlink() raises OSError during error cleanup, it is safely suppressed."""
    from unittest.mock import MagicMock

    entity = SampleModel(topic_id="unlink-err", title="Title")

    def failing_replace(src: Any, dst: Any) -> None:
        raise OSError("Replace failed")

    monkeypatch.setattr("os.replace", failing_replace)

    # Monkeypatch Path.unlink to raise OSError on cleanup
    orig_unlink = Path.unlink

    def failing_unlink(self: Path, *args: Any, **kwargs: Any) -> None:
        raise OSError("Permission denied on unlink")

    monkeypatch.setattr(Path, "unlink", failing_unlink)

    with pytest.raises(OSError, match="Replace failed"):
        repo.save(entity)



def test_filesystem_oserror_handling_in_load(
    repo: JsonRepository[SampleModel],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """ERR-006: Verify OSError during stat() or read_text() in _load_file is caught and logged."""
    from unittest.mock import MagicMock

    # 1. Simulate stat() OSError
    fake_stat_path = MagicMock(spec=Path)
    fake_stat_path.exists.return_value = True
    fake_stat_path.stat.side_effect = OSError("Simulated stat access failure")

    with caplog.at_level(logging.WARNING):
        result = repo._load_file(fake_stat_path)
    assert result is None
    assert any("Filesystem access error" in r.message for r in caplog.records)

    # 2. Simulate read_text() OSError
    caplog.clear()
    fake_read_path = MagicMock(spec=Path)
    fake_read_path.exists.return_value = True
    fake_read_path.stat.return_value.st_size = 120
    fake_read_path.read_text.side_effect = OSError("Simulated disk read error")

    with caplog.at_level(logging.WARNING):
        result = repo._load_file(fake_read_path)
    assert result is None
    assert any("Failed to read" in r.message for r in caplog.records)

