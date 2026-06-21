import time

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.schemas.contribuinte import GitHubUserInfo
from app.schemas.github import CommitInfo, ContributorInfo, PullRequestInfo, RepoStats

_GITHUB_API = "https://api.github.com"
_CACHE_TTL_SECONDS = 5 * 60

_cache: dict[str, tuple[float, object]] = {}


async def _get(client: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
    response = await client.get(url, **kwargs)  # type: ignore[arg-type]
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502, detail=f"Falha ao consultar a API do GitHub: {exc.response.status_code}"
        ) from exc
    return response


def _cache_get(key: str) -> object | None:
    entry = _cache.get(key)
    if entry is None:
        return None
    expires_at, value = entry
    if time.time() > expires_at:
        del _cache[key]
        return None
    return value


def _cache_set(key: str, value: object) -> None:
    _cache[key] = (time.time() + _CACHE_TTL_SECONDS, value)


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"
    return headers


async def get_repo_stats(repo: str) -> RepoStats:
    cache_key = f"repo_stats:{repo}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]

    async with httpx.AsyncClient() as client:
        response = await _get(client, f"{_GITHUB_API}/repos/{repo}", headers=_headers())
        data = response.json()

    stats = RepoStats(
        stars=data.get("stargazers_count", 0),
        forks=data.get("forks_count", 0),
        open_issues=data.get("open_issues_count", 0),
        watchers=data.get("subscribers_count", 0),
    )
    _cache_set(cache_key, stats)
    return stats


async def get_recent_commits(repo: str, n: int = 5) -> list[CommitInfo]:
    cache_key = f"commits:{repo}:{n}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]

    async with httpx.AsyncClient() as client:
        response = await _get(
            client, f"{_GITHUB_API}/repos/{repo}/commits", headers=_headers(), params={"per_page": n}
        )
        data = response.json()

    commits = [
        CommitInfo(
            sha=item["sha"],
            message=item["commit"]["message"].split("\n")[0],
            author=(item.get("author") or {}).get("login") or item["commit"]["author"].get("name"),
            author_avatar=(item.get("author") or {}).get("avatar_url"),
            url=item["html_url"],
            date=item["commit"]["author"].get("date"),
        )
        for item in data
    ]
    _cache_set(cache_key, commits)
    return commits


async def get_recent_prs(repo: str, n: int = 5) -> list[PullRequestInfo]:
    cache_key = f"prs:{repo}:{n}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]

    async with httpx.AsyncClient() as client:
        response = await _get(
            client,
            f"{_GITHUB_API}/repos/{repo}/pulls",
            headers=_headers(),
            params={"state": "all", "sort": "created", "direction": "desc", "per_page": n},
        )
        data = response.json()

    prs = [
        PullRequestInfo(
            number=item["number"],
            title=item["title"],
            author=(item.get("user") or {}).get("login"),
            author_avatar=(item.get("user") or {}).get("avatar_url"),
            url=item["html_url"],
            state=item["state"],
            created_at=item["created_at"],
        )
        for item in data
    ]
    _cache_set(cache_key, prs)
    return prs


async def get_top_contributors(repo: str, n: int = 5) -> list[ContributorInfo]:
    cache_key = f"contributors:{repo}:{n}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]

    async with httpx.AsyncClient() as client:
        response = await _get(
            client, f"{_GITHUB_API}/repos/{repo}/contributors", headers=_headers(), params={"per_page": n}
        )
        data = response.json()

    contributors = [
        ContributorInfo(
            login=item["login"],
            avatar_url=item["avatar_url"],
            contributions=item["contributions"],
            html_url=item["html_url"],
        )
        for item in data
    ]
    _cache_set(cache_key, contributors)
    return contributors


async def get_user_info(username: str) -> GitHubUserInfo:
    async with httpx.AsyncClient() as client:
        response = await _get(client, f"{_GITHUB_API}/users/{username}", headers=_headers())
        data = response.json()

    return GitHubUserInfo(
        github_username=data["login"],
        nome=data.get("name") or data["login"],
        avatar_url=data["avatar_url"],
        github_url=data["html_url"],
    )
