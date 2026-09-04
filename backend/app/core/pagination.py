from __future__ import annotations

from app.core.models import ApiModel


class Page[T](ApiModel):
    items: list[T]
    total: int
    page: int
    page_size: int
