from __future__ import annotations

ANIMAL_SEED_QUERIES: list[str] = [
    "funny cat video short",
    "healing dog moment",
    "cute puppy fails",
    "funny animal compilation pets",
    "cat zoomies funny",
    "dog reaction wholesome",
    "baby animal cute moment",
    "parrot talking funny",
    "hamster cute video",
    "rabbit binky cute",
    "otter holding hands healing",
    "cow cuddling wholesome",
    "goat screaming funny",
    "raccoon trash panda funny",
    "duckling following mom",
    "hedgehog eating cute",
    "squirrel stealing food funny",
    "horse friendship healing",
    "alpaca spit funny",
    "penguin waddle cute",
]

TAG_SUFFIXES = [
    "pets",
    "animals",
    "cute",
    "funny",
    "wholesome",
    "healing",
    "short video",
    "viral",
]


def expand_queries(seeds: list[str] | None = None, related: list[str] | None = None) -> list[str]:
    base = list(seeds or ANIMAL_SEED_QUERIES)
    seen: set[str] = set()
    out: list[str] = []
    for q in base:
        key = q.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(q.strip())
    for tag in related or []:
        tag = tag.strip()
        if not tag:
            continue
        combo = f"{tag} funny animal video"
        key = combo.lower()
        if key not in seen:
            seen.add(key)
            out.append(combo)
    # Light combinatorial expansion on first few seeds
    for seed in (seeds or ANIMAL_SEED_QUERIES)[:6]:
        for suffix in TAG_SUFFIXES[:4]:
            combo = f"{seed} {suffix}".strip()
            key = combo.lower()
            if key not in seen:
                seen.add(key)
                out.append(combo)
    return out
