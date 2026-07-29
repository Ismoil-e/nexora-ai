import re
import secrets
from datetime import datetime, timezone
from typing import Any
from uuid import UUID


def generate_slug(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:100]


def generate_api_key() -> tuple[str, str]:
    prefix = "nx"
    key = secrets.token_hex(32)
    full_key = f"{prefix}_{key}"
    return full_key, key


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def paginate(page: int, page_size: int) -> tuple[int, int]:
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    offset = (page - 1) * page_size
    return offset, page_size


def to_dict(model: Any, exclude: set | None = None) -> dict:
    if not model:
        return {}
    exclude = exclude or set()
    data = {}
    for column in model.__table__.columns:
        if column.name not in exclude:
            value = getattr(model, column.name)
            if isinstance(value, UUID):
                value = str(value)
            elif isinstance(value, datetime):
                value = value.isoformat()
            data[column.name] = value
    return data
