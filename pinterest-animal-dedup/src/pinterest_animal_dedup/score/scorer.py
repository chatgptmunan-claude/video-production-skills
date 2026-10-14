from __future__ import annotations

from pinterest_animal_dedup.models import (
    AnimalAnalysis,
    DedupStatus,
    DomesticDedupResult,
    PinMediaType,
    PinterestPin,
    ScoreBreakdown,
)


def score_candidate(
    pin: PinterestPin,
    analysis: AnimalAnalysis | None,
    domestic: list[DomesticDedupResult],
    aggregate: DedupStatus,
) -> ScoreBreakdown:
    blob = f"{pin.title} {pin.description}".lower()
    tone = set((analysis.tone if analysis else []) or [])

    funny_healing = 8.0
    if "funny" in tone:
        funny_healing += 10
    if "healing" in tone:
        funny_healing += 8
    if analysis and analysis.is_animal:
        funny_healing += 5
    if any(w in blob for w in ("hilarious", "wholesome", "cute", "adorable")):
        funny_healing += 4
    funny_healing = min(funny_healing, 25.0)

    hook = 6.0
    if pin.media_type == PinMediaType.VIDEO:
        hook += 10
    if analysis and analysis.has_action:
        hook += 6
    if any(w in blob for w in ("react", "zoomies", "fail", "surprise", "scream")):
        hook += 4
    hook = min(hook, 20.0)

    freshness = 12.0
    if aggregate == DedupStatus.NOT_FOUND:
        freshness = 18.0
    elif aggregate == DedupStatus.POSSIBLE_MATCH:
        freshness = 10.0
    elif aggregate == DedupStatus.CONFIRMED_MATCH:
        freshness = 4.0
    elif aggregate == DedupStatus.UNKNOWN:
        freshness = 12.0
    freshness = min(freshness, 20.0)

    remake = 10.0
    if analysis and analysis.rights_hint == "unclear":
        remake += 3
    if pin.media_type in (PinMediaType.IMAGE, PinMediaType.GIF, PinMediaType.UNKNOWN):
        remake += 4
    if aggregate != DedupStatus.CONFIRMED_MATCH:
        remake += 2
    remake = min(remake, 15.0)

    story = 5.0
    if pin.description and len(pin.description) > 40:
        story += 3
    if analysis and "Micro-moment" not in analysis.story_notes:
        story += 2
    story = min(story, 10.0)

    production = 7.0
    if pin.media_type == PinMediaType.VIDEO and pin.video_url:
        production -= 2
    if pin.media_type == PinMediaType.IMAGE:
        production += 2
    production = max(3.0, min(production, 10.0))

    return ScoreBreakdown(
        funny_healing=round(funny_healing, 1),
        hook_first_3s=round(hook, 1),
        domestic_freshness=round(freshness, 1),
        remake_headroom=round(remake, 1),
        story_completeness=round(story, 1),
        production_difficulty=round(production, 1),
    )


def adaptation_notes(
    pin: PinterestPin,
    analysis: AnimalAnalysis | None,
    aggregate: DedupStatus,
) -> tuple[str, str]:
    mode = "B"
    if analysis and analysis.rights_hint == "likely_rights_managed":
        mode = "B"
    notes = (
        "Mode B AI remake: recreate beat structure with new footage/VO; do not claim free-to-use."
    )
    if aggregate == DedupStatus.CONFIRMED_MATCH:
        notes += " Domestic likely has similar clip — differentiate hook and pacing."
    elif aggregate == DedupStatus.NOT_FOUND:
        notes += " No strong domestic hit — localize captions and trending audio carefully."
    elif aggregate == DedupStatus.UNKNOWN:
        notes += " Dedup inconclusive — treat as fresh but verify manually before publish."
    if pin.media_type != PinMediaType.VIDEO:
        notes += " Source is image/GIF — use kinetic text + SFX for first 3s."
    return mode, notes
