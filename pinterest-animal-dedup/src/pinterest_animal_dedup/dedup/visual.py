from __future__ import annotations

import io
from typing import Iterable

import imagehash
from PIL import Image

from pinterest_animal_dedup.config import settings
from pinterest_animal_dedup.http_client import fetch_bytes


def compute_hashes(image_bytes: bytes) -> tuple[str, str] | None:
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return None
    ph = str(imagehash.phash(img))
    dh = str(imagehash.dhash(img))
    return ph, dh


def hamming(a: str, b: str) -> int:
    ha = imagehash.hex_to_hash(a)
    hb = imagehash.hex_to_hash(b)
    return ha - hb


def fetch_pin_thumbnail_hash(thumbnail_url: str | None) -> tuple[str, str] | None:
    if not thumbnail_url:
        return None
    status, data, err = fetch_bytes(thumbnail_url)
    if err or status != 200 or not data:
        return None
    return compute_hashes(data)


def min_hamming_to_candidates(
    pin_hash: tuple[str, str] | None,
    candidate_hashes: Iterable[tuple[str, str]],
) -> int | None:
    if not pin_hash:
        return None
    ph_pin, dh_pin = pin_hash
    best: int | None = None
    for ph_c, dh_c in candidate_hashes:
        d = min(hamming(ph_pin, ph_c), hamming(dh_pin, dh_c))
        best = d if best is None else min(best, d)
    return best
