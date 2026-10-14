from __future__ import annotations

import json

from sqlalchemy import select

from pinterest_animal_dedup.db.schema import CandidateRow, get_session_factory
from pinterest_animal_dedup.models import (
    AnimalAnalysis,
    CandidateRecord,
    DedupStatus,
    DomesticDedupResult,
    PinterestPin,
    ScoreBreakdown,
)


def upsert_candidate(record: CandidateRecord) -> None:
    Session = get_session_factory()
    with Session() as session:
        row = session.get(CandidateRow, record.pin.pin_id)
        if row is None:
            row = CandidateRow(pin_id=record.pin.pin_id, url=record.pin.url)
            session.add(row)
        row.url = record.pin.url
        row.title = record.pin.title
        row.description = record.pin.description
        row.media_type = record.pin.media_type.value
        row.thumbnail_url = record.pin.thumbnail_url
        row.source_query = record.pin.source_query
        row.pin_json = record.pin.model_dump_json()
        row.analysis_json = record.analysis.model_dump_json() if record.analysis else None
        row.domestic_json = json.dumps([d.model_dump() for d in record.domestic], default=str)
        row.aggregate_dedup = record.aggregate_dedup_status.value
        row.score_total = record.score.total if record.score else None
        row.score_json = record.score.model_dump_json() if record.score else None
        row.adaptation_mode = record.adaptation_mode
        row.adaptation_notes = record.adaptation_notes
        session.commit()


def list_candidates(limit: int = 100) -> list[CandidateRecord]:
    Session = get_session_factory()
    with Session() as session:
        rows = session.scalars(
            select(CandidateRow)
            .order_by(CandidateRow.score_total.desc().nullslast())
            .limit(limit)
        ).all()
        out: list[CandidateRecord] = []
        for row in rows:
            pin = PinterestPin.model_validate_json(row.pin_json)
            analysis = (
                AnimalAnalysis.model_validate_json(row.analysis_json) if row.analysis_json else None
            )
            domestic = [
                DomesticDedupResult.model_validate(d)
                for d in json.loads(row.domestic_json or "[]")
            ]
            score = ScoreBreakdown.model_validate_json(row.score_json) if row.score_json else None
            out.append(
                CandidateRecord(
                    pin=pin,
                    analysis=analysis,
                    domestic=domestic,
                    aggregate_dedup_status=DedupStatus(row.aggregate_dedup),
                    score=score,
                    adaptation_mode=row.adaptation_mode,
                    adaptation_notes=row.adaptation_notes,
                )
            )
        return out
