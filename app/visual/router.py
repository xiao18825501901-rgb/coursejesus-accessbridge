from __future__ import annotations

from app.visual.spec import Renderer, VisualSpec, VisualType


def route_visual(spec: VisualSpec) -> Renderer:
    """Return a deterministic renderer after rejecting remote execution."""

    if not spec.should_generate:
        return Renderer.NONE
    allowed = {
        Renderer.DETERMINISTIC_DIAGRAM,
        Renderer.SVG,
    }
    if spec.visual_type is not VisualType.DIAGRAM or spec.renderer not in allowed:
        raise ValueError("competition runtime supports only local diagram renderers, not remote or non-diagram modes")
    if spec.renderer is Renderer.SVG and spec.semantic_precision == "ILLUSTRATIVE":
        raise ValueError("exact or bounded semantics are required for deterministic SVG")
    return spec.renderer

