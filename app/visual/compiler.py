from __future__ import annotations

import hashlib
import html
import json
import textwrap
from collections import defaultdict, deque
from dataclasses import dataclass

from app.visual.spec import Diagram, DiagramNode, Renderer, VisualSpec
from app.visual.validators import validate_output


@dataclass(frozen=True)
class CompiledVisual:
    renderer: Renderer
    svg: str
    width: int
    height: int
    sha256: str
    alt_text: str
    long_description: str


def _topological_levels(diagram: Diagram) -> dict[str, int] | None:
    """Return stable graph layers, or None when the graph contains a cycle."""

    order = [node.id for node in diagram.nodes]
    indegree = {node_id: 0 for node_id in order}
    outgoing: dict[str, list[str]] = defaultdict(list)
    for edge in diagram.edges:
        outgoing[edge.from_id].append(edge.to)
        indegree[edge.to] += 1

    queue = deque(node_id for node_id in order if indegree[node_id] == 0)
    levels = {node_id: 0 for node_id in queue}
    processed = 0
    while queue:
        current = queue.popleft()
        processed += 1
        for target in outgoing[current]:
            levels[target] = max(levels.get(target, 0), levels[current] + 1)
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if processed != len(order):
        return None
    return levels


def _grouped_positions(
    nodes: list[DiagramNode],
    levels: dict[str, int],
    *,
    direction: str,
    node_width: int,
    node_height: int,
) -> dict[str, tuple[float, float]]:
    groups: dict[int, list[str]] = defaultdict(list)
    for node in nodes:
        groups[levels[node.id]].append(node.id)
    level_keys = sorted(groups)
    positions: dict[str, tuple[float, float]] = {}
    canvas_width = 1024
    edge_padding = 70
    usable_width = canvas_width - 2 * edge_padding

    if direction == "LEFT_RIGHT":
        x_values = {
            level: edge_padding
            + (usable_width - node_width) * index / max(1, len(level_keys) - 1)
            for index, level in enumerate(level_keys)
        }
        for level in level_keys:
            members = groups[level]
            step = 92
            group_height = node_height + step * max(0, len(members) - 1)
            top = 300 - group_height / 2
            for index, node_id in enumerate(members):
                positions[node_id] = (x_values[level], top + index * step)
    else:
        y_top, y_bottom = 148, 506 - node_height
        y_values = {
            level: y_top + (y_bottom - y_top) * index / max(1, len(level_keys) - 1)
            for index, level in enumerate(level_keys)
        }
        for level in level_keys:
            members = groups[level]
            step = min(230, usable_width / max(1, len(members) - 1))
            group_width = node_width + step * max(0, len(members) - 1)
            left = (canvas_width - group_width) / 2
            for index, node_id in enumerate(members):
                positions[node_id] = (left + index * step, y_values[level])
    return positions


def _fallback_positions(
    nodes: list[DiagramNode],
    *,
    node_width: int,
    node_height: int,
) -> dict[str, tuple[float, float]]:
    positions: dict[str, tuple[float, float]] = {}
    columns = min(4, max(1, len(nodes)))
    for index, node in enumerate(nodes):
        row, column = divmod(index, columns)
        x = 70 + column * ((1024 - 140 - node_width) / max(1, columns - 1))
        y = 160 + row * 110
        positions[node.id] = (x, y)
    return positions


def _positions(diagram: Diagram) -> dict[str, tuple[float, float]]:
    node_width, node_height = 172, 72
    levels = _topological_levels(diagram)
    if levels is None:
        return _fallback_positions(
            diagram.nodes,
            node_width=node_width,
            node_height=node_height,
        )
    direction = "TOP_DOWN" if diagram.layout == "TOP_DOWN" else "LEFT_RIGHT"
    if diagram.layout == "AUTO":
        direction = "TOP_DOWN" if len(set(levels.values())) > 1 else "LEFT_RIGHT"
    return _grouped_positions(
        diagram.nodes,
        levels,
        direction=direction,
        node_width=node_width,
        node_height=node_height,
    )


def _render_node_label(
    label: str,
    *,
    x: float,
    y: float,
    node_width: int,
    node_height: int,
) -> str:
    lines = textwrap.wrap(label, width=20, break_long_words=True) or [label]
    if len(lines) > 3:
        lines = lines[:3]
        lines[-1] = lines[-1].rstrip(".") + "…"
    line_height = 19
    center = y + node_height / 2 + 6
    first_y = center - (len(lines) - 1) * line_height / 2
    return "".join(
        f'<text x="{x + node_width / 2:.0f}" y="{first_y + index * line_height:.0f}" '
        'text-anchor="middle" font-family="system-ui, sans-serif" font-size="16" '
        f'fill="#112238">{html.escape(line)}</text>'
        for index, line in enumerate(lines)
    )


