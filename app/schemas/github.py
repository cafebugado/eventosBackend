from pydantic import BaseModel


class RepoStats(BaseModel):
    stars: int
    forks: int
    open_issues: int
    watchers: int


class CommitInfo(BaseModel):
    sha: str
    message: str
    author: str | None = None
    author_avatar: str | None = None
    url: str
    date: str | None = None


class PullRequestInfo(BaseModel):
    number: int
    title: str
    author: str | None = None
    author_avatar: str | None = None
    url: str
    state: str
    created_at: str


class ContributorInfo(BaseModel):
    login: str
    avatar_url: str
    contributions: int
    html_url: str
