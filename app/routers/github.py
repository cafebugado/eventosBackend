from fastapi import APIRouter, Query, Request

from app.core.limiter import limiter
from app.schemas.github import CommitInfo, ContributorInfo, PullRequestInfo, RepoStats
from app.services.github_service import GitHubService

router = APIRouter(prefix="/github", tags=["github"])


@router.get("/repo-stats", response_model=RepoStats)
@limiter.limit("30/minute")
async def get_repo_stats(request: Request, repo: str | None = Query(default=None)) -> RepoStats:
    return await GitHubService.get_repo_stats(repo)


@router.get("/commits", response_model=list[CommitInfo])
@limiter.limit("30/minute")
async def get_recent_commits(
    request: Request, repo: str | None = Query(default=None), n: int = Query(default=5)
) -> list[CommitInfo]:
    return await GitHubService.get_recent_commits(repo, n)


@router.get("/prs", response_model=list[PullRequestInfo])
@limiter.limit("30/minute")
async def get_recent_prs(
    request: Request, repo: str | None = Query(default=None), n: int = Query(default=5)
) -> list[PullRequestInfo]:
    return await GitHubService.get_recent_prs(repo, n)


@router.get("/contributors", response_model=list[ContributorInfo])
@limiter.limit("30/minute")
async def get_top_contributors(
    request: Request, repo: str | None = Query(default=None), n: int = Query(default=5)
) -> list[ContributorInfo]:
    return await GitHubService.get_top_contributors(repo, n)
