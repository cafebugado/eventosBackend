from app.utils.slug import generate_slug, resolve_unique_slug


def test_generate_slug_basic():
    assert generate_slug("Meetup de Python") == "meetup-de-python"


def test_generate_slug_accents():
    assert generate_slug("Conferência São Paulo") == "conferencia-sao-paulo"


def test_generate_slug_special_chars():
    assert generate_slug("Evento #1 - Lançamento!") == "evento-1-lancamento"


def test_generate_slug_multiple_separators_collapse():
    assert generate_slug("A   B---C") == "a-b-c"


def test_generate_slug_strips_leading_trailing_dashes():
    assert generate_slug("---Hello World---") == "hello-world"


def test_generate_slug_empty():
    assert generate_slug("") == ""


def test_generate_slug_truncates_to_max_length():
    nome = "a" * 100
    slug = generate_slug(nome)
    assert len(slug) <= 80


def test_resolve_unique_slug_no_conflict():
    assert resolve_unique_slug("evento-x", set()) == "evento-x"


def test_resolve_unique_slug_with_conflict():
    used = {"evento-x"}
    assert resolve_unique_slug("evento-x", used) == "evento-x-2"


def test_resolve_unique_slug_with_multiple_conflicts():
    used = {"evento-x", "evento-x-2", "evento-x-3"}
    assert resolve_unique_slug("evento-x", used) == "evento-x-4"
