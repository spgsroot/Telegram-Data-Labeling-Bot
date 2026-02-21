import hashlib
import io
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path

import polars as pl
import py7zr
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Item, Label

log = logging.getLogger(__name__)


@dataclass
class ImportResult:
    loaded: int
    duplicates: int
    errors: int


async def import_from_7z(session: AsyncSession, file_bytes: bytes) -> ImportResult:
    buf = io.BytesIO(file_bytes)
    csv_data: bytes | None = None

    try:
        with py7zr.SevenZipFile(buf, mode="r") as archive:
            for name, bio in archive.read().items():
                if name.lower().endswith(".csv"):
                    csv_data = bio.read()
                    break
    except Exception as exc:
        raise ValueError(f"Не удалось открыть архив: {exc}") from exc

    if csv_data is None:
        raise ValueError("Архив не содержит CSV-файла.")

    try:
        df = pl.read_csv(io.BytesIO(csv_data), encoding="utf8")
    except Exception as exc:
        raise ValueError(f"Не удалось прочитать CSV: {exc}") from exc

    if df.is_empty():
        raise ValueError("CSV-файл пуст.")

    if "text" not in df.columns:
        raise ValueError("CSV не содержит обязательный столбец 'text'.")

    texts = df["text"].drop_nulls().unique().to_list()

    if not texts:
        return ImportResult(loaded=0, duplicates=0, errors=0)

    # asyncpg limits query parameters to 32767; each row uses 3 params (text, text_hash, status)
    batch_size = 5_000
    loaded = 0

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        rows = [
            {
                "text": t,
                "text_hash": hashlib.md5(t.encode()).hexdigest(),
                "status": "pending",
            }
            for t in batch
        ]
        stmt = pg_insert(Item).values(rows)
        stmt = stmt.on_conflict_do_nothing(index_elements=["text_hash"])
        result = await session.execute(stmt)
        loaded += result.rowcount  # type: ignore[union-attr]

    await session.commit()

    duplicates = len(texts) - loaded

    return ImportResult(loaded=loaded, duplicates=duplicates, errors=0)


async def export_to_7z(session: AsyncSession) -> bytes | None:
    rows = (
        await session.execute(
            select(Item.text, Label.score)
            .join(Label, Label.item_id == Item.id)
            .where(Label.action == "rated")
        )
    ).all()

    if not rows:
        return None

    df = pl.DataFrame({"text": [r[0] for r in rows], "score": [r[1] for r in rows]})
    csv_bytes = df.write_csv().encode("utf-8")

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "dataset_export.csv"
        csv_path.write_bytes(csv_bytes)

        archive_buf = io.BytesIO()
        with py7zr.SevenZipFile(archive_buf, mode="w") as archive:
            archive.write(csv_path, arcname="dataset_export.csv")
        return archive_buf.getvalue()
