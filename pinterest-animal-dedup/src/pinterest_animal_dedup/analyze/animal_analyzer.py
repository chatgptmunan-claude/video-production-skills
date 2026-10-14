from __future__ import annotations

import re

from pinterest_animal_dedup.models import AnimalAnalysis, PinMediaType, PinterestPin

ANIMAL_TERMS = {
    "cat": "cat",
    "kitten": "cat",
    "dog": "dog",
    "puppy": "dog",
    "hamster": "hamster",
    "rabbit": "rabbit",
    "bunny": "rabbit",
    "parrot": "bird",
    "bird": "bird",
    "duck": "duck",
    "duckling": "duck",
    "cow": "cow",
    "goat": "goat",
    "horse": "horse",
    "alpaca": "alpaca",
    "llama": "llama",
    "otter": "otter",
    "raccoon": "raccoon",
    "hedgehog": "hedgehog",
    "squirrel": "squirrel",
    "penguin": "penguin",
    "fox": "fox",
    "bear": "bear",
    "panda": "panda",
    "monkey": "monkey",
    "ape": "monkey",
    "seal": "seal",
    "pet": "pet",
    "animal": "animal",
    "猫咪": "cat",
    "小狗": "dog",
    "动物": "animal",
}

FUNNY_TERMS = ["funny", "hilarious", "fail", "lol", "meme", "prank", "goofy", "搞笑", "好笑"]
HEALING_TERMS = [
    "healing",
    "wholesome",
    "cute",
    "sweet",
    "comfort",
    "heartwarming",
    "adorable",
    "治愈",
    "暖心",
]
ACTION_TERMS = [
    "zoomies",
    "jump",
    "run",
    "chase",
    "react",
    "dance",
    "spin",
    "bite",
    "catch",
    "play",
    "fight",
    "scream",
    "talk",
    "bark",
    "meow",
]


def _text_blob(pin: PinterestPin) -> str:
    parts = [pin.title, pin.description, " ".join(pin.tags), pin.source_query]
    return " ".join(p for p in parts if p).lower()


def analyze_pin(pin: PinterestPin) -> AnimalAnalysis:
    blob = _text_blob(pin)
    labels: list[str] = []
    for term, label in ANIMAL_TERMS.items():
        if re.search(rf"\b{re.escape(term)}\b", blob) or term in blob:
            if label not in labels:
                labels.append(label)

    is_animal = bool(labels) or "animal" in blob or "pet" in blob

    tone: list[str] = []
    if any(t in blob for t in FUNNY_TERMS):
        tone.append("funny")
    if any(t in blob for t in HEALING_TERMS):
        tone.append("healing")
    if not tone and is_animal:
        tone.append("cute")

    has_action = pin.media_type == PinMediaType.VIDEO or any(t in blob for t in ACTION_TERMS)

    hook_notes = ""
    if pin.media_type == PinMediaType.VIDEO:
        hook_notes = "Video pin — prioritize first 3s motion/surprise in remake."
    elif pin.media_type in (PinMediaType.GIF, PinMediaType.IMAGE):
        hook_notes = "Static/GIF — hook must be designed in remake (text + sound + quick cut)."

    story_notes = "Micro-moment" if len(blob) < 80 else "Has narrative caption cues"

    rights = "unclear"
    if "stock" in blob or "getty" in blob or "shutterstock" in blob:
        rights = "likely_rights_managed"

    conf = 0.35
    if is_animal:
        conf += 0.35
    if labels:
        conf += 0.15
    if pin.media_type == PinMediaType.VIDEO:
        conf += 0.1
    conf = min(conf, 0.95)

    return AnimalAnalysis(
        is_animal=is_animal,
        animal_labels=labels,
        tone=tone,
        has_action=has_action,
        hook_notes=hook_notes,
        story_notes=story_notes,
        rights_hint=rights,
        confidence=conf,
    )