def compile_visual(
    spec: VisualSpec,
    *,
    alt_text: str,
    long_description: str,
    alt_text_zh: str | None = None,
    long_description_zh: str | None = None,
) -> CompiledVisual:
    """Compile a validated VisualSpec 1.0 object into deterministic, accessible SVG."""

    if spec.renderer not in {Renderer.DETERMINISTIC_DIAGRAM, Renderer.SVG}:
        raise ValueError("only deterministic diagram/SVG compilation is supported")
    if spec.diagram is None:
        raise ValueError("deterministic compilation requires a diagram")

    width = 1024
    node_width, node_height = 172, 72
    positions = _positions(spec.diagram)
    labels = list(
        dict.fromkeys(spec.exact_labels + spec.equations + spec.code_elements + spec.must_include)
    )
    label_top = 36.0
    label_bottom = label_top + 25 * (len(labels) - 1) if labels else 0.0
    content_top = min([y for _, y in positions.values()] + ([label_top] if labels else []))
    content_bottom = max(
        [y + node_height for _, y in positions.values()] + ([label_bottom + 12] if labels else [])
    )
    offset_y = 24 - content_top
    positions = {node_id: (x, y + offset_y) for node_id, (x, y) in positions.items()}
    height = int(min(576, max(260, round(content_bottom + offset_y + 24))))
    edges: list[str] = []
    nodes: list[str] = []

    for edge in spec.diagram.edges:
        from_x, from_y = positions[edge.from_id]
        to_x, to_y = positions[edge.to]
        x1, y1 = from_x + node_width / 2, from_y + node_height / 2
        x2, y2 = to_x + node_width / 2, to_y + node_height / 2
        edge_label = (
            f'<text x="{(x1 + x2) / 2:.0f}" y="{(y1 + y2) / 2 - 10:.0f}" '
            f'text-anchor="middle" font-family="system-ui, sans-serif" font-size="15">'
            f"{html.escape(edge.label or '')}</text>"
            if edge.label
            else ""
        )
        edges.append(
            f'<g data-from="{html.escape(edge.from_id)}" data-to="{html.escape(edge.to)}">'
            f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" '
            'stroke="#425f8b" stroke-width="2" marker-end="url(#ab-arrow)"/>'
            f"{edge_label}</g>"
        )

    for node in spec.diagram.nodes:
        x, y = positions[node.id]
        nodes.append(
            f'<g data-node-kind="{html.escape(node.kind)}">'
            f'<rect x="{x:.0f}" y="{y:.0f}" width="{node_width}" height="{node_height}" '
            f'rx="10" fill="#eaf0fb" stroke="#223c6d" stroke-width="2" '
            f'id="ab-node-{html.escape(node.id)}"/>'
            + _render_node_label(
                node.label,
                x=x,
                y=y,
                node_width=node_width,
                node_height=node_height,
            )
            + "</g>"
        )

    label_markup = "".join(
        f'<text x="512" y="{label_top + offset_y + index * 25:.0f}" text-anchor="middle" '
        f'font-family="system-ui, sans-serif" font-size="15" fill="#112238">'
        f"{html.escape(value)}</text>"
        for index, value in enumerate(labels)
    )
    title_en = html.escape(alt_text)
    desc_en = html.escape(long_description)
    title_zh = html.escape(alt_text_zh or alt_text)
    desc_zh = html.escape(long_description_zh or long_description)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        'aria-labelledby="ab-visual-title ab-visual-desc">'
        f'<title id="ab-visual-title" data-en="{title_en}" data-zh="{title_zh}">{title_en}</title>'
        f'<desc id="ab-visual-desc" data-en="{desc_en}" data-zh="{desc_zh}">{desc_en}</desc>'
        '<defs><marker id="ab-arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#425f8b"/></marker></defs>'
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>'
        f"{label_markup}{''.join(edges)}{''.join(nodes)}</svg>"
    )
    validate_output(
        svg.encode("utf-8"),
        mime_type="image/svg+xml",
        width=width,
        height=height,
        duration_seconds=None,
        max_bytes=1_000_000,
        max_width=width,
        max_height=height,
        max_duration_seconds=0,
    )
    payload = json.dumps(
        {
            "spec": spec.model_dump(mode="json", by_alias=True),
            "alt": alt_text,
            "alt_zh": alt_text_zh or alt_text,
            "desc": long_description,
            "desc_zh": long_description_zh or long_description,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return CompiledVisual(
        renderer=Renderer.SVG,
        svg=svg,
        width=width,
        height=height,
        sha256=hashlib.sha256(payload).hexdigest(),
        alt_text=alt_text,
        long_description=long_description,
    )
