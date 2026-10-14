from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class DedupStatus(str, enum.Enum):
    NOT_FOUND = "NOT_FOUND"
    POSSIBLE_MATCH = "POSSIBLE_MATCH"
    CONFIRMED_MATCH = "CONFIRMED_MATCH"
    UNKNOWN = "UNKNOWN"


class PinMediaType(str, enum.Enum):
    VIDEO = "video"
    IMAGE = "image"
    GIF = "gif"
    STORY = "story"
    UNKNOWN = "unknown"


class ScoreBreakdown(BaseModel):
    funny_healing: float = 0.0
    hook_first_3s: float = 0.0
    domestic_freshness: float = 0.0
    remake_headroom: float = 0.0
    story_completeness: float = 0.0
    production_difficulty: float = 0.0

    @property
    def total(self) -> float:
        return round(
            self.funny_healing
            + self.hook_first_3s
            + self.domestic_freshness
            + self.remake_headroom
            + self.story_completeness
            + self.production_difficulty,
            1,
        )


class PinterestPin(BaseModel):
    pin_id: str
    url: str
    title: str = ""
    description: str = ""
    media_type: PinMediaType = PinMediaType.UNKNOWN
    thumbnail_url: str | None = None
    video_url: str | None = None
    source_query: str = ""
    tags: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class AnimalAnalysis(BaseModel):
    is_animal: bool
    animal_labels: list[str] = Field(default_factory=list)
    tone: list[str] = Field(default_factory=list)
    has_action: bool = False
    hook_notes: str = ""
    story_notes: str = ""
    rights_hint: str = "unclear"
    confidence: float = 0.0


class SearchEvidence(BaseModel):
    platform: str
    query: str
    result_url: str | None = None
    title: str | None = None
    snippet: str | None = None
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    error: str | None = None


class DomesticDedupResult(BaseModel):
    platform: str
    status: DedupStatus
    confidence: float = 0.0
    evidence: list[SearchEvidence] = Field(default_factory=list)
    visual_hamming_min: int | None = None
    notes: str = ""


class CandidateRecord(BaseModel):
    pin: PinterestPin
    analysis: AnimalAnalysis | None = None
    domestic: list[DomesticDedupResult] = Field(default_factory=list)
    aggregate_dedup_status: DedupStatus = DedupStatus.UNKNOWN
    score: ScoreBreakdown | None = None
    adaptation_mode: str = "B"
    adaptation_notes: str = ""
