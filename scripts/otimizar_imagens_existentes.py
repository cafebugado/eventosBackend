"""Recomprime para WebP as imagens ja enviadas ao Supabase Storage e atualiza as URLs no banco.

Uso (a partir da raiz do projeto):
    python -m scripts.otimizar_imagens_existentes            # so lista o que seria feito
    python -m scripts.otimizar_imagens_existentes --apply    # executa

Para cada imagem referenciada em eventos.imagem ou galeria_fotos.url: baixa, otimiza,
envia com um novo path e atualiza o banco. O arquivo antigo e mantido, para que URLs
em cache continuem funcionando, a menos que --remover-originais seja passado.
"""

import argparse
import asyncio

import asyncpg

from app.core.config import settings
from app.integrations.supabase_storage import (
    _CACHE_CONTROL_SECONDS,
    _build_path,
    extract_storage_path,
    get_supabase_client,
)
from app.utils.image import optimize_image

_STORAGE_MARKER = "%/storage/v1/object/public/%"


async def main(apply: bool, remover_originais: bool) -> None:
    dsn = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn, statement_cache_size=0, timeout=20)
    bucket = get_supabase_client().storage.from_(settings.SUPABASE_STORAGE_BUCKET)
    antes = depois = 0
    try:
        rows = await conn.fetch(
            """
            SELECT 'eventos' AS tabela, id, imagem AS url FROM eventos WHERE imagem LIKE $1
            UNION ALL
            SELECT 'galeria_fotos', id, url FROM galeria_fotos WHERE url LIKE $1
            """,
            _STORAGE_MARKER,
        )
        print(f"{len(rows)} imagens referenciadas no banco")

        for row in rows:
            path = extract_storage_path(row["url"])
            if path is None or path.endswith(".webp"):
                continue
            if not apply:
                print(f"[dry-run] {row['tabela']} {row['id']}: {path}")
                continue

            original = await asyncio.to_thread(bucket.download, path)
            optimized = optimize_image(original)
            if optimized is None:
                print(f"mantida (sem ganho): {path}")
                continue

            new_path = _build_path(path.rsplit("/", 1)[0], "imagem.webp")
            await asyncio.to_thread(
                bucket.upload,
                new_path,
                optimized,
                {"content-type": "image/webp", "cache-control": _CACHE_CONTROL_SECONDS},
            )
            new_url = bucket.get_public_url(new_path)
            if row["tabela"] == "eventos":
                await conn.execute("UPDATE eventos SET imagem = $1 WHERE id = $2", new_url, row["id"])
            else:
                await conn.execute(
                    "UPDATE galeria_fotos SET url = $1, storage_path = $2 WHERE id = $3",
                    new_url,
                    new_path,
                    row["id"],
                )
            if remover_originais:
                await asyncio.to_thread(bucket.remove, [path])

            antes += len(original)
            depois += len(optimized)
            print(f"{path}: {len(original) // 1024} kB -> {len(optimized) // 1024} kB")
    finally:
        await conn.close()

    if apply:
        print(f"\nTotal: {antes // 1024} kB -> {depois // 1024} kB")
    else:
        print("\nNada foi alterado. Rode com --apply para executar.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="executa as alteracoes")
    parser.add_argument(
        "--remover-originais",
        action="store_true",
        help="apaga o arquivo antigo apos a troca (URLs antigas em cache deixam de funcionar)",
    )
    args = parser.parse_args()
    asyncio.run(main(args.apply, args.remover_originais))
