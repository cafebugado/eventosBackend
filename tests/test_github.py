import httpx
import pytest

from app.integrations import github

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def clear_github_cache():
    github._cache.clear()
    yield
    github._cache.clear()


def mock_github_response(
    monkeypatch: pytest.MonkeyPatch,
    payload: object,
    status_code: int = 200,
):
    calls = []
    original_async_client = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(
            (
                str(request.url),
                {"headers": request.headers},
            )
        )
        return httpx.Response(
            status_code,
            json=payload,
            request=request,
        )

    transport = httpx.MockTransport(handler)

    monkeypatch.setattr(
        github.httpx,
        "AsyncClient",
        lambda: original_async_client(transport=transport),
    )

    return calls


async def test_get_repo_stats(monkeypatch: pytest.MonkeyPatch):
    calls = mock_github_response(
        monkeypatch,
        {
            "stargazers_count": 100,
            "forks_count": 20,
            "open_issues_count": 5,
            "subscribers_count": 15,
        },
    )

    result = await github.get_repo_stats("ingrid/projeto")

    assert result.stars == 100
    assert result.forks == 20
    assert result.open_issues == 5
    assert result.watchers == 15
    assert calls[0][0].endswith("/repos/ingrid/projeto")


async def test_get_repo_stats_uses_cache(monkeypatch: pytest.MonkeyPatch):
    calls = mock_github_response(
        monkeypatch,
        {"stargazers_count": 10, "forks_count": 2},
    )

    first = await github.get_repo_stats("ingrid/cache")
    second = await github.get_repo_stats("ingrid/cache")

    assert first == second
    assert len(calls) == 1


async def test_get_repo_stats_uses_default_values(
    monkeypatch: pytest.MonkeyPatch,
):
    mock_github_response(monkeypatch, {})

    result = await github.get_repo_stats("ingrid/vazio")

    assert result.stars == 0
    assert result.forks == 0
    assert result.open_issues == 0
    assert result.watchers == 0


async def test_get_recent_commits(monkeypatch: pytest.MonkeyPatch):
    mock_github_response(
        monkeypatch,
        [
            {
                "sha": "abc123",
                "commit": {
                    "message": "Novo recurso\nDescrição adicional",
                    "author": {
                        "name": "Ingrid",
                        "date": "2026-01-01T10:00:00Z",
                    },
                },
                "author": {
                    "login": "ingrid",
                    "avatar_url": "https://example.com/avatar.png",
                },
                "html_url": "https://github.com/ingrid/projeto/commit/abc123",
            }
        ],
    )

    result = await github.get_recent_commits("ingrid/projeto", 3)

    assert len(result) == 1
    assert result[0].sha == "abc123"
    assert result[0].message == "Novo recurso"
    assert result[0].author == "ingrid"
    assert result[0].author_avatar == "https://example.com/avatar.png"


async def test_get_recent_commits_uses_author_name_fallback(
    monkeypatch: pytest.MonkeyPatch,
):
    mock_github_response(
        monkeypatch,
        [
            {
                "sha": "abc123",
                "commit": {
                    "message": "Commit local",
                    "author": {"name": "Autor Local"},
                },
                "html_url": "https://example.com/commit",
            }
        ],
    )

    result = await github.get_recent_commits("ingrid/projeto")

    assert result[0].author == "Autor Local"
    assert result[0].author_avatar is None


async def test_get_recent_prs(monkeypatch: pytest.MonkeyPatch):
    mock_github_response(
        monkeypatch,
        [
            {
                "number": 10,
                "title": "Correção de testes",
                "user": {
                    "login": "ingrid",
                    "avatar_url": "https://example.com/avatar.png",
                },
                "html_url": "https://example.com/pull/10",
                "state": "closed",
                "created_at": "2026-01-01T10:00:00Z",
            }
        ],
    )

    result = await github.get_recent_prs("ingrid/projeto")

    assert len(result) == 1
    assert result[0].number == 10
    assert result[0].title == "Correção de testes"
    assert result[0].author == "ingrid"
    assert result[0].state == "closed"


async def test_get_top_contributors(monkeypatch: pytest.MonkeyPatch):
    mock_github_response(
        monkeypatch,
        [
            {
                "login": "ingrid",
                "avatar_url": "https://example.com/avatar.png",
                "contributions": 25,
                "html_url": "https://github.com/ingrid",
            }
        ],
    )

    result = await github.get_top_contributors("ingrid/projeto", 3)

    assert len(result) == 1
    assert result[0].login == "ingrid"
    assert result[0].contributions == 25


async def test_get_user_info(monkeypatch: pytest.MonkeyPatch):
    mock_github_response(
        monkeypatch,
        {
            "login": "octocat",
            "name": "The Octocat",
            "avatar_url": "https://example.com/avatar.png",
            "html_url": "https://github.com/octocat",
        },
    )

    result = await github.get_user_info("octocat")

    assert result.github_username == "octocat"
    assert result.nome == "The Octocat"
    assert result.avatar_url == "https://example.com/avatar.png"
    assert result.github_url == "https://github.com/octocat"


async def test_get_user_info_uses_login_when_name_is_missing(
    monkeypatch: pytest.MonkeyPatch,
):
    mock_github_response(
        monkeypatch,
        {
            "login": "octocat",
            "name": None,
            "avatar_url": "https://example.com/avatar.png",
            "html_url": "https://github.com/octocat"
        },
    ),

    result = await github.get_user_info("octocat")

    assert result.nome == "octocat"


async def test_github_http_error(monkeypatch: pytest.MonkeyPatch):
    mock_github_response(monkeypatch, {"message": "Not Found"}, 404)

    with pytest.raises(github.HTTPException) as exc_info:
        await github.get_repo_stats("ingrid/inexistente")

    assert exc_info.value.status_code == 502


async def test_github_token_is_sent(monkeypatch: pytest.MonkeyPatch):
    calls = mock_github_response(monkeypatch, {})

    monkeypatch.setattr(github.settings, "GITHUB_TOKEN", "token-teste")

    await github.get_repo_stats("ingrid/projeto")

    headers = calls[0][1]["headers"]
    assert headers["Authorization"] == "Bearer token-teste"
    assert headers["Accept"] == "application/vnd.github+json"


async def test_cache_expiration(monkeypatch: pytest.MonkeyPatch):
    current_time = 1000.0

    monkeypatch.setattr(github.time, "time", lambda: current_time)

    github._cache_set("teste", "valor")

    assert github._cache_get("teste") == "valor"

    current_time += github._CACHE_TTL_SECONDS + 1

    assert github._cache_get("teste") is None
    assert "teste" not in github._cache
