from datetime import date

from app.utils.event_date import get_iso_week, get_iso_year, is_same_iso_week, parse_event_date


def test_parse_event_date_valid():
    assert parse_event_date("25/12/2026") == date(2026, 12, 25)


def test_parse_event_date_invalid_format():
    assert parse_event_date("2026-12-25") is None


def test_parse_event_date_empty():
    assert parse_event_date("") is None


def test_get_iso_week():
    assert get_iso_week(date(2026, 1, 1)) == 1


def test_get_iso_year():
    assert get_iso_year(date(2026, 1, 1)) == 2026


def test_is_same_iso_week_true():
    assert is_same_iso_week(date(2026, 6, 8), date(2026, 6, 12)) is True


def test_is_same_iso_week_false():
    assert is_same_iso_week(date(2026, 6, 8), date(2026, 6, 16)) is False
