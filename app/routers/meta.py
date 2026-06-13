from datetime import datetime
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.services.evento_service import EventoService

router = APIRouter(tags=["meta"])

_BASE_URL = "https://agendas-eventos.vercel.app"


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/og")
async def get_og_tags(path: str = Query(...), db: AsyncSession = Depends(get_db)) -> dict:
    """Gera metadados OG para uma rota /eventos/{slug}."""
    default = {
        "title": "Agenda de Eventos",
        "description": "Confira os proximos eventos de tecnologia.",
        "image": f"{_BASE_URL}/og-default.png",
        "url": f"{_BASE_URL}{path}",
    }

    prefix = "/eventos/"
    if not path.startswith(prefix):
        return default

    slug = path[len(prefix):].strip("/")
    if not slug:
        return default

    service = EventoService(db)
    try:
        evento = await service.get_event_by_slug_or_id(slug)
    except NotFoundError:
        return default

    return {
        "title": evento.nome,
        "description": evento.descricao or default["description"],
        "image": evento.imagem or default["image"],
        "url": f"{_BASE_URL}{path}",
    }


@router.get("/sitemap.xml")
async def get_sitemap(db: AsyncSession = Depends(get_db)) -> Response:
    service = EventoService(db)
    eventos = await service.get_published_events()

    static_paths = ["/", "/eventos", "/comunidades", "/contribuidores", "/galeria"]
    now = datetime.utcnow().strftime("%Y-%m-%d")

    urls = []
    for path in static_paths:
        urls.append(f"<url><loc>{escape(_BASE_URL + path)}</loc><lastmod>{now}</lastmod></url>")

    for evento in eventos:
        loc = f"{_BASE_URL}/eventos/{evento.slug}"
        lastmod = evento.updated_at.strftime("%Y-%m-%d")
        urls.append(f"<url><loc>{escape(loc)}</loc><lastmod>{lastmod}</lastmod></url>")

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(urls)
        + "</urlset>"
    )
    return Response(content=xml, media_type="application/xml")
