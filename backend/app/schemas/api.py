from __future__ import annotations
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    conversation_id: str | None = None
    document_ids: list[str] | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    mode: Literal["hybrid", "keyword", "semantic"] = "hybrid"
    document_ids: list[str] | None = None
    doc_type: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    k: int = Field(default=10, ge=1, le=50)
