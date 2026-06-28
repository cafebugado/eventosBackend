import asyncio
import re
import time
import uuid
from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings

_PUBLIC_URL_RE = re.compile(r"/storage/v1/object/public/[^/]+/(.+)$")


@lru_cache
def get_storage_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def _build_path(prefix: str, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    unique = f"{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"
    return f"{prefix}/{unique}.{ext}"


def _upload_file_sync(prefix: str, filename: str, content: bytes, content_type: str | None = None) -> str:
    client = get_storage_client()
    path = _build_path(prefix, filename)
    bucket = client.storage.from_(settings.SUPABASE_STORAGE_BUCKET)
    file_options = {"content-type": content_type} if content_type else None
    bucket.upload(path, content, file_options=file_options)  # type: ignore[arg-type]
    return bucket.get_public_url(path)


async def upload_file(prefix: str, filename: str, content: bytes, content_type: str | None = None) -> str:
    """Faz upload de um arquivo para o bucket configurado e retorna a URL publica."""
    return await asyncio.to_thread(_upload_file_sync, prefix, filename, content, content_type)


def _remove_file_sync(path: str) -> None:
    client = get_storage_client()
    client.storage.from_(settings.SUPABASE_STORAGE_BUCKET).remove([path])


async def remove_file(path: str) -> None:
    await asyncio.to_thread(_remove_file_sync, path)


def extract_storage_path(public_url: str) -> str | None:
    """Extrai o path do arquivo a partir de uma URL publica do Supabase Storage."""
    match = _PUBLIC_URL_RE.search(public_url)
    if not match:
        return None
    return match.group(1)


async def remove_by_public_url(public_url: str) -> bool:
    path = extract_storage_path(public_url)
    if path is None:
        return False
    await remove_file(path)
    return True
