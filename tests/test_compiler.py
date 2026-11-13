from __future__ import annotations

import pytest

from app.visual.spec import (
    Diagram,
    DiagramEdge,
    DiagramNode,
    Renderer,
    VisualSpec,
    VisualStyle,
    VisualType,
)


def make_spec(label: str = "Queue") -> VisualSpec:
    return VisualSpec(
        visual_spec_version="1.0",
        should_generate=True,
        pedagogical_reason="Show the order of items in a queue.",
        visual_goal="Compare the front and back of a queue.",
        visual_type=VisualType.DIAGRAM,
        renderer=Renderer.DETERMINISTIC_DIAGRAM,
        importance="HIGH",
        timing="INLINE",
        source_grounding=[],
        must_include=["Front item leaves first"],
        must_not_include=["Network requests"],
        exact_labels=[label],
        equations=[],
        code_elements=[],
        reference_assets=[],
        style=VisualStyle(
            tone="CLEAN_TECHNICAL",
            background="light neutral",
            composition="two labeled nodes",
        ),
        duration_seconds=None,
        aspect_ratio="16:9",
        cost_tier="FREE",
        confidence=1,
        fallback_renderer="DETERMINISTIC_DIAGRAM",
        cache_policy="NO_CACHE",
        language="en",
        motion_is_essential=False,
        semantic_precision="EXACT",
        diagram=Diagram(
            layout="LEFT_RIGHT",
            nodes=[
                DiagramNode(id="front", label="Front"),
                DiagramNode(id="back", label=label),
            ],
            edges=[DiagramEdge(**{"from": "front", "to": "back"})],
        ),
        animation_steps=[],
    )


def test_compiler_is_deterministic_and_accessible() -> None:
    from app.visual.compiler import compile_visual

    first = compile_visual(make_spec(), alt_text="Queue diagram", long_description="Front to back.")
    second = compile_visual(make_spec(), alt_text="Queue diagram", long_description="Front to back.")

    assert first.sha256 == second.sha256
    assert first.svg == second.svg
    assert 'role="img"' in first.svg
    assert "<title" in first.svg
    assert "<desc" in first.svg
    assert "Front item leaves first" in first.svg


def test_compiler_escapes_untrusted_text() -> None:
    from app.visual.compiler import compile_visual

    result = compile_visual(
        make_spec('<script>alert("x")</script>'),
        alt_text='"quoted" & safe',
        long_description="<control>",
    )

    assert "<script>" not in result.svg
    assert "&lt;script&gt;" in result.svg
    assert "&lt;control&gt;" in result.svg
    assert '&quot;quoted&quot; &amp; safe' in result.svg


def test_router_rejects_remote_renderers() -> None:
    from app.visual.router import route_visual

    spec = make_spec()
    remote = spec.model_copy(update={"renderer": Renderer.COMFY_IMAGE, "visual_type": VisualType.IMAGE})

    assert route_visual(spec) is Renderer.DETERMINISTIC_DIAGRAM
    with pytest.raises(ValueError, match="remote or non-diagram"):
        route_visual(remote)

