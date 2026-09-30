"""Unit tests for web duration formatting functions."""

from app.web.formatting import duration_class, format_duration


def test_format_duration_cases() -> None:
    assert format_duration(None) == "just now"
    assert format_duration(0) == "just now"
    assert format_duration(45) == "just now"
    assert format_duration(60) == "1m"
    assert format_duration(300) == "5m"
    assert format_duration(18720) == "5h 12m"  # 5h 12m
    assert format_duration(273600) == "3d 4h"  # 3d 4h


def test_duration_class_cases() -> None:
    assert duration_class(None) == "badge-sage"
    assert duration_class(0) == "badge-sage"
    assert duration_class(2 * 86400) == "badge-sage"
    assert duration_class(3 * 86400) == "badge-ochre"
    assert duration_class(5 * 86400) == "badge-ochre"
    assert duration_class(7 * 86400) == "badge-ochre"
    assert duration_class(7 * 86400 + 1) == "badge-terracotta"
    assert duration_class(10 * 86400) == "badge-terracotta"
