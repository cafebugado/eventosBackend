from datetime import date, datetime


def parse_event_date(data_evento: str) -> date | None:
    """Converte uma data no formato DD/MM/YYYY (str) para date. Retorna None se invalido."""
    if not data_evento:
        return None
    try:
        return datetime.strptime(data_evento.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def get_iso_week(d: date) -> int:
    return d.isocalendar()[1]


def get_iso_year(d: date) -> int:
    return d.isocalendar()[0]


def is_same_iso_week(a: date, b: date) -> bool:
    iso_a = a.isocalendar()
    iso_b = b.isocalendar()
    return iso_a[0] == iso_b[0] and iso_a[1] == iso_b[1]
