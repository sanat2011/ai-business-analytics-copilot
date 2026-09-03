"""Auto-select charts / KPI / tables (Phase 9)."""

from __future__ import annotations


def choose_visualization(df, question: str = "") -> str:
    raise NotImplementedError("Phase 9 — choose_visualization()")


def render_visualization(df, viz_type: str, title: str = "") -> None:
    raise NotImplementedError("Phase 9 — render_visualization()")
