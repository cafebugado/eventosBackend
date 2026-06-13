import re

# Espelha o mapeamento de acentos de src/utils/slug.js
_ACCENT_MAP = str.maketrans(
    {
        "á": "a", "à": "a", "â": "a", "ä": "a", "ã": "a", "å": "a",
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "í": "i", "ì": "i", "î": "i", "ï": "i",
        "ó": "o", "ò": "o", "ô": "o", "ö": "o", "õ": "o", "ø": "o",
        "ú": "u", "ù": "u", "û": "u", "ü": "u",
        "ý": "y", "ÿ": "y",
        "ç": "c", "ñ": "n",
    }
)

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_MULTI_DASH_RE = re.compile(r"-{2,}")

MAX_SLUG_LENGTH = 80


def generate_slug(nome: str) -> str:
    """Gera um slug a partir do nome, equivalente a src/utils/slug.js e fn_nome_to_slug() (SQL)."""
    if not nome:
        return ""

    slug = nome.lower().translate(_ACCENT_MAP)
    slug = _NON_ALNUM_RE.sub("-", slug)
    slug = _MULTI_DASH_RE.sub("-", slug)
    slug = slug.strip("-")
    slug = slug[:MAX_SLUG_LENGTH].rstrip("-")
    return slug


def resolve_unique_slug(base: str, used: set[str]) -> str:
    """Resolve um slug unico dado um conjunto de slugs ja em uso."""
    if base not in used:
        return base

    suffix = 2
    while f"{base}-{suffix}" in used:
        suffix += 1
    return f"{base}-{suffix}"
