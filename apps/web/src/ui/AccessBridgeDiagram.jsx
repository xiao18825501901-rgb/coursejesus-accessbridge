import React from "react";

import {
  graphOrderLabels,
  matrixTransformExample,
} from "../competition/lessonLogic";

function formatPoint(vector) {
  return `(${vector[0]},${vector[1]})`;
}

export function AccessBridgeDiagram({ lesson, locale, copy }) {
  if (lesson.lesson_id === "bfs-dfs") {
    const titleId = "accessbridge-bfs-title";
    const descriptionId = "accessbridge-bfs-description";
    const bfs = graphOrderLabels(lesson, "bfs").join(" → ");
    const dfs = graphOrderLabels(lesson, "dfs").join(" → ");
    return (
      <>
        <svg
          className="accessbridge-graph"
          viewBox="0 0 720 380"
          role="img"
          aria-labelledby={`${titleId} ${descriptionId}`}
        >
          <title id={titleId}>
            {locale === "en"
              ? "Five-node directed graph example"
              : "五节点有向图示例"}
          </title>
          <desc id={descriptionId}>
            {lesson.long_description[locale === "en" ? "en" : "zh"]}
          </desc>
          <defs>
            <marker
              id="ab-arrow"
              markerWidth="10"
              markerHeight="10"
              refX="8"
              refY="3"
              orient="auto"
            >
              <path d="M0,0 L0,6 L9,3 z" fill="currentColor" />
            </marker>
          </defs>
          {[
            ["A", "B", 360, 92, 205, 190],
            ["A", "C", 360, 92, 515, 190],
            ["B", "D", 205, 190, 112, 308],
            ["C", "E", 515, 190, 608, 308],
          ].map(([from, to, x1, y1, x2, y2]) => (
            <line
              key={from + to}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              className="accessbridge-edge"
              markerEnd="url(#ab-arrow)"
            />
          ))}
          {[
            ["A", 360, 55, "start"],
            ["B", 205, 150],
            ["C", 515, 150],
            ["D", 112, 268],
            ["E", 608, 268],
          ].map(([label, x, y, kind]) => (
            <g
              key={label}
              className={`accessbridge-node ${kind || ""}`}
              transform={`translate(${Number(x) - 34} ${Number(y) - 33})`}
            >
              <rect width="68" height="66" rx="18" />
              <text x="34" y="42" textAnchor="middle">
                {label}
              </text>
            </g>
          ))}
        </svg>
        <div className="accessbridge-equivalence">
          <strong>{copy.visualOrder}</strong>
          <span>{copy.bfsLabel}: {bfs}</span>
          <span>{copy.dfsLabel}: {dfs}</span>
        </div>
      </>
    );
  }

  if (lesson.lesson_id === "matrix-transform") {
    const example = matrixTransformExample();
    const forwardPoints = example.forwardStages
      .slice(1)
      .map(formatPoint)
      .join(" → ");
    const reversePoints = example.reverseStages
      .slice(1)
      .map(formatPoint)
      .join(" → ");
    return (
      <>
        <svg
          className="accessbridge-chain"
          viewBox="0 0 760 230"
          role="img"
          aria-labelledby="matrix-diagram-title matrix-diagram-description"
        >
          <title id="matrix-diagram-title">
            {locale === "en"
              ? "Homogeneous column-vector transform chain"
              : "齐次列向量变换链"}
          </title>
          <desc id="matrix-diagram-description">
            {lesson.long_description[locale === "en" ? "en" : "zh"]}
          </desc>
          <defs>
            <marker
              id="matrix-arrow"
              markerWidth="10"
              markerHeight="10"
              refX="8"
              refY="3"
              orient="auto"
            >
              <path d="M0,0 L0,6 L9,3 z" fill="currentColor" />
            </marker>
          </defs>
          {[
            ["p=(1,0,1)ᵀ", 30],
            ["S  ×2", 225],
            ["R 90° CCW", 420],
            ["T +(1,1)", 615],
          ].map(([label, x]) => (
            <g key={label} transform={`translate(${x} 62)`}>
              <rect width="130" height="80" rx="14" />
              <text x="65" y="48" textAnchor="middle">
                {label}
              </text>
            </g>
          ))}
          {[160, 355, 550].map((x) => (
            <line
              key={x}
              x1={x}
              y1="102"
              x2={x + 58}
              y2="102"
              className="accessbridge-edge"
              markerEnd="url(#matrix-arrow)"
            />
          ))}
        </svg>
        <div className="accessbridge-equivalence">
          <strong>{copy.matrixOrder}</strong>
          <span>{copy.matrixResult}: {forwardPoints}</span>
          <span>{copy.matrixReverse}: {reversePoints}</span>
        </div>
      </>
    );
  }

  return (
    <div
      className="accessbridge-stack-queue"
      role="img"
      aria-label={lesson.long_description[locale === "en" ? "en" : "zh"]}
    >
      <div>
        <strong>Stack</strong>
        <span>A</span>
        <span>B</span>
        <span>C</span>
        <b>pop → C</b>
      </div>
      <div>
        <strong>Queue</strong>
        <span>A</span>
        <span>B</span>
        <span>C</span>
        <b>dequeue → A</b>
      </div>
      <p>{copy.stackResult}</p>
    </div>
  );
}
