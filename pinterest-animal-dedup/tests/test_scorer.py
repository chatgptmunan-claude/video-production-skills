from pinterest_animal_dedup.models import (
    AnimalAnalysis,
    DedupStatus,
    PinMediaType,
    PinterestPin,
)
from pinterest_animal_dedup.score import score_candidate


def test_score_prefers_not_found_freshness():
    pin = PinterestPin(
        pin_id="1",
        url="https://www.pinterest.com/pin/1/",
        title="wholesome dog",
        media_type=PinMediaType.VIDEO,
    )
    analysis = AnimalAnalysis(is_animal=True, animal_labels=["dog"], tone=["healing"], has_action=True)
    s_nf = score_candidate(pin, analysis, [], DedupStatus.NOT_FOUND)
    s_cm = score_candidate(pin, analysis, [], DedupStatus.CONFIRMED_MATCH)
    assert s_nf.domestic_freshness > s_cm.domestic_freshness
    assert s_nf.total > 0
