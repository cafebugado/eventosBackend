from app.core.config import settings
from app.integrations import github
from app.schemas.github import CommitInfo, ContributorInfo, PullRequestInfo, RepoStats


class GitHubService:
    @staticmethod
    async def get_repo_stats(repo: str | None = None) -> RepoStats:
        return await github.get_repo_stats(repo or settings.GITHUB_REPO)

    @staticmethod
    async def get_recent_commits(repo: str | None = None, n: int = 5) -> list[CommitInfo]:
        return await github.get_recent_commits(repo or settings.GITHUB_REPO, n)

    @staticmethod
    async def get_recent_prs(repo: str | None = None, n: int = 5) -> list[PullRequestInfo]:
        return await github.get_recent_prs(repo or settings.GITHUB_REPO, n)

    @staticmethod
    async def get_top_contributors(repo: str | None = None, n: int = 5) -> list[ContributorInfo]:
        return await github.get_top_contributors(repo or settings.GITHUB_REPO, n)
