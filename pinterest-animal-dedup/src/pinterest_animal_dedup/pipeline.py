from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console

from pinterest_animal_dedup.analyze import analyze_pin
from pinterest_animal_dedup.config import ARTIFACTS_DIR, settings
from pinterest_animal_dedup.db.repository import list_candidates, upsert_candidate
from pinterest_animal_dedup.dedup import aggregate_domestic_status, run_domestic_dedup
from pinterest_animal_dedup.discover import (
    enrich_pin_detail,
    expand_queries,
    search_pins,
    search_pins_public_index,
)
from pinterest_animal_dedup.models import CandidateRecord, DedupStatus, PinterestPin
from pinterest_animal_dedup.score import adaptation_notes, score_candidate

console = Console()


def discover_pins(target: int | None = None) -> list[PinterestPin]:
    target = target or settings.discover_target_count
    queries = expand_queries()
    seen: set[str] = set()
    pins: list[PinterestPin] = []
    related_pool: list[str] = []

    for q in queries:
        if len(pins) >= target:
            break
        batch, related, err = search_pins(q, limit=settings.pinterest_max_pins_per_query)
        if err or not batch:
            idx_batch, idx_err = search_pins_public_index(
                q, limit=settings.pinterest_max_pins_per_query
            )
            if idx_err and not idx_batch:
                console.print(f"[yellow]Query '{q}': {err or idx_err}[/yellow]")
            batch = idx_batch
        related_pool.extend(related)
        for p in batch:
            if p.pin_id in seen:
                continue
            seen.add(p.pin_id)
            pins.append(p)
            if len(pins) >= target:
                break

    if len(pins) < target and related_pool:
        extra_queries = expand_queries(related=related_pool[:15])
        for q in extra_queries:
            if len(pins) >= target:
                break
            batch, _, err = search_pins(q, limit=settings.pinterest_max_pins_per_query)
            if err:
                continue
            for p in batch:
                if p.pin_id in seen:
                    continue
                seen.add(p.pin_id)
                pins.append(p)
                if len(pins) >= target:
                    break

    enriched: list[PinterestPin] = []
    for p in pins:
        enriched.append(enrich_pin_detail(p))
    return enriched


def analyze_pins(pins: list[PinterestPin]) -> list[CandidateRecord]:
    records: list[CandidateRecord] = []
    for pin in pins:
        analysis = analyze_pin(pin)
        if not analysis.is_animal:
            continue
        records.append(CandidateRecord(pin=pin, analysis=analysis))
    return records


def dedup_records(records: list[CandidateRecord]) -> list[CandidateRecord]:
    out: list[CandidateRecord] = []
    for rec in records:
        domestic = run_domestic_dedup(rec.pin, rec.analysis)
        agg = aggregate_domestic_status(domestic)
        rec.domestic = domestic
        rec.aggregate_dedup_status = agg
        out.append(rec)
    return out


def score_records(records: list[CandidateRecord]) -> list[CandidateRecord]:
    out: list[CandidateRecord] = []
    for rec in records:
        score = score_candidate(rec.pin, rec.analysis, rec.domestic, rec.aggregate_dedup_status)
        mode, notes = adaptation_notes(rec.pin, rec.analysis, rec.aggregate_dedup_status)
        rec.score = score
        rec.adaptation_mode = mode
        rec.adaptation_notes = notes
        out.append(rec)
    return out


def persist_records(records: list[CandidateRecord]) -> None:
    for rec in records:
        upsert_candidate(rec)


def _summary_line(rec: CandidateRecord, rank: int) -> str:
    title = (rec.pin.title or rec.pin.description or "（无标题）")[:60]
    score = rec.score.total if rec.score else 0
    return (
        f"| {rank} | {rec.pin.url} | {title} | {rec.aggregate_dedup_status.value} "
        f"| {score} | Mode {rec.adaptation_mode}: {rec.adaptation_notes[:80]} |"
    )


