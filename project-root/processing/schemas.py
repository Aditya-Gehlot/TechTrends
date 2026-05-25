from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime


class RawRecord(BaseModel):
    topic: str
    partition: Optional[int]
    offset: Optional[int]
    timestamp: Optional[int]
    ingested_at: Optional[datetime]
    payload: Dict[str, Any]


class NormalizedRecord(BaseModel):
    source: str
    id: str
    timestamp: datetime
    title: Optional[str] = None
    text: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    url: Optional[str] = None
    techs: List[str] = Field(default_factory=list)
    raw: Dict[str, Any] = Field(default_factory=dict)
