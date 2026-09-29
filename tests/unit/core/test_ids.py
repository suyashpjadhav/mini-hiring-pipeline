"""Unit tests for ULID generation and validation."""

from app.core.ids import is_valid_id, new_id


def test_new_id_format() -> None:
    """Test generated ULID is valid 26-character string."""
    uid = new_id()
    assert isinstance(uid, str)
    assert len(uid) == 26
    assert is_valid_id(uid) is True


def test_new_id_uniqueness() -> None:
    """Test generating 1,000 ULIDs produces 1,000 unique values."""
    ids = {new_id() for _ in range(1000)}
    assert len(ids) == 1000


def test_is_valid_id_rejects_bad_input() -> None:
    """Test validator rejects invalid ULID inputs."""
    assert is_valid_id("") is False
    assert is_valid_id("12345") is False
    assert is_valid_id("01ARZ3NDEKTSV4RRFFQ69G5FA") is False
    assert is_valid_id("01ARZ3NDEKTSV4RRFFQ69G5FA12") is False
    assert is_valid_id("01ARZ3NDEKTSV4RRFFQ69G5FAIL") is False
    assert is_valid_id("01ARZ3NDEKTSV4RRFFQ69G5FAOU") is False