def export_artifacts(records: list[CandidateRecord], run_id: str = "latest") -> Path:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    ranked = sorted(records, key=lambda r: (r.score.total if r.score else 0), reverse=True)
    md_path = ARTIFACTS_DIR / f"ranked_report_{run_id}.md"
    json_path = ARTIFACTS_DIR / f"ranked_report_{run_id}.json"

    lines = [
        "# Pinterest 动物短视频选题 — 查重与评分",
        "",
        "说明：国内状态来自公开 site: 搜索与可选缩略图哈希；NOT_FOUND 不等于国内从未发布。",
        "",
        "| 排名 | Pinterest链接 | 内容概述 | 国内查重状态 | 评分 | 建议改编方式 |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for i, rec in enumerate(ranked, start=1):
        lines.append(_summary_line(rec, i))

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    payload = [r.model_dump(mode="json") for r in ranked]
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Symlink-style copies for stable names
    (ARTIFACTS_DIR / "ranked_report.md").write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")
    (ARTIFACTS_DIR / "ranked_report.json").write_text(
        json_path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return md_path


def select_top_candidate(records: list[CandidateRecord]) -> CandidateRecord | None:
    ranked = sorted(records, key=lambda r: (r.score.total if r.score else 0), reverse=True)
    for rec in ranked:
        if rec.aggregate_dedup_status == DedupStatus.CONFIRMED_MATCH:
            continue
        if rec.analysis and rec.analysis.is_animal:
            return rec
    return ranked[0] if ranked else None


def write_mode_b_package(rec: CandidateRecord, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    pkg = out_dir / f"mode_b_pin_{rec.pin.pin_id}"
    pkg.mkdir(parents=True, exist_ok=True)

    animals = ", ".join(rec.analysis.animal_labels if rec.analysis else ["animal"])
    tones = ", ".join(rec.analysis.tone if rec.analysis else ["cute"])

    (pkg / "source.json").write_text(
        json.dumps(
            {
                "pinterest_url": rec.pin.url,
                "pin_id": rec.pin.pin_id,
                "title": rec.pin.title,
                "description": rec.pin.description,
                "media_type": rec.pin.media_type.value,
                "thumbnail_url": rec.pin.thumbnail_url,
                "rights": "unclear — Mode B remake only",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (pkg / "domestic_check.json").write_text(
        json.dumps(
            {
                "aggregate_status": rec.aggregate_dedup_status.value,
                "platforms": [d.model_dump(mode="json") for d in rec.domestic],
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    (pkg / "publish.json").write_text(
        json.dumps(
            {
                "mode": rec.adaptation_mode,
                "target_platforms": ["douyin", "kuaishou", "wechat_channels", "xiaohongshu", "bilibili"],
                "disclaimer": "AI-assisted remake; not claiming ownership of Pinterest source.",
                "score_total": rec.score.total if rec.score else None,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    script = f"""# Mode B 短片脚本 — {animals}

- 来源参考（不直接使用素材）：{rec.pin.url}
- 基调：{tones}
- 时长目标：15–25s

## Hook（0–3s）
画面：特写 {animals} 突然动作/表情反差（原创拍摄或授权素材）。
字幕：「当我以为今天会很乖…」
音效：短促 whoosh + 可爱 squeak。

## Beat 2（3–10s）
还原 Pinterest 梗的节奏：{rec.pin.title or rec.pin.description[:80]}

## Payoff（10–18s）
治愈/搞笑落点，留白 0.5s 给观众反应。

## CTA（可选）
「关注看更多冤种小宝贝」
"""
    (pkg / "script.md").write_text(script, encoding="utf-8")

    storyboard = {
        "fps": 30,
        "duration_sec": 18,
        "shots": [
            {"t": "0-3", "visual": f"Close-up {animals}, sudden movement", "text": "当我以为今天会很乖…"},
            {"t": "3-10", "visual": "Mid shot action beat matching reference rhythm", "text": ""},
            {"t": "10-16", "visual": "Reaction / wholesome punchline", "text": "治愈收尾"},
            {"t": "16-18", "visual": "Logo or follow CTA", "text": "关注"},
        ],
    }
    (pkg / "storyboard.json").write_text(
        json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return pkg


def run_demo(target: int = 20, skip_dedup: bool = False) -> list[CandidateRecord]:
    console.print("[bold]Discovering Pinterest pins…[/bold]")
    pins = discover_pins(target=target)
    console.print(f"Discovered {len(pins)} pins")
    records = analyze_pins(pins)
    console.print(f"Animal candidates after analyze: {len(records)}")
    if not skip_dedup:
        records = dedup_records(records)
    else:
        for rec in records:
            rec.aggregate_dedup_status = DedupStatus.UNKNOWN
    records = score_records(records)
    persist_records(records)
    export_artifacts(records)
    top = select_top_candidate(records)
    if top:
        pkg = write_mode_b_package(top, ARTIFACTS_DIR / "first_short_package")
        console.print(f"[green]Mode B package: {pkg}[/green]")
    return records
