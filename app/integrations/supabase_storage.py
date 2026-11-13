import asyncio
import re
import time
import uuid

from app.core.config import settings
from app.integrations.supabase_client import get_supabase_client
from app.utils.image import optimize_image

_CACHE_CONTROL_SECONDS = "31536000"
_PUBLIC_URL_RE = re.compile(r"/storage/v1/object/public/[^/]+/(.+)$")


def _build_path(prefix: str, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    unique = f"{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"
    return f"{prefix}/{unique}.{ext}"


def _upload_file_sync(prefix: str, filename: str, content: bytes, content_type: str | None = None) -> str:
    optimized = optimize_image(content)
    if optimized is not None:
        content, filename, content_type = optimized, "imagem.webp", "image/webp"

    client = get_supabase_client()
    path = _build_path(prefix, filename)
    bucket = client.storage.from_(settings.SUPABASE_STORAGE_BUCKET)
    # O path e unico por upload, entao o arquivo nunca muda e pode ser cacheado por 1 ano.
    file_options = {"cache-control": _CACHE_CONTROL_SECONDS}
    if content_type:
        file_options["content-type"] = content_type
    bucket.upload(path, content, file_options=file_options)  # type: ignore[arg-type]
    return bucket.get_public_url(path)


async def upload_file(prefix: str, filename: str, content: bytes, content_type: str | None = None) -> str:
    """Faz upload de um arquivo para o bucket configurado e retorna a URL publica."""
    return await asyncio.to_thread(_upload_file_sync, prefix, filename, content, content_type)


def _remove_file_sync(path: str) -> None:
    client = get_supabase_client()
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
