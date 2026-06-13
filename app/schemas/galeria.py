import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GaleriaFotoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    album_id: uuid.UUID
    url: str
    storage_path: str | None = None
    legenda: str | None = None
    ordem: int
    uploaded_by: uuid.UUID | None = None
    created_at: datetime


class GaleriaAlbumCreate(BaseModel):
    evento_id: uuid.UUID | None = None
    comunidade_id: uuid.UUID | None = None


class GaleriaAlbumUpdate(BaseModel):
    evento_id: uuid.UUID | None = None
    comunidade_id: uuid.UUID | None = None


class GaleriaAlbumRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    evento_id: uuid.UUID | None = None
    comunidade_id: uuid.UUID | None = None
    created_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    fotos: list[GaleriaFotoRead] = []


class GaleriaFotoUrlCreate(BaseModel):
    url: str
    legenda: str | None = None
    ordem: int = 0


class GaleriaFotoUpdate(BaseModel):
    legenda: str | None = None
