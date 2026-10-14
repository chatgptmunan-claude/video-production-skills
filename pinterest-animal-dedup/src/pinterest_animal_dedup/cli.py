from __future__ import annotations

import typer
import uvicorn
from rich.console import Console

from pinterest_animal_dedup.config import settings
from pinterest_animal_dedup.db.repository import list_candidates
from pinterest_animal_dedup.pipeline import (
    analyze_pins,
    dedup_records,
    discover_pins,
    export_artifacts,
    persist_records,
    run_demo,
    score_records,
    select_top_candidate,
    write_mode_b_package,
)
from pinterest_animal_dedup.config import ARTIFACTS_DIR

app = typer.Typer(help="Pinterest animal discovery + China domestic dedup")
console = Console()


@app.command()
def discover(
    target: int = typer.Option(settings.discover_target_count, help="Target pin count"),
):
    pins = discover_pins(target=target)
    console.print(f"Found {len(pins)} pins")
    for p in pins[:5]:
        console.print(f"  {p.pin_id} {p.url} [{p.media_type.value}]")


@app.command()
def analyze():
    pins = [r.pin for r in list_candidates(500)]
    if not pins:
        pins = discover_pins()
    records = analyze_pins(pins)
    persist_records(records)
    console.print(f"Analyzed {len(records)} animal candidates")


@app.command()
def dedup():
    records = list_candidates(500)
    if not records:
        console.print("No candidates in DB; run discover + analyze first.")
        raise typer.Exit(1)
    records = dedup_records(records)
    persist_records(records)
    console.print(f"Dedup updated for {len(records)} candidates")


@app.command()
def score():
    records = list_candidates(500)
    if not records:
        console.print("No candidates in DB.")
        raise typer.Exit(1)
    records = score_records(records)
    persist_records(records)
    export_artifacts(records)
    console.print("Scored and exported artifacts/ranked_report.md")


@app.command()
def ui(
    host: str = "127.0.0.1",
    port: int = 8765,
):
    uvicorn.run("pinterest_animal_dedup.ui.app:app", host=host, port=port, reload=False)


@app.command("run-demo")
def run_demo_cmd(
    target: int = typer.Option(20, help="Discover target"),
    fast: bool = typer.Option(False, help="Skip domestic dedup (not for production)"),
):
    records = run_demo(target=target, skip_dedup=fast)
    console.print(f"Demo complete: {len(records)} scored candidates")
    if len(records) < 10:
        console.print("[yellow]Warning: fewer than 10 candidates — Pinterest access may be limited.[/yellow]")


@app.command()
def package_top():
    records = list_candidates(100)
    top = select_top_candidate(records)
    if not top:
        raise typer.Exit("No candidate")
    path = write_mode_b_package(top, ARTIFACTS_DIR / "first_short_package")
    console.print(f"Wrote {path}")


if __name__ == "__main__":
    app()
