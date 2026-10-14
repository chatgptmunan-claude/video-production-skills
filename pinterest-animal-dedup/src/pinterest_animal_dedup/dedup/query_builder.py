from __future__ import annotations

from pinterest_animal_dedup.models import AnimalAnalysis, PinterestPin


def chinese_queries_for_pin(pin: PinterestPin, analysis: AnimalAnalysis | None, n: int = 5) -> list[str]:
    labels = (analysis.animal_labels if analysis else []) or ["动物"]
    label_cn_map = {
        "cat": "猫",
        "dog": "狗",
        "hamster": "仓鼠",
        "rabbit": "兔子",
        "bird": "鸟",
        "duck": "鸭",
        "cow": "牛",
        "goat": "羊",
        "horse": "马",
        "otter": "水獭",
        "raccoon": "浣熊",
        "penguin": "企鹅",
        "pet": "宠物",
        "animal": "动物",
    }
    cn_animals = [label_cn_map.get(l, l) for l in labels[:2]] or ["可爱动物"]
    tone = (analysis.tone if analysis else []) or ["搞笑"]
    tone_cn = "搞笑" if "funny" in tone else ("治愈" if "healing" in tone else "可爱")

    title_bit = (pin.title or pin.description or "")[:40]
    base_phrase = f"{cn_animals[0]}{tone_cn}短视频"

    queries = [
        f"{base_phrase}",
        f"{cn_animals[0]} {tone_cn} 视频",
        f"{' '.join(cn_animals)} 同款",
        f"{cn_animals[0]} 搞笑 动物",
        f"{tone_cn} {cn_animals[0]} 宠物",
        f"{cn_animals[0]} 动物 热门",
        f"宠物 {tone_cn} 短片",
    ]
    if title_bit:
        queries.append(f"{cn_animals[0]} {title_bit[:20]}")

    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        q = q.strip()
        if q and q not in seen:
            seen.add(q)
            out.append(q)
        if len(out) >= n:
            break
    while len(out) < n:
        out.append(f"{cn_animals[0]} 动物视频 {len(out)+1}")
    return out[: max(n, 5)]
