const SCALE_2 = [
  [2, 0, 0],
  [0, 2, 0],
  [0, 0, 1],
];

const ROTATE_90_CCW = [
  [0, -1, 0],
  [1, 0, 0],
  [0, 0, 1],
];

const TRANSLATE_1_1 = [
  [1, 0, 1],
  [0, 1, 1],
  [0, 0, 1],
];

function outgoingNeighbours(lesson, startId) {
  const nodes = new Map(
    lesson.visual_spec.diagram.nodes.map((node) => [node.id, node]),
  );
  const adjacency = new Map(
    lesson.visual_spec.diagram.nodes.map((node) => [node.id, []]),
  );
  for (const edge of lesson.visual_spec.diagram.edges) {
    const target = nodes.get(edge.to);
    if (!target) throw new Error(`Unknown graph edge target: ${edge.to}`);
    adjacency.get(edge.from)?.push({ id: edge.to, label: target.label });
  }
  for (const neighbours of adjacency.values()) {
    neighbours.sort((a, b) =>
      a.label.localeCompare(b.label, "en", { sensitivity: "base" }),
    );
  }
  if (!adjacency.has(startId)) throw new Error(`Unknown start node: ${startId}`);
  return adjacency;
}

/** Compute BFS from graph data without consulting any quiz answer field. */
export function graphBfsOrder(lesson, startId = "a") {
  const adjacency = outgoingNeighbours(lesson, startId);
  const queue = [startId];
  const visited = new Set();
  const order = [];
  while (queue.length) {
    const current = queue.shift();
    if (visited.has(current)) continue;
    visited.add(current);
    order.push(current);
    for (const neighbour of adjacency.get(current) ?? []) {
      if (!visited.has(neighbour.id)) queue.push(neighbour.id);
    }
  }
  return order;
}

/** Compute DFS from graph data without consulting any quiz answer field. */
export function graphDfsOrder(lesson, startId = "a") {
  const adjacency = outgoingNeighbours(lesson, startId);
  const visited = new Set();
  const order = [];
  const visit = (nodeId) => {
    if (visited.has(nodeId)) return;
    visited.add(nodeId);
    order.push(nodeId);
    for (const neighbour of adjacency.get(nodeId) ?? []) visit(neighbour.id);
  };
  visit(startId);
  return order;
}

export function graphOrderLabels(lesson, mode, startId = "a") {
  const order = mode === "dfs"
    ? graphDfsOrder(lesson, startId)
    : graphBfsOrder(lesson, startId);
  const labels = new Map(
    lesson.visual_spec.diagram.nodes.map((node) => [node.id, node.label]),
  );
  return order.map((id) => labels.get(id));
}

export function multiplyMatrices(left, right) {
  return left.map((row) =>
    right[0].map((_, columnIndex) =>
      row.reduce(
        (sum, value, rowIndex) => sum + value * right[rowIndex][columnIndex],
        0,
      ),
    ),
  );
}

export function applyMatrix(matrix, vector) {
  return matrix.map((row) =>
    row.reduce((sum, value, index) => sum + value * vector[index], 0),
  );
}

function applyOperations(point, matrices) {
  const stages = [point];
  let current = point;
  for (const matrix of matrices) {
    current = applyMatrix(matrix, current);
    stages.push(current);
  }
  return stages;
}

/**
 * A deterministic worked example:
 * p=(1,0,1)^T, scale x2, rotate 90 degrees CCW, translate by (1,1).
 * Forward: T(R(S(p))) = (1,3,1).
 * Reversed execution: S(R(T(p))) = (-2,4,1).
 */
export function matrixTransformExample() {
  const point = [1, 0, 1];
  return {
    forwardStages: applyOperations(point, [
      SCALE_2,
      ROTATE_90_CCW,
      TRANSLATE_1_1,
    ]),
    reverseStages: applyOperations(point, [
      TRANSLATE_1_1,
      ROTATE_90_CCW,
      SCALE_2,
    ]),
    forwardMatrix: multiplyMatrices(
      TRANSLATE_1_1,
      multiplyMatrices(ROTATE_90_CCW, SCALE_2),
    ),
    reverseMatrix: multiplyMatrices(
      SCALE_2,
      multiplyMatrices(ROTATE_90_CCW, TRANSLATE_1_1),
    ),
  };
}

