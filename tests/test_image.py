import io
import os

from PIL import Image

from app.utils.image import MAX_DIMENSION, optimize_image


def _png(width: int, height: int, mode: str = "RGB") -> bytes:
    # Ruido para que o PNG nao comprima bem e o WebP seja de fato menor.
    img = Image.frombytes(mode, (width, height), os.urandom(width * height * len(mode)))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def test_optimize_image_converte_para_webp_menor():
    original = _png(800, 600)

    optimized = optimize_image(original)

    assert optimized is not None
    assert len(optimized) < len(original)
    with Image.open(io.BytesIO(optimized)) as img:
        assert img.format == "WEBP"
        assert img.size == (800, 600)


def test_optimize_image_limita_dimensao_maxima():
    optimized = optimize_image(_png(3200, 1600))

    assert optimized is not None
    with Image.open(io.BytesIO(optimized)) as img:
        assert img.size == (MAX_DIMENSION, MAX_DIMENSION // 2)


def test_optimize_image_preserva_transparencia():
    optimized = optimize_image(_png(400, 400, mode="RGBA"))

    assert optimized is not None
    with Image.open(io.BytesIO(optimized)) as img:
        assert img.mode == "RGBA"


def test_optimize_image_ignora_conteudo_que_nao_e_imagem():
    assert optimize_image(b"isto nao e uma imagem") is None


def test_optimize_image_ignora_gif_animado():
    frames = [Image.new("RGB", (50, 50), color) for color in ("red", "blue")]
    buffer = io.BytesIO()
    frames[0].save(buffer, format="GIF", save_all=True, append_images=frames[1:])

    assert optimize_image(buffer.getvalue()) is None
