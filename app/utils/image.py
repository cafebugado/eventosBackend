import io

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_DIMENSION = 1600
WEBP_QUALITY = 80


def optimize_image(content: bytes) -> bytes | None:
    """Redimensiona e converte uma imagem para WebP.

    Retorna None quando o conteudo nao e uma imagem estatica suportada ou quando
    a conversao nao reduz o tamanho; nesses casos o arquivo original deve ser mantido.
    """
    try:
        with Image.open(io.BytesIO(content)) as original:
            if getattr(original, "is_animated", False):
                return None
            img = ImageOps.exif_transpose(original)
            if img.mode not in ("RGB", "RGBA"):
                has_alpha = img.mode in ("LA", "PA") or "transparency" in img.info
                img = img.convert("RGBA" if has_alpha else "RGB")
            img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            img.save(buffer, format="WEBP", quality=WEBP_QUALITY, method=6)
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError):
        return None

    optimized = buffer.getvalue()
    if len(optimized) >= len(content):
        return None
    return optimized
