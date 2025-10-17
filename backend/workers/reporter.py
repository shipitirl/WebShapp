"""Generate Markdown reports summarizing SHAP shifts."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List

from backend.queries import fetch_top_shap
from backend.deps import get_duckdb


def build_report(gid: str, k: int = 5) -> str:
    conn = get_duckdb()
    items = fetch_top_shap(conn, gid, limit=k)
    lines = [f"# SHAP Report for {gid}", "", "Top contributors:"]
    for item in items:
        lines.append(f"- **{item.feature}**: {item.impact:.4f}")
    return "\n".join(lines)


def write_report(gid: str) -> Path:
    content = build_report(gid)
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    path = reports_dir / f"{datetime.now().date()}_{gid}.md"
    path.write_text(content)
    return path
