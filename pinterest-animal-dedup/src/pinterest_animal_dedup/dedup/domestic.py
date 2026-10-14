from __future__ import annotations

from pinterest_animal_dedup.config import settings
from pinterest_animal_dedup.dedup.platforms import DOMESTIC_PLATFORMS
from pinterest_animal_dedup.dedup.query_builder import chinese_queries_for_pin
from pinterest_animal_dedup.dedup.visual import fetch_pin_thumbnail_hash, min_hamming_to_candidates
from pinterest_animal_dedup.dedup.web_search import search_platform
from pinterest_animal_dedup.models import (
    AnimalAnalysis,
    DedupStatus,
    DomesticDedupResult,
    PinterestPin,
    SearchEvidence,
)


def _status_from_evidence(
    evidence: list[SearchEvidence],
    visual_hamming: int | None,
) -> tuple[DedupStatus, float, str]:
    errors = [e for e in evidence if e.error]
    unreachable = [e for e in evidence if e.error and "HTTP" in (e.error or "")]
    if len(unreachable) >= max(3, len(evidence) // 2):
        return DedupStatus.UNKNOWN, 0.2, "Search access unstable; cannot confirm domestic presence."

    strong = [
        e
        for e in evidence
        if e.result_url
        and not e.error
        and any(
            meta["domain_hint"] in (e.result_url or "").lower()
            for meta in DOMESTIC_PLATFORMS.values()
        )
    ]
    if visual_hamming is not None and visual_hamming <= 6:
        return DedupStatus.CONFIRMED_MATCH, 0.85, f"Visual hash very close (hamming={visual_hamming})."

    if visual_hamming is not None and visual_hamming <= settings.visual_hamming_threshold:
        if strong:
            return (
                DedupStatus.CONFIRMED_MATCH,
                0.75,
                f"Text search hits + similar thumbnail (hamming={visual_hamming}).",
            )
        return (
            DedupStatus.POSSIBLE_MATCH,
            0.55,
            f"Thumbnail similarity only (hamming={visual_hamming}); verify manually.",
        )

    if len(strong) >= 2:
        return DedupStatus.POSSIBLE_MATCH, 0.6, "Multiple on-platform search hits; manual verify recommended."

    if len(strong) == 1:
        return DedupStatus.POSSIBLE_MATCH, 0.45, "Single on-platform hit; evidence thin."

    if errors and len(errors) == len(evidence):
        benign = {"no_on_platform_hits", "no_results"}
        if all((e.error or "") in benign for e in evidence):
            return DedupStatus.NOT_FOUND, 0.5, "No on-platform hits in allowed public search."
        return DedupStatus.UNKNOWN, 0.15, "All queries failed or search unavailable."

    return DedupStatus.NOT_FOUND, 0.5, "No on-platform hits in allowed public search."


def dedup_pin_on_platform(
    pin: PinterestPin,
    analysis: AnimalAnalysis | None,
    platform_key: str,
    n_queries: int | None = None,
    pin_hash: tuple[str, str] | None = None,
) -> DomesticDedupResult:
    n = n_queries or settings.dedup_queries_per_platform
    n = max(n, 5)
    queries = chinese_queries_for_pin(pin, analysis, n=n)
    evidence: list[SearchEvidence] = []
    for q in queries:
        evidence.append(search_platform(q, platform_key))

    if pin_hash is None:
        pin_hash = fetch_pin_thumbnail_hash(pin.thumbnail_url)
    visual_h = min_hamming_to_candidates(pin_hash, []) if pin_hash else None

    status, conf, notes = _status_from_evidence(evidence, visual_h)
    return DomesticDedupResult(
        platform=platform_key,
        status=status,
        confidence=conf,
        evidence=evidence,
        visual_hamming_min=visual_h,
        notes=notes,
    )


def aggregate_domestic_status(results: list[DomesticDedupResult]) -> DedupStatus:
    order = {
        DedupStatus.CONFIRMED_MATCH: 4,
        DedupStatus.POSSIBLE_MATCH: 3,
        DedupStatus.UNKNOWN: 2,
        DedupStatus.NOT_FOUND: 1,
    }
    if not results:
        return DedupStatus.UNKNOWN
    best = max(results, key=lambda r: order.get(r.status, 0))
    if best.status == DedupStatus.CONFIRMED_MATCH:
        return DedupStatus.CONFIRMED_MATCH
    if any(r.status == DedupStatus.POSSIBLE_MATCH for r in results):
        return DedupStatus.POSSIBLE_MATCH
    if all(r.status == DedupStatus.NOT_FOUND for r in results):
        return DedupStatus.NOT_FOUND
    if any(r.status == DedupStatus.UNKNOWN for r in results):
        return DedupStatus.UNKNOWN
    return DedupStatus.NOT_FOUND


def run_domestic_dedup(
    pin: PinterestPin,
    analysis: AnimalAnalysis | None,
) -> list[DomesticDedupResult]:
    pin_hash = fetch_pin_thumbnail_hash(pin.thumbnail_url)
    return [
        dedup_pin_on_platform(pin, analysis, key, pin_hash=pin_hash)
        for key in DOMESTIC_PLATFORMS
    ]
