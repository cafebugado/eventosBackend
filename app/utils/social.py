import re

_GITHUB_URL_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/([A-Za-z0-9_-]+)/?.*")
_LINKEDIN_URL_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/([A-Za-z0-9_-]+)/?.*")


def normalize_github(value: str) -> str:
    """Extrai username de uma URL do GitHub ou retorna o valor como username direto."""
    value = value.strip()
    match = _GITHUB_URL_RE.match(value)
    if match:
        return match.group(1)
    # Remove @ caso o usuario tenha passado @username
    return value.lstrip("@")


def normalize_linkedin(value: str) -> str:
    """Extrai username de uma URL do LinkedIn ou retorna o valor como username direto."""
    value = value.strip()
    match = _LINKEDIN_URL_RE.match(value)
    if match:
        return match.group(1)
    return value.lstrip("@")
