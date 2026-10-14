from pinterest_animal_dedup.dedup.domestic import _status_from_evidence
from pinterest_animal_dedup.models import DedupStatus, SearchEvidence


def test_not_found_when_no_hits():
    ev = [
        SearchEvidence(platform="douyin", query="q", error="no_results"),
        SearchEvidence(platform="douyin", query="q2", error="no_results"),
    ]
    status, _, _ = _status_from_evidence(ev, None)
    assert status in (DedupStatus.NOT_FOUND, DedupStatus.UNKNOWN)
