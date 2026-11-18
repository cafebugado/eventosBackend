import re
from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings

_CACHE_CONTROL_SECONDS = "31536000"
_PUBLIC_URL_RE = re.compile(r"/storage/v1/object/public/[^/]+/(.+)$")


@lru_cache
def get_supabase_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
